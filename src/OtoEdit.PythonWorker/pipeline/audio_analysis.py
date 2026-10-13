"""
OtoEdit Audio Analysis Modülü
Orijinal videodan tek seferde 16 kHz mono PCM çıkarır,
Silero VAD ile konuşma bölgelerini ve 10 ms pencerelik RMS enerji zarfını hesaplar.
Tüm alt modüller (STT Chunker, JumpCut v2, Waveform Peaks) bu tek analizden beslenir.
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple
import numpy as np

from utils.logger import get_logger
from config import Config

logger = get_logger("AudioAnalysis")


@dataclass
class SpeechRegion:
    start: float  # saniye
    end: float    # saniye

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class AudioAnalysis:
    duration: float
    speech_regions: List[SpeechRegion]
    rms_envelope: np.ndarray  # 10ms adımlı RMS (100 Hz)
    peaks: List[float] = field(default_factory=list)  # UI için normalize dalga formu (1000 nokta)
    rms_hop_ms: float = 10.0
    sample_rate: int = 16000

    def get_rms_at(self, time_sec: float) -> float:
        """Belirtilen saniyedeki RMS enerji değerini döner."""
        if len(self.rms_envelope) == 0:
            return 0.0
        idx = int(round(time_sec / (self.rms_hop_ms / 1000.0)))
        idx = max(0, min(idx, len(self.rms_envelope) - 1))
        return float(self.rms_envelope[idx])

    def find_energy_minimum(
        self,
        center_sec: float,
        search_window_sec: float = 0.05,
        direction: str = "both"
    ) -> float:
        """
        center_sec etrafında RMS enerjisinin en düşük olduğu saniyeyi döner (tık/patlama seslerini önler).
        direction:
          - 'both': ±search_window_sec aralığı
          - 'backward_only': [center - search_window, center] (Kesim bitişi: konuşmaya taşmayı önler)
          - 'forward_only': [center, center + search_window] (Kesim başlangıcı: konuşmaya taşmayı önler)
        """
        if len(self.rms_envelope) == 0:
            return center_sec

        hop_sec = self.rms_hop_ms / 1000.0
        if direction == "backward_only":
            min_sec = max(0.0, center_sec - search_window_sec)
            max_sec = min(self.duration, center_sec)
        elif direction == "forward_only":
            min_sec = max(0.0, center_sec)
            max_sec = min(self.duration, center_sec + search_window_sec)
        else:
            min_sec = max(0.0, center_sec - search_window_sec)
            max_sec = min(self.duration, center_sec + search_window_sec)

        start_idx = max(0, int(min_sec / hop_sec))
        end_idx = min(len(self.rms_envelope), int(max_sec / hop_sec) + 1)

        if start_idx >= end_idx:
            return center_sec

        slice_rms = self.rms_envelope[start_idx:end_idx]
        min_local_idx = int(np.argmin(slice_rms))
        best_idx = start_idx + min_local_idx
        return float(best_idx * hop_sec)

    def get_silence_regions(self, min_silence_sec: float = 0.0) -> List[Tuple[float, float]]:
        """Konuşma bölgeleri arasındaki boşluklardan sessizlik aralıklarını çıkarır."""
        silences: List[Tuple[float, float]] = []
        last_end = 0.0

        for region in sorted(self.speech_regions, key=lambda r: r.start):
            if region.start > last_end:
                gap = region.start - last_end
                if gap >= min_silence_sec:
                    silences.append((last_end, region.start))
            last_end = max(last_end, region.end)

        if self.duration > last_end:
            gap = self.duration - last_end
            if gap >= min_silence_sec:
                silences.append((last_end, self.duration))

        return silences


class AudioAnalyzer:
    """Tek kaynak ses analizi sınıfı."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def extract_pcm(self, media_path: str) -> np.ndarray:
        """FFmpeg pipe ile videodan/sesten 16 kHz mono float32 PCM çıkarır."""
        if not os.path.exists(media_path):
            raise FileNotFoundError(f"Medya dosyası bulunamadı: {media_path}")

        cmd = [
            "ffmpeg",
            "-v", "error",
            "-i", media_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate),
            "-ac", "1",
            "-f", "s16le",
            "-"
        ]

        logger.info(f"🎙️ FFmpeg ile ses çıkarılıyor (16kHz mono): {os.path.basename(media_path)}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        raw_bytes = proc.stdout

        if len(raw_bytes) == 0:
            logger.warning(f"⚠️ Ses akışı boş döndü: {media_path}")
            return np.zeros(0, dtype=np.float32)

        audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        return audio_float32

    def analyze(
        self,
        media_path: str,
        vad_threshold: float = None,
        min_silence_ms: int = None,
        num_peaks: int = 1000
    ) -> AudioAnalysis:
        """
        Medya dosyasını analiz eder:
        1. 16 kHz PCM çıkarımı
        2. Silero VAD (speech regions)
        3. RMS enerji zarfı (10ms adımlı)
        4. Normalize UI dalga formu (num_peaks)
        """
        threshold = vad_threshold if vad_threshold is not None else Config.VAD_THRESHOLD
        min_silence = min_silence_ms if min_silence_ms is not None else Config.VAD_MIN_SILENCE_MS

        audio = self.extract_pcm(media_path)
        total_samples = len(audio)
        duration = total_samples / float(self.sample_rate)

        if total_samples == 0:
            return AudioAnalysis(duration=0.0, speech_regions=[], rms_envelope=np.zeros(0), peaks=[])

        # 1. Silero VAD ile konuşma bölgelerini bul
        from faster_whisper.vad import get_speech_timestamps, VadOptions

        vad_options = VadOptions(
            threshold=threshold,
            min_silence_duration_ms=min_silence,
            speech_pad_ms=150  # 🎯 Başlangıç ünsüzlerini ve nefes ataklarını yakalamak için 150ms koruma payı
        )

        vad_raw = get_speech_timestamps(
            audio,
            vad_options=vad_options,
            sampling_rate=self.sample_rate
        )

        speech_regions: List[SpeechRegion] = []
        for seg in vad_raw:
            s_sec = round(seg["start"] / float(self.sample_rate), 4)
            e_sec = round(seg["end"] / float(self.sample_rate), 4)
            if e_sec > s_sec:
                speech_regions.append(SpeechRegion(start=s_sec, end=e_sec))

        total_speech_sec = sum(r.duration for r in speech_regions)
        logger.info(
            f"🗣️ VAD Tamamlandı: Süre={duration:.1f}s | "
            f"Konuşma={total_speech_sec:.1f}s (%{100*total_speech_sec/max(0.1, duration):.1f}) | "
            f"Bölge Sayısı={len(speech_regions)}"
        )

        # 2. 10 ms pencerelik RMS enerji zarfı (hop = 10ms = 160 sample)
        hop_samples = int(self.sample_rate * 0.010)  # 160
        num_windows = total_samples // hop_samples
        if num_windows > 0:
            trimmed = audio[:num_windows * hop_samples].reshape((num_windows, hop_samples))
            rms_envelope = np.sqrt(np.mean(trimmed ** 2, axis=1)).astype(np.float32)
        else:
            rms_envelope = np.zeros(0, dtype=np.float32)

        # 3. Waveform Peaks (UI için num_peaks adet normalize tepe)
        peaks: List[float] = []
        if len(rms_envelope) > 0 and num_peaks > 0:
            chunk_size = max(1, len(rms_envelope) // num_peaks)
            for i in range(num_peaks):
                chunk = rms_envelope[i * chunk_size : (i + 1) * chunk_size]
                if len(chunk) > 0:
                    peaks.append(float(np.max(chunk)))
                else:
                    peaks.append(0.0)
            max_p = max(peaks) if peaks and max(peaks) > 0 else 1.0
            peaks = [round(p / max_p, 4) for p in peaks]

        return AudioAnalysis(
            duration=duration,
            speech_regions=speech_regions,
            rms_envelope=rms_envelope,
            peaks=peaks,
            rms_hop_ms=10.0,
            sample_rate=self.sample_rate
        )
