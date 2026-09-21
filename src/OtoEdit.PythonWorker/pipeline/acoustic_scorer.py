"""
OtoEdit Akustik Puanlama Motoru
Ses segmentlerindeki ses patlamalarını (clipping / peak saturation), mikrofondan uzak kalmayı (low RMS),
aşırı yüksekliği ve cümleler arası enerji sürekliliğini analiz ederek 0-100 arası teknik kalite puanı üretir.
"""
from typing import Dict, Any, Optional
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    pydub_mod = importlib.import_module("pydub")
    AudioSegment = pydub_mod.AudioSegment
except Exception:
    AudioSegment = None


class AcousticScorer:
    """Belirli bir zaman penceresindeki sesin teknik kalitesini puanlayan motor."""

    def __init__(self, target_sample_rate: int = 16000):
        self.sr = target_sample_rate

    def score_audio_segment(
        self,
        audio_path: str,
        start_sec: float,
        end_sec: float,
        prev_segment_rms: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Verilen ses dosyasının [start_sec, end_sec] aralığını yükler ve
        akustik metrikleri hesaplar.

        Dönen sözlük:
            - clipping_score: 0 - 100 (100 = hiç ses patlaması yok, temiz)
            - volume_score: 0 - 100 (100 = ideal konuşma seviyesi, -20 dBFS)
            - continuity_score: 0 - 100 (Önceki cümleyle enerji uyumu)
            - current_rms_db: float (Bu segmentin ortalama dBFS değeri)
            - composite_acoustic_score: 0 - 100 (Ağırlıklı akustik puan)
        """
        duration = end_sec - start_sec
        if duration <= 0.08:
            return self._empty_score()

        if not AudioSegment:
            logger.warning("pydub yüklü değil, varsayılan akustik skor dönülüyor.")
            return self._default_score()

        try:
            # Pydub ile sadece istenen segmenti al (ms bazında)
            start_ms = max(0, int(start_sec * 1000.0))
            end_ms = int(end_sec * 1000.0)

            # Dosyadan ses segmentini yükle
            ext = audio_path.split(".")[-1].lower()
            if ext == "mp3":
                audio = AudioSegment.from_mp3(audio_path)
            elif ext in ("wav", "wave"):
                audio = AudioSegment.from_wav(audio_path)
            else:
                audio = AudioSegment.from_file(audio_path)

            segment = audio[start_ms:end_ms]
            if len(segment) == 0:
                return self._empty_score()

            # Mono yap ve numpy array'e dönüştür
            mono_seg = segment.set_channels(1)
            raw_samples = mono_seg.get_array_of_samples()
            if len(raw_samples) == 0:
                return self._empty_score()

            # Normalize edilmiş [-1.0, 1.0] aralığında float dizi
            max_possible_val = float(1 << (mono_seg.sample_width * 8 - 1))
            samples = np.array(raw_samples, dtype=np.float32) / max_possible_val

            # 1. Ses Patlaması (Clipping / Saturation) Analizi
            # 0.992 üzeri tepe değerlerini kırpılma/patlama kabul ediyoruz
            peak_threshold = 0.992
            clipped_samples = np.sum(np.abs(samples) >= peak_threshold)
            clip_ratio = float(clipped_samples) / float(len(samples))

            if clip_ratio <= 0.0001:
                clipping_score = 100.0
            else:
                # %0.5'ten fazla clipping varsa puan hızla 0'a iner
                clipping_score = max(0.0, 100.0 - (clip_ratio * 20000.0))

            # 2. RMS Enerji Hesabı (dBFS)
            rms = np.sqrt(np.mean(samples**2))
            if rms < 1e-7:
                current_rms_db = -100.0
            else:
                current_rms_db = float(20.0 * np.log10(rms))

            # İdeal insan konuşması penceresi: -26 dBFS ile -14 dBFS arası
            # -35 dBFS altı fısıltı / mikrofondan uzak kalma
            # -8 dBFS üzeri aşırı yüksek / mikrofon distorsiyonu
            if -26.0 <= current_rms_db <= -14.0:
                volume_score = 100.0
            elif current_rms_db < -26.0:
                # Düşük sese ceza (-42 dBFS'de 0 puan)
                volume_score = max(0.0, 100.0 - (abs(current_rms_db - (-26.0)) * 6.25))
            else:
                # Yüksek sese ceza (-6 dBFS'de 0 puan)
                volume_score = max(0.0, 100.0 - (abs(current_rms_db - (-14.0)) * 12.5))

            # 3. Süreklilik ve Tutarlılık (Volume Continuity)
            # Konuşmacının bir önceki seçilen cümlesinin ses seviyesi ile uyumu
            continuity_score = 100.0
            if prev_segment_rms is not None and prev_segment_rms > -80.0:
                rms_diff = abs(current_rms_db - prev_segment_rms)
                # 6 dB'den fazla ani enerji farkı dinleyiciyi rahatsız eder
                continuity_score = max(0.0, 100.0 - (rms_diff * 8.0))

            # 4. Ağırlıklı Akustik Birleşik Puan
            composite_acoustic = (
                0.45 * clipping_score +
                0.35 * volume_score +
                0.20 * continuity_score
            )

            return {
                "clipping_score": round(float(clipping_score), 2),
                "volume_score": round(float(volume_score), 2),
                "continuity_score": round(float(continuity_score), 2),
                "current_rms_db": round(float(current_rms_db), 2),
                "composite_acoustic_score": round(float(composite_acoustic), 2)
            }

        except Exception as ex:
            logger.error(f"Akustik puanlama hatası [{start_sec}-{end_sec}]: {ex}", exc_info=True)
            return self._default_score()

    @staticmethod
    def _default_score() -> Dict[str, float]:
        return {
            "clipping_score": 95.0,
            "volume_score": 90.0,
            "continuity_score": 90.0,
            "current_rms_db": -20.0,
            "composite_acoustic_score": 92.5
        }

    @staticmethod
    def _empty_score() -> Dict[str, float]:
        return {
            "clipping_score": 0.0,
            "volume_score": 0.0,
            "continuity_score": 0.0,
            "current_rms_db": -100.0,
            "composite_acoustic_score": 0.0
        }
