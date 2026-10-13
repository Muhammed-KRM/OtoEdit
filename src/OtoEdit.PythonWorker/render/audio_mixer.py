"""OtoEdit Audio Mixer & Sidechain Auto-Ducking.
Arka plan müziği (BGM), ses seviyesi dengeleme ve konuşma esnasında
müziği otomatik kısan (sidechaincompress) profesyonel ses mikseri.
"""
import os
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    ffmpeg = importlib.import_module("ffmpeg")
except Exception:
    ffmpeg = None


class AudioMixer:
    """CapCut ve Premiere Pro seviyesi otomatik kısılmalı (Auto-Ducking) ses mikseri."""

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
        if not ffmpeg or not os.path.isfile(bgm_file_path):
            logger.warning(f"AudioMixer atlanıyor: ffmpeg={bool(ffmpeg)}, dosya={bgm_file_path}")
            return speech_audio_stream

        try:
            # 1. BGM Girişi ve Döngü (aloop)
            bgm_input = ffmpeg.input(bgm_file_path)
            # Sınırsız döngü (aloop=-1) ve ses seviyesi
            bgm_a = bgm_input.audio.filter("aloop", loop=-1, size=2147483647)
            bgm_a = bgm_a.filter("volume", volume)

            # Fade In & Fade Out
            if fade_in_sec > 0:
                bgm_a = bgm_a.filter("afade", type="in", start_time=0, duration=fade_in_sec)
            if fade_out_sec > 0 and total_duration > fade_out_sec:
                fade_start = max(0, total_duration - fade_out_sec)
                bgm_a = bgm_a.filter("afade", type="out", start_time=fade_start, duration=fade_out_sec)

            if auto_ducking:
                # 2. Sidechain Compression (Konuşma gelince BGM kısılır)
                # threshold: tetiklenme hassasiyeti (0.05-0.15)
                # ratio: kısılma oranı (4:1 - 8:1)
                # attack: kısılmaya başlama süresi (150ms)
                # release: konuşma bitince eski seviyeye dönme süresi (600ms)
                threshold = max(0.02, min(0.25, ducking_amount * 0.6))
                ducked_bgm = ffmpeg.filter(
                    [bgm_a, speech_audio_stream],
                    "sidechaincompress",
                    threshold=threshold,
                    ratio=5,
                    attack=150,
                    release=650
                )
                # 3. Konuşma + Kısılmış BGM Miksi
                mixed_audio = ffmpeg.filter(
                    [speech_audio_stream, ducked_bgm],
                    "amix",
                    inputs=2,
                    duration="first",
                    dropout_transition=2
                )
                logger.info(f"🎧 AudioMixer: Auto-Ducking başarıyla uygulandı (vol={volume}, thresh={threshold})")
                return mixed_audio
            else:
                # Standart amix (Ducking olmadan)
                mixed_audio = ffmpeg.filter(
                    [speech_audio_stream, bgm_a],
                    "amix",
                    inputs=2,
                    duration="first",
                    dropout_transition=2
                )
                logger.info(f"🎧 AudioMixer: BGM başarıyla eklendi (vol={volume}, ducking=False)")
                return mixed_audio

        except Exception as ex:
            logger.error(f"AudioMixer hatası: {ex}, orijinal ses akışı korunuyor")
            return speech_audio_stream
