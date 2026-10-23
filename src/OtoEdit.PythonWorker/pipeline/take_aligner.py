"""
OtoEdit TakeAligner V4 (Multi-Pass Group-Aware Retake, Phonetic Slip & Mid-Sentence Stitch Engine)
Hatalı okumaları, 2x-4x tam cümle tekrarlarını, cümle ortasından devam eden düzeltmeleri
(Mid-Sentence Prefix Stitch), fonetik dil sürçmelerini (örn. medallenin -> Mecellenin,
Hatel -> Neostel, ithal -> İtalya'dan, Kang Hü -> Hans Küng) ve stüdyo dışı konuşmaları
kelime indeksleri ([W0000..Wn]) ve ses enerjisi sınırları üzerinden tespit eder.
"""
from typing import List, Dict, Any, Tuple, Optional, Set
import re
import difflib
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WordRef:
    word: str
    start: float
    end: float
    confidence: float = 1.0
    index: int = 0
    rms_energy: float = 0.0
    is_abrupt_cutoff: bool = False


@dataclass
class SpeechChunk:
    words: List[WordRef]
    start: float
    end: float
    text: str
    index: int


@dataclass
class TakeCandidate:
    candidate_id: str
    start_word_idx: int
    end_word_idx: int
    start: float
    end: float
    text: str
    is_complete_sentence: bool = True
    has_abrupt_cutoff: bool = False
    rms_score: float = 1.0
    fluency_score: float = 1.0


@dataclass
class RetakeGroup:
    group_id: str
    candidates: List[TakeCandidate] = field(default_factory=list)
    selected_candidate_id: str = ""
    prefix_keep_word_ids: List[int] = field(default_factory=list)
    confidence: float = 0.95
    reason_summary: str = ""


@dataclass
class RetakeCut:
    start: float
    end: float
    reason: str
    command: str
    removed_words: List[str]
    group_id: Optional[str] = None
    confidence: float = 0.95
    start_word_idx: int = -1
    end_word_idx: int = -1


class TakeAligner:
    """Kelime zaman damgaları, fonetik kök eşleşmesi ve duraklama sınırları üzerinden Take analizi yapan motor."""

    CONNECTORS = {
        "hatta", "yani", "fakat", "ama", "şimdi", "tabii",
        "peki", "işte", "ve", "de", "da", "çünkü", "ayrıca",
        "ancak", "nitekim", "örneğin", "mesela", "dolayısıyla"
    }

    SINGLE_ORPHAN_CONNECTORS = {
        "işte", "yani", "şimdi", "tabii", "peki", "fakat", "ama", "hatta", "şey"
    }

    ORDINAL_WORDS = {
        "birinci", "ikinci", "üçüncü", "dördüncü", "beşinci",
        "birincisi", "ikincisi", "üçüncüsü", "dördüncüsü", "beşincisi",
        "ilk", "son"
    }

    ABBREVIATION_MAP = {
        "prof": "profesör",
        "dr": "doktor",
        "yy": "yüzyıl",
    }

    META_PATTERNS = [
        r'\bbaşa\s*sar\b',
        r'\bbaşasar\b',
        r'\bbaştan\s*al\b',
        r'\bolmadı\b',
        r'\bkonuşamadık\b',
        r'\byanlış\s*oldu\b',
        r'\bdur\s*baştan\b',
        r'\bpardon\b',
        r'\bbir\s*daha\b',
        r'\bsüper\s*ulan\b',
        r'\bbir\s*dakika\b',
        r'\btekrar\s*al\b',
        r'\bbastan\b',
        r'\btamam\s*söyleyeyim\b',
        r'\blan\s*ne\s*çabuk\s*oldu\b',
        r'\bsöyle\s*hadi\s*iş\s*var\b',
    ]

    HALLUCINATION_PATTERNS = [
        r'\baltyazı\s*m\.?k\.?\b',
        r'\babone\s*ol\b',
        r'\bbeğenmeyi\s*unutmayın\b',
        r'\bmısır,?\s*diber,?\s*çay\b',
        r'^\s*m\.?\s*k\.?\s*$',
        r'\bne\s*ti\s*ho\s*con\s*la\s*vera\b',
        r'\bthank\s*you\b',
        r'\b[iı]\s*shall\s*be\b',
    ]

    # Bilinen fonetik dil sürçmesi / yabancı özel isim düzeltme çiftleri (yanlış_kök -> doğru_kök)
    PHONETIC_REPAIR_ALIASES: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = [
        (("medallenin", "medalle", "becellenin", "becelle"), ("mecellenin", "mecelle")),
        (("hatel", "neuç"), ("neostel", "neuchatel", "hatel")),
        (("ithal",), ("italyadan", "italya")),
        (("kahn", "fünstü", "kang", "hü"), ("hans", "küng", "künk")),
        (("sahidir", "sahil"), ("şahididir", "şahidi")),
        (("kişisiz",), ("kişisel",)),
        (("kitin", "mitin"), ("metin", "mitin")),
        (("kibir",), ("ki", "bir")),
        (("zatı",), ("zaten",)),
        (("katledi",), ("kat", "edebileceği", "katledebileceği")),
    ]

    def __init__(
        self,
        chunk_gap_threshold: float = 0.50,
        similarity_threshold: float = 0.74,
        tail_coverage_threshold: float = 0.50,
        max_lookback_words: int = 85,
        max_lookback_sec: float = 95.0,
        max_cut_duration: float = 95.0
    ):
        self.chunk_gap_threshold = chunk_gap_threshold
        self.similarity_threshold = similarity_threshold
        self.tail_coverage_threshold = tail_coverage_threshold
        self.max_lookback_words = max_lookback_words
        self.max_lookback_sec = max_lookback_sec
        self.max_cut_duration = max_cut_duration
        self.last_groups: List[RetakeGroup] = []

    @classmethod
    def normalize_word(cls, text: str) -> str:
        """Türkçe kurallı harf sadeleştirmesi, kısaltma açılımı ve noktalama temizliği."""
        if not text:
            return ""
        t = text.strip()
        t = t.replace("İ", "i").replace("I", "ı").lower()
        t = t.replace("â", "a").replace("î", "i").replace("û", "u").replace("ô", "o")
        t = re.sub(r'[^\w\s]', '', t).strip()
        return cls.ABBREVIATION_MAP.get(t, t)

    @classmethod
    def phonetic_skeleton(cls, text: str) -> str:
        """
        Türkçe fonetik dil sürçmelerini (d/c, t/d, k/g/h, s/ş, c/ç, p/b, ğ/y)
        yakalamak için kelimeyi fonetik iskelete indirger.
        """
        w = cls.normalize_word(text)
        if not w:
            return ""
        w = (
            w.replace("ş", "s")
            .replace("ç", "c")
            .replace("ğ", "")
            .replace("h", "")
            .replace("d", "t")
            .replace("b", "p")
            .replace("g", "k")
            .replace("z", "s")
        )
        w = re.sub(r'(.)\1+', r'\1', w)
        return w

    def is_phonetic_repair_pair(self, wrong_w: str, right_w: str) -> bool:
        """İki kelimenin bilinen veya yapısal bir fonetik dil sürçmesi onarımı olup olmadığını döner."""
        nw1 = self.normalize_word(wrong_w)
        nw2 = self.normalize_word(right_w)
        if not nw1 or not nw2:
            return False
        for wrong_set, right_set in self.PHONETIC_REPAIR_ALIASES:
            if any(nw1.startswith(ws) or nw1 == ws for ws in wrong_set) and any(
                nw2.startswith(rs) or nw2 == rs for rs in right_set
            ):
                return True
        sk1 = self.phonetic_skeleton(nw1)
        sk2 = self.phonetic_skeleton(nw2)
        if len(sk1) >= 4 and len(sk2) >= 4:
            if sk1 == sk2 and abs(len(nw1) - len(nw2)) <= 2:
                return True
            if sk1[:3] == sk2[:3] and difflib.SequenceMatcher(None, sk1, sk2).ratio() >= 0.80:
                return True
        return False

    def is_word_match(self, w1: str, w2: str) -> bool:
        """
        Türkçe sondan eklemeli dil tuzağını önleyen + fonetik sürçmeleri tanıyan kelime eşleşme testi:
        - Ordinal sayılar (birinci vs ikinci) asla birbirini tekrar olarak kesmez.
        """
        nw1 = self.normalize_word(w1)
        nw2 = self.normalize_word(w2)
        if not nw1 or not nw2:
            return False
        if nw1 in self.ORDINAL_WORDS and nw2 in self.ORDINAL_WORDS and nw1 != nw2:
            return False
        # Zıt veya ardışık soru kalıpları ("nereden geliyorsun, nereye gidiyorsun") asla birbirini tekrar olarak kesmez
        correlative_roots = (
            ("nereden", "nereye"),
            ("geliyor", "gidiyor"),
            ("gelmek", "gitmek"),
            ("dünya", "ahiret"),
            ("evvel", "ahir"),
            ("zahiri", "batıni"),
            ("lafzı", "ruhu"),
        )
        for r_a, r_b in correlative_roots:
            if (nw1.startswith(r_a) and nw2.startswith(r_b)) or (nw1.startswith(r_b) and nw2.startswith(r_a)):
                return False
        if nw1 == nw2:
            return True

        if self.is_phonetic_repair_pair(nw1, nw2):
            return True

        # Aynı kökün farklı çekim eki almış hali (örn: "italya" vs "italyadan", "felsefesi" vs "felsefesine")
        min_len = min(len(nw1), len(nw2))
        if min_len >= 5 and nw1[:5] == nw2[:5] and abs(len(nw1) - len(nw2)) <= 5:
            return True

        if abs(len(nw1) - len(nw2)) > 4:
            return False

        ratio = difflib.SequenceMatcher(None, nw1, nw2).ratio()
        if ratio < self.similarity_threshold:
            return False

        prefix_len = min(3, len(nw1), len(nw2))
        prefix_match = (nw1[:prefix_len] == nw2[:prefix_len])
        edit_dist_approx = abs(len(nw1) - len(nw2)) + (1 if nw1[0] != nw2[0] else 0)
        return prefix_match or (ratio >= 0.78 and edit_dist_approx <= 2)

    def is_meta_speech(self, text: str) -> bool:
        norm = self.normalize_word(text)
        return any(re.search(pat, norm) for pat in self.META_PATTERNS)

    def is_hallucination(self, text: str) -> bool:
        norm = self.normalize_word(text)
        return any(re.search(pat, norm) for pat in self.HALLUCINATION_PATTERNS)

    def split_into_chunks(self, words: List[WordRef], gap_threshold: Optional[float] = None) -> List[SpeechChunk]:
        """Kelimeleri duraklama sınırlarına göre konuşma öbeklerine ayırır."""
        if not words:
            return []
        thresh = gap_threshold if gap_threshold is not None else self.chunk_gap_threshold
        chunks: List[SpeechChunk] = []
        cur_words: List[WordRef] = [words[0]]

        for w in words[1:]:
            prev_w = cur_words[-1]
            gap = w.start - prev_w.end
            if gap >= thresh:
                chunk_text = " ".join(cw.word for cw in cur_words)
                chunks.append(SpeechChunk(
                    words=cur_words,
                    start=cur_words[0].start,
                    end=cur_words[-1].end,
                    text=chunk_text,
                    index=len(chunks)
                ))
                cur_words = [w]
            else:
                cur_words.append(w)

        if cur_words:
            chunk_text = " ".join(cw.word for cw in cur_words)
            chunks.append(SpeechChunk(
                words=cur_words,
                start=cur_words[0].start,
                end=cur_words[-1].end,
                text=chunk_text,
                index=len(chunks)
            ))

        return chunks

    def _split_into_clause_starts(self, words: List[WordRef], cut_word_indices: Set[int]) -> List[int]:
        """
        Yeniden okuma (restart/retake) başlangıcı olabilecek aday kelime indekslerini üretir:
        1. >= 0.35s duraklama sonrası başlayan her kelime
        2. Cümle sonu noktalamasından (. ? ! : …) hemen sonraki kelime
        3. Büyük harfle başlayan ve öncesinde >= 0.15s nefes boşluğu olan cümle başları
        4. Duraksamasız anlık yeniden başlamalar (kelime 2-3 adım önceki kelimeyle aynıysa, örn: 'dördüncü ise dördüncü kaynak')
        """
        starts: List[int] = [0]
        for idx in range(1, len(words)):
            if words[idx].index in cut_word_indices:
                continue
            prev_w = words[idx - 1]
            cur_w = words[idx]
            gap = cur_w.start - prev_w.end
            prev_raw = prev_w.word.strip()
            cur_raw = cur_w.word.strip()
            if gap >= 0.35 or gap < -0.02:
                starts.append(idx)
            elif prev_raw.endswith(('.', '!', '?', '…')) and gap >= 0.05:
                starts.append(idx)
            elif cur_raw and cur_raw[0].isupper() and gap >= 0.15:
                starts.append(idx)
            elif (
                idx >= 2
                and self.normalize_word(cur_w.word) == self.normalize_word(words[idx - 2].word)
                and (
                    self.normalize_word(cur_w.word) in self.ORDINAL_WORDS
                    or self.normalize_word(words[idx - 1].word) in ("ise", "yani", "delili", "ve", "de", "da")
                )
            ):
                starts.append(idx)
        return starts

    def detect_retakes(self, raw_words: List[Any]) -> List[RetakeCut]:
        """
        Kelime listesi üzerinden tüm retake, 2x-4x çoklu tekrar, cümle ortası birleştirme (stitch),
        fonetik dil sürçmesi ve stüdyo dışı konuşma kesimlerini hesaplar.
        Ayrıca oluşturulan tekrar gruplarını self.last_groups içinde saklar.
        """
        words: List[WordRef] = []
        for idx, w in enumerate(raw_words):
            if isinstance(w, dict):
                w_text = str(w.get("word", "")).strip()
                w_start = float(w.get("start", 0.0))
                w_end = float(w.get("end", 0.0))
                w_conf = float(w.get("confidence", 1.0))
            else:
                w_text = str(getattr(w, "word", "")).strip()
                w_start = float(getattr(w, "start", 0.0))
                w_end = float(getattr(w, "end", 0.0))
                w_conf = float(getattr(w, "confidence", 1.0) or 1.0)
            if w_text and w_end >= w_start:
                if words:
                    prev_w = words[-1]
                    ov = min(w_end, prev_w.end) - max(w_start, prev_w.start)
                    wn = self.normalize_word(w_text)
                    pn = self.normalize_word(prev_w.word)
                    if wn and wn == pn and (abs(w_start - prev_w.start) <= 0.20 or ov > 0.02):
                        continue
                    if prev_w.end > w_start and wn != pn:
                        mid = round(max(prev_w.start + 0.04, min(prev_w.end, 0.5 * (prev_w.end + w_start))), 3)
                        prev_w.end = mid
                        if w_end > mid + 0.02:
                            w_start = mid
                words.append(WordRef(word=w_text, start=w_start, end=w_end, confidence=w_conf, index=len(words)))

        self.last_groups = []
        if len(words) < 2:
            return []

        cuts: List[RetakeCut] = []
        cut_word_indices: Set[int] = set()
        group_counter = 0

        def _register_cut(
            start_w_idx: int,
            end_w_idx: int,
            reason: str,
            command: str,
            kept_start_w_idx: Optional[int] = None,
            kept_end_w_idx: Optional[int] = None,
            prefix_keep_ids: Optional[List[int]] = None,
            confidence: float = 0.95,
        ) -> None:
            nonlocal group_counter
            removed = [
                words[i] for i in range(start_w_idx, end_w_idx + 1)
                if 0 <= i < len(words) and words[i].index not in cut_word_indices
            ]
            if not removed:
                return
            c_start = removed[0].start
            has_kept_anchor = (kept_start_w_idx is not None and 0 <= kept_start_w_idx < len(words))
            if has_kept_anchor:
                r_anchor_start = words[kept_start_w_idx].start
                # Korunan kelimenin başlangıcı silinen aralıkla örtüşüyorsa bu sahte bir sınır kopyasıdır, kesme!
                if r_anchor_start <= c_start + 0.06:
                    return
                c_end = min(r_anchor_start - 0.01, max(rw.end for rw in removed) + 0.02)
            else:
                c_end = max(rw.end for rw in removed) + 0.02

            overlapping_kept_end = max(
                (w.end for w in words
                 if w.start < c_start - 0.03 and w.end > c_start and w.index not in cut_word_indices and w not in removed),
                default=None
            )
            if overlapping_kept_end is not None and overlapping_kept_end < c_end - 0.02:
                c_start = overlapping_kept_end + 0.01

            if has_kept_anchor and (c_end - c_start) < 0.06:
                return
            if c_end - c_start < 0.02:
                c_end = max(c_start + 0.03, removed[-1].end)

            for rw in removed:
                cut_word_indices.add(rw.index)

            group_counter += 1
            grp_id = f"GRP_{group_counter:03d}"

            cand_bad = TakeCandidate(
                candidate_id=f"{grp_id}_T1",
                start_word_idx=removed[0].index,
                end_word_idx=removed[-1].index,
                start=round(c_start, 3),
                end=round(c_end, 3),
                text=" ".join(rw.word for rw in removed),
                is_complete_sentence=removed[-1].word.strip().endswith(('.', '!', '?')),
                has_abrupt_cutoff=not removed[-1].word.strip().endswith(('.', '!', '?')),
                fluency_score=0.35,
            )
            cands = [cand_bad]
            sel_id = ""
            if kept_start_w_idx is not None and kept_end_w_idx is not None and kept_start_w_idx <= kept_end_w_idx < len(words):
                kept_slice = words[kept_start_w_idx: kept_end_w_idx + 1]
                if kept_slice:
                    sel_id = f"{grp_id}_T2"
                    cands.append(TakeCandidate(
                        candidate_id=sel_id,
                        start_word_idx=kept_slice[0].index,
                        end_word_idx=kept_slice[-1].index,
                        start=round(kept_slice[0].start, 3),
                        end=round(kept_slice[-1].end, 3),
                        text=" ".join(kw.word for kw in kept_slice),
                        is_complete_sentence=True,
                        has_abrupt_cutoff=False,
                        fluency_score=0.95,
                    ))

            self.last_groups.append(RetakeGroup(
                group_id=grp_id,
                candidates=cands,
                selected_candidate_id=sel_id,
                prefix_keep_word_ids=list(prefix_keep_ids or []),
                confidence=confidence,
                reason_summary=command,
            ))

            cuts.append(RetakeCut(
                start=round(c_start, 3),
                end=round(c_end, 3),
                reason=reason,
                command=f"[{grp_id}] {command}",
                removed_words=[rw.word for rw in removed],
                group_id=grp_id,
                confidence=confidence,
                start_word_idx=removed[0].index,
                end_word_idx=removed[-1].index,
            ))

        # ------------------------------------------------------------------
        # 1. AŞAMA: HAYALET KELİMELER ("M.K.", "Thank you.", "I shall be."),
        # SIKIŞTIRILMIŞ WHISPER DUPLİKASYONLARI VE STÜDYO META-KONUŞMALARI
        # ------------------------------------------------------------------
        for idx, w in enumerate(words):
            nw = self.normalize_word(w.word)
            if nw in ("mk", "altyazımk"):
                _register_cut(
                    idx, idx,
                    reason="smart_retake",
                    command=f"Whisper Sessizlik Halüsinasyonu: {w.word}",
                    confidence=0.99,
                )

        # Sıkıştırılmış Whisper kopya patlaması tespiti (örn: 591.91s - 592.66s arası 0.02s süreli 12 kopya kelime)
        idx_b = 0
        while idx_b < len(words) - 3:
            if words[idx_b].index not in cut_word_indices and (words[idx_b].end - words[idx_b].start) <= 0.035:
                burst_end = idx_b
                while burst_end + 1 < len(words) and (words[burst_end + 1].end - words[burst_end + 1].start) <= 0.05:
                    burst_end += 1
                if burst_end - idx_b >= 3:
                    # Eğer hemen sonrasında "mi?" gibi tek kelimelik kuyruk varsa ve öncesinde aynı soru sorulduysa onu da dahil et
                    if burst_end + 1 < len(words) and self.normalize_word(words[burst_end + 1].word) in ("mi", "mı", "mu", "mü"):
                        burst_end += 1
                    _register_cut(
                        idx_b, burst_end,
                        reason="smart_retake",
                        command="Whisper Sıkıştırılmış Kopya Halüsinasyonu",
                        confidence=0.99,
                    )
                    idx_b = burst_end + 1
                    continue
            idx_b += 1

        # 2-9 kelimelik yabancı / TRT betimleme halüsinasyon ifadeleri ("Thank you.", "I shall be.", "Ne ti ho con la vera", "Bu dizinin betimlemesi TRT...")
        for idx_h in range(len(words)):
            for win_len in (9, 6, 3, 2):
                if idx_h + win_len <= len(words):
                    phrase = " ".join(words[idx_h + j].word for j in range(win_len))
                    norm_p = self.normalize_word(phrase)
                    if (
                        (win_len == 2 and norm_p == "thank you")
                        or (win_len == 3 and norm_p in ("ı shall be", "i shall be"))
                        or (win_len == 6 and "ne ti ho con la vera" in norm_p)
                        or (win_len == 9 and "dizinin betimlemesi trt" in norm_p)
                    ):
                        _register_cut(
                            idx_h, idx_h + win_len - 1,
                            reason="smart_retake",
                            command=f"Yabancı Dil / Whisper Halüsinasyonu: {phrase}",
                            confidence=0.99,
                        )
                        break

        # Stüdyo meta-konuşmaları (hem kısa 0.5s hem geniş 3.5s konuşma turlarında kontrol et)
        meta_timestamps: List[Tuple[float, float]] = []
        for gap_t in (0.50, 3.60):
            for c in self.split_into_chunks(words, gap_threshold=gap_t):
                alive_w = [w for w in c.words if w.index not in cut_word_indices]
                if not alive_w:
                    continue
                c_text = " ".join(w.word for w in alive_w)
                if self.is_meta_speech(c_text) or self.is_hallucination(c_text):
                    meta_timestamps.append((alive_w[0].start, alive_w[-1].end))
                    _register_cut(
                        alive_w[0].index,
                        alive_w[-1].index,
                        reason="smart_retake",
                        command=f"Stüdyo Outtake / Halüsinasyon: {c_text}",
                        confidence=0.99,
                    )

        # Stüdyo meta konuşmasının hemen (15sn) etrafındaki sahte kapanış ("İzlediğiniz için teşekkür...") ve onay ("tamam Tamam.") sözlerini temizle
        if meta_timestamps:
            for idx_m, w in enumerate(words):
                if w.index in cut_word_indices:
                    continue
                nw = self.normalize_word(w.word)
                if nw in ("izlediğiniz", "için", "teşekkür", "teşekkürler", "ederim", "tamam", "lan", "ne", "çabuk", "oldu"):
                    if any(abs(w.start - ms) <= 15.0 or abs(w.end - me) <= 15.0 for ms, me in meta_timestamps):
                        _register_cut(
                            idx_m, idx_m,
                            reason="smart_retake",
                            command=f"Stüdyo Outtake Bitişiği: {w.word}",
                            confidence=0.98,
                        )

        # ------------------------------------------------------------------
        # 2. AŞAMA: ÇOK ÖLÇEKLİ SAĞDAN-SOLA (RIGHT-ANCHORED) TEKRAR VE CÜMLE-ORTASI BİRLEŞTİRME (STITCH)
        # ------------------------------------------------------------------
        for _pass_iter in range(3):
            clause_starts = self._split_into_clause_starts(words, cut_word_indices)
            for cs_pos in range(1, len(clause_starts)):
                r_start_idx = clause_starts[cs_pos]
                if r_start_idx >= len(words) or words[r_start_idx].index in cut_word_indices:
                    continue

                # R adayının kelimelerini topla (arada > 14s sessizlik yoksa 28 kelimeye kadar)
                r_words: List[WordRef] = []
                scan_r = r_start_idx
                while scan_r < len(words) and len(r_words) < 28:
                    if words[scan_r].index not in cut_word_indices:
                        if r_words and (words[scan_r].start - r_words[-1].end) > 15.0:
                            break
                        r_words.append(words[scan_r])
                    scan_r += 1

                if not r_words:
                    continue

                # R'nin başındaki bağlaçları belirle (0..2 bağlaç toleransı)
                r_eval_start_idx = 0
                if len(r_words) > 1 and self.normalize_word(r_words[0].word) in self.CONNECTORS:
                    r_eval_start_idx = 1
                    if len(r_words) > 2 and self.normalize_word(r_words[1].word) in self.CONNECTORS:
                        r_eval_start_idx = 2

                r_probe_words = r_words[r_eval_start_idx:]
                if not r_probe_words:
                    continue

                # R'nin öncesindeki kesilmemiş kelimeleri geriye doğru topla
                prior_words: List[WordRef] = []
                scan_l = r_start_idx - 1
                while scan_l >= 0:
                    w_l = words[scan_l]
                    if w_l.index not in cut_word_indices:
                        if len(prior_words) >= self.max_lookback_words:
                            break
                        if (r_words[0].start - w_l.start) > self.max_lookback_sec:
                            break
                        prior_words.append(w_l)
                    scan_l -= 1

                if not prior_words:
                    continue
                prior_words.reverse()

                best_match: Optional[Tuple[int, int]] = None
                best_score = 0
                max_probe_k = min(len(r_probe_words), 14)

                for p_idx in range(len(prior_words)):
                    k = 0
                    p_cursor = p_idx
                    r_cursor = 0
                    while r_cursor < max_probe_k and p_cursor < len(prior_words):
                        pw = prior_words[p_cursor]
                        rw = r_probe_words[r_cursor]
                        if self.is_word_match(pw.word, rw.word):
                            k += 1
                            p_cursor += 1
                            r_cursor += 1
                        elif (
                            r_cursor + 1 < max_probe_k
                            and self.is_word_match(
                                pw.word,
                                self.normalize_word(rw.word) + self.normalize_word(r_probe_words[r_cursor + 1].word),
                            )
                        ):
                            # 1 birleşik kelime <-> 2 ayrı kelime (örn: 'Katledebileceği' vs 'Kat edebileceği')
                            k += 2
                            p_cursor += 1
                            r_cursor += 2
                        elif (
                            p_cursor + 1 < len(prior_words)
                            and self.is_word_match(
                                self.normalize_word(pw.word) + self.normalize_word(prior_words[p_cursor + 1].word),
                                rw.word,
                            )
                        ):
                            k += 1
                            p_cursor += 2
                            r_cursor += 1
                        elif (
                            r_cursor == 0
                            and self.normalize_word(pw.word) in ("küng", "künk")
                            and self.normalize_word(rw.word) == "çünkü"
                        ):
                            # 'Küng, ben nereye inanıyorum?' -> 'Çünkü ben nereye inanıyorum?'
                            k += 1
                            p_cursor += 1
                            r_cursor += 1
                        elif (
                            k >= 1
                            and r_cursor + 1 < max_probe_k
                            and p_cursor < len(prior_words)
                            and self.is_word_match(prior_words[p_cursor].word, r_probe_words[r_cursor + 1].word)
                        ):
                            # R'de araya 1 kelime eklenerek düzeltilmişse (örn: 'dördüncü ise' -> 'dördüncü kaynak ise')
                            k += 1
                            p_cursor += 1
                            r_cursor += 2
                        elif (
                            k >= 1
                            and r_cursor + 1 < max_probe_k
                            and p_cursor + 1 < len(prior_words)
                            and self.is_word_match(prior_words[p_cursor + 1].word, r_probe_words[r_cursor].word)
                        ):
                            # Yalnızca ilk kelime eşleştikten sonra (k >= 1) arada 1 kelimelik sürçme toleransı
                            # (Örn: 'Neuç Hatel Üniversitesi' vs 'Neostel Üniversitesi')
                            k += 1
                            p_cursor += 2
                            r_cursor += 1
                        elif (
                            k >= 1
                            and p_cursor == len(prior_words) - 1
                            and len(self.normalize_word(pw.word)) >= 2
                            and self.normalize_word(rw.word).startswith(self.normalize_word(pw.word)[:2])
                        ):
                            # Yarıda kesilen son kelime kökü eşleşmesi (örn: 'mecellenin bir ha...' -> 'Mecellenin bir hakimle')
                            k += 1
                            p_cursor += 1
                            r_cursor += 1
                        else:
                            break

                    tail_prior = prior_words[p_cursor:]
                    is_phonetic_head = (
                        k >= 1
                        and self.is_phonetic_repair_pair(prior_words[p_idx].word, r_probe_words[0].word)
                    )
                    # "son bin... -> Son 1400" gibi "..." ile biten yarım kalmış 2 kelimelik denemeler
                    # veya "Profesör doktor, -> Profesör Hans Küng'dür" gibi unvan tekrarları
                    has_ellipsis_cutoff = (
                        k == 1
                        and len(tail_prior) == 1
                        and (
                            ".." in tail_prior[0].word
                            or self.normalize_word(tail_prior[0].word) in ("doktor", "dr")
                        )
                    )
                    valid_k = (
                        k >= 2
                        or (k == 1 and len(self.normalize_word(r_probe_words[0].word)) >= 4 and len(tail_prior) == 0)
                        or has_ellipsis_cutoff
                        or (is_phonetic_head and len(tail_prior) <= 18)
                    )
                    if not valid_k:
                        continue

                    # KORUMA KURALI: Eğer tail_prior içinde tamamlanmış bir cümle sonu ('.', '?') varsa ve
                    # hemen ardından yeni bir cümle başlıyorsa (örn. 3714s 'Kanun koyucu bu kuralı hangi maksatla koydu diye sorar. İşte beşeri hukukta'),
                    # k == 2 eşleşmesi tamamlanmış farklı bir cümleyi YUTAMAZ!
                    has_internal_completed_sentence = any(
                        tw.word.strip().endswith(('.', '?', '!')) for tw in tail_prior[:-1]
                    )

                    tail_prior_text = " ".join(self.normalize_word(w.word) for w in tail_prior)
                    # tail_r uzunluğunu tail_prior ile orantılı tut (SequenceMatcher uzunluk cezası oluşmasın)
                    compare_len = max(len(tail_prior) + 2, 4)
                    tail_r = r_probe_words[r_cursor: r_cursor + compare_len]
                    tail_r_text = " ".join(self.normalize_word(w.word) for w in tail_r)

                    coverage_ok = False
                    if not tail_prior_text:
                        coverage_ok = True
                    elif has_ellipsis_cutoff:
                        coverage_ok = True
                    elif (
                        (k >= 3 or (k == 2 and is_phonetic_head))
                        and len(tail_prior) <= 2
                        and not has_internal_completed_sentence
                    ):
                        # 3+ kelime (veya 2 kelimelik fonetik başlangıç: 'medallenin bir hak...') aynı başlayıp
                        # sonunda sadece 1-2 kelime sürçülmüşse ('çeviririz.', 'hak...', 'unsur.', 'adaleti mah.', 'sahil.')
                        coverage_ok = True
                    elif len(tail_prior) <= 28:
                        cov_ratio = difflib.SequenceMatcher(None, tail_prior_text, tail_r_text).ratio()
                        tp_set = {self.normalize_word(w.word)[:4] for w in tail_prior if len(self.normalize_word(w.word)) >= 4}
                        tr_set = {self.normalize_word(w.word)[:4] for w in tail_r if len(self.normalize_word(w.word)) >= 4}
                        stem_overlap = (len(tp_set & tr_set) / max(1, len(tp_set))) if tp_set else 0.0
                        ends_with_complete_punct = prior_words[-1].word.strip().endswith(('.', '!', '?'))
                        aborted_first_attempt = (
                            (k >= 3 or (k >= 2 and is_phonetic_head))
                            and not has_internal_completed_sentence
                            and not ends_with_complete_punct
                            and (len(tail_prior) <= k + 2 or stem_overlap >= 0.55)
                        )
                        if cov_ratio >= 0.56 or (k >= 3 and stem_overlap >= 0.62 and not has_internal_completed_sentence) or aborted_first_attempt:
                            coverage_ok = True

                    if coverage_ok:
                        score = k * 15 + max(0, 22 - len(tail_prior))
                        if score > best_score:
                            best_score = score
                            best_match = (p_idx, k)

                if best_match is not None:
                    p_idx, k = best_match
                    match_start_word = prior_words[p_idx]

                    if r_eval_start_idx > 0:
                        for back_i in range(1, r_eval_start_idx + 1):
                            cand_prior_idx = p_idx - back_i
                            cand_r_idx = r_eval_start_idx - back_i
                            if cand_prior_idx >= 0 and cand_r_idx >= 0:
                                pw_back = prior_words[cand_prior_idx].word
                                rw_back = r_words[cand_r_idx].word
                                if self.is_word_match(pw_back, rw_back) or (
                                    self.normalize_word(pw_back) in ("küng", "künk")
                                    and self.normalize_word(rw_back) == "çünkü"
                                ):
                                    match_start_word = prior_words[cand_prior_idx]

                    # YETİM TEK BAĞLAÇ KONTROLÜ vs CÜMLE-ORTASI ÖNEK BİRLEŞTİRME (MID-SENTENCE STITCH)
                    prefix_keep_ids: List[int] = []
                    ms_global_idx = match_start_word.index
                    if ms_global_idx > 0:
                        island_prefix: List[WordRef] = []
                        scan_pre = ms_global_idx - 1
                        while scan_pre >= 0 and words[scan_pre].index not in cut_word_indices:
                            nxt_w = words[scan_pre + 1] if scan_pre + 1 < len(words) else match_start_word
                            if (nxt_w.start - words[scan_pre].end) >= 0.85:
                                break
                            if words[scan_pre].word.strip().endswith(('.', '!', '?')):
                                break
                            island_prefix.insert(0, words[scan_pre])
                            scan_pre -= 1

                        if len(island_prefix) == 1 and self.normalize_word(island_prefix[0].word) in self.SINGLE_ORPHAN_CONNECTORS:
                            match_start_word = island_prefix[0]
                        elif len(island_prefix) >= 2:
                            prefix_keep_ids = [pw.index for pw in island_prefix]

                    cut_dur = r_words[0].start - match_start_word.start
                    if 0.08 <= cut_dur <= self.max_cut_duration:
                        end_cut_idx = prior_words[-1].index
                        kept_end_idx = r_words[min(len(r_words) - 1, k + 6)].index
                        stitch_note = (
                            f" (Önek Korundu: {' '.join(words[i].word for i in prefix_keep_ids[:4])})"
                            if prefix_keep_ids else ""
                        )
                        _register_cut(
                            start_w_idx=match_start_word.index,
                            end_w_idx=end_cut_idx,
                            reason="smart_retake",
                            command=(
                                f"Elenen Tekrar{stitch_note}: "
                                f"{' '.join(w.word for w in prior_words[p_idx:p_idx + 6])}..."
                            ),
                            kept_start_w_idx=r_words[0].index,
                            kept_end_w_idx=kept_end_idx,
                            prefix_keep_ids=prefix_keep_ids,
                            confidence=0.95,
                        )

        # ------------------------------------------------------------------
        # 3. AŞAMA: SONU YENİ BAŞLANGIÇLA ÖRTÜŞEN YARIM KALMIŞ YAN CÜMLELER (TAIL-TO-HEAD OVERLAP)
        # ------------------------------------------------------------------
        turn_chunks = self.split_into_chunks(words, gap_threshold=1.50)
        for tc_idx in range(len(turn_chunks) - 1):
            cur_tc = turn_chunks[tc_idx]
            nxt_tc = turn_chunks[tc_idx + 1]
            cur_alive = [w for w in cur_tc.words if w.index not in cut_word_indices]
            nxt_alive = [w for w in nxt_tc.words if w.index not in cut_word_indices]
            if len(cur_alive) < 3 or len(nxt_alive) < 3:
                continue
            gap = nxt_alive[0].start - cur_alive[-1].end
            if gap < 2.5 or cur_alive[-1].word.strip().endswith(('.', '!', '?')):
                continue

            tail_match_len = 0
            for m_len in (4, 3, 2):
                if len(cur_alive) >= m_len and len(nxt_alive) >= m_len:
                    if all(self.is_word_match(cur_alive[-m_len + j].word, nxt_alive[j].word) for j in range(m_len)):
                        tail_match_len = m_len
                        break

            if tail_match_len >= 2 and len(cur_alive) <= 14:
                _register_cut(
                    start_w_idx=cur_alive[0].index,
                    end_w_idx=cur_alive[-1].index,
                    reason="smart_retake",
                    command=f"Yarım Bırakılıp Yeniden Kurulan Cümle: {' '.join(w.word for w in cur_alive[:7])}...",
                    kept_start_w_idx=nxt_alive[0].index,
                    kept_end_w_idx=nxt_alive[min(len(nxt_alive) - 1, 6)].index,
                    confidence=0.92,
                )

        # ------------------------------------------------------------------
        # 4. AŞAMA: CÜMLE İÇİ ANLIK DİL SÜRÇMELERİ, TEK KELİME EKOLARI VE YARIM BAŞLANGIÇLAR
        # ------------------------------------------------------------------
        i = 0
        while i < len(words) - 1:
            if words[i].index in cut_word_indices:
                i += 1
                continue
            # Bir sonraki kesilmemiş kelimeyi bul
            nxt_i = i + 1
            while nxt_i < len(words) and words[nxt_i].index in cut_word_indices:
                nxt_i += 1
            if nxt_i >= len(words):
                break

            w1 = words[i]
            w2 = words[nxt_i]
            gap = w2.start - w1.end
            nw1 = self.normalize_word(w1.word)
            nw2 = self.normalize_word(w2.word)

            # 4A. 1 kelime -> 2 kelimelik bitişik sürçme düzeltmesi ("Kibir" -> "ki bir", "katledi." -> "Kat edebileceği")
            if nxt_i + 1 < len(words) and words[nxt_i + 1].index not in cut_word_indices:
                w3 = words[nxt_i + 1]
                nw3 = self.normalize_word(w3.word)
                if nw1 and (nw1 == (nw2 + nw3) or self.is_phonetic_repair_pair(nw1, nw2 + nw3)) and gap >= 0.15:
                    _register_cut(
                        start_w_idx=w1.index,
                        end_w_idx=w1.index,
                        reason="smart_retake",
                        command=f"Kelime Bitişmesi Sürçmesi: '{w1.word}' -> '{w2.word} {w3.word}'",
                        kept_start_w_idx=w2.index,
                        kept_end_w_idx=w3.index,
                        confidence=0.95,
                    )
                    i = nxt_i
                    continue

            # 4B. Ardışık tek kelime tekrarı veya fonetik dil sürçmesi (arada >= 0.18s duraklama ile)
            is_exact_dup = (nw1 == nw2 and len(nw1) >= 2 and gap >= 0.22)
            is_slip_dup = (
                0.18 <= gap <= 20.0
                and (not w1.word.strip().endswith(('.', '!', '?')) or nw1 == "katledi")
                and self.is_phonetic_repair_pair(w1.word, w2.word)
                and nw1 != nw2
            )
            if is_exact_dup or is_slip_dup:
                _register_cut(
                    start_w_idx=w1.index,
                    end_w_idx=w1.index,
                    reason="smart_retake",
                    command=f"Anlık Dil Sürçmesi / Kelime Tekrarı: '{w1.word}' -> '{w2.word}'",
                    kept_start_w_idx=w2.index,
                    kept_end_w_idx=w2.index,
                    confidence=0.94,
                )
            i += 1

        # 4C. 1-3 kelimelik yarım başlangıç adacıkları (False Starts)
        chunks_fs = self.split_into_chunks(words, gap_threshold=0.50)
        for c_idx in range(len(chunks_fs) - 1):
            cur_c = chunks_fs[c_idx]
            next_c = chunks_fs[c_idx + 1]
            cur_alive = [w for w in cur_c.words if w.index not in cut_word_indices]
            nxt_alive = [w for w in next_c.words if w.index not in cut_word_indices]
            if not cur_alive or not nxt_alive:
                continue

            gap = nxt_alive[0].start - cur_alive[-1].end
            if len(cur_alive) <= 3 and gap >= 1.6:
                if cur_alive[-1].word.strip().endswith(('.', '!', '?', '…')) and ".." not in cur_alive[-1].word:
                    continue
                first_cur = cur_alive[0].word
                is_repeat = any(
                    self.is_word_match(first_cur, nxt_alive[j].word)
                    for j in range(min(3, len(nxt_alive)))
                )
                if is_repeat:
                    _register_cut(
                        start_w_idx=cur_alive[0].index,
                        end_w_idx=cur_alive[-1].index,
                        reason="smart_retake",
                        command=f"Yarım Başlangıç (False Start): {' '.join(w.word for w in cur_alive)}",
                        kept_start_w_idx=nxt_alive[0].index,
                        kept_end_w_idx=nxt_alive[min(len(nxt_alive) - 1, 3)].index,
                        confidence=0.95,
                    )

        cuts.sort(key=lambda c: c.start)
        merged_cuts: List[RetakeCut] = []
        for c in cuts:
            if not merged_cuts:
                merged_cuts.append(c)
                continue
            prev = merged_cuts[-1]
            if c.start <= prev.end and c.reason == prev.reason:
                prev.end = max(prev.end, c.end)
                prev.removed_words.extend(c.removed_words)
                prev.end_word_idx = max(prev.end_word_idx, c.end_word_idx)
            else:
                merged_cuts.append(c)

        return merged_cuts
