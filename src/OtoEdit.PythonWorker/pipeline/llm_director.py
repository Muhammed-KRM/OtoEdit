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
from pipeline.holistic_analyzer import ENGINE_VERSION, HolisticAnalyzer, audit_overlay_sync
from pipeline.master_plan_validator import MasterPlanValidator
from pipeline.safe_zone_vision_engine import DynamicTypographySizer, SafeZoneSpatialSolver
from pipeline.theme_profiles import resolve_sub_theme
from pipeline.vlm_asset_verifier import VLMAssetVerifier
from services.gemini_client import GeminiClient
from services.pexels_client import PexelsClient
from services.web_image_crawler import WebImageCrawler
from utils.logger import get_logger

logger = get_logger("LlmDirector")

# Otomatik yönetmen yazılarının arkasındaki yarı saydam siyah kutu (editörde ve render'da aynı)
TEXT_BACKDROP_COLOR = "#00000080"


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
        self.verifier = VLMAssetVerifier(gemini_client=self.gemini, enable_vlm=True)
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

        normalized_cuts = self.analyzer._normalize_cuts(cuts or [])

        # AŞAMA 3: Kelime-Senkronlu Kurgu Olaylarını Somutlaştır
        # NOT: Sıradan nefes/retake kesimlerine (normalized_cuts[:8]) körlemesine geçiş efekti
        # eklenmez; geçiş efektleri YALNIZCA anlamlı konu/bölüm (chapter) sınırlarında üretilir
        # ve yalnızca hızlı sola kayma (slideleft) + temiz swish-whoosh sesi kullanılır.
        for ch_idx, ch in enumerate(chapter_plans):
            if ch_idx > 0 and ch.start_sec > 3.5:
                tr_ts = round(ch.start_sec, 2)
                sfx_ts = tr_ts

                tr_type = "slideleft"
                tr_dur = 0.40
                sfx_preset = "capcut-swish-large"
                sfx_name = "Swish Whoosh (Large 794558)"
                sfx_dur = 0.81
                sfx_vol = 0.22

                generated_transitions.append({
                    "id": f"ad_tr_ch_{ch_idx}",
                    "timestamp": tr_ts,
                    "boundaryTime": tr_ts,
                    "boundarySourceTime": tr_ts,
                    "type": tr_type,
                    "transitionType": tr_type,
                    "duration": tr_dur,
                })
                generated_sfx.append({
                    "id": f"ad_sfx_tr_ch_{ch_idx}",
                    "name": sfx_name,
                    "presetId": sfx_preset,
                    "synthPreset": sfx_preset,
                    "type": "whoosh",
                    "category": "whoosh",
                    "sourceUrl": f"sfx://{sfx_preset}",
                    "timestamp": sfx_ts,
                    "start": sfx_ts,
                    "duration": sfx_dur,
                    "volume": sfx_vol,
                    "subThemeRole": "TOPIC_TRANSITION",
                    "isTransitionSfx": True,
                })

            # Grup bazlı (PROGRESSIVE_LIST & PAIRED_TERMS) toplam satır sayısını ve uyumlu grup font boyutunu önceden hesapla
            group_counts: Dict[str, int] = {}
            group_texts: Dict[str, List[str]] = {}
            for e_item in ch.events:
                if e_item.group_id and e_item.stack_slot is not None:
                    group_counts[e_item.group_id] = group_counts.get(e_item.group_id, 0) + 1
                    group_texts.setdefault(e_item.group_id, []).append(e_item.text_primary)

            group_harmonized_font: Dict[str, int] = {}
            for grp_id, texts in group_texts.items():
                st_cnt = max(2, group_counts.get(grp_id, len(texts)))
                computed_sizes = [
                    DynamicTypographySizer.compute(
                        text=t_str,
                        stack_count=st_cnt,
                        stack_slot=0,
                        action_type="PAIRED_TERMS" if st_cnt == 2 else "PROGRESSIVE_LIST",
                    )[0]
                    for t_str in texts
                ]
                group_harmonized_font[grp_id] = min(computed_sizes) if computed_sizes else 46

            for evt in ch.events:
                action_type = evt.action_type
                dur = round(max(0.45, evt.end_sec - evt.start_sec), 2)
                sub_theme = resolve_sub_theme(theme_profile, action_type)

                # --------------------------------------------------------------
                # 1. KİŞİ VEYA ESER TANITIMI (PERSON_INTRODUCTION / WORK_INTRODUCTION):
                # SADECE kişi veya somut bir eser tanıtıldığında doğrulanmış Wikipedia görseli konur!
                # Mini-Tema A: Aniden belirir (pop-up) + "Tın" sesi (ding-bright, vol: 0.18)
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
                            max_candidates=3,
                            is_work=(action_type == "WORK_INTRODUCTION"),
                        )
                        if not cand_portraits:
                            cand_portraits = self.crawler.gather_verified_candidates(
                                query_tr=wiki_tr,
                                query_en=wiki_en,
                                fallback_en=evt.fallback_minimal_query_en or wiki_en or wiki_tr,
                                max_candidates=3,
                            )
                        portrait_asset = self.verifier.select_best_candidate(
                            candidates=cand_portraits,
                            spoken_context_tr=evt.text_primary,
                            concept_title_tr=evt.text_primary,
                            theme_display_name=theme_profile.display_name,
                        )

                    typo_spec = spatial_solver.solve_dynamic_typography_and_placement(
                        text=evt.text_primary,
                        start_sec=evt.start_sec,
                        end_sec=evt.end_sec,
                        stack_count=1,
                        stack_slot=None,
                        action_type=action_type,
                    )

                    # Sol üste (X=18.5%, Y=24%) Kişi / Eser Adı
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
                        "positionX": typo_spec.position_x_pct,
                        "positionY": typo_spec.position_y_pct,
                        "fontSize": typo_spec.font_size_1080p,
                        "maxWidthCqi": typo_spec.max_width_cqi,
                        "lineHeight": typo_spec.line_height,
                        "stackCount": 1,
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
                        "animation": sub_theme.entry_animation,
                        "exitAnimation": sub_theme.exit_animation,
                        "actionType": action_type,
                        "subThemeRole": sub_theme.role_id,
                        "preset": theme_profile.preset_id,
                        "anchorSlot": "TOP_LEFT_CARD",
                        "trackId": 2,
                        "track_id": 2,
                        "semanticPriority": True,
                        "pairedGroupId": pair_group_id,
                        "groupId": pair_group_id,
                    })

                    # Sağ üste (X=82%, Y=28%) Doğrulanmış Wikipedia Portresi / Eser Görseli
                    if portrait_asset:
                        chosen_url = str(portrait_asset["url"])
                        self.crawler.used_links.add(chosen_url)
                        styling = portrait_asset.get("styling", {})
                        img_x, img_y = spatial_solver.register_external_box(
                            evt.start_sec, evt.end_sec, 82.0, 28.0, 26.0, 28.0
                        )
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
                            "positionX": img_x,
                            "positionY": img_y,
                            "scale": 0.90,
                            "opacity": 98.0,
                            "animation": sub_theme.entry_animation,
                            "exitAnimation": sub_theme.exit_animation,
                            "actionType": action_type,
                            "subThemeRole": sub_theme.role_id,
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
                            "groupId": pair_group_id,
                        })

                    generated_sfx.append({
                        "id": f"ad_sfx_{evt.event_id}",
                        "name": sub_theme.sfx_name,
                        "presetId": sub_theme.sfx_preset_id,
                        "type": sub_theme.sfx_type,
                        "category": "ui",
                        "sourceUrl": f"sfx://{sub_theme.sfx_preset_id}",
                        "timestamp": evt.start_sec,
                        "start": evt.start_sec,
                        "duration": sub_theme.sfx_duration,
                        "volume": sub_theme.sfx_volume,
                        "subThemeRole": sub_theme.role_id,
                        "boundEventId": f"ad_txt_{evt.event_id}",
                    })
                    continue

                # --------------------------------------------------------------
                # 2. KÜMÜLATİF LİSTE (PROGRESSIVE_LIST) VE İKİLİ KAVRAM (PAIRED_TERMS):
                # Sol sütuna alt alta (1-3 satır tamamen omuz üstü Y=16%, 27%, 38%; 4. satır Y=49%) dizilir,
                # Sol sütun (4 satır) dolduğunda Sağ sütuna (X=81.5%, Y=16%...) geçer!
                # Mini-Tema B (PROGRESSIVE_LIST): typewriter + keyboard-type (HER MADDEDE ÇALAR!)
                # Mini-Tema C (PAIRED_TERMS): slide-up + pop-bubble (HER KAVRAMDA ÇALAR!)
                # --------------------------------------------------------------
                if evt.stack_slot is not None:
                    slot = int(evt.stack_slot)
                    st_count = max(
                        2,
                        group_counts.get(
                            evt.group_id or "",
                            3 if action_type == "PROGRESSIVE_LIST" else 2,
                        ),
                    )
                    typo_spec = spatial_solver.solve_dynamic_typography_and_placement(
                        text=evt.text_primary,
                        start_sec=evt.start_sec,
                        end_sec=evt.end_sec,
                        stack_count=st_count,
                        stack_slot=slot,
                        action_type=action_type,
                    )
                    font_sz = group_harmonized_font.get(evt.group_id or "", typo_spec.font_size_1080p)
                    horiz_pos = "left" if typo_spec.position_x_pct < 50.0 else "right"
                    text_color = (
                        theme_profile.accent_color_hex
                        if sub_theme.use_accent_color
                        else theme_profile.text_color_hex
                    )

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
                        "positionX": typo_spec.position_x_pct,
                        "positionY": typo_spec.position_y_pct,
                        "fontSize": font_sz,
                        "maxWidthCqi": typo_spec.max_width_cqi,
                        "lineHeight": typo_spec.line_height,
                        "stackCount": st_count,
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
                        "animation": sub_theme.entry_animation,
                        "exitAnimation": sub_theme.exit_animation,
                        "actionType": action_type,
                        "subThemeRole": sub_theme.role_id,
                        "preset": theme_profile.preset_id,
                        "anchorSlot": typo_spec.anchor_slot,
                        "trackId": stack_track_id,
                        "track_id": stack_track_id,
                        "semanticPriority": True,
                        "pairedGroupId": evt.group_id or f"stack_{evt.event_id}",
                        "groupId": evt.group_id or f"stack_{evt.event_id}",
                        "stackSlot": slot,
                    })

                    # HER MADDEDE (slot = 0, 1, 2, 3, 4...) KENDİ MİNİ-TEMA SESİ ÇALAR!
                    generated_sfx.append({
                        "id": f"ad_sfx_{evt.event_id}",
                        "name": sub_theme.sfx_name,
                        "presetId": sub_theme.sfx_preset_id,
                        "type": sub_theme.sfx_type,
                        "category": "ui" if sub_theme.sfx_type == "keyboard" else "pop",
                        "sourceUrl": f"sfx://{sub_theme.sfx_preset_id}",
                        "timestamp": evt.start_sec,
                        "start": evt.start_sec,
                        "duration": sub_theme.sfx_duration,
                        "volume": sub_theme.sfx_volume,
                        "subThemeRole": sub_theme.role_id,
                        "boundEventId": f"ad_txt_{evt.event_id}",
                    })
                    continue

                # --------------------------------------------------------------
                # 3. TEKİL KAVRAM VURGUSU (SINGLE_TERM, ENUMERATION_CALLOUT, DEFINITION_CALLOUT):
                # Sol üst veya Sağ üst güvenli boşlukta (Y=22%, omuz üstü, yüz/gövde teması %0)
                # 54-62px büyük puntoyla çıkar, kelimesi bitince hemen kaybolur!
                # --------------------------------------------------------------
                typo_spec = spatial_solver.solve_dynamic_typography_and_placement(
                    text=evt.text_primary,
                    start_sec=evt.start_sec,
                    end_sec=evt.end_sec,
                    stack_count=1,
                    stack_slot=None,
                    action_type=action_type,
                )

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
                    "position": ["right" if typo_spec.position_x_pct > 50.0 else "left", "top"],
                    "positionX": typo_spec.position_x_pct,
                    "positionY": typo_spec.position_y_pct,
                    "fontSize": typo_spec.font_size_1080p,
                    "maxWidthCqi": typo_spec.max_width_cqi,
                    "lineHeight": typo_spec.line_height,
                    "stackCount": 1,
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
                    "animation": sub_theme.entry_animation,
                    "exitAnimation": sub_theme.exit_animation,
                    "actionType": action_type,
                    "subThemeRole": sub_theme.role_id,
                    "preset": theme_profile.preset_id,
                    "anchorSlot": typo_spec.anchor_slot,
                    "trackId": 2,
                    "track_id": 2,
                    "semanticPriority": bool(evt.semantic_priority),
                })

                generated_sfx.append({
                    "id": f"ad_sfx_{evt.event_id}",
                    "name": sub_theme.sfx_name,
                    "presetId": sub_theme.sfx_preset_id,
                    "type": sub_theme.sfx_type,
                    "category": "pop" if sub_theme.sfx_type == "pop" else "ui",
                    "sourceUrl": f"sfx://{sub_theme.sfx_preset_id}",
                    "timestamp": evt.start_sec,
                    "start": evt.start_sec,
                    "duration": sub_theme.sfx_duration,
                    "volume": sub_theme.sfx_volume,
                    "subThemeRole": sub_theme.role_id,
                    "boundEventId": f"ad_txt_{evt.event_id}",
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
            cuts=normalized_cuts,
        )

        # Yazıların arkasındaki yarı saydam siyah kutu (editör/render) — Pydantic varsayılanına
        # güvenmeden açıkça yazılır; böylece EDL hangi yoldan kaydedilirse kaydedilsin kutu kaybolmaz.
        for ov in valid_overlays:
            if isinstance(ov, dict) and ov.get("type") == "text" and not ov.get("backgroundColor"):
                ov["backgroundColor"] = TEXT_BACKDROP_COLOR

        # AŞAMA 5: Senkron Denetimi — her yazının, kendi transkriptindeki konuşulan kelimeyle aynı anda
        # başladığını doğrula (farklı bir videonun transkripti veya kayma varsa loglarda anında görünür)
        sync_report = audit_overlay_sync(valid_overlays, segments)
        if sync_report["mismatches"]:
            logger.warning(
                f"[SyncAudit] {len(sync_report['mismatches'])}/{sync_report['checked']} yazı konuşulan "
                f"kelimeyle eşleşmedi: {sync_report['mismatches'][:5]}"
            )
        else:
            logger.info(f"[SyncAudit] {sync_report['checked']} yazının tamamı konuşulan kelimeyle senkron.")

        logger.info(
            f"[LlmDirector] Motor={ENGINE_VERSION} | Tema={theme_profile.id} | "
            f"Overlay={len(valid_overlays)} SFX={len(valid_sfx)} Geçiş={len(valid_transitions)}"
        )

        return {
            "theme_profile_id": theme_profile.id,
            "subject_summary": summary,
            "engine_version": ENGINE_VERSION,
            "sync_audit": sync_report,
            "overlays": valid_overlays,
            "sfx_list": valid_sfx,
            "sfxClips": valid_sfx,
            "transitions": valid_transitions,
        }
