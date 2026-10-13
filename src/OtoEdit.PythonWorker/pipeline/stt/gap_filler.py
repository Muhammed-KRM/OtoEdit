"""
OtoEdit Kayıp Kelime Dedektörü (Gap Filler)
- Silero VAD konuşma bölgeleri referans alınarak transkriptte atlanmış konuşmalar tespit edilir.
- >= 0.4 sn konuşma olup içinde hiç kelime bulunmayan bölgeler şüpheli boşluk kabul edilir.
- Şüpheli bölgeler küçük bağlamla kesilip STT zinciri üzerinden yeniden istenir.
- Kurtarılan kelimeler zaman sırasına göre transkripte eklenir.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Tuple
from config import Config
from pipeline.audio_analysis import AudioAnalysis
from pipeline.stt.base import Word
from pipeline.stt.chunker import AudioChunk
from pipeline.stt.engine_chain import STTEngineChain
from utils.logger import get_logger

logger = get_logger("STT.GapFiller")


class GapFiller:
    """Atlanan konuşma bölgelerini tespit edip kurtaran motor."""

    def __init__(self, min_gap_sec: float = 0.40):
        self.min_gap_sec = min_gap_sec

    def find_untranscribed_gaps(
        self,
        analysis: AudioAnalysis,
        words: List[Word]
    ) -> List[Tuple[float, float]]:
        """VAD konuşma bölgelerinden içinde kelime bulunmayanları tespit eder."""
        gaps: List[Tuple[float, float]] = []

        for region in analysis.speech_regions:
            if region.duration < self.min_gap_sec:
                continue

            # Bu konuşma bölgesine düşen kelime var mı?
            has_word = any(
                w.end > region.start and w.start < region.end
                for w in words
            )

            if not has_word:
                gaps.append((region.start, region.end))

        return gaps

    def fill_gaps(
        self,
        media_path: str,
        analysis: AudioAnalysis,
        words: List[Word],
        chain: STTEngineChain,
        temp_dir: Path = None
    ) -> List[Word]:
        """Tespit edilen şüpheli boşlukları yeniden transkribe ederek kelimeleri kurtarır."""
        gaps = self.find_untranscribed_gaps(analysis, words)
        if not gaps:
            logger.info("✨ Şüpheli transkript boşluğu bulunamadı, tüm konuşmalar kapsandı.")
            return words

        logger.info(f"🔍 {len(gaps)} adet kelimesiz konuşma bölgesi tespit edildi. Kurtarma deneniyor...")
        work_dir = temp_dir or Config.TEMP_DIR
        os.makedirs(work_dir, exist_ok=True)

        recovered_words: List[Word] = []

        for idx, (g_start, g_end) in enumerate(gaps, start=1):
            clip_start = max(0.0, g_start - 0.5)
            clip_end = min(analysis.duration, g_end + 0.5)
            clip_path = str(work_dir / f"gap_{idx}_{int(g_start*1000)}.mp3")

            try:
                # Küçük ses kesiti al
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(clip_start),
                    "-to", str(clip_end),
                    "-i", media_path,
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-ar", "16000",
                    "-ac", "1",
                    "-b:a", "32k",
                    clip_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                chunk = AudioChunk(
                    index=900 + idx,
                    start_sec=clip_start,
                    end_sec=clip_end,
                    audio_path=clip_path,
                    has_speech=True
                )

                chunk_words, engine_used = chain.transcribe_chunk(chunk)

                # Boşluk aralığına denk gelen kelimeleri süz
                valid_words = [
                    w for w in chunk_words
                    if w.end >= g_start - 0.2 and w.start <= g_end + 0.2
                ]

                if valid_words:
                    word_texts = " ".join(w.word for w in valid_words)
                    logger.info(
                        f"🎯 Boşluk kurtarıldı [{g_start:.2f}s - {g_end:.2f}s] ({engine_used}): '{word_texts}'"
                    )
                    recovered_words.extend(valid_words)
                else:
                    logger.info(
                        f"ℹ️ Boşlukta kelime bulunamadı [{g_start:.2f}s - {g_end:.2f}s] (nefes/öksürük olabilir)."
                    )

            except Exception as ex:
                logger.warning(f"⚠️ Boşluk kurtarma denemesi başarısız [{g_start:.2f}s - {g_end:.2f}s]: {ex}")
            finally:
                if os.path.exists(clip_path):
                    try:
                        os.remove(clip_path)
                    except Exception:
                        pass

        if not recovered_words:
            return words

        # Tüm kelimeleri birleştir ve zamana göre sırala
        all_words = list(words) + recovered_words
        all_words.sort(key=lambda w: w.start)

        # Mükerrer kelimeleri temizle (aynı zaman aralığında birden fazla kelime)
        deduped_words: List[Word] = []
        for w in all_words:
            if not deduped_words:
                deduped_words.append(w)
                continue
            prev = deduped_words[-1]
            # Eğer aynı kelime veya 50ms içinde çok yakın başlangıçsa
            if abs(w.start - prev.start) < 0.05 and w.word.lower() == prev.word.lower():
                continue
            deduped_words.append(w)

        logger.info(f"✨ GapFiller tamamlandı: {len(recovered_words)} adet kayıp kelime başarıyla eklendi.")
        return deduped_words
