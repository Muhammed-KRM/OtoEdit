"""
OtoEdit 3-Aşamalı Çok Ajanlı Transkript Denetçisi ve İteratif Retake Doğrulama Motoru (Transcript Verifier V4)
Kullanıcının tasarladığı Çok Ajanlı 3-Tur Doğrulama Mimarisi:
- 1. AŞAMA (Paralel Parça Ajanları): Videoyu uzunluğa göre sessizlik sınırlarından parçalara böler.
  Her parçada kelime indeksleri ([W0000..Wn]) ve ses enerjisi etiketleriyle tekrar gruplarını (GRP_xxx)
  ve tüm aday okumaları (doğrusu dahil) çıkarır.
- 2. AŞAMA (Çok Kriterli Seçici & Bağlam Ek Yeri Kontrolü): Her tekrar grubunda seçilen adayı;
  (a) önceki ve sonraki cümle ile dilbilgisel/anlamsal uyum,
  (b) kelimenin yarıda kesilip kesilmediği,
  (c) ses tonu / RMS enerji tutarlılığı
  kriterleriyle puanlar ve [Önceki Cümle + Seçilen Tekrar + Sonraki Cümle] birleşimini kontrol eder.
- 3. AŞAMA (3-Turlu Küresel Metin Kontrolü & Koyu Turuncu 'uncertain_retake' Emniyet Sübabı):
  Tüm seçilen tekrarları yerlerine yerleştirip tam metni baştan sona denetler.
  Sorun varsa 2. turda grup aday listesinden alternatif adayı dener veya yerel pencereyi yeniden tarar.
  3. tur sonunda hâlâ %100 emin olunamayan kesimleri 'uncertain_retake' (Editörde Koyu Turuncu) olarak işaretler.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple, Set
import difflib
import re
from models.edl_model import CutItem
from models.transcript_model import TranscriptResult
from pipeline.audio_analysis import AudioAnalysis
from pipeline.take_aligner import TakeAligner, RetakeGroup, TakeCandidate
from services.gemini_client import GeminiClient
from utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptVerifier:
    """Çok ajanlı, 3-turlu iteratif anlamsal kurgu ve retake doğrulama motoru."""

    UNCERTAIN_CONFIDENCE_THRESHOLD = 0.78
    MAX_VERIFICATION_PASSES = 3

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()
        self.aligner = TakeAligner()

    @staticmethod
    def _extract_flat_words(transcript: TranscriptResult) -> List[Dict[str, Any]]:
        """Transkriptten kelime düzeyinde [W0000..Wn] listesini çıkarır ve sınır örtüşmelerini tekilleştirir."""
        raw_candidates: List[Tuple[str, float, float]] = []
        raw_words = getattr(transcript, "words", None) or []
        if raw_words:
            for w in raw_words:
                if isinstance(w, dict):
                    wt = str(w.get("word", "")).strip()
                    ws = float(w.get("start", 0.0))
                    we = float(w.get("end", ws))
                else:
                    wt = str(getattr(w, "word", "")).strip()
                    ws = float(getattr(w, "start", 0.0))
                    we = float(getattr(w, "end", ws))
                if wt and we >= ws:
                    raw_candidates.append((wt, ws, we))
        else:
            for seg in getattr(transcript, "segments", []) or []:
                seg_words = getattr(seg, "words", None) if not isinstance(seg, dict) else seg.get("words")
                if seg_words:
                    for w in seg_words:
                        wt = str(w.get("word", "") if isinstance(w, dict) else getattr(w, "word", "")).strip()
                        ws = float(w.get("start", 0.0) if isinstance(w, dict) else getattr(w, "start", 0.0))
                        we = float(w.get("end", ws) if isinstance(w, dict) else getattr(w, "end", ws))
                        if wt and we >= ws:
                            raw_candidates.append((wt, ws, we))

        raw_candidates.sort(key=lambda item: (item[1], -item[2]))
        flat: List[Dict[str, Any]] = []
        for wt, ws, we in raw_candidates:
            if flat:
                prev = flat[-1]
                ps, pe = prev["start"], prev["end"]
                ov = min(we, pe) - max(ws, ps)
                wn = TakeAligner.normalize_word(wt)
                pn = TakeAligner.normalize_word(prev["word"])
                if wn and wn == pn and (abs(ws - ps) <= 0.20 or ov > 0.02):
                    continue
                if pe > ws and wn != pn:
                    mid = round(max(ps + 0.04, min(pe, 0.5 * (pe + ws))), 3)
                    prev["end"] = mid
                    if we > mid + 0.02:
                        ws = mid
            flat.append({"id": len(flat), "word": wt, "start": ws, "end": we})
        return flat

    @staticmethod
    def _compute_word_rms(w_start: float, w_end: float, analysis: Optional[AudioAnalysis]) -> float:
        """Kelimenin ortalama RMS ses enerjisini hesaplar."""
        if analysis is None or analysis.rms_envelope is None or len(analysis.rms_envelope) == 0:
            return 0.5
        hop = analysis.rms_hop_ms / 1000.0
        i0 = max(0, int(w_start / hop))
        i1 = min(len(analysis.rms_envelope), max(i0 + 1, int(w_end / hop) + 1))
        sub = analysis.rms_envelope[i0:i1]
        return float(sub.mean()) if len(sub) > 0 else 0.0

    @classmethod
    def _is_protected_speech_island_hallucination(
        cls,
        words_slice: List[Dict[str, Any]],
        all_words: List[Dict[str, Any]],
        analysis: Optional[AudioAnalysis],
    ) -> bool:
        """
        Whisper bazen uzun sessizlikler arasındaki gerçek konuşma adacıklarının (3s-12s) üzerine
        yanlışlıkla 'İzlediğiniz için teşekkürler' veya 'Bu dizinin betimlemesi TRT tarafından
        Sesli Betimleme Derneğine yaptırılmıştır' yazar (Örn: 626.3s, 2655.2s, 2990.8s, 3083.5s).
        Eğer bu bölgede gerçek konuşma enerjisi varsa ve hemen yanında stüdyo sohbeti ('lan ne çabuk oldu')
        yoksa, bu gerçek konuşma adacığını KESİNLİKLE KORUR!
        """
        if not words_slice:
            return False
        text_norm = TakeAligner.normalize_word(" ".join(w["word"] for w in words_slice))
        is_suspected_phrase = (
            "izlediğiniz için teşekkür" in text_norm
            or "sesli betimleme derneğine" in text_norm
            or "trt tarafından" in text_norm
        )
        if not is_suspected_phrase:
            return False

        s_sec = words_slice[0]["start"]
        e_sec = words_slice[-1]["end"]
        # Stüdyo meta konuşmasına (örn. 3896s 'lan ne çabuk oldu söyle hadi iş var') yakınsa koruma!
        nearby_words = [
            w["word"] for w in all_words
            if abs(w["start"] - e_sec) <= 15.0 or abs(s_sec - w["end"]) <= 15.0
        ]
        nearby_norm = TakeAligner.normalize_word(" ".join(nearby_words))
        if any(k in nearby_norm for k in ("ne çabuk oldu", "söyle hadi", "iş var", "tamam söyleyeyim", "baştan al")):
            return False

        # Ses enerjisi varsa gerçek konuşma adasıdır -> Koru!
        if analysis is not None:
            rms_val = cls._compute_word_rms(s_sec, e_sec, analysis)
            if rms_val > 0.008:
                return True
        return True

    def _partition_into_silence_bounded_chunks(
        self,
        words: List[Dict[str, Any]],
        video_duration: float,
    ) -> List[List[Dict[str, Any]]]:
        """
        Videonun uzunluğuna göre kelimeleri doğal uzun sessizlik sınırlarından (>= 1.8s)
        parçalara (chunk) ayırır. Tekrarların parça sınırında bölünmemesi için 12 kelimelik örtüşme bırakır.
        """
        if not words:
            return []
        target_chunk_words = 260 if video_duration > 1200 else (180 if video_duration > 300 else 140)
        overlap_words = 12
        chunks: List[List[Dict[str, Any]]] = []
        start_idx = 0
        n = len(words)

        while start_idx < n:
            end_idx = min(n, start_idx + target_chunk_words)
            if end_idx < n:
                # end_idx civarında en uzun sessizlik boşluğunu (>= 1.5s) bul ve oradan böl
                best_split = end_idx
                best_gap = -1.0
                search_lo = max(start_idx + 60, end_idx - 45)
                search_hi = min(n - 1, end_idx + 45)
                for k in range(search_lo, search_hi):
                    gap = words[k + 1]["start"] - words[k]["end"]
                    if gap > best_gap:
                        best_gap = gap
                        best_split = k + 1
                end_idx = best_split

            chunks.append(words[start_idx:end_idx])
            if end_idx >= n:
                break
            start_idx = max(start_idx + 40, end_idx - overlap_words)

        return chunks

    def _run_chunk_detector_agent(
        self,
        chunk_idx: int,
        chunk_words: List[Dict[str, Any]],
        already_cut_ids: Set[int],
        analysis: Optional[AudioAnalysis],
    ) -> List[Dict[str, Any]]:
        """
        1. AŞAMA PARÇA AJANI:
        Kendi parçasındaki kelimeleri inceler; kalan dil sürçmelerini, yarım bırakılan cümleleri
        veya tekrarları grup ID'si ile döndürür.
        """
        alive = [w for w in chunk_words if w["id"] not in already_cut_ids]
        if len(alive) < 5 or not self.gemini or not self.gemini.is_available():
            return []

        # Yalnızca içinde şüpheli duraksama, yarım cümle veya benzer kök tekrarı olan parçaları LLM'e gönder
        # (Böylece temiz parçalar için gereksiz gecikme oluşmaz)
        has_potential_disfluency = False
        for i in range(len(alive) - 1):
            w_cur = alive[i]
            w_nxt = alive[i + 1]
            gap = w_nxt["start"] - w_cur["end"]
            if ".." in w_cur["word"] or (gap >= 2.0 and not w_cur["word"].endswith((".", "!", "?"))):
                has_potential_disfluency = True
                break
            if i + 2 < len(alive) and self.aligner.is_word_match(w_cur["word"], alive[i + 2]["word"]):
                has_potential_disfluency = True
                break

        if not has_potential_disfluency:
            return []

        tokens_str_parts: List[str] = []
        for idx_a, w in enumerate(alive):
            if idx_a > 0:
                gap = w["start"] - alive[idx_a - 1]["end"]
                if gap >= 1.5:
                    tokens_str_parts.append(f"<SESSIZLIK:{gap:.1f}s>")
            tokens_str_parts.append(f"[W{w['id']:04d}] {w['word']}")

        chunk_transcript = " ".join(tokens_str_parts)
        prompt = (
            "Sen OtoEdit Çok Ajanlı Retake (Tekrar ve Dil Sürçmesi) Tespit Ajanısın (Parça #"
            f"{chunk_idx + 1}).\n"
            "Aşağıdaki konuşma metninde her kelime [W0000] formatında numaralandırılmıştır ve "
            "aradaki uzun duraksamalar <SESSIZLIK:Xs> olarak gösterilmiştir.\n\n"
            "GÖREVİN:\n"
            "1. Konuşmacının dilinin sürçtüğü, kelimeyi yarıda bıraktığı veya aynı cümleyi/ibareyi birden fazla kez okuduğu "
            "yerleri tespit et.\n"
            "2. Her tekrar grubuna bir grup adı (örn. 'GRP_A1') ver ve elenmesi gereken hatalı okumanın başlangıç-bitiş "
            "kelime ID'lerini (cut_start_word_id, cut_end_word_id) ve korunan doğru okumanın başlangıç-bitiş kelime ID'lerini "
            "(keep_start_word_id, keep_end_word_id) belirt.\n"
            "3. ÇOK ÖNEMLİ: Eğer konuşmacı 1. denemede cümlenin başını doğru okuyup ortasında takıldıysa ve 2. denemede "
            "cümlenin ortasından devam ettiyse, 1. denemenin sağlam başlangıç kelimelerini KESME; sadece takıldığı kelimeden "
            "itibaren kes!\n"
            "4. Tamamlanmış, anlamlı ve tekrar edilmemiş normal cümleleri KESİNLİKLE KESME!\n"
            "5. Emin olma dereceni `confidence` (0.50 ile 1.00 arası) olarak yaz.\n\n"
            "SADECE JSON dizisi döndür (hiçbir sorun yoksa [] döndür):\n"
            '[{"group_id":"GRP_A1","cut_start_word_id":12,"cut_end_word_id":15,"keep_start_word_id":16,"keep_end_word_id":22,"confidence":0.92,"reason":"Cümle yarıda bırakılıp tekrar okunmuş"}]\n\n'
            f"METİN PARÇASI:\n{chunk_transcript}"
        )

        try:
            parsed = self.gemini.generate_json(prompt, max_retries=1)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
            if isinstance(parsed, dict) and isinstance(parsed.get("groups"), list):
                return [item for item in parsed["groups"] if isinstance(item, dict)]
        except Exception as ex:
            logger.warning(f"Parça Ajanı #{chunk_idx + 1} uyarısı: {ex}")
        return []

    def _evaluate_context_splice_and_criteria(
        self,
        group: RetakeGroup,
        all_words: List[Dict[str, Any]],
        cut_word_ids: Set[int],
        analysis: Optional[AudioAnalysis],
    ) -> Tuple[float, str]:
        """
        2. AŞAMA SEÇİCİ VE BAĞLAM EK YERİ (CONTEXT SPLICE) KONTROLÜ:
        Seçilen tekrar adayını (ve varsa korunan cümle başı önekini):
        1) Önceki korunan cümle ve sonraki korunan cümle ile birleştirip anlam/ek yeri uyumunu,
        2) Kelimenin yarıda kesilip kesilmediğini (cutoff / süre),
        3) Ses tonu / RMS enerji farkını
        kontrol eder ve nihai güven puanını (confidence) hesaplar.
        """
        if not group.candidates:
            return group.confidence, group.reason_summary

        bad_cand = group.candidates[0]
        good_cand = group.candidates[-1] if len(group.candidates) > 1 else None
        score = group.confidence

        # Kriter 1: Seçilen (korunan) adayın son kelimesi çok kısa (< 50ms) veya yarıda kesilmiş mi?
        if good_cand is not None:
            good_words = [
                all_words[i]
                for i in range(good_cand.start_word_idx, min(len(all_words), good_cand.end_word_idx + 1))
            ]
            if good_words:
                last_gw = good_words[-1]
                if ".." in last_gw["word"] or (last_gw["end"] - last_gw["start"]) < 0.04:
                    score -= 0.18

                # Kriter 2: Ses tonu / RMS enerjisi önceki cümleye göre aşırı farklı mı?
                if analysis is not None:
                    good_rms = self._compute_word_rms(good_words[0]["start"], good_words[-1]["end"], analysis)
                    # Önceki 5 korunan kelimenin RMS enerjisi
                    prev_alive = [
                        w for w in all_words[:bad_cand.start_word_idx]
                        if w["id"] not in cut_word_ids
                    ][-5:]
                    if prev_alive:
                        prev_rms = self._compute_word_rms(prev_alive[0]["start"], prev_alive[-1]["end"], analysis)
                        if prev_rms > 0.01 and good_rms > 0.01:
                            ratio = max(good_rms, prev_rms) / max(0.001, min(good_rms, prev_rms))
                            if ratio > 4.5:
                                # Aşırı ses tonu / seviye sıçraması varsa belirsizlik uyarısı düş
                                score -= 0.12

                # Kriter 3: Bağlam Ek Yeri (Context Splice) Kontrolü
                # Önceki korunan son kelime ile seçilen tekrarın ilk kelimesi aynı kelimeyi üst üste bindiriyor mu?
                prev_kept = [
                    w for w in all_words[:bad_cand.start_word_idx]
                    if w["id"] not in cut_word_ids
                ]
                if prev_kept:
                    last_prev_norm = TakeAligner.normalize_word(prev_kept[-1]["word"])
                    first_good_norm = TakeAligner.normalize_word(good_words[0]["word"])
                    if last_prev_norm and last_prev_norm == first_good_norm:
                        # Ek yerinde çift kelime oluştu!
                        score -= 0.22

        return round(max(0.40, min(0.99, score)), 3), group.reason_summary

    def _run_global_three_pass_verification_loop(
        self,
        all_words: List[Dict[str, Any]],
        cut_word_ids: Set[int],
        groups: List[RetakeGroup],
        analysis: Optional[AudioAnalysis],
    ) -> Tuple[Set[int], Set[int], List[Tuple[int, int, str, str]]]:
        """
        3. AŞAMA: 3-TURLU KÜRESEL TAM METİN KONTROLÜ VE GERİ İZLEME (BACKTRACKING) DÖNGÜSÜ:
        Tüm tekrarlar yerlerine yerleştirildikten sonra oluşan nihai metni baştan sona inceler.
        - Tur 1 & Tur 2: Birleştirilmiş metinde hâlâ yan yana kalan tekrarlar (n-gram / cümle tekrarı)
          veya grup seçimi kaynaklı ek yeri hatası varsa tespit eder ve düzeltir.
        - Tur 3 Sonu: 3. turda da emin olunamayan veya sınırda kalan bölgeler varsa daha fazla uzatmadan
          bunları 'uncertain_retake' (Editörde Koyu Turuncu) olarak işaretler.
        """
        uncertain_word_ids: Set[int] = set()
        extra_cuts: List[Tuple[int, int, str, str]] = []

        for pass_num in range(1, self.MAX_VERIFICATION_PASSES + 1):
            kept_stream = [w for w in all_words if w["id"] not in cut_word_ids]
            if len(kept_stream) < 4:
                break

            issues_found = 0
            idx = 0
            while idx < len(kept_stream) - 2:
                w_a = kept_stream[idx]
                w_b = kept_stream[idx + 1]
                norm_a = TakeAligner.normalize_word(w_a["word"])
                norm_b = TakeAligner.normalize_word(w_b["word"])

                # 1. Birleştirme (Splice) sonrası yan yana düşmüş ikili/üçlü kelime tekrarı kontrolü
                if (
                    idx + 3 < len(kept_stream)
                    and self.aligner.is_word_match(w_a["word"], kept_stream[idx + 2]["word"])
                    and self.aligner.is_word_match(w_b["word"], kept_stream[idx + 3]["word"])
                ):
                    w_c = kept_stream[idx + 2]
                    if (w_c["start"] - w_b["end"]) <= 25.0:
                        cut_word_ids.add(w_a["id"])
                        cut_word_ids.add(w_b["id"])
                        reason_tag = "smart_retake" if pass_num < 3 else "uncertain_retake"
                        if reason_tag == "uncertain_retake":
                            uncertain_word_ids.add(w_a["id"])
                            uncertain_word_ids.add(w_b["id"])
                        extra_cuts.append((
                            w_a["id"],
                            w_b["id"],
                            reason_tag,
                            f"[Tur-{pass_num} Küresel Kontrol] Kalan İkili Tekrar: '{w_a['word']} {w_b['word']}'",
                        ))
                        issues_found += 1
                        idx += 2
                        continue

                # 2. Birleştirme sonrası yan yana düşmüş tekil kelime tekrarı ("onun ... onun", "ve ... ve")
                if norm_a and norm_a == norm_b and len(norm_a) >= 2:
                    gap = w_b["start"] - w_a["end"]
                    if 0.18 <= gap <= 12.0:
                        cut_word_ids.add(w_a["id"])
                        reason_tag = "smart_retake" if pass_num < 3 else "uncertain_retake"
                        if reason_tag == "uncertain_retake":
                            uncertain_word_ids.add(w_a["id"])
                        extra_cuts.append((
                            w_a["id"],
                            w_a["id"],
                            reason_tag,
                            f"[Tur-{pass_num} Küresel Kontrol] Ek Yeri Kelime Tekrarı: '{w_a['word']}'",
                        ))
                        issues_found += 1
                        idx += 1
                        continue

                idx += 1

            logger.info(
                f"🔍 [Retake Küresel Doğrulama - Tur {pass_num}/{self.MAX_VERIFICATION_PASSES}] "
                f"Korunan kelime: {len(kept_stream)}, Tespit edilen ek kusur: {issues_found}"
            )
            if issues_found == 0:
                # Anlam bozan hiçbir tekrar kalmadı -> Geçti!
                break

        # Grup bazlı güven puanı (confidence) eşiğin altında kalanları 'uncertain_retake' olarak işaretle
        for grp in groups:
            conf, _ = self._evaluate_context_splice_and_criteria(grp, all_words, cut_word_ids, analysis)
            grp.confidence = conf
            if conf < self.UNCERTAIN_CONFIDENCE_THRESHOLD and grp.candidates:
                bad_c = grp.candidates[0]
                for wid in range(bad_c.start_word_idx, bad_c.end_word_idx + 1):
                    uncertain_word_ids.add(wid)

        return cut_word_ids, uncertain_word_ids, extra_cuts

    def audit_transcript(
        self,
        transcript: TranscriptResult,
        analysis: Optional[AudioAnalysis] = None,
        existing_cuts: Optional[List[CutItem]] = None,
        aligner_groups: Optional[List[RetakeGroup]] = None,
    ) -> List[CutItem]:
        """
        3-Aşamalı Çok Ajanlı Retake & Semantik Doğrulama Hattını çalıştırır.
        Elenen kısımları 'smart_retake' (Sarı) veya 3. tur sonunda belirsiz kalanları
        'uncertain_retake' (Koyu Turuncu) CutItem listesi olarak döndürür.
        """
        all_words = self._extract_flat_words(transcript)
        if len(all_words) < 3:
            return []

        video_duration = float(getattr(transcript, "duration", 0.0) or (all_words[-1]["end"] if all_words else 0.0))
        existing_cuts = existing_cuts or []

        # Zaten retake olarak kesilmiş kelime ID'lerini belirle
        already_cut_ids: Set[int] = set()
        for w in all_words:
            w_mid = (w["start"] + w["end"]) / 2.0
            if any(
                c.start - 0.02 <= w_mid <= c.end + 0.02
                for c in existing_cuts
                if "retake" in (c.reason or "")
            ):
                already_cut_ids.add(w["id"])

        # ------------------------------------------------------------------
        # 1. AŞAMA: SESSİZLİK-SINIRLI PARÇALAMA VE PARALEL PARÇA AJANLARI
        # ------------------------------------------------------------------
        chunks = self._partition_into_silence_bounded_chunks(all_words, video_duration)
        logger.info(
            f"🧠 3-Aşamalı Çok Ajanlı Retake Denetimi başlıyor: "
            f"{len(all_words)} kelime, {len(chunks)} sessizlik-sınırlı parça..."
        )

        agent_findings: List[Dict[str, Any]] = []
        if self.gemini and self.gemini.is_available() and chunks:
            max_workers = min(4, len(chunks))
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        self._run_chunk_detector_agent,
                        c_idx,
                        c_words,
                        already_cut_ids,
                        analysis,
                    ): c_idx
                    for c_idx, c_words in enumerate(chunks)
                }
                for fut in as_completed(futures):
                    try:
                        res = fut.result()
                        if res:
                            agent_findings.extend(res)
                    except Exception as ex:
                        logger.warning(f"Paralel parça ajanı hatası: {ex}")

        groups: List[RetakeGroup] = list(aligner_groups or [])
        new_cuts: List[CutItem] = []

        # Parça ajanlarının bulduğu yeni tekrar gruplarını doğrula ve ekle
        for idx_f, item in enumerate(agent_findings, start=1):
            try:
                cs_id = int(item.get("cut_start_word_id", -1))
                ce_id = int(item.get("cut_end_word_id", -1))
                ks_id = int(item.get("keep_start_word_id", -1))
                ke_id = int(item.get("keep_end_word_id", -1))
                conf = float(item.get("confidence", 0.80) or 0.80)
                reason_txt = str(item.get("reason", "AI Semantik Tekrar")).strip()
                grp_id = str(item.get("group_id", f"GRP_AI_{idx_f:02d}"))
            except Exception:
                continue

            if not (0 <= cs_id <= ce_id < len(all_words)):
                continue
            if (ce_id - cs_id) > 25:
                # Güvenlik sınırı: Tek seferde 25 kelimeden uzun tam paragraf silinmesini engelle
                continue

            slice_words = [all_words[i] for i in range(cs_id, ce_id + 1) if i not in already_cut_ids]
            if not slice_words:
                continue

            # Gerçek konuşma adası koruması ("İzlediğiniz için teşekkürler" / "TRT Sesli Betimleme")
            if self._is_protected_speech_island_hallucination(slice_words, all_words, analysis):
                logger.info(
                    f"🛡️ Gerçek konuşma adası korundu (AI silme talebi reddedildi): "
                    f"[{slice_words[0]['start']:.2f}s - {slice_words[-1]['end']:.2f}s]"
                )
                continue

            # Eğer keep_start_word_id verilmişse, silinen kısım ile korunan kısım arasında
            # gerçekten kelime/kök benzerliği veya yarım kalmışlık olduğundan emin ol
            is_verified_repeat = False
            if 0 <= ks_id <= ke_id < len(all_words):
                keep_words = [all_words[i] for i in range(ks_id, ke_id + 1)]
                if keep_words:
                    # 1. Silinen kısım ile korunan kısım zamanda örtüşüyorsa (GapFiller sınır kopyası), ASLA kesme!
                    ov_time = min(slice_words[-1]["end"], keep_words[-1]["end"]) - max(slice_words[0]["start"], keep_words[0]["start"])
                    # 2. Silinen tekrar adayı korunan adaydan önce gelmeli (cs_id < ks_id) ve aralarındaki mesafe <= 25s olmalı
                    # (Örn: 4166s 'Hoşçakalın' yüzünden 52 saniye sonraki 4218s gerçek 'Hoşçakalın.' kapanışı silinemez!)
                    time_dist = keep_words[0]["start"] - slice_words[-1]["end"]
                    if ov_time <= 0.04 and cs_id < ks_id and -0.05 <= time_dist <= 25.0:
                        cut_txt = " ".join(TakeAligner.normalize_word(w["word"]) for w in slice_words)
                        keep_txt = " ".join(TakeAligner.normalize_word(w["word"]) for w in keep_words)
                        sim = difflib.SequenceMatcher(None, cut_txt, keep_txt).ratio()
                        if sim >= 0.45 or any(
                            self.aligner.is_word_match(sw["word"], kw["word"])
                            for sw in slice_words[:2]
                            for kw in keep_words[:3]
                        ):
                            is_verified_repeat = True
            elif ".." in slice_words[-1]["word"]:
                is_verified_repeat = True
                conf = min(conf, 0.75)  # Tek başına yarım kalmış ('...') parça ise belirsiz (uncertain) aday yap

            if not is_verified_repeat:
                continue

            c_start = slice_words[0]["start"]
            c_end = slice_words[-1]["end"] + 0.02
            if analysis is not None:
                c_start = analysis.find_energy_minimum(c_start, search_window_sec=0.025, direction="backward_only")
                c_end = analysis.find_energy_minimum(c_end, search_window_sec=0.025, direction="forward_only")

            # Korunan komşu kelimelerle (veya zamanı örtüşen gerçek konuşma kelimeleriyle) çarpışmayı önle!
            slice_id_set = {sw["id"] for sw in slice_words}
            for other_w in all_words:
                oid = other_w["id"]
                if oid in slice_id_set or oid in already_cut_ids:
                    continue
                os_t, oe_t = other_w["start"], other_w["end"]
                if os_t < c_end and oe_t > c_start:
                    # Eğer başka bir korunan kelime kesim aralığının tam içindeyse bu kesimi iptal et!
                    if os_t >= c_start - 0.05 and oe_t <= c_end + 0.05:
                        c_end = c_start
                        break
                    elif os_t < c_start and oe_t > c_start:
                        c_start = max(c_start, oe_t + 0.01)
                    elif os_t < c_end and oe_t > c_end:
                        c_end = min(c_end, os_t - 0.01)

            if (c_end - c_start) < 0.08:
                continue

            for sw in slice_words:
                already_cut_ids.add(sw["id"])

            cand_bad = TakeCandidate(
                candidate_id=f"{grp_id}_T1",
                start_word_idx=slice_words[0]["id"],
                end_word_idx=slice_words[-1]["id"],
                start=slice_words[0]["start"],
                end=slice_words[-1]["end"],
                text=" ".join(w["word"] for w in slice_words),
                fluency_score=0.40,
            )
            cands = [cand_bad]
            if 0 <= ks_id <= ke_id < len(all_words):
                kw_slice = [all_words[i] for i in range(ks_id, ke_id + 1)]
                if kw_slice:
                    cands.append(TakeCandidate(
                        candidate_id=f"{grp_id}_T2",
                        start_word_idx=kw_slice[0]["id"],
                        end_word_idx=kw_slice[-1]["id"],
                        start=kw_slice[0]["start"],
                        end=kw_slice[-1]["end"],
                        text=" ".join(w["word"] for w in kw_slice),
                        fluency_score=0.92,
                    ))

            groups.append(RetakeGroup(
                group_id=grp_id,
                candidates=cands,
                selected_candidate_id=cands[-1].candidate_id,
                confidence=conf,
                reason_summary=reason_txt,
            ))

            reason_code = "smart_retake" if conf >= self.UNCERTAIN_CONFIDENCE_THRESHOLD else "uncertain_retake"
            new_cuts.append(CutItem(
                id=f"cut_ai_retake_{cs_id}",
                start=round(c_start, 3),
                end=round(c_end, 3),
                reason=reason_code,
                source="ai_verifier",
                command=f"[{grp_id}] {reason_txt}: {' '.join(w['word'] for w in slice_words[:6])}",
            ))

        # ------------------------------------------------------------------
        # 2. & 3. AŞAMA: BAĞLAM EK YERİ KONTROLÜ VE 3-TURLU KÜRESEL TAM METİN DOĞRULAMA DÖNGÜSÜ
        # ------------------------------------------------------------------
        _, uncertain_word_ids, loop_extra_cuts = self._run_global_three_pass_verification_loop(
            all_words=all_words,
            cut_word_ids=already_cut_ids,
            groups=groups,
            analysis=analysis,
        )

        for idx_le, (ws_id, we_id, r_tag, cmd_txt) in enumerate(loop_extra_cuts, start=1):
            c_start = all_words[ws_id]["start"]
            c_end = all_words[we_id]["end"] + 0.02
            if analysis is not None:
                c_start = analysis.find_energy_minimum(c_start, search_window_sec=0.025, direction="backward_only")
                c_end = analysis.find_energy_minimum(c_end, search_window_sec=0.025, direction="forward_only")
            new_cuts.append(CutItem(
                id=f"cut_pass3_{idx_le}_{ws_id}",
                start=round(c_start, 3),
                end=round(c_end, 3),
                reason=r_tag,
                source="ai_verifier",
                command=cmd_txt,
            ))

        # Mevcut kesimler içinde 3. tur sonunda belirsiz (uncertain) olarak işaretlenenlerin reason değerini güncelle
        if uncertain_word_ids and existing_cuts:
            for ec in existing_cuts:
                if "retake" in (ec.reason or ""):
                    for wid in uncertain_word_ids:
                        w = all_words[wid]
                        w_mid = (w["start"] + w["end"]) / 2.0
                        if ec.start - 0.02 <= w_mid <= ec.end + 0.02:
                            ec.reason = "uncertain_retake"
                            if ec.command and "[Belirsiz Retake]" not in ec.command:
                                ec.command = f"[Belirsiz Retake] {ec.command}"
                            break

        logger.info(
            f"✅ 3-Aşamalı Çok Ajanlı Retake Denetimi tamamlandı: "
            f"{len(new_cuts)} ek kesim üretildi, {len(uncertain_word_ids)} belirsiz kelime işaretlendi."
        )
        return new_cuts
