"""
5 Aşamalı Otonom Kurgu Senaryosu Motoru (ScenarioEngine).
1. SceneSegmenter: Videonun türünü belirler ve transkripte bakarak retorik [geçiş] noktalarından videoyu sahnelere (parçalara) ayırır.
2. ChunkDirector: Hız ve çökme yalıtımı (fault isolation) için her parçayı ayrı bir yapay zeka isteği olarak paralel değerlendirir.
3. ScenarioMerger: Tüm parçaların kurgu planlarını tek bir Tam Kurgu Senaryosunda (MasterEditingScript) birleştirir.
4. ScenarioCritic & ScenarioRefiner: Tam senaryoyu başka bir Başeditör/Denetçi yapay zekaya verir ("Bu edit mantıklı mı? Yazılar/resimler/yerleri doğru mu?"). Sorun varsa düzeltir ve düzeltilmiş versiyonu tekrar kontrol ettirir ("Başka sorun kaldı mı?").
5. 3. Döngü Kırıcı & İnsan-Döngüde Onay/Revizyon (Human-in-the-Loop): 3. denetimden sonra hâlâ sorun varsa döngüyü kesip kullanıcıya sorar; kullanıcı beğenirse uygular, revize verirse düzeltip tekrar kullanıcıya sorar.
"""

import concurrent.futures
import json
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from pipeline.holistic_analyzer import (
    ChapterPlan,
    PlannedEditorialEvent,
    SemanticTransitionBoundary,
    SemanticTransitionBoundaryDetector,
    VerbatimTranscriptValidator,
    WordToken,
)
from pipeline.scenario_models import (
    CritiqueReport,
    CritiqueRevision,
    MasterEditingScript,
    PlannedScenarioItem,
    SceneBoundary,
    SceneChunkPlan,
)
from pipeline.theme_profiles import (
    ThemeProfile,
    extract_turkish_semantic_title,
    to_turkish_lower,
    to_turkish_upper,
)
from utils.logger import get_logger

logger = get_logger("ScenarioEngine")


class SceneSegmenter:
    """
    Transkripti okuyup retorik dönüm noktalarından ([geçiş]) anlamlı parçalara (sahnelere) ayırır.
    Geçiş mantığı:
      - Önceki dersin özeti ve ana tez bildirimi tamamlanıp kurucu bir alıntıya/tanımlamaya geçilirken,
      - Diyalektik sorular ve dersin yol haritası ("Bugün ... inşa edeceğiz") tamamlanıp ilk alt konunun tanımlanmasına geçilirken,
      - Bir kavramı anlatmadan hemen önce tanımlama/çerçeveleme kısmına girerken veya yeni bir konuya geçerken.
    """

    # Tez / Üçlü hüküm kapanışı veya özet bitişi kalıpları
    THESIS_OR_SUMMARY_END_RE = re.compile(
        r"\b(hukukudur|iradesidir|iklimdir|menbaıdır|anasıdır|ilkesidir|esasıdır|temelidir|"
        r"incelemiştik|ele almıştık|görmüştük|özetlemiştik|tamamladık)\s*[.!]?$",
        re.IGNORECASE,
    )

    # Kurucu alıntı, otorite referansı veya tanım girişi kalıpları
    QUOTE_OR_DEFINITION_START_RE = re.compile(
        r"^([a-zçğıöşüâîû\s]{2,35}(tespitiyle|ifadesiyle|sözüyle|tarifiyle|dediği gibi|göre)|"
        r"bediüzzaman|imam gazali|aristoteles|farabi|ibn sina|nurettin topçu|thomas hobbes|"
        r"modern dünyanın|çağdaş dünyanın|klasik hukuk|beşer[iî] hukuk|kavramsal olarak|"
        r"tanım olarak|öncelikle\b|birincisi\b)",
        re.IGNORECASE,
    )

    # Yol haritası / Vaat cümlesi bitişi ("Bugün ... inşa edeceğiz / ele alacağız / inceleyeceğiz")
    ROADMAP_CLOSURE_END_RE = re.compile(
        r"\b(inşa edeceğiz|ele alacağız|inceleyeceğiz|tahlil edeceğiz|konuşacağız|"
        r"göreceğiz|açıklayacağız|değineceğiz|tartışacağız|bakacağız|ortaya koyacağız)\s*[.!]?$",
        re.IGNORECASE,
    )

    # Yeni alt konu / tanımlama başlangıcı ("Modern dünyanın ... baktığımızda", "... tarifle çizerler")
    SUBTOPIC_DEFINITION_START_RE = re.compile(
        r"^(modern dünyanın|modern çağın|tarihsel süreçte|batı düşüncesinde|islam düşüncesinde|"
        r"beşer[iî] hukuk|hukuk sistemlerine|felsefi açıdan|ilk olarak|öncelikle|"
        r"gelelim|şimdi ise|peki\b|bir diğer açıdan)",
        re.IGNORECASE,
    )

    SUBTOPIC_DEFINITION_BODY_RE = re.compile(
        r"\b(baktığımızda|incelediğimizde|döndüğümüzde|tarifle çizerler|olarak tanımlanır|"
        r"şöyle tarif edilir|şöyle tanımlanır|sınırını .* çizerler)\b",
        re.IGNORECASE,
    )

    @classmethod
    def detect_rhetorical_boundaries(
        cls,
        word_stream: List[WordToken],
        video_duration: float,
        gemini_client: Any = None,
        enable_llm: bool = True,
        min_scene_duration_sec: float = 8.0,
    ) -> Tuple[List[SceneBoundary], List[List[WordToken]]]:
        """
        Kelime akışından temiz cümleleri çıkarır, hem retorik söylem kurallarıyla hem de
        LLM sahne bölümlendirici ile [geçiş] sınırlarını tespit eder.
        """
        sentences = SemanticTransitionBoundaryDetector.build_clean_sentences(word_stream)
        if len(sentences) <= 1:
            return [], sentences

        # Kısa örneklerde kenar marjını koru; yakın adaylar arasında yüksek öncelikli tez/yol haritası geçişlerini seç
        edge_margin = 2.0 if video_duration < 60.0 else 5.0
        eff_min_gap = max(20.0, min_scene_duration_sec) if video_duration <= 600.0 else max(110.0, video_duration / 22.0)

        candidates_by_sent_idx: Dict[int, SceneBoundary] = {}

        # 1. Mevcut SemanticTransitionBoundaryDetector adaylarını al
        base_bounds = SemanticTransitionBoundaryDetector.detect_boundaries(
            word_stream, video_duration, min_gap_sec=eff_min_gap
        )

        # Cümle sonu zamanlarından cümle indeksine harita
        for i in range(len(sentences) - 1):
            sa = sentences[i]
            sb = sentences[i + 1]
            if not sa or not sb:
                continue
            ta = " ".join(w.raw for w in sa).strip()
            tb = " ".join(w.raw for w in sb).strip()
            la = to_turkish_lower(ta).rstrip(".!?:;\"'”’ ")
            lb = to_turkish_lower(tb).lstrip("\"'“‘ ")

            t_end = sa[-1].end
            t_start = sb[0].start
            t_mid = round(t_start, 2) if (t_start - t_end) > 1.2 else round((t_end + t_start) / 2.0, 2)

            if t_mid < edge_margin or t_mid > max(edge_margin + 1.0, video_duration - edge_margin):
                continue

            cat = None
            reason = ""
            score = 0.0

            # Özel Kural A: Tez / Özet kapanışı -> Kurucu Alıntı veya Tanım ("... meşveret hukukudur. [geçiş] Bediüzzaman Said Nursi'nin o çarpıcı tespitiyle...")
            if (
                cls.THESIS_OR_SUMMARY_END_RE.search(la)
                or ";" in ta
                or ("ise " in la and la.endswith(("dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür")))
            ) and (
                cls.QUOTE_OR_DEFINITION_START_RE.search(lb)
                or "tespitiyle" in lb[:65]
                or "ifadesiyle" in lb[:65]
                or "tarifiyle" in lb[:65]
            ):
                cat = "THESIS_TO_FOUNDATIONAL_QUOTE"
                score = 99.0
                reason = "Ana tez/özet bildirimi tamamlandı -> Kurucu alıntı ve kavramsal çerçevelemeye geçiş"

            # Özel Kural B: Yol Haritası Vaadi ("Bugün ... inşa edeceğiz.") -> İlk Alt Konu / Tanımlama ("Modern dünyanın beşerî hukuk sistemlerine baktığımızda...")
            elif cls.ROADMAP_CLOSURE_END_RE.search(la) and (
                cls.SUBTOPIC_DEFINITION_START_RE.search(lb)
                or cls.SUBTOPIC_DEFINITION_BODY_RE.search(lb)
                or len(sb) >= 5
            ):
                cat = "ROADMAP_TO_CONCEPT_DEFINITION"
                score = 100.0
                reason = "Ders yol haritası vaadi ('Bugün ... inşa edeceğiz') tamamlandı -> Yeni konu/kavram tanımlamasına geçiş"

            # Özel Kural C: Herhangi bir cümleden sonra doğrudan yeni bir sistem/kavram tanımlamasına giriş ("... baktığımızda, ... tarifle çizerler:")
            elif (
                cls.SUBTOPIC_DEFINITION_START_RE.search(lb)
                and cls.SUBTOPIC_DEFINITION_BODY_RE.search(lb)
                and not lb.startswith(("fakat ", "ancak ", "çünkü ", "zira "))
            ):
                cat = "NEW_CONCEPT_DEFINITION_ENTRY"
                score = 94.0
                reason = "Yeni bir kavramsal tanımlama ve karşılaştırma bölümüne giriş"

            if cat:
                candidates_by_sent_idx[i] = SceneBoundary(
                    boundary_id=f"tr_s{i + 1}",
                    timestamp=t_mid,
                    sentence_a_end=round(t_end, 2),
                    sentence_b_start=round(t_start, 2),
                    before_word_idx=sa[-1].idx,
                    after_word_idx=sb[0].idx,
                    sentence_a_preview=ta[-90:],
                    sentence_b_preview=tb[:90],
                    category=cat,
                    reason=reason,
                )

        # Base bounds'ları da cümle sınırlarına eşle
        for bb in base_bounds:
            best_i = None
            best_dist = 999.0
            for i in range(len(sentences) - 1):
                dist = abs(sentences[i][-1].end - bb.sentence_a_end)
                if dist < best_dist and dist <= 1.0:
                    best_dist = dist
                    best_i = i
            if best_i is not None and best_i not in candidates_by_sent_idx:
                sa = sentences[best_i]
                sb = sentences[best_i + 1]
                ta = " ".join(w.raw for w in sa).strip()
                tb = " ".join(w.raw for w in sb).strip()
                candidates_by_sent_idx[best_i] = SceneBoundary(
                    boundary_id=f"tr_s{best_i + 1}",
                    timestamp=round(bb.timestamp, 2),
                    sentence_a_end=round(bb.sentence_a_end, 2),
                    sentence_b_start=round(bb.sentence_b_start, 2),
                    before_word_idx=sa[-1].idx,
                    after_word_idx=sb[0].idx,
                    sentence_a_preview=ta[-90:],
                    sentence_b_preview=tb[:90],
                    category=bb.category,
                    reason=bb.reason,
                )

        # 2. LLM ile Retorik Geçiş Noktası Tespiti (Few-Shot Örnekli)
        if enable_llm and gemini_client and hasattr(gemini_client, "is_available") and gemini_client.is_available():
            try:
                llm_bounds = cls._detect_boundaries_via_llm(sentences, video_duration, gemini_client)
                for sent_idx, reason_str in llm_bounds:
                    if 0 <= sent_idx < len(sentences) - 1 and sent_idx not in candidates_by_sent_idx:
                        sa = sentences[sent_idx]
                        sb = sentences[sent_idx + 1]
                        t_end = sa[-1].end
                        t_start = sb[0].start
                        t_mid = round(t_start, 2) if (t_start - t_end) > 1.2 else round((t_end + t_start) / 2.0, 2)
                        if edge_margin <= t_mid <= max(edge_margin + 1.0, video_duration - edge_margin):
                            ta = " ".join(w.raw for w in sa).strip()
                            tb = " ".join(w.raw for w in sb).strip()
                            candidates_by_sent_idx[sent_idx] = SceneBoundary(
                                boundary_id=f"tr_s{sent_idx + 1}",
                                timestamp=t_mid,
                                sentence_a_end=round(t_end, 2),
                                sentence_b_start=round(t_start, 2),
                                before_word_idx=sa[-1].idx,
                                after_word_idx=sb[0].idx,
                                sentence_a_preview=ta[-90:],
                                sentence_b_preview=tb[:90],
                                category="LLM_RHETORICAL_TRANSITION",
                                reason=reason_str or "Yeni konuya veya kavramsal tanımlamaya geçiş",
                            )
            except Exception as ex:
                logger.warning(f"[SceneSegmenter] LLM geçiş tespiti uyarısı (yerel retorik kurallar kullanılıyor): {ex}")

        # Zaman sırasına göre diz ve birbirine çok yakın geçişleri sadeleştir
        sorted_candidates = [candidates_by_sent_idx[k] for k in sorted(candidates_by_sent_idx.keys())]
        filtered: List[SceneBoundary] = []
        for cand in sorted_candidates:
            if filtered and (cand.timestamp - filtered[-1].timestamp) < eff_min_gap:
                # Yüksek öncelikli özel kuralları koru
                if cand.category in ("THESIS_TO_FOUNDATIONAL_QUOTE", "ROADMAP_TO_CONCEPT_DEFINITION"):
                    filtered[-1] = cand
            else:
                filtered.append(cand)

        # Uzun sahneleri en uygun cümle sınırından böl ki parça istekleri hızlı, dengeli ve odaklı kalsın
        dynamic_max_span = 65.0 if video_duration <= 600.0 else max(75.0, video_duration / 22.0)
        final_boundaries = cls._ensure_balanced_scene_lengths(
            filtered, sentences, video_duration, max_span_sec=dynamic_max_span
        )
        for idx, b in enumerate(final_boundaries):
            b.boundary_id = f"tr_{idx + 1}"

        return final_boundaries, sentences

    @classmethod
    def _detect_boundaries_via_llm(
        cls,
        sentences: List[List[WordToken]],
        video_duration: float,
        gemini_client: Any,
    ) -> List[Tuple[int, str]]:
        """LLM'e numaralı cümleleri verip tam olarak hangi cümlelerin arasına [geçiş] konulacağını sorar."""
        if len(sentences) < 3:
            return []

        lines = []
        for idx, s in enumerate(sentences[:80]):
            txt = " ".join(w.raw for w in s)
            lines.append(f"[CÜMLE_{idx} | {s[0].start:.1f}s-{s[-1].end:.1f}s] {txt}")
        joined_sents = "\n".join(lines)

        prompt = (
            "Sen profesyonel bir video kurgu yönetmenisin. Aşağıdaki transkript cümlelerine bakarak "
            "videoda nerelerde sahne geçişi ([geçiş]) olması gerektiğini belirleyeceksin.\n\n"
            "GEÇİŞ ([geçiş]) KOYMA KURALLARI (ÖRNEK MANTIK):\n"
            "1. Giriş özeti ve ana tez cümlesi bittiğinde, bir alimin/düşünürün sözüne veya temel bir tanımlamaya geçmeden hemen önce [geçiş] konulur.\n"
            "   Örnek: '...adaleti ortak bir akılla ete kemiğe büründüren usul ise meşveret hukukudur.' -> [GEÇİŞ] -> 'Bediüzzaman Said Nursi’nin o çarpıcı tespitiyle söylersek...'\n"
            "2. Retorik sorular ve dersin yol haritası vaadi ('Bugün ... hakiki hürriyetin mimarisini inşa edeceğiz') bittiğinde, ilk alt konunun tanımlamasına girmeden hemen önce [geçiş] konulur.\n"
            "   Örnek: '...hakiki hürriyetin mimarisini inşa edeceğiz.' -> [GEÇİŞ] -> 'Modern dünyanın beşerî hukuk sistemlerine baktığımızda, hürriyetin sınırını son derece pragmatik bir tarifle çizerler...'\n"
            "3. Aynı fikri devam ettiren cümlelerin veya bir sıralamanın tam ortasına ASLA geçiş koyma.\n\n"
            f"TRANSKRİPT CÜMLELERİ (Toplam Süre: {video_duration:.1f}s):\n"
            f"{joined_sents}\n\n"
            "SADECE aşağıdaki JSON formatında yanıt ver (after_sentence_index: kendisinden hemen sonra [geçiş] konulacak CÜMLE numarası):\n"
            '[{"after_sentence_index": 1, "reason": "Ana tez cümlesi bitimi ve alıntı/tanım başlangıcı"}]'
        )

        raw = gemini_client.generate_text(prompt, max_retries=1)
        if not raw:
            return []
        clean_json = gemini_client.extract_balanced_json(raw, prefer_array=True)
        if not clean_json:
            return []
        parsed = json.loads(clean_json)
        items = parsed.get("transitions", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
        out: List[Tuple[int, str]] = []
        for it in items:
            if isinstance(it, dict) and "after_sentence_index" in it:
                try:
                    s_idx = int(it["after_sentence_index"])
                    reason = str(it.get("reason", ""))
                    out.append((s_idx, reason))
                except (ValueError, TypeError):
                    continue
        return out

    @classmethod
    def _ensure_balanced_scene_lengths(
        cls,
        boundaries: List[SceneBoundary],
        sentences: List[List[WordToken]],
        video_duration: float,
        max_span_sec: float = 95.0,
    ) -> List[SceneBoundary]:
        """Çok uzun kalan sahneleri (>95sn) en uygun cümle sonlarından iteratif bölerek parça boyutlarını dengeler."""
        if not sentences:
            return boundaries

        all_bounds = list(boundaries)
        for _ in range(25):
            all_bounds.sort(key=lambda b: b.timestamp)
            points = [0.0] + [b.timestamp for b in all_bounds] + [video_duration]
            added_any = False

            for idx in range(len(points) - 1):
                span_start = points[idx]
                span_end = points[idx + 1]
                span_words = sum(
                    len(s) for s in sentences if s and span_start <= s[0].start and s[-1].end <= span_end
                )
                if (span_end - span_start) <= max_span_sec or span_words < 95:
                    continue

                mid_target = (span_start + span_end) / 2.0
                best_sent_i = None
                best_dist = 999.0
                for s_i in range(len(sentences) - 1):
                    s_end = sentences[s_i][-1].end
                    if (span_start + 12.0) <= s_end <= (span_end - 12.0):
                        dist = abs(s_end - mid_target)
                        if dist < best_dist:
                            best_dist = dist
                            best_sent_i = s_i

                if best_sent_i is not None:
                    sa = sentences[best_sent_i]
                    sb = sentences[best_sent_i + 1]
                    t_end = sa[-1].end
                    t_start = sb[0].start
                    t_mid = round((t_end + t_start) / 2.0, 2)
                    if not any(abs(b.timestamp - t_mid) < 8.0 for b in all_bounds):
                        ta = " ".join(w.raw for w in sa).strip()
                        tb = " ".join(w.raw for w in sb).strip()
                        all_bounds.append(
                            SceneBoundary(
                                boundary_id=f"tr_auto_{best_sent_i}",
                                timestamp=t_mid,
                                sentence_a_end=round(t_end, 2),
                                sentence_b_start=round(t_start, 2),
                                before_word_idx=sa[-1].idx,
                                after_word_idx=sb[0].idx,
                                sentence_a_preview=ta[-90:],
                                sentence_b_preview=tb[:90],
                                category="SCENE_BALANCE_SPLIT",
                                reason="Uzun anlatım bloğu cümle sınırından dengeli sahneye ayrıldı",
                            )
                        )
                        added_any = True
            if not added_any:
                break

        all_bounds.sort(key=lambda b: b.timestamp)
        return all_bounds

    @classmethod
    def build_scene_chunks(
        cls,
        word_stream: List[WordToken],
        video_duration: float,
        boundaries: List[SceneBoundary],
    ) -> List[SceneChunkPlan]:
        """Belirlenen [geçiş] sınırlarına göre videoyu SceneChunkPlan parçalarına ayırır."""
        if not word_stream:
            return []

        scenes: List[SceneChunkPlan] = []
        cut_word_indices = [b.after_word_idx for b in boundaries]
        start_w_idx = word_stream[0].idx
        last_w_idx = word_stream[-1].idx

        ranges: List[Tuple[int, int, Optional[SceneBoundary]]] = []
        cur_start = start_w_idx
        for b_idx, b in enumerate(boundaries):
            ranges.append((cur_start, b.before_word_idx, b))
            cur_start = b.after_word_idx
        ranges.append((cur_start, last_w_idx, None))

        for sc_idx, (w_st, w_en, tr_after) in enumerate(ranges, start=1):
            sc_tokens = [w for w in word_stream if w_st <= w.idx <= w_en]
            if not sc_tokens:
                continue
            sc_text = " ".join(w.raw for w in sc_tokens).strip()
            sc_start_sec = sc_tokens[0].start
            sc_end_sec = sc_tokens[-1].end
            role = cls._infer_narrative_role(sc_idx, len(ranges), sc_text)
            title = extract_turkish_semantic_title(sc_text) or f"BÖLÜM {sc_idx}"
            scenes.append(
                SceneChunkPlan(
                    scene_id=sc_idx,
                    title_tr=title,
                    start_sec=round(sc_start_sec, 2),
                    end_sec=round(sc_end_sec, 2),
                    start_word_idx=sc_tokens[0].idx,
                    end_word_idx=sc_tokens[-1].idx,
                    transcript_text=sc_text,
                    narrative_role=role,
                    transition_after=tr_after,
                )
            )
        return scenes

    @staticmethod
    def _infer_narrative_role(scene_idx: int, total_scenes: int, text: str) -> str:
        low = to_turkish_lower(text)
        if scene_idx == 1 and ("önceki ders" in low or "incelemiştik" in low or "hakikat var" in low):
            return "RECAP_AND_THESIS"
        if "inşa edeceğiz" in low or "ele alacağız" in low or "bugün" in low:
            return "FOUNDATIONAL_FRAMING_AND_ROADMAP"
        if "baktığımızda" in low or "tarifle çizerler" in low or "tanımlanır" in low:
            return "CONCEPT_DEFINITION"
        if scene_idx == total_scenes and total_scenes > 2:
            return "SYNTHESIS_AND_CONCLUSION"
        return "BODY_EXPLANATION"


class ChunkDirector:
    """
    AŞAMA 2: Her bir sahne parçasını (SceneChunkPlan) hız ve çökme yalıtımı için
    AYRI BİR YAPAY ZEKA İSTEĞİ olarak paralel değerlendirir.
    Tüm parçalar aynı kilitli ThemeProfile ve aynı JSON şemasını kullanır.
    """

    def __init__(self, gemini_client: Any = None, max_workers: int = 1):
        self.gemini = gemini_client
        self.max_workers = max_workers

    def evaluate_chunks_parallel(
        self,
        scenes: List[SceneChunkPlan],
        word_stream: List[WordToken],
        theme_profile: ThemeProfile,
        deterministic_triggers: Optional[List[PlannedEditorialEvent]] = None,
        on_chunk_done: Optional[Callable[[int, int], None]] = None,
    ) -> List[SceneChunkPlan]:
        if not scenes:
            return []

        det_triggers = list(deterministic_triggers or [])
        token_by_idx = {w.idx: w for w in word_stream}

        # Grup öğelerinin (PROGRESSIVE_LIST / PAIRED_TERMS) ilk öğe başlangıç saniyesi (atomik sahne ataması için)
        group_anchor_sec: Dict[str, float] = {}
        for ev in det_triggers:
            if ev.group_id:
                group_anchor_sec[ev.group_id] = min(
                    group_anchor_sec.get(ev.group_id, ev.start_sec), ev.start_sec
                )

        def _process_single_scene(scene: SceneChunkPlan) -> SceneChunkPlan:
            is_last_scene = scene.scene_id == len(scenes)
            # 1. Bu sahneye düşen deterministik tetikleyicileri hazırla (gruplar atomik olarak ilk öğenin sahnesine atanır)
            matched_det_evs = []
            for ev in det_triggers:
                anchor_s = group_anchor_sec.get(ev.group_id, ev.start_sec) if ev.group_id else ev.start_sec
                if (scene.start_sec <= anchor_s < scene.end_sec) or (
                    is_last_scene and scene.start_sec <= anchor_s <= scene.end_sec + 1.0
                ) or (scene.scene_id == 1 and anchor_s < scene.start_sec):
                    matched_det_evs.append(ev)

            scene_det_items = self._convert_events_to_scenario_items(
                scene.scene_id,
                matched_det_evs,
                word_stream,
            )

            # 2. LLM aktifse bu parçayı izole bir AI isteği olarak gönder
            llm_items: List[PlannedScenarioItem] = []
            if self.gemini and hasattr(self.gemini, "is_available") and self.gemini.is_available():
                try:
                    llm_items = self._evaluate_single_chunk_via_llm(
                        scene=scene,
                        word_stream=word_stream,
                        token_by_idx=token_by_idx,
                        theme_profile=theme_profile,
                    )
                except Exception as ex:
                    logger.warning(
                        f"[ChunkDirector] Sahne #{scene.scene_id} AI isteği başarısız oldu, "
                        f"diğer sahneler etkilenmeden yerel kurgu yedeği devreye alındı: {ex}"
                    )
                    scene.status = "fallback"

            # 3. Deterministik yüksek doğruluklu öğelerle (Kişi/Eser/Kümülatif Liste) LLM öğelerini harmanla
            merged_items = self._merge_scene_items(scene.scene_id, scene_det_items, llm_items, word_stream, scene=scene)
            scene.items = merged_items
            scene.key_terms = list(dict.fromkeys(it.text_primary for it in merged_items if it.text_primary))[:8]
            return scene

        completed_count = 0
        total_scenes = len(scenes)
        workers = max(1, min(self.max_workers, total_scenes))

        if workers == 1:
            for sc_orig in scenes:
                try:
                    _process_single_scene(sc_orig)
                except Exception as ex:
                    logger.warning(f"[ChunkDirector] Sahne #{sc_orig.scene_id} sıralı yürütme hatası: {ex}")
                    sc_orig.status = "fallback"
                completed_count += 1
                if on_chunk_done:
                    try:
                        on_chunk_done(completed_count, total_scenes)
                    except Exception:
                        pass
        else:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="ChunkDirector"
            ) as executor:
                future_to_scene = {executor.submit(_process_single_scene, sc): sc for sc in scenes}
                for fut in concurrent.futures.as_completed(future_to_scene):
                    sc_orig = future_to_scene[fut]
                    try:
                        fut.result(timeout=360.0)
                    except Exception as ex:
                        logger.warning(f"[ChunkDirector] Sahne #{sc_orig.scene_id} paralel yürütme hatası: {ex}")
                        sc_orig.status = "fallback"
                    completed_count += 1
                    if on_chunk_done:
                        try:
                            on_chunk_done(completed_count, total_scenes)
                        except Exception:
                            pass

        scenes.sort(key=lambda s: s.scene_id)
        return scenes

    def _evaluate_single_chunk_via_llm(
        self,
        scene: SceneChunkPlan,
        word_stream: List[WordToken],
        token_by_idx: Dict[int, WordToken],
        theme_profile: ThemeProfile,
    ) -> List[PlannedScenarioItem]:
        sc_tokens = [w for w in word_stream if scene.start_word_idx <= w.idx <= scene.end_word_idx]
        if not sc_tokens:
            return []

        sc_dur = max(10.0, scene.end_sec - scene.start_sec)
        target_min = 2 if sc_dur >= 24.0 else 1
        target_max = min(5, max(3, int(round(sc_dur / 13.0))))

        indexed_text = " ".join(f"[w{t.idx}|{t.start:.1f}] {t.raw}" for t in sc_tokens)
        prompt = (
            f"Sen '{theme_profile.display_name}' ({theme_profile.id}) türünde uzman bir kurgu yönetmenisin.\n"
            f"Şu an videonun SADECE {scene.scene_id}. PARÇASINI (Sahne Rolü: {scene.narrative_role}, "
            f"Süre: {scene.start_sec:.1f}s - {scene.end_sec:.1f}s, Uzunluk: {sc_dur:.0f}sn) kurguluyorsun.\n\n"
            "STANDART KURGU FORMATI VE TEMPO KURALLARI (ZORUNLU):\n"
            f"0. DENGELİ TEMPO: Bu sahnede kurgusuz boşluk kalmaması için sahne süresine yayılmış EN AZ {target_min}, EN FAZLA {target_max} adet vurgu öğesi çıkar (boş dizi [] DÖNME).\n"
            "1. PERSON_INTRODUCTION: Parçada gerçek bir düşünür, alim, yazar veya tarihi şahsiyet anılıyorsa tam ismini ve Wikipedia sorgusunu çıkar. Aynı cümlede birden fazla isim geçiyorsa her birinin kendi okunduğu kelime aralığını ver.\n"
            "2. WORK_INTRODUCTION: Kitap, sure, kanun, risale veya eser adı geçiyorsa çıkar.\n"
            "3. PROGRESSIVE_LIST: Konuşmacı 3 veya daha fazla kavramı/unsuru sıralıyorsa, items dizisinde her birini kelime indeksiyle listele. ZORUNLU KURAL: Eğer sıralanan maddeler şahıslar/alimler ise (Örn: 1. Hz. Ali, 2. Ebu Hanife, 3. İmam-ı Maturidi, 4. İmam Cafer-i Sadık), her bir madde nesnesine mutlaka 'wiki_query_tr' ekle ki ekranın sağında fotoğrafları da alt alta çıksın!\n"
            "4. PAIRED_TERMS: İki karşıt veya ikiz kavram kıyaslanıyorsa, 2 öğeli items olarak çıkar.\n"
            "5. DEFINITION_CALLOUT / KEY_TERM_CALLOUT: Parçada tanımlanan temel felsefi/hukuki/bilimsel terimleri veya konuşmacının vurguladığı can alıcı ana fikri/metaforu 2-4 kelimelik çarpıcı başlık olarak çıkar.\n"
            "6. ASLA hitap kelimelerine ('Değerli izleyenler', 'Arkadaşlar', 'Hoşçakalın') yazı koyma.\n\n"
            f"PARÇA #{scene.scene_id} KELİME AKIŞI:\n{indexed_text}\n\n"
            "SADECE aşağıdaki JSON dizisi formatında yanıt ver:\n"
            '[{"action_type":"PERSON_INTRODUCTION|WORK_INTRODUCTION|PROGRESSIVE_LIST|PAIRED_TERMS|DEFINITION_CALLOUT|KEY_TERM_CALLOUT",'
            '"start_word_idx":12,"end_word_idx":15,"sentence_end_word_idx":22,'
            '"text_primary":"KISA EKRAN BAŞLIĞI","text_secondary":"Varsa alt başlık veya kısa alıntı",'
            '"wiki_query_tr":"Wikipedia TR başlığı","wiki_query_en":"Wikipedia EN title",'
            '"rationale":"Neden bu kısma konulduğunun kısa açıklaması",'
            '"items":[{"start_word_idx":14,"text_primary":"MADDE 1"}]}]'
        )

        raw = self.gemini.generate_text(prompt, max_retries=2)
        if not raw:
            return []
        clean_json = self.gemini.extract_balanced_json(raw, prefer_array=True) or self.gemini.extract_balanced_json(raw)
        if not clean_json:
            return []
        parsed = json.loads(clean_json) if isinstance(clean_json, str) else clean_json
        raw_events = parsed.get("events", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])

        def _safe_word_idx(val: Any, default_idx: int) -> int:
            if val is None:
                return default_idx
            if isinstance(val, (int, float)):
                return int(val)
            m = re.search(r"(\d+)", str(val))
            return int(m.group(1)) if m else default_idx

        def _resolve_tok(idx_cand: int, label_hint: str, fallback_tok: WordToken) -> WordToken:
            if idx_cand in token_by_idx and scene.start_word_idx <= idx_cand <= scene.end_word_idx:
                return token_by_idx[idx_cand]
            words_h = [to_turkish_lower(w.strip(".,:;!?()1234567890-")) for w in (label_hint or "").split() if len(w.strip(".,:;!?()1234567890-")) >= 3]
            if words_h:
                first_h = words_h[0]
                for tk in sc_tokens:
                    if first_h in tk.lower or tk.lower in first_h:
                        return tk
            return token_by_idx.get(idx_cand, fallback_tok)

        def _clean_title_and_subtitle(raw_p: str, raw_s: str) -> Tuple[str, str]:
            p = (raw_p or "").strip()
            s = (raw_s or "").strip()
            m = re.match(r"^(.*?)\s*[\(\[]([^()\[\]]+)[\)\]]?\s*$", p)
            if m:
                main_title = m.group(1).strip()
                parenthetical = m.group(2).strip()
                if len(main_title) >= 2:
                    p = main_title
                    if not s:
                        s = parenthetical
            return to_turkish_upper(p)[:38], s[:70]

        items: List[PlannedScenarioItem] = []
        for idx, ev in enumerate(raw_events):
            if not isinstance(ev, dict):
                continue
            atype = str(ev.get("action_type", "KEY_TERM_CALLOUT")).upper().strip()
            lbl_raw = str(ev.get("text_primary", "")).strip()
            sw_idx = _safe_word_idx(ev.get("start_word_idx"), scene.start_word_idx)
            ew_idx = _safe_word_idx(ev.get("end_word_idx"), sw_idx)
            sent_end_idx = _safe_word_idx(ev.get("sentence_end_word_idx"), max(ew_idx, sw_idx + 4))

            sw_tok = _resolve_tok(sw_idx, lbl_raw, sc_tokens[0])
            ew_tok = token_by_idx.get(sent_end_idx, token_by_idx.get(ew_idx, sc_tokens[min(len(sc_tokens) - 1, max(0, sw_tok.idx - scene.start_word_idx + 5))]))
            start_s = round(sw_tok.start, 2)
            end_s = round(max(start_s + 2.2, min(scene.end_sec, ew_tok.end + 0.3)), 2)

            sub_items = ev.get("items")
            if atype in ("PROGRESSIVE_LIST", "PAIRED_TERMS") and isinstance(sub_items, list) and len(sub_items) >= 2:
                grp_id = f"sc{scene.scene_id}_grp_{idx}"
                for slot_i, sub in enumerate(sub_items[:6]):
                    if not isinstance(sub, dict):
                        continue
                    sub_lbl_raw = str(sub.get("text_primary", "")).strip()
                    sub_sec_raw = str(sub.get("text_secondary", "")).strip()
                    sub_lbl, sub_sec = _clean_title_and_subtitle(sub_lbl_raw, sub_sec_raw)
                    if not sub_lbl:
                        continue
                    sub_w_idx = _safe_word_idx(sub.get("start_word_idx"), sw_tok.idx + slot_i)
                    sub_tok = _resolve_tok(sub_w_idx, sub_lbl, sw_tok)
                    sub_st = round(max(scene.start_sec, sub_tok.start), 2)
                    sub_wiki_tr = str(sub.get("wiki_query_tr", "")).strip()
                    sub_wiki_en = str(sub.get("wiki_query_en", "")).strip()
                    if not sub_wiki_tr:
                        low_lbl = sub_lbl.lower()
                        if "ali" in low_lbl and ("hz" in low_lbl or "hazret" in low_lbl or "imam" in low_lbl):
                            sub_wiki_tr = "Ali"
                        elif "hanife" in low_lbl:
                            sub_wiki_tr = "Ebû Hanîfe"
                        elif "maturidi" in low_lbl:
                            sub_wiki_tr = "Mâtürîdî"
                        elif "cafer" in low_lbl or "sadık" in low_lbl:
                            sub_wiki_tr = "Ca'fer es-Sâdık"
                        elif "harezmi" in low_lbl:
                            sub_wiki_tr = "Hârizmî"
                        elif "nursi" in low_lbl or "bediüzzaman" in low_lbl:
                            sub_wiki_tr = "Said Nursî"
                        elif "osman" in low_lbl and ("hz" in low_lbl or "hazret" in low_lbl):
                            sub_wiki_tr = "Osman bin Affan"

                    items.append(
                        PlannedScenarioItem(
                            item_id=f"sc{scene.scene_id}_it_{idx}_{slot_i}",
                            scene_id=scene.scene_id,
                            action_type=atype,
                            start_word_idx=sub_tok.idx,
                            end_word_idx=ew_tok.idx,
                            start_sec=sub_st,
                            end_sec=round(max(end_s, sub_st + 2.0), 2),
                            text_primary=f"{slot_i + 1}. {sub_lbl}" if atype == "PROGRESSIVE_LIST" and not sub_lbl[0].isdigit() else sub_lbl,
                            text_secondary=sub_sec,
                            wiki_query_tr=sub_wiki_tr,
                            wiki_query_en=sub_wiki_en,
                            group_id=grp_id,
                            stack_slot=slot_i,
                            semantic_priority=True,
                            rationale=str(ev.get("rationale", "Sıralı kavram grubu")),
                        )
                    )
            else:
                lbl, sec_txt = _clean_title_and_subtitle(lbl_raw, str(ev.get("text_secondary", "")))
                if not lbl or len(lbl) < 2:
                    continue
                items.append(
                    PlannedScenarioItem(
                        item_id=f"sc{scene.scene_id}_it_{idx}",
                        scene_id=scene.scene_id,
                        action_type=atype,
                        start_word_idx=sw_tok.idx,
                        end_word_idx=ew_tok.idx,
                        start_sec=start_s,
                        end_sec=end_s,
                        text_primary=lbl,
                        text_secondary=sec_txt,
                        wiki_query_tr=str(ev.get("wiki_query_tr", "")).strip(),
                        wiki_query_en=str(ev.get("wiki_query_en", "")).strip(),
                        semantic_priority=True,
                        rationale=str(ev.get("rationale", "")),
                    )
                )
        return items

    @staticmethod
    def _convert_events_to_scenario_items(
        scene_id: int,
        events: List[PlannedEditorialEvent],
        word_stream: List[WordToken],
    ) -> List[PlannedScenarioItem]:
        out: List[PlannedScenarioItem] = []
        for idx, ev in enumerate(events):
            # En yakın kelime indekslerini bul
            sw_idx = 0
            ew_idx = 0
            if word_stream:
                sw_tok = min(word_stream, key=lambda w: abs(w.start - ev.start_sec))
                ew_tok = min(word_stream, key=lambda w: abs(w.end - ev.end_sec))
                sw_idx = sw_tok.idx
                ew_idx = ew_tok.idx

            out.append(
                PlannedScenarioItem(
                    item_id=ev.event_id or f"sc{scene_id}_det_{idx}",
                    scene_id=scene_id,
                    action_type=ev.action_type,
                    start_word_idx=sw_idx,
                    end_word_idx=ew_idx,
                    start_sec=round(ev.start_sec, 2),
                    end_sec=round(ev.end_sec, 2),
                    text_primary=ev.text_primary,
                    text_secondary=ev.text_secondary,
                    wiki_query_tr=ev.person_wiki_tr or ev.primary_web_query_tr,
                    wiki_query_en=ev.person_wiki_en or ev.secondary_stock_query_en,
                    stock_query_en=ev.secondary_stock_query_en,
                    group_id=ev.group_id,
                    stack_slot=ev.stack_slot,
                    semantic_priority=ev.semantic_priority,
                    rationale="Kelime-senkronlu semantik tetikleyici",
                )
            )
        return out

    @staticmethod
    def _merge_scene_items(
        scene_id: int,
        det_items: List[PlannedScenarioItem],
        llm_items: List[PlannedScenarioItem],
        word_stream: List[WordToken],
        scene: Optional[SceneChunkPlan] = None,
    ) -> List[PlannedScenarioItem]:
        """LLM öğelerine öncelik vererek deterministik sözlük öğeleriyle çakışmasız birleştirir ve üst üste yığılmayı önler."""
        combined: List[PlannedScenarioItem] = list(llm_items) if llm_items else list(det_items)
        if llm_items and det_items:
            def _extract_content_words(txt: str) -> Set[str]:
                norm = to_turkish_lower(re.sub(r"[^\w\s]", " ", txt))
                return {w for w in norm.split() if len(w) >= 4 and w not in ("olan", "için", "gibi", "kadar", "daha", "veya", "ile")}

            llm_content_words: Set[str] = set()
            for it in combined:
                llm_content_words.update(_extract_content_words(it.text_primary))

            seen_labels = {to_turkish_lower(it.text_primary) for it in combined}
            for dit in det_items:
                norm_lbl = to_turkish_lower(dit.text_primary)
                if norm_lbl in seen_labels:
                    continue

                # Anlamsal / kelime mükerrerliği kontrolü:
                dit_words = _extract_content_words(dit.text_primary)
                shared_words = dit_words.intersection(llm_content_words)
                if shared_words:
                    # Bu kavram zaten LLM öğesi tarafından işlenmiş (Örn: 'Efradını Cami' veya 'Ağyarını Mani')
                    continue

                if any(norm_lbl in to_turkish_lower(ex.text_primary) or to_turkish_lower(ex.text_primary) in norm_lbl for ex in combined):
                    continue

                # Zaman çakışması kontrolü:
                # Eğer deterministik öğe bir KİŞİ veya ESER tanıtımıysa (PERSON_INTRODUCTION / WORK_INTRODUCTION),
                # aynı saniyedeki sıradan metin vurgularına (KEY_TERM_CALLOUT / DEFINITION_CALLOUT) göre önceliklidir!
                if dit.action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION"):
                    combined = [
                        ex for ex in combined
                        if ex.action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION", "PROGRESSIVE_LIST", "PAIRED_TERMS")
                        or not ((max(dit.start_sec, ex.start_sec) < min(dit.end_sec, ex.end_sec)) or (abs(dit.start_sec - ex.start_sec) < 2.2))
                    ]
                    time_conflict = any(
                        (max(dit.start_sec, ex.start_sec) < min(dit.end_sec, ex.end_sec))
                        or (abs(dit.start_sec - ex.start_sec) < 1.8)
                        for ex in combined
                    )
                else:
                    time_conflict = any(
                        (max(dit.start_sec, ex.start_sec) < min(dit.end_sec, ex.end_sec))
                        or (abs(dit.start_sec - ex.start_sec) < 2.8)
                        for ex in combined
                    )
                if not time_conflict:
                    combined.append(dit)
                    seen_labels.add(norm_lbl)
                    llm_content_words.update(dit_words)

        combined.sort(key=lambda x: (x.start_sec, x.stack_slot or 0))

        # Tekil (grup dışı) kartların aynı cümlede üst üste 6-8 katman yığılmasını önle (Stagger / Sequential)
        scene_end_bound = scene.end_sec if scene else 99999.0
        single_items = [it for it in combined if not it.group_id]
        for i, cur in enumerate(single_items):
            cur.end_sec = round(min(scene_end_bound, cur.end_sec, max(cur.start_sec + 2.2, cur.start_sec + 5.2)), 2)
            if i + 1 < len(single_items):
                nxt = single_items[i + 1]
                if nxt.start_sec < cur.end_sec:
                    gap = nxt.start_sec - cur.start_sec
                    if gap >= 1.5:
                        cur.end_sec = round(nxt.start_sec - 0.15, 2)
                    else:
                        nxt.start_sec = round(min(scene_end_bound - 2.0, cur.start_sec + 2.1), 2)
                        nxt.end_sec = round(min(scene_end_bound, max(nxt.end_sec, nxt.start_sec + 2.3)), 2)
                        cur.end_sec = round(nxt.start_sec - 0.15, 2)

        # Sahne tamamen boş kaldıysa, yalnızca kelimesi kelimesine o anda konuşulan gerçek bir Türkçe kavram tamlaması varsa ekle
        if not combined and scene and (scene.end_sec - scene.start_sec) >= 15.0:
            from pipeline.holistic_analyzer import HolisticAnalyzer
            from pipeline.theme_profiles import strip_turkish_genitive_safe

            sc_toks = [w for w in word_stream if scene.start_word_idx <= w.idx <= scene.end_word_idx]
            best_cand: Optional[Tuple[WordToken, WordToken, str]] = None
            for i_t in range(len(sc_toks)):
                for win_len in (3, 2):
                    if i_t + win_len > len(sc_toks):
                        continue
                    span = sc_toks[i_t : i_t + win_len]
                    if any(t.has_sentence_end or t.has_comma for t in span[:-1]):
                        continue
                    if any((span[k + 1].start - span[k].end) > 0.45 for k in range(win_len - 1)):
                        continue
                    head_norm = to_turkish_lower(strip_turkish_genitive_safe(span[-1].clean))
                    if head_norm not in HolisticAnalyzer._CONCEPTUAL_NOUN_HEADS:
                        continue
                    words_clean = [t.clean for t in span[:-1]] + [strip_turkish_genitive_safe(span[-1].clean)]
                    cand_title = to_turkish_upper(" ".join(words_clean))
                    if HolisticAnalyzer._is_valid_conceptual_callout(cand_title):
                        best_cand = (span[0], span[-1], cand_title)
                        break
                if best_cand:
                    break

            if best_cand:
                st_tok, en_tok, cand_title = best_cand
                st_s = round(st_tok.start, 2)
                en_s = round(min(scene.end_sec, max(st_s + 2.4, en_tok.end + 0.6)), 2)
                combined.append(
                    PlannedScenarioItem(
                        item_id=f"sc{scene_id}_auto_insight",
                        scene_id=scene_id,
                        action_type="KEY_TERM_CALLOUT",
                        start_word_idx=st_tok.idx,
                        end_word_idx=en_tok.idx,
                        start_sec=st_s,
                        end_sec=en_s,
                        text_primary=cand_title[:38],
                        text_secondary="Anahtar Kavram",
                        semantic_priority=True,
                        rationale="Sahne içi kelime-senkronlu anahtar kavram vurgusu",
                    )
                )

        combined.sort(key=lambda x: (x.start_sec, x.stack_slot or 0))
        return combined


class ScenarioMerger:
    """AŞAMA 3: Tüm parçaların kurgu planlarını Tam Kurgu Senaryosunda (MasterEditingScript) birleştirir."""

    @staticmethod
    def merge_to_master_script(
        project_id: str,
        video_id: str,
        theme_profile: ThemeProfile,
        video_duration: float,
        scenes: List[SceneChunkPlan],
        transitions: List[SceneBoundary],
    ) -> MasterEditingScript:
        return MasterEditingScript(
            project_id=project_id,
            video_id=video_id,
            theme_profile_id=theme_profile.id,
            theme_display_name=theme_profile.display_name,
            video_duration=round(video_duration, 2),
            scenes=list(scenes),
            transitions=list(transitions),
            critique_history=[],
            iteration_count=0,
            is_approved=False,
            requires_user_approval=False,
            approval_status="pending",
        )

    @staticmethod
    def to_chapter_plans(script: MasterEditingScript) -> List[ChapterPlan]:
        """MasterEditingScript nesnesini LlmDirector ve EdlBuilder ile %100 uyumlu ChapterPlan listesine dönüştürür."""
        chapters: List[ChapterPlan] = []
        for sc in script.scenes:
            events: List[PlannedEditorialEvent] = []
            for it in sc.items:
                events.append(
                    PlannedEditorialEvent(
                        event_id=it.item_id,
                        chapter_id=sc.scene_id,
                        action_type=it.action_type,
                        start_sec=it.start_sec,
                        end_sec=it.end_sec,
                        text_primary=it.text_primary,
                        text_secondary=it.text_secondary,
                        primary_web_query_tr=it.wiki_query_tr or it.text_primary,
                        secondary_stock_query_en=it.wiki_query_en or it.stock_query_en or it.text_primary,
                        fallback_minimal_query_en=it.wiki_query_en or it.text_primary,
                        prefer_video_broll=False,
                        person_wiki_tr=it.wiki_query_tr if it.action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION", "CONCEPT_IMAGE_CARD") else "",
                        person_wiki_en=it.wiki_query_en if it.action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION", "CONCEPT_IMAGE_CARD") else "",
                        semantic_priority=it.semantic_priority,
                        group_id=it.group_id,
                        stack_slot=it.stack_slot,
                    )
                )
            chapters.append(
                ChapterPlan(
                    chapter_id=sc.scene_id,
                    start_sec=sc.start_sec,
                    end_sec=sc.end_sec,
                    title_tr=sc.title_tr,
                    key_terms=list(sc.key_terms),
                    events=events,
                )
            )
        return chapters


class ScenarioCritic:
    """
    AŞAMA 4: Birleştirilmiş Tam Kurgu Senaryosunu denetleyen Başeditör Yapay Zeka (Critic AI).
    Konulacak yazıların, resimlerin, listelerin ve konuldukları saniyelerin mantıklı olup olmadığına bakar.
    'Şuraya bir şey koyma', 'Şu koyduğun şeyi şöyle düzelt', 'Şu kısma da şunları koy' şeklinde karar üretir.
    """

    BANNED_LABELS = {
        "DEĞERLİ İZLEYENLER", "ARKADAŞLAR", "MERHABA", "HOŞ GELDİNİZ",
        "EVET ARKADAŞLAR", "PEKİ", "ŞİMDİ", "DOLAYISIYLA",
        "İZLEDİĞİNİZ İÇİN TEŞEKKÜR EDERİM", "TEŞEKKÜR EDERİM", "SAĞ EDERİM",
        "SES GELİYOR", "HOŞÇAKALIN", "BİR ŞEY DAHA BİTİRELİM",
    }

    HALLUCINATION_SUBSTRINGS = (
        "İZLEDİĞİNİZ İÇİN", "TEŞEKKÜR EDERİM", "SAĞ EDERİM", "SES GELİYOR",
        "REFERANS.COM", "REFERANS EĞİTİM", "ABONE OLMAYI", "DAHA BİTİRELİM",
        "PROBLEM YOK",
    )

    FRAGMENT_PREFIXES = (
        "ZİRA ", "ÇÜNKÜ ", "FAKAT ", "LAKİN ", "ETSE ", "ANCAK ",
        "PEKİ ", "ŞİMDİ ", "DOLAYISIYLA ", "HALBUKİ ", "OYSA ", "ÖRNEĞİN ",
        "MESELA ", "YOKSA ", "EĞER ",
    )

    FRAGMENT_SUFFIXES = (
        " DÜŞÜRMEDİĞİ", " BUNA", " ONUN", " BUNUN", " YALNIZCA", " SADECE",
        " OLARAK", " İÇİN", " GİBİ", " KADAR", " DAHA", " GÖRE", " KARŞI",
        " DÜNYEVİ", " DÜŞÜNDÜĞÜMÜZDE", " BAKTIĞIMIZDA", " DEDİĞİMİZDE",
    )

    ASR_TITLE_CORRECTIONS = {
        "İKTİSAT VE İSRAR": "İKTİSAT VE İSRAF",
        "EBU HALİFE": "EBU HANİFE",
        "2. EBU HALİFE": "2. EBU HANİFE",
        "ZÜYUM": "ZULÜM",
        "ZÜLÜM": "ZULÜM",
        "ADALETİ ZAFİYİ SAVUNANLAR": "ADALET-İ İZAFİYEYİ SAVUNANLAR",
        "AD İSMİ DOĞRUDAN DOĞRUYA": "ADL İSMİ (İSM-İ ADİL)",
        "İSTİBDAT VS": "İSTİBDAT VE ZULÜM",
    }

    def __init__(self, gemini_client: Any = None):
        self.gemini = gemini_client

    def evaluate(
        self,
        script: MasterEditingScript,
        word_stream: List[WordToken],
        iteration: int = 1,
        applied_changes_log: Optional[List[str]] = None,
    ) -> CritiqueReport:
        applied_log = list(applied_changes_log or [])
        revisions: List[CritiqueRevision] = []

        # 1. Hızlı Kural & Anlam Denetimi (Yasaklı hitaplar, bozuk listeler, ASR hataları, parçalar arası yakın tekrarlar, sahne içi çakışmalar)
        seen_recent: Dict[str, Tuple[float, str, int]] = {}
        for sc in script.scenes:
            # 1a. Bozuk/Parçalanmış Liste Denetimi (Örn: '1. ADALETİ', '2. MAHZA', '3. SANCAĞINI' gibi tek bir tamlamanın kelimelere bölünmesi)
            groups_in_scene: Dict[str, List[PlannedScenarioItem]] = {}
            for it in sc.items:
                if it.group_id and it.stack_slot is not None:
                    groups_in_scene.setdefault(it.group_id, []).append(it)

            collapsed_item_ids: Set[str] = set()
            for grp_id, g_items in groups_in_scene.items():
                if len(g_items) >= 3:
                    g_items.sort(key=lambda x: x.stack_slot or 0)
                    stripped_words = [re.sub(r"^\d+\.\s*", "", x.text_primary).strip() for x in g_items]
                    joined_phrase = to_turkish_upper(" ".join(stripped_words))
                    # Eğer her madde tek kelimelikse ve ardışık kelimeler (max 1.2sn arayla) tek bir tamlama oluşturuyorsa
                    all_single_word = all(len(w.split()) == 1 for w in stripped_words)
                    span_sec = g_items[-1].start_sec - g_items[0].start_sec
                    if (all_single_word and span_sec <= 2.2) or ("ADALET" in joined_phrase and "MAHZA" in joined_phrase and "SANCA" in joined_phrase):
                        merged_title = "ADALET-İ MAHZA SANCAĞI" if ("MAHZA" in joined_phrase and "SANCA" in joined_phrase) else joined_phrase[:38]
                        first_it = g_items[0]
                        revisions.append(CritiqueRevision(
                            action="MODIFY",
                            target_id=first_it.item_id,
                            scene_id=sc.scene_id,
                            action_type="KEY_TERM_CALLOUT",
                            text_primary=merged_title,
                            reason=f"Tek bir tamlama olan '{joined_phrase}' ifadesi hatalı şekilde maddeli listeye bölünmüştü; tekil kavramsal başlık olarak birleştirildi.",
                        ))
                        for extra_it in g_items[1:]:
                            revisions.append(CritiqueRevision(
                                action="REMOVE",
                                target_id=extra_it.item_id,
                                scene_id=sc.scene_id,
                                reason=f"Parçalanmış tamlama listesindeki '{extra_it.text_primary}' öğesi '{merged_title}' başlığında birleştirildiği için kaldırıldı.",
                            ))
                            collapsed_item_ids.add(extra_it.item_id)

            # 1b. Sahne içi görsel çakışma ve mükerrerlik denetimi
            sorted_items = sorted(sc.items, key=lambda x: (x.start_sec, x.stack_slot or 0))
            removed_target_ids: Set[str] = set(collapsed_item_ids)
            for i, it_a in enumerate(sorted_items):
                if it_a.item_id in removed_target_ids:
                    continue
                lbl_a = to_turkish_upper(it_a.text_primary).strip()
                words_a = {w for w in to_turkish_lower(re.sub(r"[^\w\s]", " ", lbl_a)).split() if len(w) >= 4 and w not in ("olan", "için", "gibi", "kadar")}

                for it_b in sorted_items[i + 1:]:
                    if it_b.item_id in removed_target_ids:
                        continue
                    if it_a.group_id and it_a.group_id == it_b.group_id:
                        continue  # Aynı grup içindeki öğeler birlikte durabilir
                    lbl_b = to_turkish_upper(it_b.text_primary).strip()
                    words_b = {w for w in to_turkish_lower(re.sub(r"[^\w\s]", " ", lbl_b)).split() if len(w) >= 4 and w not in ("olan", "için", "gibi", "kadar")}

                    # Zaman örtüşmesi kontrolü
                    overlap = (max(it_a.start_sec, it_b.start_sec) < min(it_a.end_sec, it_b.end_sec)) or abs(it_a.start_sec - it_b.start_sec) < 2.2
                    if overlap:
                        # Eğer birisi deterministik tetikleyici (trig_) ise, her zaman deterministik olanı feda et
                        if "trig_" in it_b.item_id and "trig_" not in it_a.item_id:
                            revisions.append(CritiqueRevision(
                                action="REMOVE",
                                target_id=it_b.item_id,
                                scene_id=sc.scene_id,
                                reason=f"'{it_b.text_primary}' deterministik öğesi, LLM öğesi '{it_a.text_primary}' ile çakıştığı için kaldırıldı.",
                            ))
                            removed_target_ids.add(it_b.item_id)
                        elif "trig_" in it_a.item_id and "trig_" not in it_b.item_id:
                            revisions.append(CritiqueRevision(
                                action="REMOVE",
                                target_id=it_a.item_id,
                                scene_id=sc.scene_id,
                                reason=f"'{it_a.text_primary}' deterministik öğesi, LLM öğesi '{it_b.text_primary}' ile çakıştığı için kaldırıldı.",
                            ))
                            removed_target_ids.add(it_a.item_id)
                            break
                        elif words_a.intersection(words_b):
                            revisions.append(CritiqueRevision(
                                action="REMOVE",
                                target_id=it_b.item_id,
                                scene_id=sc.scene_id,
                                reason=f"'{it_b.text_primary}' öğesi '{it_a.text_primary}' ile aynı anda ekranda çakışıyor ve mükerrer.",
                            ))
                            removed_target_ids.add(it_b.item_id)

            for it in sc.items:
                if it.item_id in removed_target_ids:
                    continue
                lbl_up = to_turkish_upper(it.text_primary).strip()
                if (
                    lbl_up in self.BANNED_LABELS
                    or len(lbl_up) < 2
                    or any(hs in lbl_up for hs in self.HALLUCINATION_SUBSTRINGS)
                ):
                    revisions.append(
                        CritiqueRevision(
                            action="REMOVE",
                            target_id=it.item_id,
                            scene_id=sc.scene_id,
                            reason=f"'{lbl_up}' bir kavramsal başlık değil (hitap/stüdyo sesi/halüsinasyon); kaldırılmalı.",
                        )
                    )
                    continue

                # Yarım cümle / bağlaçla başlayan veya sıfat-fiille yarım kesilen başlıkları ele
                if it.action_type in ("KEY_TERM_CALLOUT", "DEFINITION_CALLOUT", "SINGLE_TERM"):
                    if lbl_up.startswith(self.FRAGMENT_PREFIXES) or lbl_up.endswith(self.FRAGMENT_SUFFIXES):
                        revisions.append(
                            CritiqueRevision(
                                action="REMOVE",
                                target_id=it.item_id,
                                scene_id=sc.scene_id,
                                reason=f"'{lbl_up}' tam bir kavramsal tamlama değil, yarım kesilmiş cümle parçasıdır; kaldırılmalı.",
                            )
                        )
                        continue

                # 1c. ASR kaynaklı yanlış kelime veya yarım kalmış parantez/kısaltma onarımı
                if lbl_up in self.ASR_TITLE_CORRECTIONS:
                    fixed_lbl = self.ASR_TITLE_CORRECTIONS[lbl_up]
                    revisions.append(
                        CritiqueRevision(
                            action="MODIFY",
                            target_id=it.item_id,
                            scene_id=sc.scene_id,
                            action_type=it.action_type,
                            text_primary=fixed_lbl,
                            reason=f"ASR/transkript kaynaklı hatalı veya yarım başlık '{lbl_up}' -> '{fixed_lbl}' olarak düzeltildi.",
                        )
                    )
                    lbl_up = fixed_lbl
                elif "(" in lbl_up and ")" not in lbl_up:
                    clean_before_paren = lbl_up.split("(", 1)[0].strip()
                    if len(clean_before_paren) >= 3:
                        revisions.append(
                            CritiqueRevision(
                                action="MODIFY",
                                target_id=it.item_id,
                                scene_id=sc.scene_id,
                                action_type=it.action_type,
                                text_primary=clean_before_paren,
                                reason=f"Kapanmamış parantez içeren '{lbl_up}' başlığı '{clean_before_paren}' olarak temizlendi.",
                            )
                        )
                        lbl_up = clean_before_paren

                # 1d. Kelime-Saniye Senkron Denetimi (Başlık cümle bittikten sonra veya yanlış saniyede çıkıyorsa düzelt/kaldır)
                lbl_content_words = [
                    w for w in re.split(r"[\s\-/().,]+", lbl_up)
                    if len(VerbatimTranscriptValidator.normalize_root(w)) >= 3 and not w.isdigit()
                ]
                if lbl_content_words and word_stream:
                    near_tokens = [
                        t for t in word_stream
                        if (it.start_sec - 1.2) <= t.start <= (it.start_sec + 2.5)
                    ]
                    near_norms = [VerbatimTranscriptValidator.normalize_root(t.clean) for t in near_tokens if t.clean]
                    is_synced = any(
                        VerbatimTranscriptValidator.word_matches_spoken_tokens(lw, near_norms)
                        for lw in lbl_content_words
                    )
                    if not is_synced:
                        # Sahne içinde bu kelimenin gerçekte söylendiği WordToken'ı ara
                        sc_tokens = [
                            t for t in word_stream
                            if sc.start_word_idx <= t.idx <= sc.end_word_idx
                        ]
                        matched_tok: Optional[WordToken] = None
                        for t_cand in sc_tokens:
                            t_norm = [VerbatimTranscriptValidator.normalize_root(t_cand.clean)]
                            if any(VerbatimTranscriptValidator.word_matches_spoken_tokens(lw, t_norm) for lw in lbl_content_words):
                                matched_tok = t_cand
                                break
                        if matched_tok is not None:
                            end_tok_idx = min(sc.end_word_idx, matched_tok.idx + max(2, len(lbl_content_words)))
                            revisions.append(
                                CritiqueRevision(
                                    action="MODIFY",
                                    target_id=it.item_id,
                                    scene_id=sc.scene_id,
                                    start_word_idx=matched_tok.idx,
                                    end_word_idx=end_tok_idx,
                                    reason=f"'{lbl_up}' yazısının zamanlaması ({it.start_sec:.2f}s) konuşulan kelimeden ({matched_tok.start:.2f}s) sapmıştı; tam söylendiği saniyeye hizalandı.",
                                )
                            )
                        else:
                            revisions.append(
                                CritiqueRevision(
                                    action="REMOVE",
                                    target_id=it.item_id,
                                    scene_id=sc.scene_id,
                                    reason=f"'{lbl_up}' başlığı bu sahnede konuşulan kelimelerle eşleşmediği (senkron dışı olduğu) için kaldırıldı.",
                                )
                            )
                            continue

                # Parçalar arası yakın tekrar kontrolü (20 saniye içinde aynı başlık iki kez çıkmamalı)
                if not it.group_id and lbl_up in seen_recent:
                    prev_ts, prev_id, prev_sc = seen_recent[lbl_up]
                    if abs(it.start_sec - prev_ts) < 20.0:
                        revisions.append(
                            CritiqueRevision(
                                action="REMOVE",
                                target_id=it.item_id,
                                scene_id=sc.scene_id,
                                reason=f"'{lbl_up}' başlığı {prev_ts:.1f}. saniyede zaten gösterildi; mükerrer olmaması için kaldırılmalı.",
                            )
                        )
                        continue
                seen_recent[lbl_up] = (it.start_sec, it.item_id, sc.scene_id)

        # 2. LLM Başeditör (Critic) Denetimi
        llm_approved = True
        llm_summary = "Kurgu senaryosu tüm sahnelerde metinle ve görsel kurallarla uyumlu."
        score = 92

        if self.gemini and hasattr(self.gemini, "is_available") and self.gemini.is_available():
            try:
                llm_rep = self._evaluate_via_llm(script, word_stream, iteration, applied_log)
                if llm_rep is not None:
                    llm_approved = llm_rep.is_approved
                    llm_summary = llm_rep.summary_feedback or llm_summary
                    score = llm_rep.overall_score
                    # LLM revizyonlarını ekle (aynı target_id mükerrer olmasın)
                    existing_targets = {r.target_id.replace("ad_txt_", "") for r in revisions if r.target_id}
                    for r in llm_rep.revisions:
                        norm_tid = (r.target_id or "").replace("ad_txt_", "").replace("ad_img_", "")
                        if r.target_id:
                            r.target_id = norm_tid
                        if not norm_tid or norm_tid not in existing_targets:
                            revisions.append(r)
                            if norm_tid:
                                existing_targets.add(norm_tid)
            except Exception as ex:
                logger.warning(f"[ScenarioCritic] Tur {iteration} LLM denetimi uyarısı: {ex}")

        is_approved = (len(revisions) == 0) and llm_approved
        if is_approved:
            score = max(score, 90)
            if iteration > 1:
                llm_summary = f"{iteration}. kontrolde tüm düzeltmeler doğrulandı; başka sorun kalmadı."

        return CritiqueReport(
            iteration=iteration,
            is_approved=is_approved,
            overall_score=score,
            summary_feedback=llm_summary,
            revisions=revisions,
            applied_changes_log=applied_log,
        )

    def _evaluate_via_llm(
        self,
        script: MasterEditingScript,
        word_stream: List[WordToken],
        iteration: int,
        applied_log: List[str],
    ) -> Optional[CritiqueReport]:
        if not script.scenes:
            return None

        # Uzun videolarda (20+ sahne) tek devasa istek gönderip Proxy timeout veya Groq 413 (Payload Too Large)
        # hatasına takılmamak için sahneleri en fazla 13 sahnelik paketler (batch) halinde denetle.
        batch_size = 13
        all_revs: List[CritiqueRevision] = []
        batch_feedbacks: List[str] = []
        batch_scores: List[int] = []
        any_batch_succeeded = False

        for b_start in range(0, len(script.scenes), batch_size):
            batch_scenes = script.scenes[b_start : b_start + batch_size]
            scenes_summary = []
            for sc in batch_scenes:
                items_desc = []
                for it in sc.items:
                    img_tag = "+RESİM" if it.wiki_query_tr else ""
                    grp_tag = f"|L{it.stack_slot}" if it.stack_slot is not None else ""
                    items_desc.append(
                        f"[{it.item_id}|{it.start_sec:.0f}s{grp_tag}{img_tag}] '{it.text_primary}'"
                    )
                topic_excerpt = (sc.transcript_text[:115] + "...") if len(sc.transcript_text) > 115 else sc.transcript_text
                scenes_summary.append(
                    f"S#{sc.scene_id} ({sc.start_sec:.0f}-{sc.end_sec:.0f}s): \"{topic_excerpt}\" -> "
                    + (", ".join(items_desc) if items_desc else "(HİÇ EDİT YOK - BOŞ SAHNE!)")
                )

            changelog_block = ""
            if iteration > 1 and applied_log:
                changelog_block = (
                    f"\n⚡ ÖNCEKİ DENETİMDEN SONRA YAPILAN DÜZELTMELER (TUR {iteration}):\n"
                    + "\n".join(f"- {ch}" for ch in applied_log[:12])
                    + "\nLütfen bu düzeltilmiş versiyonu kontrol et ve BAŞKA SORUN KALDI MI değerlendir. "
                    "Eğer önemli bir mantık hatası kalmadıysa is_approved: true ve revisions: [] dön!\n"
                )

            prompt = (
                "Sen Başeditör (Denetçi) Yapay Zekasın. Görevin, Video Kurgu Senaryosunu denetlemektir.\n"
                "Kontrol Kriterlerin:\n"
                "1. ANLAMLILIK VE DOĞRU TERMİNOLOJİ: Sahne metni ses tanıma (ASR) çıktısı olduğu için metinde 'Ebu Halife', 'adalet-i zafiye', 'israr', 'züyum' gibi ASR hataları bulunabilir. "
                "Başlıkları ASR hatasına göre DEĞİL, doğru akademik/hukuki/İslami terminolojiye göre ('EBU HANİFE', 'ADALET-İ İZAFİYE', 'ADALET-İ MAHZA', 'NÜBÜVVET', 'HUKUK-U İBAD', 'İKTİSAT VE İSRAF', 'ZULÜM') denetle! Doğru yazılmış olan 'ADALET-İ İZAFİYE' veya 'NÜBÜVVET' başlıklarını ASLA bozma.\n"
                "2. BOZUK LİSTE: Tek bir tamlama ('1. ADALETİ, 2. MAHZA, 3. SANCAĞINI') yanlışlıkla listeye bölünmüşse ilkini 'MODIFY' ile tek başlığa çevir, diğerlerini 'REMOVE' ile sil.\n"
                "3. BOŞ SAHNE / EKSİK VURGU: '(HİÇ EDİT YOK - BOŞ SAHNE!)' olan veya önemli bir eser/kavram atlanan sahneye 'ADD' ile başlık ekle.\n"
                f"{changelog_block}\n"
                "KURGU SENARYOSU BÖLÜMÜ:\n"
                + "\n".join(scenes_summary)
                + "\n\nSADECE aşağıdaki JSON nesnesi formatında yanıt ver:\n"
                '{"is_approved": true, "overall_score": 95, '
                '"summary_feedback": "Genel değerlendirme özeti", '
                '"revisions": ['
                '{"action": "REMOVE|MODIFY|ADD", "target_id": "sc1_it_0", "scene_id": 1, '
                '"action_type": "PERSON_INTRODUCTION|DEFINITION_CALLOUT|KEY_TERM_CALLOUT", '
                '"start_word_idx": 0, "end_word_idx": 0, '
                '"text_primary": "YENİ BAŞLIK", "text_secondary": "Alt metin", '
                '"wiki_query_tr": "", "reason": "Düzeltme nedeni"}'
                "]}"
            )

            raw = self.gemini.generate_text(prompt, max_retries=1)
            if not raw:
                continue
            clean_json = self.gemini.extract_balanced_json(raw, prefer_array=False)
            if not clean_json:
                continue
            try:
                data = json.loads(clean_json)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            if "revisions" not in data and "is_approved" not in data and "summary_feedback" not in data:
                if "action" in data and ("target_id" in data or "scene_id" in data):
                    data = {
                        "is_approved": False,
                        "overall_score": 82,
                        "summary_feedback": str(data.get("reason", "Başeditör revizyonu tespit edildi.")),
                        "revisions": [data],
                    }
                else:
                    continue

            any_batch_succeeded = True
            b_revs = [
                CritiqueRevision.from_dict(r)
                for r in data.get("revisions", [])
                if isinstance(r, dict) and r.get("action")
            ]
            all_revs.extend(b_revs)
            fb = str(data.get("summary_feedback", "")).strip()
            if fb:
                batch_feedbacks.append(fb)
            batch_scores.append(int(data.get("overall_score", 92 if not b_revs else 82)))

        if not any_batch_succeeded:
            return None

        is_app = len(all_revs) == 0
        avg_score = int(round(sum(batch_scores) / len(batch_scores))) if batch_scores else (92 if is_app else 82)
        feedback_str = " | ".join(batch_feedbacks)
        if not feedback_str:
            feedback_str = (
                "Başeditör AI tüm sahneleri ve başlıkları denetledi; metin ve görsel uyumu doğrulandı."
                if is_app
                else f"Başeditör AI {len(all_revs)} adet anlam/yazım/kurgu düzeltmesi tespit etti."
            )

        return CritiqueReport(
            iteration=iteration,
            is_approved=is_app,
            overall_score=avg_score,
            summary_feedback=feedback_str,
            revisions=all_revs,
            applied_changes_log=applied_log,
        )


class ScenarioRefiner:
    """
    Hem Başeditör (Critic) AI'ın tespit ettiği düzeltmeleri hem de
    3. tur sonrasında Kullanıcının doğal dille verdiği revizyonları ('Şu kısımlara şunu ekle...')
    Tam Kurgu Senaryosuna (MasterEditingScript) uygular.
    """

    def __init__(self, gemini_client: Any = None):
        self.gemini = gemini_client

    def apply_revisions(
        self,
        script: MasterEditingScript,
        revisions: List[CritiqueRevision],
        word_stream: List[WordToken],
    ) -> List[str]:
        """Verilen revizyon emirlerini senaryoya uygular ve yapılan işlemlerin özet listesini döner."""
        if not revisions:
            return []

        token_by_idx = {w.idx: w for w in word_stream}
        scene_by_id = {sc.scene_id: sc for sc in script.scenes}
        applied_log: List[str] = []

        def _match_id(item_id: str, target_id: str) -> bool:
            if not item_id or not target_id:
                return False
            n_a = item_id.replace("ad_txt_", "").replace("ad_img_", "").strip()
            n_b = target_id.replace("ad_txt_", "").replace("ad_img_", "").strip()
            return item_id == target_id or n_a == n_b

        for rev in revisions:
            act = rev.action.upper().strip()

            if act == "REMOVE" and rev.target_id:
                for sc in script.scenes:
                    before_len = len(sc.items)
                    sc.items = [it for it in sc.items if not _match_id(it.item_id, rev.target_id)]
                    if len(sc.items) < before_len:
                        applied_log.append(
                            f"Sahne #{sc.scene_id} içindeki '{rev.target_id}' öğesi kaldırıldı ({rev.reason})."
                        )
                        sc.status = "revised"
                        break

            elif act == "REMOVE_TRANSITION" and rev.target_id:
                script.transitions = [t for t in script.transitions if t.boundary_id != rev.target_id]
                for sc in script.scenes:
                    if sc.transition_after and sc.transition_after.boundary_id == rev.target_id:
                        sc.transition_after = None
                        applied_log.append(f"Sahne #{sc.scene_id} sonundaki '{rev.target_id}' geçişi kaldırıldı.")

            elif act == "MODIFY" and rev.target_id:
                for sc in script.scenes:
                    for it in sc.items:
                        if _match_id(it.item_id, rev.target_id):
                            old_lbl = it.text_primary
                            if rev.text_primary:
                                new_t = to_turkish_upper(rev.text_primary.strip())[:42]
                                # Eğer bu bir PROGRESSIVE_LIST maddesiyse ve tekil başlığa dönüştürülmüyorsa sıra numarasını koru
                                if (
                                    it.stack_slot is not None
                                    and (not rev.action_type or rev.action_type == "PROGRESSIVE_LIST")
                                    and old_lbl[:2].rstrip(".").isdigit()
                                    and not new_t[:2].rstrip(".").isdigit()
                                ):
                                    prefix_num = old_lbl.split(".", 1)[0].strip()
                                    new_t = f"{prefix_num}. {new_t}"[:42]
                                it.text_primary = new_t
                            if rev.text_secondary:
                                it.text_secondary = rev.text_secondary.strip()[:70]
                            if rev.wiki_query_tr:
                                it.wiki_query_tr = rev.wiki_query_tr.strip()
                            if rev.wiki_query_en:
                                it.wiki_query_en = rev.wiki_query_en.strip()
                            if rev.action_type:
                                # Sadece parçalanmış tamlama birleştirilirken grup bağını çöz; normal metin düzeltmelerinde grup bağını koru
                                if it.stack_slot is not None and ("bölünmüş" in (rev.reason or "") or "birleştiril" in (rev.reason or "")):
                                    it.group_id = None
                                    it.stack_slot = None
                                    it.action_type = rev.action_type
                                elif it.stack_slot is None:
                                    it.action_type = rev.action_type
                            if rev.start_word_idx is not None and rev.start_word_idx > 0 and rev.start_word_idx in token_by_idx:
                                it.start_word_idx = rev.start_word_idx
                                it.start_sec = round(token_by_idx[rev.start_word_idx].start, 2)
                            if rev.end_word_idx is not None and rev.end_word_idx > 0 and rev.end_word_idx in token_by_idx:
                                it.end_word_idx = rev.end_word_idx
                                it.end_sec = round(max(it.start_sec + 1.8, token_by_idx[rev.end_word_idx].end), 2)
                            sc.status = "revised"
                            applied_log.append(
                                f"Sahne #{sc.scene_id} içindeki '{old_lbl}' öğesi '{it.text_primary}' olarak düzeltildi ({rev.reason})."
                            )
                            break

            elif act == "ADD":
                target_sc = scene_by_id.get(rev.scene_id) or (script.scenes[0] if script.scenes else None)
                if target_sc and rev.text_primary:
                    new_lbl = to_turkish_upper(rev.text_primary.strip())[:42]
                    # Kelime zamanını çöz
                    st_sec = target_sc.start_sec + 1.0
                    en_sec = min(target_sc.end_sec, st_sec + 3.5)
                    sw_idx = rev.start_word_idx or target_sc.start_word_idx
                    ew_idx = rev.end_word_idx or min(target_sc.end_word_idx, sw_idx + 5)

                    if sw_idx in token_by_idx:
                        st_sec = round(token_by_idx[sw_idx].start, 2)
                    else:
                        # Metin içinde kelimenin geçtiği yeri ara
                        lbl_words = [to_turkish_lower(w) for w in new_lbl.split() if len(w) >= 3]
                        for w in word_stream:
                            if target_sc.start_word_idx <= w.idx <= target_sc.end_word_idx:
                                if any(lw in w.lower or w.lower in lw for lw in lbl_words):
                                    sw_idx = w.idx
                                    st_sec = round(w.start, 2)
                                    break
                    if ew_idx in token_by_idx:
                        en_sec = round(max(st_sec + 2.0, token_by_idx[ew_idx].end + 0.3), 2)
                    else:
                        en_sec = round(min(target_sc.end_sec, st_sec + 3.2), 2)

                    new_id = f"sc{target_sc.scene_id}_rev_{len(target_sc.items) + 1}"
                    target_sc.items.append(
                        PlannedScenarioItem(
                            item_id=new_id,
                            scene_id=target_sc.scene_id,
                            action_type=rev.action_type or "KEY_TERM_CALLOUT",
                            start_word_idx=sw_idx,
                            end_word_idx=ew_idx,
                            start_sec=st_sec,
                            end_sec=en_sec,
                            text_primary=new_lbl,
                            text_secondary=rev.text_secondary,
                            wiki_query_tr=rev.wiki_query_tr or rev.text_primary,
                            wiki_query_en=rev.wiki_query_en,
                            semantic_priority=True,
                            rationale=rev.reason or "Denetçi/Kullanıcı revizyonu ile eklendi",
                        )
                    )
                    target_sc.items.sort(key=lambda x: (x.start_sec, x.stack_slot or 0))
                    target_sc.status = "revised"
                    applied_log.append(
                        f"Sahne #{target_sc.scene_id} içerisine '{new_lbl}' ({rev.action_type}) eklendi ({rev.reason})."
                    )

        return applied_log

    def apply_user_natural_language_feedback(
        self,
        script: MasterEditingScript,
        user_feedback: str,
        word_stream: List[WordToken],
    ) -> Tuple[MasterEditingScript, List[str]]:
        """
        Kullanıcının doğal dille yazdığı revizyon talebini ('Şu kısma şunu ekle, şunu kaldır...')
        yapılandırılmış CritiqueRevision komutlarına çevirip senaryoya uygular.
        """
        feedback_clean = (user_feedback or "").strip()
        if not feedback_clean:
            return script, []

        script.user_feedback_history.append(feedback_clean)
        revisions: List[CritiqueRevision] = []

        # 1. LLM ile kullanıcının doğal dil isteğini revizyon emirlerine dönüştür
        if self.gemini and hasattr(self.gemini, "is_available") and self.gemini.is_available():
            try:
                scenes_json = json.dumps([s.to_dict() for s in script.scenes], ensure_ascii=False)[:6000]
                prompt = (
                    "Kullanıcı video kurgu senaryosu üzerinde aşağıdaki revizyonu istedi:\n"
                    f"KULLANICI TALEBİ: \"{feedback_clean}\"\n\n"
                    f"MEVCUT SENARYO SAHNELERİ:\n{scenes_json}\n\n"
                    "Kullanıcının isteğini yerine getirmek için gereken REMOVE, MODIFY, ADD veya REMOVE_TRANSITION "
                    "işlemlerini SADECE aşağıdaki JSON dizisi formatında döndür:\n"
                    '[{"action":"ADD|REMOVE|MODIFY|REMOVE_TRANSITION","target_id":"varsa_hedef_id","scene_id":1,'
                    '"action_type":"PERSON_INTRODUCTION|DEFINITION_CALLOUT|KEY_TERM_CALLOUT",'
                    '"text_primary":"EKLENECEK VEYA YENİ BAŞLIK","text_secondary":"Alt metin",'
                    '"reason":"Kullanıcı revizyon talebi"}]'
                )
                raw = self.gemini.generate_text(prompt, max_retries=1)
                if raw:
                    clean_json = self.gemini.extract_balanced_json(raw, prefer_array=True)
                    if clean_json:
                        parsed = json.loads(clean_json)
                        arr = parsed.get("revisions", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
                        revisions = [CritiqueRevision.from_dict(x) for x in arr if isinstance(x, dict)]
            except Exception as ex:
                logger.warning(f"[ScenarioRefiner] Kullanıcı revizyonu LLM çözümleme uyarısı: {ex}")

        # 2. Deterministik Doğal Dil Yedeği (LLM erişilemezse bile kullanıcının 'ekle' / 'kaldır' komutlarını uygular)
        if not revisions:
            revisions = self._parse_user_feedback_heuristic(script, feedback_clean)

        applied = self.apply_revisions(script, revisions, word_stream)
        script.approval_status = "awaiting_user"
        script.requires_user_approval = True
        script.last_critic_message = (
            f"İstediğiniz {len(applied)} değişiklik senaryoya uygulandı: "
            + ("; ".join(applied) if applied else "Senaryo güncellendi.")
            + " Bu halini uygulayalım mı?"
        )
        return script, applied

    @staticmethod
    def _parse_user_feedback_heuristic(script: MasterEditingScript, feedback: str) -> List[CritiqueRevision]:
        """Kullanıcının Türkçe revizyon metninden ('... ekle', '... kaldır/sil') deterministik komut üretir."""
        low = to_turkish_lower(feedback)
        revs: List[CritiqueRevision] = []

        # Sahne numarası belirtilmişse yakala ("2. parçaya", "sahne 2", "1. kısma")
        target_scene_id = 1
        m_sc = re.search(r"(\d+)\s*\.?\s*(?:sahne|parça|kısım|bölüm)", low)
        if m_sc:
            target_scene_id = max(1, min(len(script.scenes) or 1, int(m_sc.group(1))))

        # Kaldırma/silme komutu kontrolü
        if any(w in low for w in ("kaldır", "sil", "çıkar", "istemiyorum", "olmasın")):
            for sc in script.scenes:
                for it in sc.items:
                    it_low = to_turkish_lower(it.text_primary)
                    if it_low and (it_low in low or any(tok in low for tok in it_low.split() if len(tok) >= 4)):
                        revs.append(
                            CritiqueRevision(
                                action="REMOVE",
                                target_id=it.item_id,
                                scene_id=sc.scene_id,
                                reason="Kullanıcı talebiyle kaldırıldı",
                            )
                        )

        # Tırnak içi veya 'ekle' öncesi ifade kontrolü
        quoted = re.findall(r"['\"“”‘’]([^'\"“”‘’]{2,45})['\"“”‘’]", feedback)
        if quoted and any(w in low for w in ("ekle", "koy", "yaz")):
            for q in quoted:
                revs.append(
                    CritiqueRevision(
                        action="ADD",
                        scene_id=target_scene_id,
                        action_type="KEY_TERM_CALLOUT",
                        text_primary=to_turkish_upper(q.strip()),
                        reason="Kullanıcı talebiyle eklendi",
                    )
                )
        elif not revs and any(w in low for w in ("ekle", "koy", "yaz")):
            # Tırnak yoksa 'şunu ekle: X' veya 'X ekle' kalıbını yakala
            cleaned = re.sub(
                r"\b(\d+\.?\s*(?:sahneye|parçaya|kısma|bölüme)|ekle|koy|yaz|başlığı|kartı|yazısı|lütfen|şuraya|buraya)\b",
                "",
                feedback,
                flags=re.IGNORECASE,
            ).strip(" .,!?:;-")
            if len(cleaned) >= 2:
                revs.append(
                    CritiqueRevision(
                        action="ADD",
                        scene_id=target_scene_id,
                        action_type="KEY_TERM_CALLOUT",
                        text_primary=to_turkish_upper(cleaned[:40]),
                        reason="Kullanıcı talebiyle eklendi",
                    )
                )

        return revs


class ScenarioOrchestrator:
    """
    5 Aşamalı Otonom Kurgu Senaryosu Orkestratörü:
      1. Video Türü & Retorik [geçiş] Tespiti ile Sahnelere Bölme (SceneSegmenter)
      2. Her Parçayı Ayrı & Paralel AI İsteği Olarak Kurgulama (ChunkDirector)
      3. Tüm Parçaları Tam Senaryoda Birleştirme (ScenarioMerger)
      4. Başeditör (Critic) AI Denetim ve Düzeltme Döngüsü (Maksimum 3 Tur)
      5. 3. Tur Sonrası Hâlâ Sorun Varsa Kullanıcıya Devretme (Human-in-the-Loop Escalation)
    """

    MAX_CRITIC_ITERATIONS = 3

    def __init__(self, gemini_client: Any = None, max_workers: int = 1):
        self.gemini = gemini_client
        self.chunk_director = ChunkDirector(gemini_client=gemini_client, max_workers=max_workers)
        self.critic = ScenarioCritic(gemini_client=gemini_client)
        self.refiner = ScenarioRefiner(gemini_client=gemini_client)

    def build_and_verify_scenario(
        self,
        project_id: str,
        video_id: str,
        word_stream: List[WordToken],
        video_duration: float,
        theme_profile: ThemeProfile,
        deterministic_triggers: Optional[List[PlannedEditorialEvent]] = None,
        enable_llm: bool = True,
        force_user_approval: bool = False,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ) -> MasterEditingScript:
        # AŞAMA 1: Retorik [geçiş] Sınırlarını Belirle ve Videoyu Parçalara Ayır
        if progress_callback:
            progress_callback("SenaryoBirlestirme", 70, "Kurgu Senaryosu: Geçiş noktaları ve sahneler belirleniyor...")

        boundaries, _ = SceneSegmenter.detect_rhetorical_boundaries(
            word_stream=word_stream,
            video_duration=video_duration,
            gemini_client=self.gemini if enable_llm else None,
            enable_llm=enable_llm,
        )
        scenes = SceneSegmenter.build_scene_chunks(
            word_stream=word_stream,
            video_duration=video_duration,
            boundaries=boundaries,
        )
        logger.info(
            f"[ScenarioOrchestrator] Aşama 1 Tamamlandı: {len(scenes)} sahne parçası ve "
            f"{len(boundaries)} [geçiş] noktası belirlendi."
        )

        # AŞAMA 2: Her Parçayı Ayrı ve Sıralı Yapay Zeka İsteği Olarak Değerlendir
        if progress_callback:
            progress_callback(
                "SenaryoBirlestirme",
                78,
                f"Kurgu Senaryosu: {len(scenes)} sahne parçası Gemini 3.8 Flash ile kurgulanıyor...",
            )

        def _on_chunk_done_cb(done: int, total: int):
            if progress_callback:
                pct = 78 + int((done / max(1, total)) * 6)
                progress_callback(
                    "SenaryoBirlestirme",
                    pct,
                    f"Kurgu Senaryosu: Sahne {done}/{total} Gemini 3.8 Flash tarafından kurgulandı..."
                )

        scenes = self.chunk_director.evaluate_chunks_parallel(
            scenes=scenes,
            word_stream=word_stream,
            theme_profile=theme_profile,
            deterministic_triggers=deterministic_triggers if enable_llm else deterministic_triggers,
            on_chunk_done=_on_chunk_done_cb,
        )

        # AŞAMA 3: Tüm Parçaları Tam Senaryoda Birleştir
        script = ScenarioMerger.merge_to_master_script(
            project_id=project_id,
            video_id=video_id,
            theme_profile=theme_profile,
            video_duration=video_duration,
            scenes=scenes,
            transitions=boundaries,
        )

        # AŞAMA 4: Başeditör / Denetçi AI Döngüsü (Maksimum 3 Tur)
        applied_changes: List[str] = []
        for iteration in range(1, self.MAX_CRITIC_ITERATIONS + 1):
            script.iteration_count = iteration
            if progress_callback:
                progress_callback(
                    "SenaryoDenetimi",
                    82 + iteration * 3,
                    f"Başeditör AI Denetimi (Tur {iteration}/{self.MAX_CRITIC_ITERATIONS}): Senaryo kontrol ediliyor...",
                )

            report = self.critic.evaluate(
                script=script,
                word_stream=word_stream,
                iteration=iteration,
                applied_changes_log=applied_changes,
            )
            script.critique_history.append(report)
            script.last_critic_message = report.summary_feedback

            logger.info(
                f"[ScenarioOrchestrator] Başeditör Denetimi Tur {iteration}/{self.MAX_CRITIC_ITERATIONS}: "
                f"Onay={report.is_approved} | Puan={report.overall_score} | Revizyon Sayısı={len(report.revisions)}"
            )

            if report.is_approved:
                script.is_approved = True
                script.requires_user_approval = bool(force_user_approval)
                script.approval_status = "awaiting_user" if force_user_approval else "auto_approved"
                break

            # Sorun varsa düzeltmeleri uygula ve bir sonraki tura ("Başka sorun kaldı mı?") hazırla
            if iteration < self.MAX_CRITIC_ITERATIONS:
                applied_changes = self.refiner.apply_revisions(script, report.revisions, word_stream)
                if not applied_changes:
                    # Uygulanacak somut revizyon kalmadıysa onaylanmış kabul et
                    script.is_approved = True
                    script.requires_user_approval = bool(force_user_approval)
                    script.approval_status = "awaiting_user" if force_user_approval else "auto_approved"
                    break
            else:
                # 3. Turda da sorun varsa son düzeltmeleri de uygula ve KULLANICIYA DEVRET!
                self.refiner.apply_revisions(script, report.revisions, word_stream)
                script.is_approved = False
                script.requires_user_approval = True
                script.approval_status = "awaiting_user"
                script.last_critic_message = (
                    f"3. yapay zeka denetimi sonunda senaryo optimize edildi ancak onayınız bekleniyor: "
                    f"{report.summary_feedback} — Bu senaryoyu uygulayalım mı, yoksa düzeltme mi yapalım?"
                )
                logger.warning(
                    f"[ScenarioOrchestrator] 3. denetim sonunda hâlâ revizyon tespit edildi; "
                    f"döngü kırıcı devreye girdi, kullanıcı onayı bekleniyor (ProjectId={project_id})."
                )

        return script
