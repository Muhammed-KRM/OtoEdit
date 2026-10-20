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

    @staticmethod
    def compute_perceptual_peaks(
        audio: np.ndarray,
        sample_rate: int,
        duration: float,
        num_peaks: int = None
    ) -> List[float]:
        """
        Sıfır zaman kaymalı (Zero-Drift), gürültü kapılı (Noise-Gated) ve
        algısal desibel (dBFS / Power-Law) ölçekli yüksek çözünürlüklü dalga formu üretir.
        """
        total_samples = len(audio)
        if total_samples == 0 or duration <= 0:
            return []

        # 1. Çözünürlük belirleme: num_peaks belirtilmemişse adaptif yüksek yoğunluk (40-80 Hz = 12.5ms-25ms)
        if num_peaks is None or num_peaks <= 0:
            if duration <= 1200.0:
                peaks_per_sec = 80  # <= 20 dk: 12.5 ms çözünürlük
            elif duration <= 3600.0:
                peaks_per_sec = 50  # 20-60 dk: 20 ms çözünürlük
            else:
                peaks_per_sec = 40  # > 60 dk: 25 ms çözünürlük
            target_peaks = max(500, int(round(duration * peaks_per_sec)))
        else:
            target_peaks = int(num_peaks)

        # 2. 10ms (100 Hz) temel akustik pencereleme (Peak + RMS hibrit enerji)
        hop_samples = max(1, int(sample_rate * 0.010))
        num_windows = total_samples // hop_samples
        if num_windows <= 0:
            return [0.0] * target_peaks

        trimmed = np.abs(audio[:num_windows * hop_samples]).reshape((num_windows, hop_samples))
        peak_env = np.max(trimmed, axis=1).astype(np.float32)
        rms_env = np.sqrt(np.mean(trimmed ** 2, axis=1)).astype(np.float32)
        hybrid_env = 0.65 * peak_env + 0.35 * rms_env

        # 3. Sıfır zaman kaymalı (Zero-Drift) kayan noktalı sınır eşlemesi
        if target_peaks >= num_windows:
            idx_map = np.linspace(0, num_windows - 1, target_peaks).astype(np.int64)
            raw_peaks = hybrid_env[idx_map]
        else:
            edges = np.linspace(0, num_windows, target_peaks + 1, dtype=np.int64)
            starts = np.clip(edges[:-1], 0, num_windows - 1)
            raw_peaks = np.maximum.reduceat(hybrid_env, starts)

        if len(raw_peaks) == 0:
            return []

        # 4. Akustik Gürültü Tabanı (Noise Floor) ve 99.2 Persentil Algısal dBFS Ölçekleme
        noise_floor = float(np.percentile(raw_peaks, 15))
        gate = max(0.0012, min(0.0080, noise_floor * 2.2))

        active = raw_peaks[raw_peaks > gate]
        if len(active) > 10:
            ref_ceiling = float(np.percentile(active, 99.2))
        else:
            ref_ceiling = float(np.max(raw_peaks))

        denom = max(1e-5, ref_ceiling - gate)
        normalized = np.clip((raw_peaks - gate) / denom, 0.0, 1.0)

        # İnsan kulağının fısıltı ve vurguları algılama eğrisi (Power-Law 0.52)
        perceptual = np.power(normalized, 0.52)
        # Gürültü kapısı altındaki tam sessizlikleri 0.0 olarak koru
        perceptual = np.where(raw_peaks <= gate, 0.0, perceptual)

        return [round(float(p), 3) for p in perceptual]

    def analyze(
        self,
        media_path: str,
        vad_threshold: float = None,
        min_silence_ms: int = None,
        num_peaks: int = None
    ) -> AudioAnalysis:
        """
        Medya dosyasını analiz eder:
        1. 16 kHz PCM çıkarımı
        2. Silero VAD (speech regions)
        3. RMS enerji zarfı (10ms adımlı)
        4. Sıfır kaymalı, yüksek çözünürlüklü algısal UI dalga formu (peaks)
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

        # 3. Yüksek Çözünürlüklü, Sıfır Kaymalı Algısal Dalga Formu (Waveform Peaks)
        peaks = self.compute_perceptual_peaks(
            audio=audio,
            sample_rate=self.sample_rate,
            duration=duration,
            num_peaks=num_peaks
        )
        logger.info(f"📊 Yüksek çözünürlüklü ses dalga formu üretildi: {len(peaks)} nokta ({len(peaks)/max(0.1, duration):.1f} Hz)")

        return AudioAnalysis(
            duration=duration,
            speech_regions=speech_regions,
            rms_envelope=rms_envelope,
            peaks=peaks,
            rms_hop_ms=10.0,
            sample_rate=self.sample_rate
        )
