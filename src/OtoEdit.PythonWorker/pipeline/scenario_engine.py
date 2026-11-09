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
from typing import Any, Callable, Dict, List, Optional, Tuple

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
        eff_min_gap = max(20.0, min_scene_duration_sec)

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

        # Uzun sahneleri (> 95sn) en uygun cümle sınırından böl ki paralel parça istekleri hızlı ve odaklı kalsın
        final_boundaries = cls._ensure_balanced_scene_lengths(filtered, sentences, video_duration, max_span_sec=95.0)
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
                if (span_end - span_start) <= max_span_sec:
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
            merged_items = self._merge_scene_items(scene.scene_id, scene_det_items, llm_items, word_stream)
            scene.items = merged_items
            scene.key_terms = list(dict.fromkeys(it.text_primary for it in merged_items if it.text_primary))[:8]
            return scene

        completed_count = 0
        total_scenes = len(scenes)
        workers = max(1, min(self.max_workers, total_scenes))

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

        indexed_text = " ".join(f"[w{t.idx}|{t.start:.1f}] {t.raw}" for t in sc_tokens)
        prompt = (
            f"Sen '{theme_profile.display_name}' ({theme_profile.id}) türünde uzman bir kurgu yönetmenisin.\n"
            f"Şu an videonun SADECE {scene.scene_id}. PARÇASINI (Sahne Rolü: {scene.narrative_role}, "
            f"Süre: {scene.start_sec:.1f}s - {scene.end_sec:.1f}s) kurguluyorsun.\n\n"
            "STANDART KURGU FORMATI KURALLARI (TÜM PARÇALARDA AYNI FORMAT ZORUNLUDUR):\n"
            "1. PERSON_INTRODUCTION: Parçada gerçek bir düşünür, alim, yazar veya tarihi şahsiyet (Örn: Bediüzzaman Said Nursi, Thomas Hobbes, Nurettin Topçu) anılıyorsa tam ismini ve Wikipedia sorgusunu çıkar.\n"
            "2. WORK_INTRODUCTION: Kitap, kanun, risale veya eser adı geçiyorsa çıkar.\n"
            "3. PROGRESSIVE_LIST: Konuşmacı 3 veya daha fazla kavramı/unsuru sıralıyorsa (Örn: '1. Hürriyet, 2. Müsbet İsyan İradesi, 3. Meşveret Hukuku'), items dizisinde her birini kelime indeksiyle listele.\n"
            "4. PAIRED_TERMS: İki karşıt veya ikiz kavram kıyaslanıyorsa (Örn: 'İman ve Hürriyet' vs 'İstibdat ve Tahakküm'), 2 öğeli items olarak çıkar.\n"
            "5. DEFINITION_CALLOUT / KEY_TERM_CALLOUT: Parçada tanımlanan temel felsefi/hukuki/bilimsel terimleri (Örn: 'ADALET-İ MAHZA', 'EFRADINI CÂMİ AĞYARINI MÂNİ', 'PRAGMATİK HÜRRİYET TARİFİ') çıkar.\n"
            "6. ASLA hitap kelimelerine ('Değerli izleyenler', 'Arkadaşlar') yazı koyma.\n\n"
            f"PARÇA #{scene.scene_id} KELİME AKIŞI:\n{indexed_text}\n\n"
            "SADECE aşağıdaki JSON dizisi formatında yanıt ver:\n"
            '[{"action_type":"PERSON_INTRODUCTION|WORK_INTRODUCTION|PROGRESSIVE_LIST|PAIRED_TERMS|DEFINITION_CALLOUT|KEY_TERM_CALLOUT",'
            '"start_word_idx":12,"end_word_idx":15,"sentence_end_word_idx":22,'
            '"text_primary":"KISA EKRAN BAŞLIĞI","text_secondary":"Varsa alt başlık veya kısa alıntı",'
            '"wiki_query_tr":"Wikipedia TR başlığı","wiki_query_en":"Wikipedia EN title",'
            '"rationale":"Neden bu kısma konulduğunun kısa açıklaması",'
            '"items":[{"start_word_idx":14,"text_primary":"MADDE 1"}]}]'
        )

        raw = self.gemini.generate_text(prompt, max_retries=1)
        if not raw:
            return []
        clean_json = self.gemini.extract_balanced_json(raw, prefer_array=True)
        if not clean_json:
            return []
        parsed = json.loads(clean_json)
        raw_events = parsed.get("events", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])

        items: List[PlannedScenarioItem] = []
        for idx, ev in enumerate(raw_events):
            if not isinstance(ev, dict):
                continue
            atype = str(ev.get("action_type", "KEY_TERM_CALLOUT")).upper().strip()
            sw_idx = int(ev.get("start_word_idx", scene.start_word_idx))
            ew_idx = int(ev.get("end_word_idx", sw_idx))
            sent_end_idx = int(ev.get("sentence_end_word_idx", max(ew_idx, sw_idx + 4)))

            sw_tok = token_by_idx.get(sw_idx, sc_tokens[0])
            ew_tok = token_by_idx.get(sent_end_idx, token_by_idx.get(ew_idx, sc_tokens[-1]))
            start_s = round(sw_tok.start, 2)
            end_s = round(max(start_s + 2.2, min(scene.end_sec, ew_tok.end + 0.3)), 2)

            sub_items = ev.get("items")
            if atype in ("PROGRESSIVE_LIST", "PAIRED_TERMS") and isinstance(sub_items, list) and len(sub_items) >= 2:
                grp_id = f"sc{scene.scene_id}_grp_{idx}"
                for slot_i, sub in enumerate(sub_items[:6]):
                    if not isinstance(sub, dict):
                        continue
                    sub_lbl = to_turkish_upper(str(sub.get("text_primary", "")).strip())[:38]
                    if not sub_lbl:
                        continue
                    sub_w_idx = int(sub.get("start_word_idx", sw_idx + slot_i))
                    sub_tok = token_by_idx.get(sub_w_idx, sw_tok)
                    sub_st = round(max(scene.start_sec, sub_tok.start), 2)
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
                            text_secondary=str(sub.get("text_secondary", "")).strip()[:60],
                            group_id=grp_id,
                            stack_slot=slot_i,
                            semantic_priority=True,
                            rationale=str(ev.get("rationale", "Sıralı kavram grubu")),
                        )
                    )
            else:
                lbl = to_turkish_upper(str(ev.get("text_primary", "")).strip())[:42]
                if not lbl or len(lbl) < 3:
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
                        text_secondary=str(ev.get("text_secondary", "")).strip()[:70],
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
    ) -> List[PlannedScenarioItem]:
        """Deterministik öğelerle LLM öğelerini çakışma ve mükerrerlik olmadan birleştirir."""
        combined: List[PlannedScenarioItem] = list(det_items)
        seen_labels = {to_turkish_lower(it.text_primary) for it in combined}

        for lit in llm_items:
            norm_lbl = to_turkish_lower(lit.text_primary)
            if norm_lbl in seen_labels:
                continue
            # Aynı saniyede (<= 1.2sn) aynı tipte başka bir tekil öğe varsa çakışmayı önle
            conflict = any(
                abs(lit.start_sec - ex.start_sec) < 1.2 and not lit.group_id and not ex.group_id
                for ex in combined
            )
            if not conflict:
                combined.append(lit)
                seen_labels.add(norm_lbl)

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
                        person_wiki_tr=it.wiki_query_tr,
                        person_wiki_en=it.wiki_query_en,
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

        # 1. Hızlı Kural Denetimi (Yasaklı hitaplar, parçalar arası yakın tekrarlar, aşırı sıkışık öğeler)
        seen_recent: Dict[str, Tuple[float, str, int]] = {}
        for sc in script.scenes:
            for it in sc.items:
                lbl_up = to_turkish_upper(it.text_primary).strip()
                if lbl_up in self.BANNED_LABELS or len(lbl_up) < 2:
                    revisions.append(
                        CritiqueRevision(
                            action="REMOVE",
                            target_id=it.item_id,
                            scene_id=sc.scene_id,
                            reason=f"'{lbl_up}' bir kavramsal başlık değil, hitap/bağlaç ifadesidir; kaldırılmalı.",
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
                    existing_targets = {r.target_id for r in revisions if r.target_id}
                    for r in llm_rep.revisions:
                        if not r.target_id or r.target_id not in existing_targets:
                            revisions.append(r)
                            if r.target_id:
                                existing_targets.add(r.target_id)
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
        scenes_summary = []
        for sc in script.scenes:
            items_desc = [
                f"  - [id={it.item_id} | {it.action_type} | w{it.start_word_idx}..w{it.end_word_idx} ({it.start_sec:.1f}s-{it.end_sec:.1f}s)] "
                f"Başlık='{it.text_primary}'" + (f" | Alt='{it.text_secondary}'" if it.text_secondary else "")
                for it in sc.items
            ]
            tr_desc = (
                f"  -> [GEÇİŞ id={sc.transition_after.boundary_id} @ {sc.transition_after.timestamp:.1f}s | Neden: {sc.transition_after.reason}]"
                if sc.transition_after
                else "  -> [Video Sonu]"
            )
            scenes_summary.append(
                f"SAHNE #{sc.scene_id} ({sc.start_sec:.1f}s - {sc.end_sec:.1f}s | Rol: {sc.narrative_role}):\n"
                f"  Metin: \"{sc.transcript_text[:360]}\"\n"
                f"  Planlanan Editler ({len(sc.items)} adet):\n"
                + ("\n".join(items_desc) if items_desc else "  (Boş)")
                + f"\n{tr_desc}"
            )

        changelog_block = ""
        if iteration > 1 and applied_log:
            changelog_block = (
                f"\n⚡ ÖNCEKİ DENETİMDEN SONRA YAPILAN DÜZELTMELER (TUR {iteration}):\n"
                + "\n".join(f"- {ch}" for ch in applied_log)
                + "\nLütfen bu düzeltilmiş versiyonu kontrol et ve BAŞKA SORUN KALDI MI değerlendir. "
                "Eğer önemli bir mantık hatası kalmadıysa is_approved: true dön!\n"
            )

        prompt = (
            "Sen Başeditör (Denetçi) Yapay Zekasın. Görevin, parça parça oluşturulup birleştirilen "
            "Tam Video Kurgu Senaryosunu denetlemektir.\n"
            "Kontrol Kriterlerin:\n"
            "1. Konulacak yazılar, kişi/eser resimleri, kümülatif listeler ve konuldukları kısımlar metinle mantıklı mı?\n"
            "2. Gereksiz, anlamsız veya mükerrer bir yazı/resim varsa 'REMOVE' ile kaldır.\n"
            "3. Yanlış yazılmış veya eksik kalmış bir başlık varsa 'MODIFY' ile düzelt.\n"
            "4. Metinde çok önemli bir düşünür, eser veya kavram geçtiği halde o sahneye hiçbir edit konulmamışsa 'ADD' ile ekle.\n"
            f"{changelog_block}\n"
            "MEVCUT TAM KURGU SENARYOSU:\n"
            + "\n\n".join(scenes_summary)
            + "\n\nSADECE aşağıdaki JSON formatında yanıt ver:\n"
            '{"is_approved": true, "overall_score": 95, '
            '"summary_feedback": "Genel değerlendirme özeti", '
            '"revisions": ['
            '{"action": "REMOVE|MODIFY|ADD", "target_id": "sc1_it_0", "scene_id": 1, '
            '"action_type": "PERSON_INTRODUCTION|DEFINITION_CALLOUT|KEY_TERM_CALLOUT", '
            '"start_word_idx": 10, "end_word_idx": 15, '
            '"text_primary": "YENİ BAŞLIK", "text_secondary": "Alt metin", '
            '"wiki_query_tr": "", "reason": "Düzeltme nedeni"}'
            "]}"
        )

        raw = self.gemini.generate_text(prompt, max_retries=1)
        if not raw:
            return None
        clean_json = self.gemini.extract_balanced_json(raw, prefer_array=False)
        if not clean_json:
            return None
        data = json.loads(clean_json)
        if not isinstance(data, dict):
            return None

        revs = [
            CritiqueRevision.from_dict(r)
            for r in data.get("revisions", [])
            if isinstance(r, dict) and r.get("action")
        ]
        is_app = bool(data.get("is_approved", len(revs) == 0))
        if len(revs) == 0:
            is_app = True

        return CritiqueReport(
            iteration=iteration,
            is_approved=is_app,
            overall_score=int(data.get("overall_score", 90 if is_app else 75)),
            summary_feedback=str(data.get("summary_feedback", "")),
            revisions=revs,
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

        for rev in revisions:
            act = rev.action.upper().strip()

            if act == "REMOVE" and rev.target_id:
                for sc in script.scenes:
                    before_len = len(sc.items)
                    sc.items = [it for it in sc.items if it.item_id != rev.target_id]
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
                        if it.item_id == rev.target_id:
                            old_lbl = it.text_primary
                            if rev.text_primary:
                                it.text_primary = to_turkish_upper(rev.text_primary.strip())[:42]
                            if rev.text_secondary:
                                it.text_secondary = rev.text_secondary.strip()[:70]
                            if rev.action_type:
                                it.action_type = rev.action_type
                            if rev.start_word_idx is not None and rev.start_word_idx in token_by_idx:
                                it.start_word_idx = rev.start_word_idx
                                it.start_sec = round(token_by_idx[rev.start_word_idx].start, 2)
                            if rev.end_word_idx is not None and rev.end_word_idx in token_by_idx:
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

    def __init__(self, gemini_client: Any = None, max_workers: int = 4):
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
