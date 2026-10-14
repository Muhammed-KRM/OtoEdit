"""
OtoEdit TakeAligner (Take-Aware Restart and Retake Detector)
Hatalı okumaları, cümle içi yeniden başlamaları (restarts), yarım kalan denemeleri
ve stüdyo dışı konuşmaları kelime zaman damgaları üzerinden deterministik olarak tespit eder.

Kural: Okuma ve ders videolarında her zaman son (başarılı) take korunur,
önceki başarısız denemeler ve aradaki duraklamalar budanır.
"""
from typing import List, Dict, Any, Tuple, Optional, Set
import re
import difflib
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WordRef:
    word: str
    start: float
    end: float
    confidence: float = 1.0
    index: int = 0


@dataclass
class SpeechChunk:
    words: List[WordRef]
    start: float
    end: float
    text: str
    index: int


@dataclass
class RetakeCut:
    start: float
    end: float
    reason: str
    command: str
    removed_words: List[str]


class TakeAligner:
    """Kelime zaman damgaları ve duraklama sınırları üzerinden Take analizi yapan motor."""

    CONNECTORS = {
        "hatta", "yani", "fakat", "ama", "şimdi", "tabii",
        "peki", "işte", "ve", "de", "da", "çünkü", "ayrıca"
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
        r'\bbastan\b'
    ]

    HALUCINATION_PATTERNS = [
        r'\baltyazı\s*m\.?k\.?\b',
        r'\babone\s*ol\b',
        r'\bbeğenmeyi\s*unutmayın\b',
        r'\bmısır,?\s*diber,?\s*çay\b'
    ]

    def __init__(
        self,
        chunk_gap_threshold: float = 0.50,
        similarity_threshold: float = 0.75,
        tail_coverage_threshold: float = 0.55,
        max_lookback_words: int = 30,
        max_lookback_sec: float = 25.0,
        max_cut_duration: float = 40.0
    ):
        self.chunk_gap_threshold = chunk_gap_threshold
        self.similarity_threshold = similarity_threshold
        self.tail_coverage_threshold = tail_coverage_threshold
        self.max_lookback_words = max_lookback_words
        self.max_lookback_sec = max_lookback_sec
        self.max_cut_duration = max_cut_duration

    @staticmethod
    def normalize_word(text: str) -> str:
        """Türkçe kurallı harf sadeleştirmesi ve noktalama temizliği."""
        if not text:
            return ""
        t = text.strip()
        t = t.replace("İ", "i").replace("I", "ı").lower()
        t = t.replace("â", "a").replace("î", "i").replace("û", "u")
        t = re.sub(r'[^\w\s]', '', t)
        return t

    def is_word_match(self, w1: str, w2: str) -> bool:
        """
        Türkçe sondan eklemeli dil tuzağını önleyen kelime benzerlik testi:
        - difflib benzerliği >= threshold
        - VE (ilk 3 harf aynı VEYA Levenshtein mesafesi <= 1)
        """
        nw1 = self.normalize_word(w1)
        nw2 = self.normalize_word(w2)
        if not nw1 or not nw2:
            return False
        if nw1 == nw2:
            return True

        # Uzunluk farkı çok büyükse eşleşmez
        if abs(len(nw1) - len(nw2)) > 3:
            return False

        ratio = difflib.SequenceMatcher(None, nw1, nw2).ratio()
        if ratio < self.similarity_threshold:
            return False

        # İlk 3 harf uyumu (kök başlangıcı) veya 1 harf farkı (örn: bürhandır / hürhandır)
        prefix_len = min(3, len(nw1), len(nw2))
        prefix_match = (nw1[:prefix_len] == nw2[:prefix_len])

        edit_dist_approx = abs(len(nw1) - len(nw2)) + (1 if nw1[0] != nw2[0] else 0)
        return prefix_match or (ratio >= 0.80 and edit_dist_approx <= 1)

    def is_meta_speech(self, text: str) -> bool:
        norm = self.normalize_word(text)
        return any(re.search(pat, norm) for pat in self.META_PATTERNS)

    def is_hallucination(self, text: str) -> bool:
        norm = self.normalize_word(text)
        return any(re.search(pat, norm) for pat in self.HALUCINATION_PATTERNS)

    def split_into_chunks(self, words: List[WordRef]) -> List[SpeechChunk]:
        """Kelimeleri duraklama sınırlarına (gap >= chunk_gap_threshold) göre konuşma öbeklerine ayırır."""
        if not words:
            return []

        chunks: List[SpeechChunk] = []
        cur_words: List[WordRef] = [words[0]]

        for w in words[1:]:
            prev_w = cur_words[-1]
            gap = w.start - prev_w.end
            if gap >= self.chunk_gap_threshold:
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

    def detect_retakes(self, raw_words: List[Any]) -> List[RetakeCut]:
        """
        Kelime listesi üzerinden tüm retake, restart ve yarım okuma kesimlerini hesaplar.
        raw_words: Word nesneleri veya dict listesi.
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
                words.append(WordRef(word=w_text, start=w_start, end=w_end, confidence=w_conf, index=idx))

        if len(words) < 2:
            return []

        chunks = self.split_into_chunks(words)
        cuts: List[RetakeCut] = []
        num_chunks = len(chunks)
        cut_word_indices: Set[int] = set()

        # 1. Aşama: Meta konuşma ve Halüsinasyon öbekleri
        for c in chunks:
            if self.is_meta_speech(c.text) or self.is_hallucination(c.text):
                cuts.append(RetakeCut(
                    start=c.start,
                    end=c.end,
                    reason="smart_retake",
                    command=f"Stüdyo Outtake / Halüsinasyon: {c.text}",
                    removed_words=[w.word for w in c.words]
                ))
                for w in c.words:
                    cut_word_indices.add(w.index)

        # 2. Aşama: Sağdan Sola (Right-Anchored) Restart / Retake Hizalama
        # Başarılı son okumayı (R) baz alarak, geride kalan başarısız tekrarları (L) bul
        for r_chunk_idx in range(1, num_chunks):
            r_chunk = chunks[r_chunk_idx]
            if not r_chunk.words or r_chunk.words[0].index in cut_word_indices:
                continue

            # R'nin başındaki kelimeleri al (0..2 bağlaç toleransı ile)
            r_words = r_chunk.words
            r_eval_start_idx = 0
            if len(r_words) > 1 and self.normalize_word(r_words[0].word) in self.CONNECTORS:
                r_eval_start_idx = 1
                if len(r_words) > 2 and self.normalize_word(r_words[1].word) in self.CONNECTORS:
                    r_eval_start_idx = 2

            r_probe_words = r_words[r_eval_start_idx:]
            if not r_probe_words:
                continue

            # R'nin öncesindeki kelimeler havuzunu geriye doğru topla
            # max_lookback_words ve max_lookback_sec sınırları içinde
            prior_words: List[WordRef] = []
            for l_chunk_idx in range(r_chunk_idx - 1, -1, -1):
                prev_chunk = chunks[l_chunk_idx]
                for w in reversed(prev_chunk.words):
                    if w.index in cut_word_indices:
                        continue
                    if len(prior_words) >= self.max_lookback_words:
                        break
                    if (r_chunk.start - w.start) > self.max_lookback_sec:
                        break
                    prior_words.append(w)
                if len(prior_words) >= self.max_lookback_words or (prior_words and (r_chunk.start - prior_words[-1].start) > self.max_lookback_sec):
                    break

            if not prior_words:
                continue

            prior_words.reverse()  # Kronolojik sıraya geri çevir

            # prior_words içinde R'nin başı ile eşleşen öbek ara
            best_match: Optional[Tuple[int, int]] = None  # (start_in_prior, match_length)
            best_score = 0

            # Farklı probe uzunluklarını dene (en az 2 kelime, ya da 1 kelime + uzun duraklama)
            max_probe_k = min(len(r_probe_words), 8)

            for p_idx in range(len(prior_words)):
                # Eşleşen kelime sayısını say
                k = 0
                while k < max_probe_k and (p_idx + k) < len(prior_words):
                    pw = prior_words[p_idx + k]
                    rw = r_probe_words[k]
                    if self.is_word_match(pw.word, rw.word):
                        k += 1
                    else:
                        break

                if k >= 2 or (k == 1 and len(self.normalize_word(r_probe_words[0].word)) >= 4):
                    # Kuyruk kapsaması kontrolü:
                    # prior_words'teki eşleşmeden sonra P'ye kadar olan kısım, R'de tekrar edilmiş mi?
                    tail_prior = prior_words[p_idx + k:]
                    tail_prior_text = " ".join(self.normalize_word(w.word) for w in tail_prior)
                    
                    tail_r = r_probe_words[k: k + len(tail_prior) + 3]
                    tail_r_text = " ".join(self.normalize_word(w.word) for w in tail_r)

                    coverage_ok = False
                    if not tail_prior_text:
                        # Tam tekrar başlangıcı, arkasından hemen durulmuş
                        coverage_ok = True
                    else:
                        # Kuyruk en fazla 15 kelime olmalı ve R'de bulunmalı
                        if len(tail_prior) <= 15:
                            cov_ratio = difflib.SequenceMatcher(None, tail_prior_text, tail_r_text).ratio()
                            if cov_ratio >= self.tail_coverage_threshold:
                                coverage_ok = True

                    if coverage_ok:
                        score = k * 10 + (10 - len(tail_prior))
                        if score > best_score:
                            best_score = score
                            best_match = (p_idx, k)

            if best_match is not None:
                p_idx, k = best_match
                match_start_word = prior_words[p_idx]

                # Eğer R'nin başında bağlaç(lar) atlandıysa ve prior_words'ün eşleşme öncesinde de
                # aynı bağlaç(lar) söylenmişse, kesim başlangıcını o bağlacın başına çek (R'deki bağlaç korunur)
                if r_eval_start_idx > 0:
                    for back_i in range(1, r_eval_start_idx + 1):
                        cand_prior_idx = p_idx - back_i
                        cand_r_idx = r_eval_start_idx - back_i
                        if cand_prior_idx >= 0 and cand_r_idx >= 0:
                            if self.is_word_match(prior_words[cand_prior_idx].word, r_words[cand_r_idx].word):
                                match_start_word = prior_words[cand_prior_idx]
                
                # Kesim: L'deki eşleşmenin ilk kelimesinden, R'nin başlangıcına kadar
                # (R'nin başındaki bağlaç da korunur)
                cut_start = match_start_word.start
                cut_end = r_chunk.words[0].start
                cut_duration = cut_end - cut_start

                if 0.20 <= cut_duration <= self.max_cut_duration:
                    # Bu aralıktaki kelimeleri topla
                    removed_w = [
                        w for w in words
                        if w.start >= cut_start - 0.05 and w.end <= cut_end + 0.05 and w.index not in cut_word_indices
                    ]
                    
                    if removed_w:
                        for rw in removed_w:
                            cut_word_indices.add(rw.index)

                        cuts.append(RetakeCut(
                            start=round(cut_start, 3),
                            end=round(cut_end, 3),
                            reason="smart_retake",
                            command=f"Elenen Tekrar ({len(removed_w)} kelime): {' '.join(rw.word for rw in removed_w[:8])}...",
                            removed_words=[rw.word for rw in removed_w]
                        ))
                        logger.info(
                            f"🔁 Retake tespit edildi: [{cut_start:.2f}s - {cut_end:.2f}s] "
                            f"({cut_duration:.1f}s) | Silinen: '{' '.join(rw.word for rw in removed_w[:5])}...'"
                        )

        # 3. Aşama: Yarım Başlangıçlar (False Starts)
        # 1-3 kelimelik kısa bir öbek + ardından >= 2.0s duraklama + ve sonrasında
        # aynı/benzer bağlamla yeniden başlama varsa o küçük adacığı kes
        for c_idx in range(len(chunks) - 1):
            cur_c = chunks[c_idx]
            next_c = chunks[c_idx + 1]

            if any(w.index in cut_word_indices for w in cur_c.words):
                continue
            if any(w.index in cut_word_indices for w in next_c.words):
                continue

            gap = next_c.start - cur_c.end
            if len(cur_c.words) <= 3 and gap >= 2.0:
                # cur_c kelimelerinden biri next_c'de tekrar ediyor mu?
                first_cur = self.normalize_word(cur_c.words[0].word)
                first_next = self.normalize_word(next_c.words[0].word)

                is_repeat = (first_cur == first_next) or (
                    len(next_c.words) > 1 and first_cur == self.normalize_word(next_c.words[1].word)
                )

                if is_repeat or len(cur_c.words) == 1:
                    cut_start = cur_c.start
                    cut_end = next_c.start
                    for rw in cur_c.words:
                        cut_word_indices.add(rw.index)
                    cuts.append(RetakeCut(
                        start=round(cut_start, 3),
                        end=round(cut_end, 3),
                        reason="smart_retake",
                        command=f"Yarım Başlangıç (False Start): {cur_c.text}",
                        removed_words=[w.word for w in cur_c.words]
                    ))
                    logger.info(f"✂️ False Start kesildi: [{cut_start:.2f}s - {cut_end:.2f}s] '{cur_c.text}'")

        # Kesimleri zamanına göre sırala ve çakışanları birleştir
        cuts.sort(key=lambda c: c.start)
        merged_cuts: List[RetakeCut] = []
        for c in cuts:
            if not merged_cuts:
                merged_cuts.append(c)
                continue
            prev = merged_cuts[-1]
            if c.start <= prev.end:
                prev.end = max(prev.end, c.end)
                prev.removed_words.extend(c.removed_words)
            else:
                merged_cuts.append(c)

        return merged_cuts
