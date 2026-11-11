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
    pcm_samples: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32), repr=False)

    def find_speech_region_for_word(self, word_start: float, word_end: float) -> SpeechRegion:
        """Verilen kelime zaman aralığını kapsayan veya en çok örtüşen VAD konuşma adasını döner."""
        best_reg = None
        best_ov = 0.0
        for reg in self.speech_regions:
            ov = min(word_end, reg.end) - max(word_start, reg.start)
            if ov > best_ov:
                best_ov = ov
                best_reg = reg
        return best_reg

    def _extract_onset_mfcc(self, onset_sec: float, window_sec: float = 0.68) -> np.ndarray:
        """
        Belirtilen başlangıç saniyesinden itibaren ilk aktif konuşma zarfının (window_sec)
        normalize Log-Mel + MFCC öznitelik matrisini (T x D) çıkarır.
        """
        if self.pcm_samples is None or len(self.pcm_samples) == 0:
            return np.zeros((0, 0), dtype=np.float32)

        sr = self.sample_rate
        s_idx = max(0, int((onset_sec - 0.04) * sr))
        e_idx = min(len(self.pcm_samples), int((onset_sec + window_sec + 0.15) * sr))
        if e_idx - s_idx < int(0.18 * sr):
            return np.zeros((0, 0), dtype=np.float32)

        seg = self.pcm_samples[s_idx:e_idx].astype(np.float32)
        # Ön-vurgu (Pre-emphasis: y[n] = x[n] - 0.97 * x[n-1])
        seg = np.append(seg[0], seg[1:] - 0.97 * seg[:-1])

        win_len = int(0.025 * sr)  # 400 sample (25ms)
        hop_len = int(0.010 * sr)  # 160 sample (10ms)
        if len(seg) < win_len:
            return np.zeros((0, 0), dtype=np.float32)

        num_frames = 1 + (len(seg) - win_len) // hop_len
        frames = np.lib.stride_tricks.as_strided(
            seg,
            shape=(num_frames, win_len),
            strides=(seg.strides[0] * hop_len, seg.strides[0]),
        ).copy()

        # Enerji kapısı ile gerçek ses başlangıcını (active voice onset) bul
        frame_rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-10)
        peak_rms = float(np.max(frame_rms)) if len(frame_rms) > 0 else 0.0
        if peak_rms < 1e-4:
            return np.zeros((0, 0), dtype=np.float32)

        active_idx = np.where(frame_rms >= max(0.002, peak_rms * 0.14))[0]
        if len(active_idx) > 0:
            first_active = max(0, int(active_idx[0]) - 1)
            max_frames = int(window_sec / 0.010)
            frames = frames[first_active: first_active + max_frames]

        if len(frames) < 10:
            return np.zeros((0, 0), dtype=np.float32)

        hann = np.hanning(win_len).astype(np.float32)
        spec = np.abs(np.fft.rfft(frames * hann, n=512, axis=1)) ** 2  # (T, 257)

        # 24 Mel filtresi (80 Hz - 7600 Hz)
        n_mels = 24
        freqs = np.linspace(0.0, sr / 2.0, 257)
        mel_min = 2595.0 * np.log10(1.0 + 80.0 / 700.0)
        mel_max = 2595.0 * np.log10(1.0 + 7600.0 / 700.0)
        mel_pts = np.linspace(mel_min, mel_max, n_mels + 2)
        hz_pts = 700.0 * (10.0 ** (mel_pts / 2595.0) - 1.0)

        fb = np.zeros((n_mels, 257), dtype=np.float32)
        for m in range(1, n_mels + 1):
            f_left, f_center, f_right = hz_pts[m - 1], hz_pts[m], hz_pts[m + 1]
            left_slope = (freqs - f_left) / max(1e-5, f_center - f_left)
            right_slope = (f_right - freqs) / max(1e-5, f_right - f_center)
            fb[m - 1] = np.maximum(0.0, np.minimum(left_slope, right_slope))

        mel_energy = np.dot(spec, fb.T)
        log_mel = np.log(np.maximum(mel_energy, 1e-8))

        # Kanal/kazanç bağımsızlığı için Cepstral Mean Normalization (CMN) ve çerçeve L2 normalizasyonu
        log_mel = log_mel - np.mean(log_mel, axis=1, keepdims=True)
        norms = np.linalg.norm(log_mel, axis=1, keepdims=True)
        feats = log_mel / np.maximum(norms, 1e-6)
        return feats.astype(np.float32)

    def compute_onset_similarity(self, t1: float, t2: float, window_sec: float = 0.68) -> float:
        """
        İki konuşma adasının başlangıç sesleri (t1 ve t2) arasındaki akustik
        Log-Mel / MFCC + DTW (Dynamic Time Warping) benzerliğini [0.0, 1.0] aralığında hesaplar.
        STT tekrarlanan kelimeyi yutsa bile aynı kelimeyle başlayan adalarda yüksek skor üretir.
        """
        f1 = self._extract_onset_mfcc(t1, window_sec=window_sec)
        f2 = self._extract_onset_mfcc(t2, window_sec=window_sec)
        if f1.size == 0 or f2.size == 0:
            return 0.0

        n, m = len(f1), len(f2)
        k_len = min(n, m)
        if k_len < 10:
            return 0.0
        f1 = f1[:k_len]
        f2 = f2[:k_len]

        # Kosinüs mesafe matrisi: D[i, j] = 1 - cos(f1[i], f2[j]) in [0, 2]
        sim_matrix = np.clip(np.dot(f1, f2.T), -1.0, 1.0)
        cost_matrix = 1.0 - sim_matrix

        # Sakoe-Chiba bantlı (±12 çerçeve = ±120ms) DTW
        band = max(8, int(k_len * 0.22))
        dp = np.full((k_len, k_len), 1e9, dtype=np.float32)
        dp[0, 0] = cost_matrix[0, 0]

        for i in range(k_len):
            j_start = max(0, i - band)
            j_end = min(k_len, i + band + 1)
            for j in range(j_start, j_end):
                if i == 0 and j == 0:
                    continue
                c = cost_matrix[i, j]
                prev_best = 1e9
                if i > 0:
                    prev_best = min(prev_best, dp[i - 1, j])
                if j > 0:
                    prev_best = min(prev_best, dp[i, j - 1])
                if i > 0 and j > 0:
                    prev_best = min(prev_best, dp[i - 1, j - 1])
                dp[i, j] = c + prev_best

        avg_dtw_cost = float(dp[k_len - 1, k_len - 1]) / float(2 * k_len)
        dtw_sim = max(0.0, min(1.0, 1.0 - avg_dtw_cost))
        return round(dtw_sim, 4)

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
            sample_rate=self.sample_rate,
            pcm_samples=audio,
        )
