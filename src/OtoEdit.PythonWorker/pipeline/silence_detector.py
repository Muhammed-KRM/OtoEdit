from pathlib import Path
from typing import List
from config import Config
from models.edl_model import CutItem
from utils.logger import get_logger

logger = get_logger(__name__)


class SilenceDetector:
    """Videodaki veya sesteki uzun sessizlikleri (jump-cut) tespit eden motor."""

    def __init__(self, min_silence_len: int = 0, silence_thresh: int = 0, padding_sec: float = 0.1, min_keep_duration_sec: float = 0.35):
        self.min_silence_len = min_silence_len or Config.SILENCE_MIN_LEN_MS
        self.silence_thresh = silence_thresh or Config.SILENCE_THRESH_DBFS
        self.padding_sec = padding_sec  # Kelime başı/sonu kırpılmasını önleyen güvenlik marjı (100ms)
        self.min_keep_duration_sec = min_keep_duration_sec

    def detect(self, audio_path: str) -> List[CutItem]:
        """Ses dosyasındaki sessizlik aralıklarını bularak CutItem listesi döner."""
        logger.info(f"Sessizlik algılama başlıyor: {audio_path} (eşik={self.silence_thresh}dBFS, min={self.min_silence_len}ms)")
        cuts = []

        try:
            import importlib
            pydub_mod = importlib.import_module("pydub")
            pydub_silence = importlib.import_module("pydub.silence")
            AudioSegment = pydub_mod.AudioSegment
            detect_silence = pydub_silence.detect_silence

            ext = Path(audio_path).suffix.lower()
            if ext == ".mp3":
                audio = AudioSegment.from_mp3(audio_path)
            elif ext in (".wav", ".wave"):
                audio = AudioSegment.from_wav(audio_path)
            else:
                audio = AudioSegment.from_file(audio_path)

            # Sessiz aralıklar [(start_ms, end_ms), ...] döner
            silent_ranges_ms = detect_silence(
                audio,
                min_silence_len=self.min_silence_len,
                silence_thresh=self.silence_thresh
            )

            # Kısa sesleri yoksayma (Merge silences if gap < min_keep_duration_ms)
            min_keep_ms = self.min_keep_duration_sec * 1000.0
            merged_silences = []
            for current in silent_ranges_ms:
                if not merged_silences:
                    merged_silences.append(current)
                else:
                    prev = merged_silences[-1]
                    gap = current[0] - prev[1]
                    if gap < min_keep_ms:
                        # Gap is too small, merge the silences (i.e. cut out the short noise too)
                        merged_silences[-1] = (prev[0], current[1])
                    else:
                        merged_silences.append(current)

            for idx, (start_ms, end_ms) in enumerate(merged_silences, start=1):
                start_sec = max(0.0, (start_ms / 1000.0) + self.padding_sec)
                end_sec = max(start_sec, (end_ms / 1000.0) - self.padding_sec)

                # Eğer güvenlik payı uygulandıktan sonra bile anlamlı bir sessizlik kalıyorsa (en az 0.2sn)
                if end_sec - start_sec >= 0.2:
                    cuts.append(CutItem(
                        id=f"cut_silence_{idx}",
                        start=round(start_sec, 2),
                        end=round(end_sec, 2),
                        reason="silence",
                        source="auto"
                    ))

            logger.info(f"Sessizlik algılama tamamlandı: {len(cuts)} sessiz kesim bölgesi bulundu.")
        except Exception as e:
            logger.error(f"Sessizlik algılama hatası ({audio_path}): {e}", exc_info=True)

        return cuts
