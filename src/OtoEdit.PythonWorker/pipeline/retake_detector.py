"""
OtoEdit Akıllı Hatalı Tekrar Eleyici (Smart Retake Detector) V4
TakeAligner V4 ve 3-Aşamalı Çok Ajanlı TranscriptVerifier V4 motorlarını kullanarak:
- Tekrar okumaları (retakes),
- Cümle ortası birleştirmeleri (Mid-Sentence Prefix Stitch),
- Fonetik dil sürçmelerini,
- Stüdyo meta-komutlarını ve hayalet halüsinasyonları ("M.K.", "Thank you" vb.) tespit eder.
- 3. tur sonunda %100 emin olunamayan kesimleri 'uncertain_retake' (Editörde Koyu Turuncu) olarak işaretler.
"""
from typing import List, Dict, Any, Tuple, Set, Optional
from models.edl_model import CutItem
from models.transcript_model import TranscriptResult, TranscriptSegment
from pipeline.acoustic_scorer import AcousticScorer
from pipeline.audio_analysis import AudioAnalysis
from pipeline.transcript_verifier import TranscriptVerifier
from pipeline.take_aligner import TakeAligner, RetakeCut
from utils.logger import get_logger

logger = get_logger(__name__)


class RetakeDetector:
    """Take-Aware hizalama ve 3-Aşamalı Çok Ajanlı Doğrulama ile hatalı tekrarları budayan motor."""

    def __init__(
        self,
        similarity_threshold: float = 0.74,
        transcript_verifier: Optional[TranscriptVerifier] = None
    ):
        self.similarity_threshold = similarity_threshold
        self.aligner = TakeAligner(similarity_threshold=similarity_threshold)
        self.scorer = AcousticScorer()
        self.transcript_verifier = transcript_verifier or TranscriptVerifier()

    def is_meta_speech(self, text: str) -> bool:
        return self.aligner.is_meta_speech(text)

    ORDINAL_WORDS = {'birinci', 'ikinci', 'üçüncü', 'dördüncü', 'beşinci', 'içinci', 'ilk', 'son'}

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Geriye dönük uyumluluk: İki metin arasındaki benzerliği döner."""
        t1 = self.aligner.normalize_word(text1)
        t2 = self.aligner.normalize_word(text2)
        ord1 = set(t1.split()).intersection(self.ORDINAL_WORDS)
        ord2 = set(t2.split()).intersection(self.ORDINAL_WORDS)
        if ord1 and ord2 and ord1 != ord2:
            return 0.0
        import difflib
        return difflib.SequenceMatcher(None, t1, t2).ratio()

    def detect_retakes(
        self,
        audio_path: str,
        transcript: TranscriptResult,
        silence_cuts: Optional[List[CutItem]] = None,
        analysis: Optional[AudioAnalysis] = None,
        enable_ai_verification: bool = True
    ) -> List[CutItem]:
        """
        Transkript kelimeleri üzerinden TakeAligner V4 ve 3-Aşamalı TranscriptVerifier V4 ile
        retake, cümle ortası birleştirme (stitch) ve yarım okumaları tespit eder.
        Sınırları enerji minimumuna (RMS) tek yönlü yaslar ve CutItem listesi döndürür.
        """
        words = getattr(transcript, "words", None) or []
        if not words:
            words = []
            for seg in getattr(transcript, "segments", []):
                if getattr(seg, "words", None):
                    words.extend(seg.words)
                elif getattr(seg, "text", None):
                    tokens = seg.text.strip().split()
                    step = (seg.end - seg.start) / max(1, len(tokens))
                    for i, tok in enumerate(tokens):
                        words.append({
                            "word": tok,
                            "start": seg.start + i * step,
                            "end": seg.start + (i + 1) * step
                        })

        if len(words) < 2:
            logger.info("Transkriptte yeterli kelime bulunamadı, retake analizi atlandı.")
            return []

        logger.info(f"Akıllı Retake analizi (Take-Aware V4 + 3-Pass Multi-Agent) başlıyor ({len(words)} kelime taranıyor)...")

        raw_cuts = self.aligner.detect_retakes(words)
        logger.info(
            f"TakeAligner V4 {len(raw_cuts)} aday retake/restart bölgesi ve "
            f"{len(self.aligner.last_groups)} tekrar grubu buldu."
        )

        cut_items: List[CutItem] = []
        for idx, rc in enumerate(raw_cuts, start=1):
            c_start = rc.start
            c_end = rc.end

            if analysis is not None:
                c_start = analysis.find_energy_minimum(c_start, search_window_sec=0.025, direction="backward_only")
                c_end = analysis.find_energy_minimum(c_end, search_window_sec=0.025, direction="forward_only")

            if (c_end - c_start) >= 0.02:
                cut_items.append(CutItem(
                    id=f"cut_retake_{idx}",
                    start=round(c_start, 3),
                    end=round(max(c_start + 0.03, c_end), 3),
                    reason=rc.reason or "smart_retake",
                    source="auto",
                    command=rc.command
                ))

        # 3-AŞAMALI ÇOK AJANLI DOĞRULAMA DÖNGÜSÜ (Paralel Parça Ajanları + Bağlam Ek Yeri + 3 Tur Küresel Kontrol)
        if enable_ai_verification and self.transcript_verifier:
            try:
                ai_cuts = self.transcript_verifier.audit_transcript(
                    transcript=transcript,
                    analysis=analysis,
                    existing_cuts=(silence_cuts or []) + cut_items,
                    aligner_groups=self.aligner.last_groups,
                )
                if ai_cuts:
                    logger.info(f"🧠 3-Aşamalı Çok Ajanlı Denetçiden {len(ai_cuts)} ek retake/belirsiz kesim eklendi.")
                    cut_items.extend(ai_cuts)
            except Exception as e:
                logger.warning(f"AI Transkript Denetiminde hata (ihmal edildi): {e}")

        # Sırala ve yalnızca aynı reason olan çakışanları birleştir
        cut_items.sort(key=lambda c: c.start)
        merged: List[CutItem] = []
        for c in cut_items:
            if not merged:
                merged.append(c)
                continue
            prev = merged[-1]
            if c.start <= prev.end and c.reason == prev.reason:
                prev.end = round(max(prev.end, c.end), 3)
                if c.command and c.command not in (prev.command or ""):
                    prev.command = f"{prev.command} | {c.command}"
            else:
                merged.append(c)

        smart_cnt = sum(1 for c in merged if c.reason == "smart_retake")
        uncertain_cnt = sum(1 for c in merged if c.reason == "uncertain_retake")
        logger.info(
            f"Akıllı Retake analizi tamamlandı: Toplam {len(merged)} kesim "
            f"({smart_cnt} kesin sarı retake, {uncertain_cnt} belirsiz koyu turuncu retake)."
        )
        return merged
