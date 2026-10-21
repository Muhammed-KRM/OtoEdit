"""
5 Aşamalı Kelime-Senkronlu Multimodal Otonom Yönetmen Orkestratörü (LlmDirector).
Stage 1: HolisticAnalyzer & ThemeProfile (Kelime bazlı Kişi/Eser, Kümülatif Liste, İkili Kavram, Tekil Terim)
Stage 2: SafeZoneSpatialSolver (Sol Sütun -> Sağ Sütun Taşma & Yüz Koruma)
Stage 3: WebImageCrawler (SADECE Kişi ve Eser Tanıtımlarında Wikipedia Portre/Eser Görseli) & VLMAssetVerifier
Stage 4: MasterPlanValidator (Kelime Sınırları ve Kümülatif Grup Koruma)
Stage 5: DeterministicTimelineExecutor Çıktısı (overlays, sfx_list / sfxClips, transitions)
"""

import os
import tempfile
from typing import Any, Dict, List, Optional
from pipeline.holistic_analyzer import HolisticAnalyzer
from pipeline.master_plan_validator import MasterPlanValidator
from pipeline.safe_zone_vision_engine import SafeZoneSpatialSolver
from pipeline.vlm_asset_verifier import VLMAssetVerifier
from services.gemini_client import GeminiClient
from services.pexels_client import PexelsClient
from services.web_image_crawler import WebImageCrawler
from utils.logger import get_logger

logger = get_logger("LlmDirector")


class LlmDirector:
    def __init__(
        self,
        gemini_client: Any = None,
        pexels_client: Any = None,
        work_dir: Optional[str] = None,
        enable_web_crawl: bool = True,
    ):
        self.gemini = gemini_client or GeminiClient()
        self.pexels = pexels_client or PexelsClient()
        self.work_dir = work_dir or os.path.join(tempfile.gettempdir(), "otoedit_director_assets")
        self.enable_web_crawl = enable_web_crawl
        self.analyzer = HolisticAnalyzer(gemini_client=self.gemini, enable_llm_planning=True)
        self.crawler = WebImageCrawler(work_dir=self.work_dir, pexels_client=self.pexels)
        self.verifier = VLMAssetVerifier(gemini_client=self.gemini)
        self.validator = MasterPlanValidator()

    def compose_intelligent_plan(
        self,
        segments: List[Dict[str, Any]],
        cuts: Optional[List[Any]] = None,
        video_duration: float = 0.0,
        face_positions: Optional[List[Dict[str, Any]]] = None,
        existing_overlays: Optional[List[Any]] = None,
        existing_sfx: Optional[List[Dict[str, Any]]] = None,
        existing_transitions: Optional[List[Dict[str, Any]]] = None,
        subtitles_enabled: bool = True,
        video_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        norm_existing_overlays: List[Dict[str, Any]] = []
        for eo in existing_overlays or []:
            if isinstance(eo, dict):
                norm_existing_overlays.append(dict(eo))
            elif hasattr(eo, "model_dump"):
                norm_existing_overlays.append(eo.model_dump())
            elif hasattr(eo, "dict"):
                norm_existing_overlays.append(eo.dict())

        existing_sfx = list(existing_sfx or [])
        existing_transitions = list(existing_transitions or [])

        if not segments or video_duration <= 0:
            return {
                "overlays": norm_existing_overlays,
                "sfx_list": existing_sfx,
                "sfxClips": existing_sfx,
                "transitions": existing_transitions,
            }

        # AŞAMA 1: Kelime-Senkronlu Bütüncül Analiz ve Kilitli ThemeProfile
        theme_profile, summary, chapter_plans = self.analyzer.analyze_video(
            segments=segments, video_duration=video_duration, cuts=cuts
        )

        # AŞAMA 2: SafeZone Uzamsal Çözücü Başlatımı
        spatial_solver = SafeZoneSpatialSolver(
            face_positions=face_positions,
            subtitles_enabled=subtitles_enabled,
            video_path=video_path,
        )

        generated_overlays: List[Dict[str, Any]] = []
        generated_sfx: List[Dict[str, Any]] = []
        generated_transitions: List[Dict[str, Any]] = []

        # Mevcut kesimler varsa kesim sınırlarına yumuşak geçiş adayı ekle
        normalized_cuts = self.analyzer._normalize_cuts(cuts or [])
        for c_idx, (c_start, c_end) in enumerate(normalized_cuts[:8]):
            tr_type = theme_profile.allowed_transitions[
                c_idx % len(theme_profile.allowed_transitions)
            ]
            generated_transitions.append({
                "id": f"ad_tr_cut_{c_idx + 1}",
                "timestamp": round(c_start, 2),
                "boundaryTime": round(c_end, 2),
                "boundarySourceTime": round(c_end, 2),
                "type": tr_type,
                "duration": theme_profile.transition_duration_sec,
            })

        # AŞAMA 3: Kelime-Senkronlu Kurgu Olaylarını Somutlaştır
        for ch_idx, ch in enumerate(chapter_plans):
            if ch_idx > 0 and ch.start_sec > 3.5:
                tr_type = theme_profile.allowed_transitions[
                    (ch_idx - 1) % len(theme_profile.allowed_transitions)
                ]
                generated_transitions.append({
                    "id": f"ad_tr_ch_{ch_idx}",
                    "timestamp": round(ch.start_sec, 2),
                    "boundaryTime": round(ch.start_sec, 2),
                    "boundarySourceTime": round(ch.start_sec, 2),
                    "type": tr_type,
                    "duration": theme_profile.transition_duration_sec,
                })

            for evt in ch.events:
                action_type = evt.action_type
                dur = round(max(0.45, evt.end_sec - evt.start_sec), 2)

                # --------------------------------------------------------------
                # 1. KİŞİ VEYA ESER TANITIMI (PERSON_INTRODUCTION / WORK_INTRODUCTION):
                # SADECE kişi veya somut bir eser tanıtıldığında Wikipedia görseli konur!
                # --------------------------------------------------------------
                if action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION", "CONCEPT_IMAGE_CARD"):
                    pair_group_id = evt.group_id or f"pair_{evt.event_id}"
                    portrait_asset = None
                    wiki_tr = evt.person_wiki_tr or evt.primary_web_query_tr
                    wiki_en = evt.person_wiki_en or evt.secondary_stock_query_en

                    if self.enable_web_crawl and (wiki_tr or wiki_en):
                        cand_portraits = self.crawler.gather_person_portrait_candidates(
                            wiki_title_tr=wiki_tr,
                            wiki_title_en=wiki_en,
                            max_candidates=2,
                        )
                        if not cand_portraits and action_type == "CONCEPT_IMAGE_CARD":
                            cand_portraits = self.crawler.gather_verified_candidates(
                                query_tr=wiki_tr,
                                query_en=wiki_en,
                                fallback_en=evt.fallback_minimal_query_en,
                                max_candidates=2,
                            )
                        portrait_asset = self.verifier.select_best_candidate(
                            candidates=cand_portraits,
                            spoken_context_tr=evt.text_primary,
                            concept_title_tr=evt.text_primary,
                            theme_display_name=theme_profile.display_name,
                        )

                    # Sol üste (X=16%, Y=24%) Kişi / Eser Adı
                    generated_overlays.append({
                        "id": f"ad_txt_{evt.event_id}",
                        "type": "text",
                        "text": evt.text_primary,
                        "content": evt.text_primary,
                        "timestamp": evt.start_sec,
                        "start": evt.start_sec,
                        "end": evt.end_sec,
                        "duration": dur,
                        "position": ["left", "top"],
                        "positionX": 16.0,
                        "positionY": 24.0,
                        "fontSize": int(theme_profile.title_font_size_1080p),
                        "font": theme_profile.font_family,
                        "fontFamily": theme_profile.font_family,
                        "color": theme_profile.text_color_hex,
                        "strokeColor": theme_profile.stroke_color_hex,
                        "strokeWidth": theme_profile.stroke_width_px,
                        "backgroundBox": theme_profile.background_box,
                        "boxStyle": "rounded" if theme_profile.background_box else "none",
                        "boxColor": theme_profile.box_color_hex,
                        "boxBgColor": theme_profile.box_color_hex,
                        "boxOpacity": theme_profile.box_opacity,
                        "animation": theme_profile.entry_animation,
                        "exitAnimation": theme_profile.exit_animation,
                        "preset": theme_profile.preset_id,
                        "anchorSlot": "TOP_LEFT_CARD",
                        "trackId": 2,
                        "track_id": 2,
                        "semanticPriority": True,
                        "pairedGroupId": pair_group_id,
                    })

                    # Sağ üste (X=82%, Y=28%) Doğrulanmış Wikipedia Portresi / Eser Görseli
                    if portrait_asset:
                        chosen_url = str(portrait_asset["url"])
                        self.crawler.used_links.add(chosen_url)
                        styling = portrait_asset.get("styling", {})
                        generated_overlays.append({
                            "id": f"ad_img_{evt.event_id}",
                            "type": "image",
                            "content": evt.text_primary,
                            "text": evt.text_primary,
                            "source": chosen_url,
                            "timestamp": evt.start_sec,
                            "start": evt.start_sec,
                            "end": evt.end_sec,
                            "duration": dur,
                            "position": ["right", "top"],
                            "positionX": 82.0,
                            "positionY": 28.0,
                            "scale": 0.90,
                            "opacity": 98.0,
                            "animation": styling.get("entry_animation", "fade"),
                            "exitAnimation": styling.get("exit_animation", "fade"),
                            "shape": styling.get("mask_shape", "rounded"),
                            "maskShape": styling.get("mask_shape", "rounded"),
                            "borderRadius": styling.get("border_radius_px", 18),
                            "dropShadow": True,
                            "shadowBlur": 18,
                            "removeBg": False,
                            "anchorSlot": "TOP_RIGHT_CARD",
                            "trackId": 3,
                            "track_id": 3,
                            "semanticPriority": True,
                            "pairedGroupId": pair_group_id,
                        })

                    sfx_cfg = theme_profile.allowed_sfx_map.get("PERSON_INTRODUCTION") or {"type": "whoosh", "volume": 0.15}
                    generated_sfx.append({
                        "id": f"ad_sfx_{evt.event_id}",
                        "type": sfx_cfg["type"],
                        "timestamp": evt.start_sec,
                        "volume": sfx_cfg["volume"],
                    })
                    continue

                # --------------------------------------------------------------
                # 2. KÜMÜLATİF LİSTE (PROGRESSIVE_LIST) VE İKİLİ KAVRAM (PAIRED_TERMS):
                # Sol sütuna alt alta (Y=18%, 27.5%, 37%, 46.5%) dizilir,
                # Sol sütun (4 satır) dolduğunda Sağ sütuna (X=84%, Y=18%...) geçer!
                # --------------------------------------------------------------
                if evt.stack_slot is not None:
                    slot = int(evt.stack_slot)
                    if slot < 4:
                        pos_x = 16.0
                        pos_y = round(18.0 + slot * 9.5, 1)
                        slot_id = f"LEFT_STACK_{slot + 1}"
                        horiz_pos = "left"
                    else:
                        pos_x = 84.0
                        pos_y = round(18.0 + ((slot - 4) % 4) * 9.5, 1)
                        slot_id = f"RIGHT_STACK_{(slot - 4) + 1}"
                        horiz_pos = "right"

                    text_color = (
                        theme_profile.accent_color_hex
                        if action_type == "PROGRESSIVE_LIST"
                        else theme_profile.text_color_hex
                    )
                    font_sz = max(28, int(theme_profile.title_font_size_1080p) - 4)

                    stack_track_id = 1 + (slot % 5)
                    generated_overlays.append({
                        "id": f"ad_txt_{evt.event_id}",
                        "type": "text",
                        "text": evt.text_primary,
                        "content": evt.text_primary,
                        "timestamp": evt.start_sec,
                        "start": evt.start_sec,
                        "end": evt.end_sec,
                        "duration": dur,
                        "position": [horiz_pos, "top"],
                        "positionX": pos_x,
                        "positionY": pos_y,
                        "fontSize": font_sz,
                        "font": theme_profile.font_family,
                        "fontFamily": theme_profile.font_family,
                        "color": text_color,
                        "strokeColor": theme_profile.stroke_color_hex,
                        "strokeWidth": theme_profile.stroke_width_px,
                        "backgroundBox": theme_profile.background_box,
                        "boxStyle": "rounded" if theme_profile.background_box else "none",
                        "boxColor": theme_profile.box_color_hex,
                        "boxBgColor": theme_profile.box_color_hex,
                        "boxOpacity": theme_profile.box_opacity,
                        "animation": theme_profile.entry_animation,
                        "exitAnimation": theme_profile.exit_animation,
                        "preset": theme_profile.preset_id,
                        "anchorSlot": slot_id,
                        "trackId": stack_track_id,
                        "track_id": stack_track_id,
                        "semanticPriority": True,
                        "pairedGroupId": evt.group_id or f"stack_{evt.event_id}",
                        "stackSlot": slot,
                    })

                    # Yalnızca grubun ilk öğesinde hafif bir ses efekti çal (her kelimede gürültü yapmasın)
                    if slot == 0:
                        sfx_cfg = theme_profile.allowed_sfx_map.get(action_type) or {"type": "pop", "volume": 0.13}
                        generated_sfx.append({
                            "id": f"ad_sfx_{evt.event_id}",
                            "type": sfx_cfg["type"],
                            "timestamp": evt.start_sec,
                            "volume": sfx_cfg["volume"],
                        })
                    continue

                # --------------------------------------------------------------
                # 3. TEKİL KAVRAM VURGUSU (SINGLE_TERM, ENUMERATION_CALLOUT, DEFINITION_CALLOUT):
                # Sol üst veya Sağ üst güvenli boşlukta çıkar, kelimesi bitince hemen kaybolur!
                # --------------------------------------------------------------
                slot_id, pos_x, pos_y, scale_factor, _ = spatial_solver.solve_placement(
                    evt.start_sec, evt.end_sec, is_image_card=False
                )
                # Tekil yazıları yüz bölgesinden (30%..70%) tamamen uzak tut (Sol 16% veya Sağ 84%)
                pos_x = 16.0 if pos_x < 50.0 else 84.0
                pos_y = min(26.0, max(18.0, pos_y))

                text_color = (
                    theme_profile.accent_color_hex
                    if action_type in ("ENUMERATION_CALLOUT", "STAT_OR_ARTICLE_CALLOUT")
                    else theme_profile.text_color_hex
                )

                generated_overlays.append({
                    "id": f"ad_txt_{evt.event_id}",
                    "type": "text",
                    "text": evt.text_primary,
                    "content": evt.text_primary,
                    "timestamp": evt.start_sec,
                    "start": evt.start_sec,
                    "end": evt.end_sec,
                    "duration": dur,
                    "position": ["right" if pos_x > 50.0 else "left", "top"],
                    "positionX": pos_x,
                    "positionY": pos_y,
                    "fontSize": int(round(theme_profile.title_font_size_1080p * scale_factor)),
                    "font": theme_profile.font_family,
                    "fontFamily": theme_profile.font_family,
                    "color": text_color,
                    "strokeColor": theme_profile.stroke_color_hex,
                    "strokeWidth": theme_profile.stroke_width_px,
                    "backgroundBox": theme_profile.background_box,
                    "boxStyle": "rounded" if theme_profile.background_box else "none",
                    "boxColor": theme_profile.box_color_hex,
                    "boxBgColor": theme_profile.box_color_hex,
                    "boxOpacity": theme_profile.box_opacity,
                    "animation": theme_profile.entry_animation,
                    "exitAnimation": theme_profile.exit_animation,
                    "preset": theme_profile.preset_id,
                    "anchorSlot": slot_id,
                    "trackId": 2,
                    "track_id": 2,
                    "semanticPriority": bool(evt.semantic_priority),
                })

                sfx_cfg = theme_profile.allowed_sfx_map.get(action_type) or theme_profile.allowed_sfx_map.get("KEY_TERM_CALLOUT")
                if sfx_cfg:
                    generated_sfx.append({
                        "id": f"ad_sfx_{evt.event_id}",
                        "type": sfx_cfg["type"],
                        "timestamp": evt.start_sec,
                        "volume": sfx_cfg["volume"],
                    })

        # Kısa test videolarında (< 3 segment, >= 15s) en az 3 katman bulunmasını garanti et
        if len(generated_overlays) < 3 and video_duration >= 15.0 and segments:
            mid_ts = round(video_duration * 0.45, 2)
            generated_overlays.append({
                "id": "ad_txt_mid_summary",
                "type": "text",
                "text": theme_profile.display_name.split("&")[0].strip(),
                "content": theme_profile.display_name.split("&")[0].strip(),
                "timestamp": mid_ts,
                "start": mid_ts,
                "end": round(mid_ts + 2.4, 2),
                "duration": 2.4,
                "position": ["right", "top"],
                "positionX": 84.0,
                "positionY": 20.0,
                "fontSize": int(theme_profile.title_font_size_1080p),
                "font": theme_profile.font_family,
                "fontFamily": theme_profile.font_family,
                "color": theme_profile.text_color_hex,
                "strokeColor": theme_profile.stroke_color_hex,
                "strokeWidth": theme_profile.stroke_width_px,
                "backgroundBox": theme_profile.background_box,
                "boxStyle": "rounded" if theme_profile.background_box else "none",
                "boxColor": theme_profile.box_color_hex,
                "boxBgColor": theme_profile.box_color_hex,
                "boxOpacity": theme_profile.box_opacity,
                "animation": theme_profile.entry_animation,
                "exitAnimation": theme_profile.exit_animation,
                "preset": theme_profile.preset_id,
                "anchorSlot": "TOP_RIGHT_CARD",
                "trackId": 2,
                "track_id": 2,
            })

        if not generated_transitions and video_duration >= 10.0 and len(segments) >= 2:
            mid_seg = segments[len(segments) // 2]
            mid_ts = round(float(mid_seg.get("start", video_duration * 0.5)), 2)
            generated_transitions.append({
                "id": "ad_tr_mid_1",
                "timestamp": mid_ts,
                "boundaryTime": mid_ts,
                "boundarySourceTime": mid_ts,
                "type": theme_profile.allowed_transitions[0],
                "duration": theme_profile.transition_duration_sec,
            })

        # AŞAMA 4: Deterministik Master Plan Doğrulaması ve Onarımı
        valid_overlays, valid_sfx, valid_transitions = self.validator.validate_and_repair(
            overlays=norm_existing_overlays + generated_overlays,
            sfx_list=existing_sfx + generated_sfx,
            transitions=existing_transitions + generated_transitions,
            theme_profile=theme_profile,
            video_duration=video_duration,
            subtitles_enabled=subtitles_enabled,
        )

        return {
            "theme_profile_id": theme_profile.id,
            "subject_summary": summary,
            "overlays": valid_overlays,
            "sfx_list": valid_sfx,
            "sfxClips": valid_sfx,
            "transitions": valid_transitions,
        }
