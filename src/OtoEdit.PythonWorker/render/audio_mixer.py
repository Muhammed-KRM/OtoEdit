"""OtoEdit Audio Mixer & Sidechain Auto-Ducking.
Arka plan müziği (BGM), ses seviyesi dengeleme, konuşma esnasında
müziği otomatik kısan (sidechaincompress), çok kanallı SFX (ses efekti) mikseri
ve -14 LUFS yayın standardı ses normalizasyonu (loudnorm) servisi.
"""
import os
from typing import Dict, Any, Optional, List, Callable
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
        "keyboard-type": "keyboard-typing",
        "keyboard": "keyboard-typing",
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

        candidate_ids = [preset_id] if preset_id else []
        if preset_id in cls.SFX_PRESET_ALIASES:
            candidate_ids.append(cls.SFX_PRESET_ALIASES[preset_id])

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
    def mix_sfx_clips(
        cls,
        speech_audio_stream: Any,
        sfx_clips: List[Dict[str, Any]],
        temp_dir: str = "/app/temp",
        resolver_fn: Optional[Callable[..., Optional[str]]] = None
    ) -> Any:
        """
        Zaman çizgisindeki çoklu SFX (Whoosh, Pop, Ding vb.) ses kliplerini
        adelay, volume ve afade filtreleriyle ana ses akışına miksler.
        """
        if not ffmpeg or not sfx_clips:
            return speech_audio_stream

        try:
            valid_sfx_streams = []
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

                sfx_a = ffmpeg.input(local_path).audio
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

            if not valid_sfx_streams:
                return speech_audio_stream

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
