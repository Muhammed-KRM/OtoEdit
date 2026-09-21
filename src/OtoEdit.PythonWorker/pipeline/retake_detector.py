"""
OtoEdit Akıllı Hatalı Tekrar Eleyici (Smart Retake Detector)
Transkript üzerinde anlamsal tekrar öbeklerini tespit eder,
AcousticScorer ile ses kalitelerini (patlama, fısıltı, süreklilik) karşılaştırır ve
en kaliteli olanı seçip hatalı tekrarları EDL CutItem olarak döndürür.
"""
from typing import List, Dict, Any, Tuple
import difflib
from models.edl_model import CutItem
from models.transcript_model import TranscriptResult, TranscriptSegment
from pipeline.acoustic_scorer import AcousticScorer
from utils.logger import get_logger

logger = get_logger(__name__)


class RetakeCandidate:
    def __init__(self, segment: TranscriptSegment, index: int):
        self.segment = segment
        self.index = index
        self.text = segment.text.strip().lower()
        self.score: float = 0.0
        self.metrics: Dict[str, float] = {}


class RetakeDetector:
    """Transkript ve ses sinyali üzerinden hatalı tekrarları budayan motor."""

    def __init__(self, similarity_threshold: float = 0.60):
        self.similarity_threshold = similarity_threshold
        self.scorer = AcousticScorer()

    def detect_retakes(self, audio_path: str, transcript: TranscriptResult) -> List[CutItem]:
        """
        Transkript segmentlerini kronolojik olarak tarar, birbirini tekrar eden
        veya yarıda bırakılan cümleleri gruplar, en iyi skora sahip olanı seçip
        diğerlerini CutItem listesi olarak döndürür.
        """
        if not transcript.segments or len(transcript.segments) < 2:
            return []

        logger.info(f"Akıllı Retake analizi başlıyor ({len(transcript.segments)} segment inceleniyor)...")
        cut_items: List[CutItem] = []
        segments = transcript.segments
        n = len(segments)
        visited = set()
        prev_chosen_rms: float = -20.0  # Başlangıç referansı

        i = 0
        while i < n:
            if i in visited:
                i += 1
                continue

            current_group: List[RetakeCandidate] = [RetakeCandidate(segments[i], i)]
            j = i + 1

            # Aynı cümlenin ardışık veya kısa aralıklı tekrarlarını ara
            while j < min(n, i + 4):
                if j in visited:
                    j += 1
                    continue

                sim = self._calculate_similarity(segments[i].text, segments[j].text)
                prefix_match = self._is_prefix_restart(segments[i].text, segments[j].text)

                if sim >= self.similarity_threshold or prefix_match:
                    current_group.append(RetakeCandidate(segments[j], j))
                    visited.add(j)
                else:
                    break
                j += 1

            # Eğer birden fazla aday bulunduysa (Tekrar/Retake var!)
            if len(current_group) > 1:
                logger.info(f"🔁 Retake grubu tespit edildi! {len(current_group)} aday cümle yarışacak.")

                # Her adayın akustik ve kelime güven skorlarını hesapla
                for cand in current_group:
                    acoustics = self.scorer.score_audio_segment(
                        audio_path=audio_path,
                        start_sec=cand.segment.start,
                        end_sec=cand.segment.end,
                        prev_segment_rms=prev_chosen_rms
                    )
                    cand.metrics = acoustics

                    # Semantik Tamlık Skoru: Cümle sonu noktalanmış mı, kelime sayısı yeterli mi?
                    word_count = len(cand.segment.words) if cand.segment.words else len(cand.segment.text.split())
                    has_terminal_punct = any(cand.segment.text.strip().endswith(p) for p in ['.', '!', '?'])
                    completeness_score = min(100.0, word_count * 12.0) if not has_terminal_punct else 100.0

                    # Kelime başı Whisper güven ortalaması
                    conf_scores = [w.confidence for w in getattr(cand.segment, 'words', []) if hasattr(w, 'confidence') and w.confidence is not None]
                    avg_conf = (sum(conf_scores) / len(conf_scores) * 100.0) if conf_scores else 90.0

                    # 🏆 Nihai Birleşik Skor Formülü:
                    # 40% Akustik Kalite + 35% Semantik Tamlık + 25% Tanıma Güveni
                    cand.score = (
                        0.40 * acoustics["composite_acoustic_score"] +
                        0.35 * completeness_score +
                        0.25 * avg_conf
                    )
                    logger.info(
                        f"  -> Aday #{cand.index} [{cand.segment.start:.1f}s - {cand.segment.end:.1f}s]: "
                        f"Skor={cand.score:.1f} | Akustik={acoustics['composite_acoustic_score']} "
                        f"| Clipping={acoustics['clipping_score']} | Metin='{cand.segment.text}'"
                    )

                # Skoru en yüksek olanı KAZANAN olarak seç
                current_group.sort(key=lambda c: c.score, reverse=True)
                winner = current_group[0]
                losers = current_group[1:]

                logger.info(f"  ✅ Kazanan Cümle: #{winner.index} ({winner.score:.1f} puan). Hatalı olanlar siliniyor.")
                prev_chosen_rms = winner.metrics.get("current_rms_db", prev_chosen_rms)

                # Kaybeden tüm adayları EDL kesim listesine ekle
                for loser in losers:
                    cut_items.append(CutItem(
                        id=f"cut_retake_{loser.index}",
                        start=round(loser.segment.start, 2),
                        end=round(loser.segment.end, 2),
                        reason=f"smart_retake (Skor: {loser.score:.1f} vs Kazanan: {winner.score:.1f})",
                        source="auto",
                        command=f"Elenen Tekrar: {loser.segment.text}"
                    ))
            else:
                # Tekrar yok, bu segmentin ses seviyesini referans olarak al
                seg_acoustics = self.scorer.score_audio_segment(audio_path, segments[i].start, segments[i].end)
                prev_chosen_rms = seg_acoustics.get("current_rms_db", prev_chosen_rms)

            visited.add(i)
            i += 1

        logger.info(f"Akıllı Retake analizi bitti: Toplam {len(cut_items)} hatalı tekrar budandı.")
        return cut_items

    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """İki cümlenin difflib benzerlik oranını döner."""
        return difflib.SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()

    @staticmethod
    def _is_prefix_restart(str1: str, str2: str) -> bool:
        """Cümleye baştan başlama (false start) durumunu kontrol eder."""
        w1 = str1.lower().strip().split()
        w2 = str2.lower().strip().split()
        if not w1 or not w2:
            return False
        # İlk 2 veya 3 kelime aynı mı?
        common_words = 0
        for a, b in zip(w1, w2):
            if a == b:
                common_words += 1
            else:
                break
        return common_words >= 2
