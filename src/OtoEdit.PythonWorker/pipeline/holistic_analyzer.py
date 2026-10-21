"""
Aşama 1: Bütüncül Video Analizcisi (HolisticAnalyzer).
Videonun tamamını (00:00 -> son saniye) anlamsal bölümlere (Chapters) ayırır,
tek bir kilitli ThemeProfile seçer ve her bölüme orantılı kurgu eylemleri planlar.
"""

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pipeline.theme_profiles import (
    THEME_PROFILE_REGISTRY,
    ThemeProfile,
    detect_theme_profile_heuristic,
    extract_turkish_semantic_title,
    to_turkish_lower,
)
from utils.logger import get_logger

logger = get_logger("HolisticAnalyzer")


@dataclass
class PlannedEditorialEvent:
    event_id: str
    chapter_id: int
    action_type: str  # "CHAPTER_TITLE_CARD" | "CONCEPT_IMAGE_CARD" | "KEY_TERM_CALLOUT" | "STAT_OR_ARTICLE_CALLOUT" | "EMPHASIS_STICKER"
    start_sec: float
    end_sec: float
    text_primary: str
    text_secondary: str = ""
    primary_web_query_tr: str = ""
    secondary_stock_query_en: str = ""
    fallback_minimal_query_en: str = ""
    prefer_video_broll: bool = False


@dataclass
class ChapterPlan:
    chapter_id: int
    start_sec: float
    end_sec: float
    title_tr: str
    key_terms: List[str] = field(default_factory=list)
    events: List[PlannedEditorialEvent] = field(default_factory=list)


class HolisticAnalyzer:
    """
    Uzun veya kısa videoları bütünsel olarak analiz edip Bölüm Orantılı
    (Chapter-Proportional) kurgu eylem planı çıkaran yönetmen katmanı.
    """

    def __init__(self, gemini_client: Any = None, enable_llm_planning: bool = False):
        self.gemini = gemini_client
        self.enable_llm_planning = enable_llm_planning

    def analyze_video(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        cuts: Optional[List[Any]] = None,
    ) -> Tuple[ThemeProfile, str, List[ChapterPlan]]:
        """
        Döndürür: (locked_theme_profile, subject_summary, chapter_plans)
        """
        normalized_cuts = self._normalize_cuts(cuts or [])
        active_segments = self._filter_active_segments(segments, normalized_cuts)
        full_text = " ".join(str(s.get("text", "")).strip() for s in active_segments)

        # 1. Kilitli ThemeProfile tespiti
        theme_profile = detect_theme_profile_heuristic(full_text)

        # 2. Videoyu kronolojik bölümlere (Chapters) ayır (00:00 -> video_duration)
        # 20 dk (1200sn) video -> ~8 bölüm (her biri ~150sn)
        safe_duration = max(5.0, float(video_duration or 30.0))
        target_chapter_len = 150.0 if safe_duration >= 300.0 else max(25.0, safe_duration / 3.0)
        num_chapters = max(1, min(16, int(round(safe_duration / target_chapter_len))))
        chapter_boundaries = self._find_natural_chapter_boundaries(
            active_segments, safe_duration, num_chapters
        )

        # 3. Her bölüm için LLM (etkinse) veya Morfo-Sözdizimsel Analizci ile kurgu planı üret
        chapter_plans: List[ChapterPlan] = []
        for ch_idx in range(len(chapter_boundaries) - 1):
            ch_start = chapter_boundaries[ch_idx]
            ch_end = chapter_boundaries[ch_idx + 1]
            ch_segs = [
                s
                for s in active_segments
                if float(s.get("start", 0)) >= ch_start - 0.5
                and float(s.get("end", s.get("start", 0))) <= ch_end + 1.5
            ]
            if not ch_segs and active_segments:
                # En yakın segmenti dahil et
                nearest = min(
                    active_segments,
                    key=lambda s: abs(float(s.get("start", 0)) - (ch_start + ch_end) / 2.0),
                )
                ch_segs = [nearest]
            if not ch_segs:
                continue

            ch_plan = self._plan_single_chapter(
                chapter_id=ch_idx + 1,
                ch_start=ch_start,
                ch_end=ch_end,
                ch_segments=ch_segs,
                theme_profile=theme_profile,
            )
            chapter_plans.append(ch_plan)

        subject_summary = (
            f"{theme_profile.display_name} ({len(chapter_plans)} Bölüm, {safe_duration:.1f}s)"
        )
        logger.info(
            f"[HolisticAnalyzer] Tamamlandı: Tema='{theme_profile.id}', "
            f"Bölüm Sayısı={len(chapter_plans)}, "
            f"Toplam Olay={sum(len(c.events) for c in chapter_plans)}"
        )
        return theme_profile, subject_summary, chapter_plans

    def _find_natural_chapter_boundaries(
        self,
        active_segments: List[Dict[str, Any]],
        video_duration: float,
        num_chapters: int,
    ) -> List[float]:
        """
        İdeal eşit zaman noktalarına (i * D / M) en yakın cümle arası boşluğu
        (seg[k].end -> seg[k+1].start) bularak cümle ortasında kesmeyi önler.
        """
        if num_chapters <= 1 or not active_segments:
            return [0.0, video_duration]

        boundaries = [0.0]
        ideal_step = video_duration / num_chapters
        min_chapter_gap = min(15.0, max(4.0, video_duration * 0.15))

        for i in range(1, num_chapters):
            ideal_ts = i * ideal_step
            best_ts = round(ideal_ts, 2)
            best_score = -999.0
            for k in range(len(active_segments) - 1):
                gap_start = float(active_segments[k].get("end", 0))
                gap_end = float(active_segments[k + 1].get("start", gap_start))
                mid_gap = (gap_start + gap_end) / 2.0
                dist = abs(mid_gap - ideal_ts)
                if dist <= max(8.0, ideal_step * 0.35):
                    pause_dur = max(0.0, gap_end - gap_start)
                    score = pause_dur * 5.0 - (dist / 20.0)
                    if score > best_score:
                        best_score = score
                        best_ts = round(mid_gap, 2)
            if best_ts > boundaries[-1] + min_chapter_gap and best_ts < video_duration - min_chapter_gap:
                boundaries.append(best_ts)

        boundaries.append(round(video_duration, 2))
        return boundaries

    def _plan_single_chapter(
        self,
        chapter_id: int,
        ch_start: float,
        ch_end: float,
        ch_segments: List[Dict[str, Any]],
        theme_profile: ThemeProfile,
    ) -> ChapterPlan:
        """
        Tek bir bölüm (ör. 07:30 - 10:00) için LLM destekli veya deterministik
        anlamsal olayları (Bölüm Başlığı + Görsel Kart + Anahtar Terim) üretir.
        """
        ch_duration = max(1.0, ch_end - ch_start)
        max_events = max(
            2,
            min(
                6,
                int(math.floor((ch_duration / 60.0) * theme_profile.max_overlays_per_minute)) + 1,
            ),
        )

        if self.enable_llm_planning and self.gemini and getattr(self.gemini, "is_available", lambda: False)():
            llm_plan = self._call_llm_for_chapter(
                chapter_id, ch_start, ch_end, ch_segments, theme_profile, max_events
            )
            if llm_plan:
                return llm_plan

        first_seg_text = str(ch_segments[0].get("text", ""))
        chapter_title = (
            extract_turkish_semantic_title(first_seg_text, max_chars=30)
            or f"BÖLÜM {chapter_id}"
        )

        events: List[PlannedEditorialEvent] = []
        min_gap = min(theme_profile.min_gap_between_overlays_sec, max(4.0, ch_duration / 3.0))

        # 1. Bölüm Başlığı Kartı (CHAPTER_TITLE_CARD)
        first_ts = max(0.3, float(ch_segments[0].get("start", ch_start)) + 0.3)
        first_end = min(ch_end - 0.3, first_ts + 3.5)
        if first_end <= first_ts + 0.8:
            first_end = first_ts + 2.5

        events.append(
            PlannedEditorialEvent(
                event_id=f"evt_ch{chapter_id}_01",
                chapter_id=chapter_id,
                action_type="CHAPTER_TITLE_CARD",
                start_sec=round(first_ts, 2),
                end_sec=round(first_end, 2),
                text_primary=chapter_title,
                text_secondary=f"Bölüm {chapter_id}",
            )
        )
        last_event_ts = first_ts

        # 2. Bölüm içi aday segmentleri önem skoruna göre değerlendir
        scored_candidates = []
        for s in ch_segments[1:]:
            s_start = float(s.get("start", 0))
            s_text = str(s.get("text", "")).strip()
            if len(s_text) < 10:
                continue
            score = self._score_semantic_importance(s_text)
            scored_candidates.append((score, s_start, s))

        scored_candidates.sort(key=lambda x: x[1])  # Kronolojik sıra
        step_sec = max(min_gap * 0.75, ch_duration / max(2, max_events))

        evt_counter = 2
        for _score, s_start, seg in scored_candidates:
            if len(events) >= max_events:
                break
            if s_start - last_event_ts < step_sec:
                continue

            s_text = str(seg.get("text", "")).strip()
            semantic_title = extract_turkish_semantic_title(s_text, max_chars=32)
            if not semantic_title or len(semantic_title) < 3:
                continue

            lower_text = to_turkish_lower(s_text)
            has_number = bool(re.search(r"\b(\d+|madde|md\.|fıkra|yüzde|%)\b", lower_text))
            if has_number:
                action_type = "STAT_OR_ARTICLE_CALLOUT"
            elif evt_counter % 2 == 0:
                action_type = "CONCEPT_IMAGE_CARD"
            else:
                action_type = "KEY_TERM_CALLOUT"

            web_q_tr, stock_q_en, fallback_q_en = self._build_visual_queries(
                semantic_title, s_text, theme_profile.id
            )

            ev_end = min(ch_end - 0.2, s_start + 3.8)
            if ev_end <= s_start + 1.0:
                ev_end = s_start + 3.0

            events.append(
                PlannedEditorialEvent(
                    event_id=f"evt_ch{chapter_id}_{evt_counter:02d}",
                    chapter_id=chapter_id,
                    action_type=action_type,
                    start_sec=round(s_start, 2),
                    end_sec=round(ev_end, 2),
                    text_primary=semantic_title,
                    text_secondary="",
                    primary_web_query_tr=web_q_tr,
                    secondary_stock_query_en=stock_q_en,
                    fallback_minimal_query_en=fallback_q_en,
                )
            )
            last_event_ts = s_start
            evt_counter += 1

        return ChapterPlan(
            chapter_id=chapter_id,
            start_sec=round(ch_start, 2),
            end_sec=round(ch_end, 2),
            title_tr=chapter_title,
            key_terms=[e.text_primary for e in events],
            events=events,
        )

    def _call_llm_for_chapter(
        self,
        chapter_id: int,
        ch_start: float,
        ch_end: float,
        ch_segments: List[Dict[str, Any]],
        theme_profile: ThemeProfile,
        max_events: int,
    ) -> Optional[ChapterPlan]:
        """GeminiClient üzerinden bölüm için yapılandırılmış JSON kurgu planı üretir."""
        try:
            lines = [
                f"[{float(s.get('start', 0)):.1f}s - {float(s.get('end', 0)):.1f}s] {str(s.get('text', '')).strip()}"
                for s in ch_segments[:45]
            ]
            transcript_block = "\n".join(lines)
            prompt = (
                f"Sen profesyonel bir kurgu yönetmenisin. Video teması: {theme_profile.display_name}.\n"
                f"Bu bölüm [{ch_start:.1f}s - {ch_end:.1f}s] aralığındadır.\n"
                f"Aşağıdaki transkriptten en fazla {max_events} adet kurgu olayı seç.\n"
                "KURALLAR:\n"
                "1. 'text_primary' TAM BİR TÜRKÇE KAVRAM VEYA İSİM TAMLAMASI olmalıdır (en fazla 30 karakter). "
                "ASLA cümleyi ortasından kesme, ASLA '...' kullanma!\n"
                "2. 'CONCEPT_IMAGE_CARD' için 'secondary_stock_query_en' alanında SOYUT KELİME YASAKTIR; "
                "fotoğrafta fiziksel olarak görünen SOMUT NESNE veya MEKAN yaz (örn. 'wooden judge gavel law book desk').\n"
                "3. Olaylar arasında en az 18 saniye boşluk bırak.\n"
                "Sadece aşağıdaki JSON formatında yanıt ver:\n"
                '{"chapter_title": "...", "events": [{"action_type": "CHAPTER_TITLE_CARD|CONCEPT_IMAGE_CARD|KEY_TERM_CALLOUT", '
                '"start_sec": 12.5, "text_primary": "...", "primary_web_query_tr": "...", "secondary_stock_query_en": "..."}]}\n\n'
                f"TRANSKRİPT:\n{transcript_block}"
            )
            raw = self.gemini.generate_text(prompt, max_retries=1)
            if not raw:
                return None
            cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            data = self.gemini._safe_parse_json(cleaned) if hasattr(self.gemini, "_safe_parse_json") else json.loads(cleaned)
            if not isinstance(data, dict):
                return None
            raw_events = data.get("events", [])
            if not raw_events:
                return None

            events: List[PlannedEditorialEvent] = []
            for idx, ev in enumerate(raw_events[:max_events]):
                st = max(ch_start + 0.2, min(ch_end - 2.0, float(ev.get("start_sec", ch_start))))
                title = extract_turkish_semantic_title(str(ev.get("text_primary", "")), max_chars=32)
                if not title:
                    continue
                web_q, stock_q, fallback_q = self._build_visual_queries(title, title, theme_profile.id)
                events.append(
                    PlannedEditorialEvent(
                        event_id=f"evt_ch{chapter_id}_{idx + 1:02d}",
                        chapter_id=chapter_id,
                        action_type=str(ev.get("action_type", "KEY_TERM_CALLOUT")),
                        start_sec=round(st, 2),
                        end_sec=round(min(ch_end - 0.2, st + 3.8), 2),
                        text_primary=title,
                        primary_web_query_tr=str(ev.get("primary_web_query_tr") or web_q),
                        secondary_stock_query_en=str(ev.get("secondary_stock_query_en") or stock_q),
                        fallback_minimal_query_en=fallback_q,
                    )
                )
            if not events:
                return None
            return ChapterPlan(
                chapter_id=chapter_id,
                start_sec=round(ch_start, 2),
                end_sec=round(ch_end, 2),
                title_tr=extract_turkish_semantic_title(str(data.get("chapter_title", "")), 30) or events[0].text_primary,
                key_terms=[e.text_primary for e in events],
                events=events,
            )
        except Exception as exc:
            logger.warning(f"[HolisticAnalyzer] Bölüm {chapter_id} LLM çağrısı yedek plana düştü: {exc}")
            return None

    def _score_semantic_importance(self, text: str) -> float:
        lower = to_turkish_lower(text)
        score = 1.0
        for kw in (
            "önemli", "dikkat", "şart", "kural", "madde", "kanun",
            "temel", "birincisi", "ikincisi", "sonuç", "kritik", "özetle",
        ):
            if kw in lower:
                score += 1.5
        if "?" in text or "!" in text:
            score += 1.0
        return score

    def _build_visual_queries(
        self, title_tr: str, sentence_tr: str, theme_id: str
    ) -> Tuple[str, str, str]:
        """Türkçe kavramı somut Türkçe web sorgusuna ve somut İngilizce stok sorgusuna çevirir."""
        lower = to_turkish_lower(title_tr + " " + sentence_tr)
        if any(k in lower for k in ("mahkeme", "dava", "hukuk", "kanun", "hakim", "hmk", "yargı", "anayasa")):
            return (
                f"{title_tr} adalet hukuk",
                "wooden judge gavel law book courtroom desk",
                "scales of justice law library",
            )
        if any(k in lower for k in ("sözleşme", "imza", "borç", "taraflar", "dilekçe", "tebligat")):
            return (
                f"{title_tr} hukuki belge sözleşme",
                "signing legal contract document fountain pen desk",
                "business contract signature close up",
            )
        if theme_id == "corporate_explainer":
            return (
                f"{title_tr} iş dünyası",
                "modern executive boardroom presentation analytics",
                "minimalist corporate office architecture",
            )
        if theme_id == "tech_review":
            return (
                f"{title_tr} teknoloji",
                "modern software engineering monitor code close up",
                "clean minimal technology desk hardware",
            )
        if theme_id == "cinematic_documentary":
            return (
                f"{title_tr} belgesel tarih",
                "cinematic historical architecture dramatic lighting",
                "vintage archive manuscript library",
            )
        return (
            title_tr,
            "minimalist academic study books library desk",
            "clean modern architectural interior light",
        )

    @staticmethod
    def _normalize_cuts(cuts: List[Any]) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for c in cuts:
            if isinstance(c, (tuple, list)) and len(c) >= 2:
                out.append((float(c[0]), float(c[1])))
            elif isinstance(c, dict):
                out.append((float(c.get("start", 0.0)), float(c.get("end", 0.0))))
            elif hasattr(c, "start") and hasattr(c, "end"):
                out.append((float(getattr(c, "start", 0.0)), float(getattr(c, "end", 0.0))))
        return out

    def _filter_active_segments(
        self, segments: List[Dict[str, Any]], cuts: List[Tuple[float, float]]
    ) -> List[Dict[str, Any]]:
        active = []
        for s in segments:
            s_start = float(s.get("start", 0.0))
            s_end = float(s.get("end", s_start + 2.0))
            mid = (s_start + s_end) / 2.0
            if not any(c_start <= mid <= c_end for c_start, c_end in cuts):
                active.append(s)
        return active
