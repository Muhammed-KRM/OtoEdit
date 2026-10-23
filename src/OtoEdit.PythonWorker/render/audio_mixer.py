"""OtoEdit Audio Mixer & Sidechain Auto-Ducking.
Arka plan müziği (BGM), ses seviyesi dengeleme, konuşma esnasında
müziği otomatik kısan (sidechaincompress), çok kanallı SFX (ses efekti) mikseri
ve -14 LUFS yayın standardı ses normalizasyonu (loudnorm) servisi.
"""
import os
import shutil
import subprocess
import wave
from typing import Dict, Any, Optional, List, Callable, Tuple
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    ffmpeg = importlib.import_module("ffmpeg")
except Exception:
    ffmpeg = None


class AudioMixer:
    """CapCut ve Premiere Pro seviyesi otomatik kısılmalı (Auto-Ducking), SFX ve Loudnorm ses mikseri."""

    @classmethod
    def apply_bgm_with_ducking(
        cls,
        speech_audio_stream: Any,
        bgm_file_path: str,
        total_duration: float,
        volume: float = 0.25,
        auto_ducking: bool = True,
        ducking_amount: float = 0.15,
        fade_in_sec: float = 1.0,
        fade_out_sec: float = 2.0
    ) -> Any:
        """
        Konuşma ses akışı ile arka plan müziğini birleştirir.
        auto_ducking=True ise konuşma başladığında müzik otomatik olarak kısılır (sidechain compression).
        """
        if not ffmpeg or not bgm_file_path or not os.path.isfile(bgm_file_path):
            logger.warning(f"AudioMixer atlanıyor: ffmpeg={bool(ffmpeg)}, dosya={bgm_file_path}")
            return speech_audio_stream

        try:
            # 1. BGM Girişi ve Döngü (aloop)
            bgm_input = ffmpeg.input(bgm_file_path)
            bgm_a = bgm_input.audio.filter("aloop", loop=-1, size=2147483647)
            bgm_a = bgm_a.filter("volume", volume)

            # Fade In & Fade Out
            if fade_in_sec > 0:
                bgm_a = bgm_a.filter("afade", type="in", start_time=0, duration=fade_in_sec)
            if fade_out_sec > 0 and total_duration > fade_out_sec:
                fade_start = max(0, total_duration - fade_out_sec)
                bgm_a = bgm_a.filter("afade", type="out", start_time=fade_start, duration=fade_out_sec)

            if auto_ducking:
                threshold = max(0.02, min(0.25, ducking_amount * 0.6))
                ducked_bgm = ffmpeg.filter(
                    [bgm_a, speech_audio_stream],
                    "sidechaincompress",
                    threshold=threshold,
                    ratio=5,
                    attack=150,
                    release=650
                )
                mixed_audio = ffmpeg.filter(
                    [speech_audio_stream, ducked_bgm],
                    "amix",
                    inputs=2,
                    duration="first",
                    dropout_transition=2,
                    normalize=0,
                )
                logger.info(f"🎧 AudioMixer: Auto-Ducking başarıyla uygulandı (vol={volume}, thresh={threshold})")
                return mixed_audio
            else:
                mixed_audio = ffmpeg.filter(
                    [speech_audio_stream, bgm_a],
                    "amix",
                    inputs=2,
                    duration="first",
                    dropout_transition=2,
                    normalize=0,
                )
                logger.info(f"🎧 AudioMixer: BGM başarıyla eklendi (vol={volume}, ducking=False)")
                return mixed_audio

        except Exception as ex:
            logger.error(f"AudioMixer hatası: {ex}, orijinal ses akışı korunuyor")
            return speech_audio_stream

    SFX_PRESET_ALIASES: Dict[str, str] = {
        "keyboard-type": "keyboard-type",
        "keyboard": "keyboard-type",
        "ding": "ding-bright",
        "pop": "pop-bubble",
        "whoosh": "capcut-swish-large",
        "whoosh-fast": "capcut-swish-large",
        "swish": "capcut-swish-large",
        "capcut-swish-large": "capcut-swish-large",
    }

    @classmethod
    def _resolve_local_sfx_asset(cls, clip: Dict[str, Any], raw_source: str) -> Optional[str]:
        """
        Yerel assets/sfx/ dizinindeki gerçek stüdyo SFX dosyalarını (.wav / .ogg)
        presetId, synthPreset veya /assets/sfx/ yoluna göre öncelikli olarak çözer.
        """
        sfx_assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "sfx"))
        if not os.path.isdir(sfx_assets_dir):
            return None

        preset_id = str(clip.get("presetId") or clip.get("synthPreset") or "").strip()
        if not preset_id and raw_source.startswith("sfx://"):
            preset_id = raw_source.replace("sfx://", "").strip("/")

        candidate_ids: List[str] = []
        if preset_id in cls.SFX_PRESET_ALIASES:
            candidate_ids.append(cls.SFX_PRESET_ALIASES[preset_id])
        if preset_id and preset_id not in candidate_ids:
            candidate_ids.append(preset_id)

        for cid in candidate_ids:
            for ext in (".wav", ".ogg", ""):
                cand = os.path.join(sfx_assets_dir, f"{cid}{ext}")
                if os.path.isfile(cand):
                    return cand

        clean_src = raw_source.split("?")[0].replace("\\", "/")
        if clean_src.startswith("/assets/sfx/") or clean_src.startswith("assets/sfx/"):
            rel_name = clean_src.split("assets/sfx/", 1)[-1].lstrip("/")
            if rel_name:
                cand = os.path.join(sfx_assets_dir, rel_name)
                if os.path.isfile(cand):
                    return cand
                base_no_ext = os.path.splitext(rel_name)[0]
                for ext in (".wav", ".ogg"):
                    cand_ext = os.path.join(sfx_assets_dir, f"{base_no_ext}{ext}")
                    if os.path.isfile(cand_ext):
                        return cand_ext

        return None

    @classmethod
    def _decode_audio_to_pcm(cls, local_path: str, sample_rate: int = 44100) -> Optional[np.ndarray]:
        """Ses dosyasını 44.1kHz stereo float32 (-1.0..1.0) numpy dizisine decode eder."""
        try:
            cmd = [
                "ffmpeg", "-v", "error",
                "-i", local_path,
                "-f", "s16le", "-acodec", "pcm_s16le",
                "-ac", "2", "-ar", str(sample_rate),
                "-"
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=30)
            if res.returncode != 0 or not res.stdout:
                return None
            pcm_i16 = np.frombuffer(res.stdout, dtype=np.int16)
            if pcm_i16.size < 2:
                return None
            if pcm_i16.size % 2 != 0:
                pcm_i16 = pcm_i16[:-1]
            return pcm_i16.reshape(-1, 2).astype(np.float32) / 32768.0
        except Exception as ex:
            logger.debug(f"PCM decode uyarısı ({local_path}): {ex}")
            return None

    @classmethod
    def _premix_sfx_to_master_wav(
        cls,
        resolved_specs: List[Dict[str, Any]],
        temp_dir: str,
        sample_rate: int = 44100
    ) -> Optional[str]:
        """
        Tüm SFX kliplerini tek bir master stereo WAV dosyasında birleştirir.
        Böylece FFmpeg filtergraph'ta 140+ ayrı input ve duplicate FilterNode çakışması oluşmaz.
        """
        if not resolved_specs:
            return None

        pcm_cache: Dict[str, np.ndarray] = {}
        prepared_clips: List[Tuple[int, np.ndarray]] = []
        max_end_sample = 0

        for spec in resolved_specs:
            local_path = spec["local_path"]
            if local_path not in pcm_cache:
                decoded = cls._decode_audio_to_pcm(local_path, sample_rate=sample_rate)
                if decoded is None:
                    continue
                pcm_cache[local_path] = decoded

            base_pcm = pcm_cache[local_path]
            total_frames = base_pcm.shape[0]
            if total_frames == 0:
                continue

            trim_start = spec["trim_start"]
            duration = spec["duration"]
            volume = spec["volume"]
            fade_in = spec["fade_in"]
            fade_out = spec["fade_out"]
            start_sec = spec["start_sec"]

            s_frame = min(total_frames, max(0, int(round(trim_start * sample_rate))))
            if duration > 0:
                e_frame = min(total_frames, s_frame + int(round(duration * sample_rate)))
            else:
                e_frame = total_frames

            if e_frame <= s_frame:
                continue

            clip_pcm = base_pcm[s_frame:e_frame].copy() * float(volume)
            clip_len = clip_pcm.shape[0]

            if fade_in > 0:
                fi_samples = min(clip_len, int(round(fade_in * sample_rate)))
                if fi_samples > 1:
                    env_in = np.linspace(0.0, 1.0, fi_samples, dtype=np.float32)[:, None]
                    clip_pcm[:fi_samples] *= env_in

            if fade_out > 0:
                fo_samples = min(clip_len, int(round(fade_out * sample_rate)))
                if fo_samples > 1:
                    env_out = np.linspace(1.0, 0.0, fo_samples, dtype=np.float32)[:, None]
                    clip_pcm[-fo_samples:] *= env_out

            dest_start = max(0, int(round(start_sec * sample_rate)))
            dest_end = dest_start + clip_len
            if dest_end > max_end_sample:
                max_end_sample = dest_end
            prepared_clips.append((dest_start, clip_pcm))

        if not prepared_clips or max_end_sample <= 0:
            return None

        master_buf = np.zeros((max_end_sample, 2), dtype=np.float32)
        for dest_start, clip_pcm in prepared_clips:
            dest_end = dest_start + clip_pcm.shape[0]
            master_buf[dest_start:dest_end] += clip_pcm

        np.clip(master_buf, -1.0, 1.0, out=master_buf)
        master_i16 = (master_buf * 32767.0).astype(np.int16)

        os.makedirs(temp_dir, exist_ok=True)
        master_wav_path = os.path.join(temp_dir, "sfx_master_premix.wav")
        with wave.open(master_wav_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(master_i16.tobytes())

        return master_wav_path if os.path.isfile(master_wav_path) else None

    @classmethod
    def mix_sfx_clips(
        cls,
        speech_audio_stream: Any,
        sfx_clips: List[Dict[str, Any]],
        temp_dir: str = "/app/temp",
        resolver_fn: Optional[Callable[..., Optional[str]]] = None
    ) -> Any:
        """
        Zaman çizgisindeki çoklu SFX (Whoosh, Pop, Ding vb.) ses kliplerini
        tek bir master WAV katmanında birleştirerek ana ses akışına miksler.
        """
        if not ffmpeg or not sfx_clips:
            return speech_audio_stream

        try:
            resolved_specs: List[Dict[str, Any]] = []
            for clip in sfx_clips:
                if not isinstance(clip, dict):
                    continue

                raw_source = str(clip.get("sourceUrl") or clip.get("source") or clip.get("url") or "").strip()

                # 1. Önce yerel assets/sfx/ dizinini kontrol et
                local_path = cls._resolve_local_sfx_asset(clip, raw_source)

                # 2. Yerel assets/sfx/ içinde bulunamadıysa mevcut resolver veya dosya kontrolüne geç
                if not local_path:
                    if not raw_source:
                        continue
                    if os.path.isfile(raw_source):
                        local_path = raw_source
                    elif resolver_fn is not None:
                        try:
                            local_path = resolver_fn(raw_source, temp_dir=temp_dir)
                        except TypeError:
                            local_path = resolver_fn(raw_source)

                if not local_path or not os.path.isfile(local_path):
                    logger.warning(f"SFX ses dosyası bulunamadı, atlanıyor: {raw_source or clip.get('presetId')}")
                    continue

                start_sec = float(
                    clip.get("start") if clip.get("start") is not None else clip.get("timestamp", 0.0)
                )
                start_sec = max(0.0, start_sec)
                duration = float(clip.get("duration") or 0.0)
                trim_start = max(0.0, float(clip.get("trimStart") or clip.get("trim_start") or 0.0))
                raw_vol = float(clip.get("volume") if clip.get("volume") is not None else 0.8)
                # Eğer volume 0..100 yüzdelik olarak geldiyse (örn. video overlay volume=100) 0.0..1.0 aralığına çevir
                volume = (raw_vol / 100.0) if raw_vol > 1.5 else raw_vol
                if volume <= 0.005:
                    continue
                fade_in = float(clip.get("fadeIn") or 0.0)
                fade_out = float(clip.get("fadeOut") or 0.0)

                # Eğer dosya bir video katmanıysa ve içinde ses kanalı (audio stream) yoksa güvenle atla
                if local_path.lower().endswith((".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")):
                    try:
                        probe_info = ffmpeg.probe(local_path)
                        has_audio_track = any(s.get("codec_type") == "audio" for s in probe_info.get("streams", []))
                        if not has_audio_track:
                            continue
                    except Exception:
                        pass

                resolved_specs.append({
                    "local_path": local_path,
                    "start_sec": start_sec,
                    "duration": duration,
                    "trim_start": trim_start,
                    "volume": volume,
                    "fade_in": fade_in,
                    "fade_out": fade_out,
                })

            if not resolved_specs:
                return speech_audio_stream

            # Hızlı ve sıfır-çakışmalı NumPy Master WAV ön-miksajı
            master_wav = cls._premix_sfx_to_master_wav(resolved_specs, temp_dir=temp_dir)
            if master_wav and os.path.isfile(master_wav):
                sfx_master_stream = ffmpeg.input(master_wav).audio
                mixed = ffmpeg.filter(
                    [speech_audio_stream, sfx_master_stream],
                    "amix",
                    inputs=2,
                    duration="first",
                    dropout_transition=0,
                    normalize=0,
                )
                logger.info(f"🔊 AudioMixer: {len(resolved_specs)} SFX klibi tek master kanalda başarıyla mikslendi.")
                return mixed

            # Fallback: Her SFX klibi için benzersiz dosya yolu oluşturarak ffmpeg-python DAG çakışmasını önle
            valid_sfx_streams = []
            os.makedirs(temp_dir, exist_ok=True)
            for idx, spec in enumerate(resolved_specs):
                src_path = spec["local_path"]
                ext = os.path.splitext(src_path)[1] or ".wav"
                unique_path = os.path.join(temp_dir, f"_sfx_node_{idx:04d}{ext}")
                if not os.path.exists(unique_path):
                    try:
                        os.symlink(os.path.abspath(src_path), unique_path)
                    except Exception:
                        shutil.copyfile(src_path, unique_path)

                sfx_a = ffmpeg.input(unique_path).audio
                trim_start = spec["trim_start"]
                duration = spec["duration"]
                volume = spec["volume"]
                fade_in = spec["fade_in"]
                fade_out = spec["fade_out"]
                start_sec = spec["start_sec"]

                if trim_start > 0 and duration > 0:
                    sfx_a = sfx_a.filter("atrim", start=trim_start, duration=duration).filter("asetpts", "PTS-STARTPTS")
                elif trim_start > 0:
                    sfx_a = sfx_a.filter("atrim", start=trim_start).filter("asetpts", "PTS-STARTPTS")
                elif duration > 0:
                    sfx_a = sfx_a.filter("atrim", duration=duration).filter("asetpts", "PTS-STARTPTS")

                sfx_a = sfx_a.filter("volume", volume)

                if fade_in > 0:
                    sfx_a = sfx_a.filter("afade", type="in", start_time=0, duration=fade_in)
                if fade_out > 0 and duration > fade_out:
                    sfx_a = sfx_a.filter("afade", type="out", start_time=max(0.0, duration - fade_out), duration=fade_out)

                delay_ms = int(round(start_sec * 1000))
                if delay_ms > 0:
                    sfx_a = sfx_a.filter("adelay", f"{delay_ms}|{delay_ms}")

                valid_sfx_streams.append(sfx_a)

            all_streams = [speech_audio_stream] + valid_sfx_streams
            mixed = ffmpeg.filter(
                all_streams,
                "amix",
                inputs=len(all_streams),
                duration="first",
                dropout_transition=0,
                normalize=0,
            )
            logger.info(f"🔊 AudioMixer: {len(valid_sfx_streams)} SFX klibi başarıyla mikslendi.")
            return mixed

        except Exception as ex:
            logger.error(f"SFX miksleme hatası: {ex}, mevcut ses akışı korunuyor")
            return speech_audio_stream

    @classmethod
    def apply_loudnorm(
        cls,
        audio_stream: Any,
        target_i: float = -14.0,
        target_tp: float = -1.5,
        target_lra: float = 11.0
    ) -> Any:
        """
        Yayın standardı (-14 LUFS) ses yüksekliği normalizasyonunu (FFmpeg loudnorm) uygular.
        """
        if not ffmpeg or audio_stream is None:
            return audio_stream

        try:
            if hasattr(audio_stream, "filter"):
                normalized = audio_stream.filter("loudnorm", I=target_i, TP=target_tp, LRA=target_lra)
            else:
                normalized = ffmpeg.filter(audio_stream, "loudnorm", I=target_i, TP=target_tp, LRA=target_lra)
            logger.info(f"🎚️ AudioMixer: Loudnorm uygulandı (I={target_i} LUFS, TP={target_tp} dBTP, LRA={target_lra})")
            return normalized
        except Exception as ex:
            logger.error(f"Loudnorm uygulama hatası: {ex}")
            return audio_stream
