"""
OtoEdit Akıllı Hatalı Tekrar Eleyici (Smart Retake Detector) V3
TakeAligner motorunu kullanarak transkript kelime zaman damgaları üzerinden
tekrar okumaları (retakes), cümle içi yeniden başlamaları (restarts) ve
stüdyo meta-komutlarını tespit eder.

Kural: Puanlama tabanlı rastgele seçim kaldırılmıştır. Okuma ve ders videolarında
her zaman son (başarılı) take korunur, önceki hatalı denemeler budanır.
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
    """Take-Aware hizalama ile hatalı tekrarları deterministik budayan akıllı motor."""

    def __init__(
        self,
        similarity_threshold: float = 0.75,
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
        Transkript kelimeleri üzerinden TakeAligner ile retake ve yarım okumaları tespit eder.
        Sınırları enerji minimumuna (RMS) tek yönlü yaslar ve CutItem listesi döndürür.
        """
        words = getattr(transcript, "words", None) or []
        if not words:
            # Fallback: segmentlerden kelimeleri topla veya metinden üret
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

        logger.info(f"Akıllı Retake analizi (Take-Aware v3) başlıyor ({len(words)} kelime taranıyor)...")

        raw_cuts = self.aligner.detect_retakes(words)
        logger.info(f"TakeAligner {len(raw_cuts)} aday retake/restart bölgesi buldu.")

        cut_items: List[CutItem] = []
        for idx, rc in enumerate(raw_cuts, start=1):
            c_start = rc.start
            c_end = rc.end

            # Kenarları lokal RMS enerji minimumuna oturt.
            # Retake artık yalnızca elenen kelimeleri kapsadığı için kenarlar DIŞARI doğru
            # (sessizliğe) yaslanır: başlangıç geriye, bitiş ileriye.
            if analysis is not None:
                c_start = analysis.find_energy_minimum(c_start, search_window_sec=0.025, direction="backward_only")
                c_end = analysis.find_energy_minimum(c_end, search_window_sec=0.025, direction="forward_only")

            if (c_end - c_start) >= 0.15:
                cut_items.append(CutItem(
                    id=f"cut_retake_{idx}",
                    start=round(c_start, 2),
                    end=round(c_end, 2),
                    reason="smart_retake",
                    source="auto",
                    command=rc.command
                ))

        # 3. AŞAMA: LLM TABANLI SEMANTİK VE YETİM KELİME DENETİMİ (Antigravity Gemini)
        if enable_ai_verification and self.transcript_verifier:
            try:
                ai_cuts = self.transcript_verifier.audit_transcript(
                    transcript=transcript,
                    analysis=analysis,
                    existing_cuts=(silence_cuts or []) + cut_items
                )
                if ai_cuts:
                    logger.info(f"🧠 AI Transkript Denetçisinden {len(ai_cuts)} ek retake/yetim kesim eklendi.")
                    cut_items.extend(ai_cuts)
            except Exception as e:
                logger.warning(f"AI Transkript Denetiminde hata (ihmal edildi): {e}")

        # Sırala ve çakışanları birleştir
        cut_items.sort(key=lambda c: c.start)
        merged: List[CutItem] = []
        for c in cut_items:
            if not merged:
                merged.append(c)
                continue
            prev = merged[-1]
            if c.start <= prev.end:
                prev.end = max(prev.end, c.end)
                if c.command and c.command not in (prev.command or ""):
                    prev.command = f"{prev.command} | {c.command}"
            else:
                merged.append(c)

        logger.info(f"Akıllı Retake analizi tamamlandı: Toplam {len(merged)} hatalı tekrar budandı.")
        return merged
