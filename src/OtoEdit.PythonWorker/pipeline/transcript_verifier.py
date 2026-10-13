"""
OtoEdit AI Transkript Denetçisi ve Semantik Retake Motoru (Transcript Verifier)
Transkripti anlamsal bütünlük, konuşma takılmaları (false starts), yetim bağlaç/kırıntı ifadeler
ve stüdyo outtake'leri açısından Gemini LLM ile denetler. Elenen segmentleri kelime sınırlarına
ve RMS dip noktalarına oturtarak EDL CutItem listesi üretir.
"""
from typing import List, Dict, Any, Optional, Tuple
from models.edl_model import CutItem
from models.transcript_model import TranscriptResult, TranscriptSegment
from pipeline.audio_analysis import AudioAnalysis
from services.gemini_client import GeminiClient
from utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptVerifier:
    """Gemini destekli anlamsal kurgu denetçisi."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()

    def audit_transcript(
        self,
        transcript: TranscriptResult,
        analysis: Optional[AudioAnalysis] = None,
        existing_cuts: Optional[List[CutItem]] = None
    ) -> List[CutItem]:
        """
        Transkripti analiz eder ve elenmesi gereken kısımları CutItem listesi olarak döndürür.
        existing_cuts verilirse, Jump-Cut tarafından zaten kesilmiş alanlar atlanır.
        """
        if not transcript.segments or len(transcript.segments) < 2:
            return []

        segments = transcript.segments
        logger.info(f"🧠 AI Transkript Denetimi başlıyor ({len(segments)} segment)...")

        # 1. Zaten kesilmiş aralıkları tespit et
        cut_intervals: List[Tuple[float, float]] = []
        if existing_cuts:
            cut_intervals = [(c.start, c.end) for c in existing_cuts]

        def _is_in_existing_cut(s_start: float, s_end: float) -> bool:
            dur = max(0.01, s_end - s_start)
            for c_start, c_end in cut_intervals:
                overlap = max(0.0, min(s_end, c_end) - max(s_start, c_start))
                if overlap / dur > 0.8:
                    return True
            return False

        # 2. Denetlenecek aday segmentleri hazırla
        candidate_segments: List[Dict[str, Any]] = []
        for idx, seg in enumerate(segments):
            if _is_in_existing_cut(seg.start, seg.end):
                continue
            text = seg.text.strip()
            if not text:
                continue
            candidate_segments.append({
                "id": idx,
                "start": seg.start,
                "end": seg.end,
                "text": text
            })

        if not candidate_segments:
            logger.info("Tüm segmentler zaten kesilmiş veya boş, AI denetimi atlandı.")
            return []

        # 3. Segment sayısı fazlaysa (örn. >120) pencerelere böl, değilse tek seferde analiz et
        BATCH_SIZE = 100
        OVERLAP = 10
        rejected_items: List[Dict[str, Any]] = []

        if len(candidate_segments) <= BATCH_SIZE:
            rejected_items = self.gemini.audit_transcript_coherence(candidate_segments)
        else:
            logger.info(f"Segment sayısı yüksek ({len(candidate_segments)}), parçalı analiz yapılıyor...")
            i = 0
            seen_ids = set()
            while i < len(candidate_segments):
                batch = candidate_segments[i: i + BATCH_SIZE]
                res = self.gemini.audit_transcript_coherence(batch)
                for item in res:
                    item_id = item.get("id")
                    if item_id is not None and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        rejected_items.append(item)
                i += (BATCH_SIZE - OVERLAP)

        if not rejected_items:
            logger.info("AI Transkript Denetçisi elenecek ek segment bulamadı (Transkript akıcı).")
            return []

        # 4. Elenen segmentleri CutItem'a dönüştür (Kelime sınırları ve RMS dip noktası hizalaması)
        cuts: List[CutItem] = []
        for item in rejected_items:
            seg_id = item.get("id")
            if seg_id is None or not (0 <= seg_id < len(segments)):
                continue

            seg = segments[seg_id]
            c_start = seg.start
            c_end = seg.end

            # Kelime sınırlarına oturt
            if getattr(seg, "words", None) and len(seg.words) > 0:
                c_start = seg.words[0].start
                c_end = seg.words[-1].end

            # RMS zarfı varsa kenar ince ayarı yap (patlamayı/klik sesini önle)
            if analysis is not None:
                c_start = analysis.find_energy_minimum(c_start, search_window_sec=0.06)
                c_end = analysis.find_energy_minimum(c_end, search_window_sec=0.06)

            reason_code = item.get("reason", "semantic_retake")
            desc = item.get("description", seg.text)

            cuts.append(CutItem(
                id=f"cut_ai_retake_{seg_id}",
                start=round(c_start, 2),
                end=round(c_end, 2),
                reason=f"smart_retake (AI: {reason_code})",
                source="ai_verifier",
                command=f"AI Budanan Konuşma: {desc}"
            ))
            logger.info(f"✂️ AI Kurgu Denetçisi segmenti eledi: #{seg_id} [{c_start:.2f}s - {c_end:.2f}s] '{seg.text}' ({desc})")

        logger.info(f"AI Transkript Denetimi bitti: {len(cuts)} hatalı/yarım segment budandı.")
        return cuts
