"""
OtoEdit Akıllı Hatalı Tekrar Eleyici (Smart Retake Detector) V2
Transkript üzerinde anlamsal tekrar öbeklerini, stüdyo meta-komutlarını ("başa sar", "olmadı")
ve yarım kalan cümleleri tespit eder. AcousticScorer ile ses kalitelerini (patlama, fısıltı, süreklilik)
karşılaştırır ve en kaliteli olanı seçip hatalı tekrarları EDL CutItem olarak döndürür.
"""
from typing import List, Dict, Any, Tuple, Set, Optional
import re
import difflib
from models.edl_model import CutItem
from models.transcript_model import TranscriptResult, TranscriptSegment
from pipeline.acoustic_scorer import AcousticScorer
from pipeline.audio_analysis import AudioAnalysis
from pipeline.transcript_verifier import TranscriptVerifier
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
    """Transkript ve ses sinyali üzerinden hatalı tekrarları budayan akıllı motor."""

    def _create_retake_cut(
        self,
        cut_id: str,
        segment: TranscriptSegment,
        reason: str,
        command: str,
        analysis: Optional[AudioAnalysis] = None
    ) -> CutItem:
        """
        Retake kesimini segmentin ilk kelimesinin başlangıcından
        son kelimesinin bitişine oturtur ve kenarları lokal RMS minimumuna çeker (Adım 7).
        """
        c_start = segment.start
        c_end = segment.end

        # Kelime sınırlarına oturt
        if getattr(segment, "words", None) and len(segment.words) > 0:
            c_start = segment.words[0].start
            c_end = segment.words[-1].end

        # RMS zarfı varsa kenar ince ayarı
        if analysis is not None:
            c_start = analysis.find_energy_minimum(c_start, search_window_sec=0.05)
            c_end = analysis.find_energy_minimum(c_end, search_window_sec=0.05)

        return CutItem(
            id=cut_id,
            start=round(c_start, 2),
            end=round(c_end, 2),
            reason=reason,
            source="auto",
            command=command
        )

    META_RESTART_PATTERNS = [
        r'\bbaşa\s*sar\b',
        r'\bbaşasar\b',
        r'\bbaştan\s*al\b',
        r'\bolmadı\b',
        r'\bkonuşamadık\b',
        r'\byanlış\s*oldu\b',
        r'\bdur\s*baştan\b',
        r'\bpardon\b',
        r'\bbir\s*daha\b'
    ]

    ORDINAL_WORDS = {'birinci', 'ikinci', 'üçüncü', 'dördüncü', 'beşinci', 'içinci', 'ilk', 'son'}
    STOPWORDS = {'ve', 'bu', 'da', 'de', 'için', 'ile', 'en', 'ise', 'o', 'çok', 'gibi', 'kadar', 'daha', 'yani', 'olan', 'olarak', 'tam'}

    def __init__(self, similarity_threshold: float = 0.45, transcript_verifier: Optional[TranscriptVerifier] = None):
        self.similarity_threshold = similarity_threshold
        self.scorer = AcousticScorer()
        self.transcript_verifier = transcript_verifier or TranscriptVerifier()

    @staticmethod
    def normalize_tr(text: str) -> str:
        """Türkçe karakterleri (İ/I/i/ı) Unicode combining karakter tuzaklarına takılmadan normalize eder."""
        return text.replace("İ", "i").replace("I", "ı").lower().replace("i̇", "i")

    def is_meta_speech(self, text: str) -> bool:
        """Kayıt esnasında söylenen stüdyo meta komutlarını ('başa sar', 'olmadı') tespit eder."""
        t = self.normalize_tr(text)
        return any(re.search(pat, t) for pat in self.META_RESTART_PATTERNS)

    def extract_keywords(self, text: str) -> Set[str]:
        t = self.normalize_tr(text)
        words = re.findall(r'\w+', t)
        return set(w for w in words if w not in self.STOPWORDS and len(w) > 1)

    def has_conflicting_ordinals(self, text1: str, text2: str) -> bool:
        """'Birinci öncül' ile 'İkinci öncül' gibi zıt sıralı ifadelerin yanlışlıkla eşleşmesini önler."""
        t1 = self.normalize_tr(text1)
        t2 = self.normalize_tr(text2)
        ord1 = set(re.findall(r'\w+', t1)).intersection(self.ORDINAL_WORDS)
        ord2 = set(re.findall(r'\w+', t2)).intersection(self.ORDINAL_WORDS)
        if ord1 and ord2 and ord1 != ord2:
            return True
        return False

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Zıt öncülleri koruyan, anlamsal anahtar kelime Jaccard ve difflib hibrit benzerliği."""
        if self.has_conflicting_ordinals(text1, text2):
            return 0.0

        kw1 = self.extract_keywords(text1)
        kw2 = self.extract_keywords(text2)
        if not kw1 or not kw2:
            return 0.0

        intersection = kw1.intersection(kw2)
        union = kw1.union(kw2)
        jaccard = len(intersection) / len(union)
        
        # Kelime bazlı örtüşme yeterliyse Jaccard'ı esas al
        if len(intersection) >= 2 or jaccard >= 0.40:
            return jaccard

        # Ekstra difflib benzerliği (kelimeler çok azsa)
        char_sim = difflib.SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()
        return (jaccard * 0.7) + (char_sim * 0.3)

    def detect_retakes(
        self,
        audio_path: str,
        transcript: TranscriptResult,
        silence_cuts: List[CutItem] = None,
        analysis: Optional[AudioAnalysis] = None,
        enable_ai_verification: bool = True
    ) -> List[CutItem]:
        """
        Transkript segmentlerini kronolojik olarak tarar, meta-konuşmaları doğrudan keser,
        tekrarlanan cümleleri gruplar, en kaliteli olanı seçip hatalı olanları CutItem listesi olarak döndürür.
        silence_cuts verilirse, Auto-Jumpcut ile zaten kesilmiş sessizlik alanları taranmayarak vakit kazanılır.
        """
        if not transcript.segments or len(transcript.segments) < 2:
            return []

        logger.info(f"Akıllı Retake analizi başlıyor ({len(transcript.segments)} segment inceleniyor)...")
        cut_items: List[CutItem] = []
        segments = transcript.segments
        n = len(segments)
        visited = set()
        prev_chosen_rms: float = -20.0  # Başlangıç referansı

        # 🚀 OPTİMİZASYON: 1 Saatlik ses dosyasını RAM'e BİR KEZ yükle
        if hasattr(self.scorer, "load_audio"):
            self.scorer.load_audio(audio_path)

        try:
            i = 0
            while i < n:
                if i in visited:
                    i += 1
                    continue

                seg_i = segments[i]
                text_i = seg_i.text

                # SESSİZLİK KONTROLÜ: Auto-Jumpcut'ın zaten kestiği alanlardaki segmentleri doğrudan atla (vakit kaybetme)
                if silence_cuts:
                    in_silence = False
                    for sc in silence_cuts:
                        overlap_start = max(seg_i.start, sc.start)
                        overlap_end = min(seg_i.end, sc.end)
                        if overlap_end > overlap_start:
                            seg_dur = max(0.01, seg_i.end - seg_i.start)
                            if (overlap_end - overlap_start) / seg_dur > 0.6:
                                in_silence = True
                                break
                    if in_silence:
                        logger.info(f"⏭ Auto-Jumpcut sessizliğinde kalan segment Retake'te atlandı: #{i} '{text_i}'")
                        visited.add(i)
                        i += 1
                        continue

                # HALÜSİNASYON KONTROLÜ: Tam sessizlikte üretilen uydurma Whisper metinlerini atla.
                seg_acoustics = self.scorer.score_audio_segment(audio_path, seg_i.start, seg_i.end)
                if seg_acoustics.get("current_rms_db", -20.0) < -45.0:
                    logger.info(f"🔇 Whisper Halüsinasyonu Atlandı (Sessizlik): #{i} '{text_i}' (RMS: {seg_acoustics.get('current_rms_db', -99):.1f}dB)")
                    visited.add(i)
                    i += 1
                    continue

                # 1. KURAL: Meta-konuşma içeriyorsa ("başa sar", "olmadı", "Allah konuşamadık") doğrudan KES!
                if self.is_meta_speech(text_i):
                    logger.info(f"🛑 Meta-konuşma / Outtake tespit edildi: #{i} '{text_i}'")
                    cut_items.append(self._create_retake_cut(
                        cut_id=f"cut_retake_{i}",
                        segment=seg_i,
                        reason=f"smart_retake (Stüdyo Outtake: {text_i})",
                        command=f"Elenen Stüdyo Konuşması: {text_i}",
                        analysis=analysis
                    ))
                    visited.add(i)

                    # Hemen önceki cümle yarım kalmışsa (nokta ile bitmiyorsa) onu da outtake olarak kes
                    if i > 0 and (i - 1) not in visited:
                        prev_seg = segments[i - 1]
                        if not prev_seg.text.strip().endswith(('.', '!', '?')):
                            logger.info(f"✂ Yarım kalan cümle outtake ile birlikte kesildi: #{i-1} '{prev_seg.text}'")
                            cut_items.append(self._create_retake_cut(
                                cut_id=f"cut_retake_{i-1}",
                                segment=prev_seg,
                                reason="smart_retake (Yarım Kalan İptal Edilmiş Cümle)",
                                command=f"Elenen Yarım Cümle: {prev_seg.text}",
                                analysis=analysis
                            ))
                            visited.add(i - 1)

                    i += 1
                    continue

                # 2. KURAL: Aynı cümlenin ardışık veya kısa aralıklı tekrarlarını ara
                current_group: List[RetakeCandidate] = [RetakeCandidate(seg_i, i)]
                j = i + 1

                while j < min(n, i + 5):
                    if j in visited:
                        j += 1
                        continue

                    # Eğer j meta-konuşmaysa bu grupta yarışmasın, kendi adımında direkt kesilsin
                    if self.is_meta_speech(segments[j].text):
                        j += 1
                        continue

                    sim = self.calculate_similarity(segments[i].text, segments[j].text)
                    prefix_match = self._is_prefix_restart(segments[i].text, segments[j].text)

                    if sim >= self.similarity_threshold or prefix_match:
                        current_group.append(RetakeCandidate(segments[j], j))
                        visited.add(j)

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

                        # Kronolojik Recency Bonus: Genelde en son söylenen tekrar doğrusudur (+0.5 puan/indeks)
                        recency_bonus = min(5.0, (cand.index - current_group[0].index) * 2.0)

                        # 🏆 Nihai Birleşik Skor Formülü
                        cand.score = (
                            0.40 * acoustics["composite_acoustic_score"] +
                            0.35 * completeness_score +
                            0.25 * avg_conf +
                            recency_bonus
                        )
                        logger.info(
                            f"  -> Aday #{cand.index} [{cand.segment.start:.1f}s - {cand.segment.end:.1f}s]: "
                            f"Skor={cand.score:.1f} | Akustik={acoustics['composite_acoustic_score']} "
                            f"| Metin='{cand.segment.text}'"
                        )

                    # Skoru en yüksek olanı KAZANAN olarak seç
                    current_group.sort(key=lambda c: c.score, reverse=True)
                    winner = current_group[0]
                    losers = current_group[1:]

                    logger.info(f"  ✅ Kazanan Cümle: #{winner.index} ({winner.score:.1f} puan). Hatalı olanlar siliniyor.")
                    prev_chosen_rms = winner.metrics.get("current_rms_db", prev_chosen_rms)

                    # Kaybeden tüm adayları EDL kesim listesine ekle
                    for loser in losers:
                        cut_items.append(self._create_retake_cut(
                            cut_id=f"cut_retake_{loser.index}",
                            segment=loser.segment,
                            reason=f"smart_retake (Skor: {loser.score:.1f} vs Kazanan: {winner.score:.1f})",
                            command=f"Elenen Tekrar: {loser.segment.text}",
                            analysis=analysis
                        ))
                else:
                    # Tekrar yok, bu segmentin ses seviyesini referans olarak al
                    seg_acoustics = self.scorer.score_audio_segment(audio_path, segments[i].start, segments[i].end)
                    prev_chosen_rms = seg_acoustics.get("current_rms_db", prev_chosen_rms)

                visited.add(i)
                i += 1
        finally:
            # İşlem bittiğinde RAM'i temizle
            if hasattr(self.scorer, "clear_cache"):
                self.scorer.clear_cache()

        # 3. AŞAMA: LLM TABANLI SEMANTİK VE YETİM KELİME DENETİMİ (A5 & C2)
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

        logger.info(f"Akıllı Retake analizi bitti: Toplam {len(cut_items)} hatalı tekrar budandı.")
        return cut_items

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
