"""
5 Aşamalı Multimodal Otonom Yönetmen Orkestratörü (LlmDirector).
Stage 1: HolisticAnalyzer & ThemeProfile
Stage 2: SafeZoneSpatialSolver (ve KeyframeSnapshotAnalyzer)
Stage 3: WebImageCrawler & VLMAssetVerifier (Graceful Degradation ile)
Stage 4: MasterPlanValidator
Stage 5: DeterministicTimelineExecutor Çıktısı (overlays, sfx_list / sfxClips, transitions)
"""

import os
import tempfile
from typing import Any, Dict, List, Optional
from pipeline.holistic_analyzer import HolisticAnalyzer
from pipeline.master_plan_validator import MasterPlanValidator
from pipeline.safe_zone_vision_engine import SafeZoneSpatialSolver
from pipeline.vlm_asset_verifier import VLMAssetVerifier
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
        self.gemini = gemini_client
        self.pexels = pexels_client or PexelsClient()
        self.work_dir = work_dir or os.path.join(tempfile.gettempdir(), "otoedit_director_assets")
        self.enable_web_crawl = enable_web_crawl
        self.analyzer = HolisticAnalyzer(gemini_client=self.gemini)
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

        # AŞAMA 1: Bütüncül Analiz, Kilitli ThemeProfile ve Bölüm Orantılı Plan
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

        # Mevcut kesimler varsa kesim sınırlarına da geçiş adayı ekle
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

        # AŞAMA 3: Her Bölümdeki Kurgu Olaylarını Somutlaştır ve Görselleri Doğrula
        for ch_idx, ch in enumerate(chapter_plans):
            # Bölüm geçişi (İlk bölüm hariç her bölüm başlangıcına cümle arası yumuşak geçiş)
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

                # Eğer görsel kartıysa (CONCEPT_IMAGE_CARD), Çoklu Kaynaktan Ara ve VLM ile Doğrula
                if action_type == "CONCEPT_IMAGE_CARD" and self.enable_web_crawl:
                    candidates = self.crawler.gather_verified_candidates(
                        query_tr=evt.primary_web_query_tr,
                        query_en=evt.secondary_stock_query_en,
                        fallback_en=evt.fallback_minimal_query_en,
                        max_candidates=3,
                    )
                    best_asset = self.verifier.select_best_candidate(
                        candidates=candidates,
                        spoken_context_tr=evt.text_primary,
                        concept_title_tr=evt.text_primary,
                        theme_display_name=theme_profile.display_name,
                    )

                    if best_asset:
                        slot_id, pos_x, pos_y, scale_factor, _ = spatial_solver.solve_placement(
                            evt.start_sec, evt.end_sec, is_image_card=True
                        )
                        styling = best_asset.get("styling", {})
                        dur = round(max(1.5, evt.end_sec - evt.start_sec), 2)
                        chosen_url = str(best_asset["url"])
                        self.crawler.used_links.add(chosen_url)
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
                            "position": ["right" if pos_x >= 50.0 else "left", "top"],
                            "positionX": pos_x,  # 0..100 yüzdelik birim!
                            "positionY": pos_y,  # 0..100 yüzdelik birim!
                            "scale": round(scale_factor * 1.05, 2),
                            "opacity": 96.0,
                            "animation": styling.get("entry_animation", "fade"),
                            "exitAnimation": styling.get("exit_animation", "fade"),
                            "shape": styling.get("mask_shape", "rounded"),
                            "maskShape": styling.get("mask_shape", "rounded"),
                            "borderRadius": styling.get("border_radius_px", 18),
                            "dropShadow": styling.get("drop_shadow", True),
                            "shadowBlur": styling.get("shadow_blur_px", 18),
                            "removeBg": styling.get("remove_bg", False),
                            "anchorSlot": slot_id,
                            "trackId": 2,
                            "track_id": 2,
                        })
                        sfx_cfg = theme_profile.allowed_sfx_map.get("CONCEPT_IMAGE_CARD")
                        if sfx_cfg:
                            generated_sfx.append({
                                "id": f"ad_sfx_{evt.event_id}",
                                "type": sfx_cfg["type"],
                                "timestamp": evt.start_sec,
                                "volume": sfx_cfg["volume"],
                            })
                        continue
                    else:
                        # ZARİF GERİ ÇEKİLME (Graceful Degradation):
                        # VLM >= 75 puanlı görsel bulamadıysa alakasız resim koymak yerine
                        # şık bir Tipografik Anahtar Kavram Kartına (KEY_TERM_CALLOUT) dönüştür!
                        logger.info(
                            f"[LlmDirector] '{evt.text_primary}' için VLM onaylı görsel bulunamadı -> "
                            "KEY_TERM_CALLOUT'a zarifçe dönüştürüldü."
                        )
                        action_type = "KEY_TERM_CALLOUT"
                elif action_type == "CONCEPT_IMAGE_CARD":
                    action_type = "KEY_TERM_CALLOUT"

                # Metin Kartı (CHAPTER_TITLE_CARD, KEY_TERM_CALLOUT, STAT_OR_ARTICLE_CALLOUT)
                slot_id, pos_x, pos_y, scale_factor, _ = spatial_solver.solve_placement(
                    evt.start_sec, evt.end_sec, is_image_card=False
                )
                dur = round(max(1.5, evt.end_sec - evt.start_sec), 2)
                generated_overlays.append({
                    "id": f"ad_txt_{evt.event_id}",
                    "type": "text",
                    "text": evt.text_primary,
                    "content": evt.text_primary,
                    "timestamp": evt.start_sec,
                    "start": evt.start_sec,
                    "end": evt.end_sec,
                    "duration": dur,
                    "position": ["right" if pos_x > 55.0 else ("left" if pos_x < 45.0 else "center"), "top"],
                    "positionX": pos_x,
                    "positionY": pos_y,
                    "fontSize": int(round(theme_profile.title_font_size_1080p * scale_factor)),
                    "font": theme_profile.font_family,
                    "fontFamily": theme_profile.font_family,
                    "color": (
                        theme_profile.secondary_accent_hex
                        if action_type == "STAT_OR_ARTICLE_CALLOUT"
                        else theme_profile.text_color_hex
                    ),
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
                })
                sfx_cfg = theme_profile.allowed_sfx_map.get(action_type)
                if sfx_cfg:
                    generated_sfx.append({
                        "id": f"ad_sfx_{evt.event_id}",
                        "type": sfx_cfg["type"],
                        "timestamp": evt.start_sec,
                        "volume": sfx_cfg["volume"],
                    })

        # Eğer kısa bir videoda (< 3 segment) toplam katman sayısı 3'ün altındaysa ve süre >= 15sn ise
        # orta noktaya bir Vurgu / Özet Kartı ekle ki zaman çizelgesi dengeli dolsun
        if len(generated_overlays) < 3 and video_duration >= 15.0 and segments:
            mid_ts = round(video_duration * 0.45, 2)
            slot_id, pos_x, pos_y, scale_factor, _ = spatial_solver.solve_placement(
                mid_ts, mid_ts + 3.2, is_image_card=False
            )
            generated_overlays.append({
                "id": "ad_txt_mid_summary",
                "type": "text",
                "text": theme_profile.display_name.split("&")[0].strip(),
                "content": theme_profile.display_name.split("&")[0].strip(),
                "timestamp": mid_ts,
                "start": mid_ts,
                "end": round(mid_ts + 3.2, 2),
                "duration": 3.2,
                "position": ["right" if pos_x >= 50.0 else "left", "top"],
                "positionX": pos_x,
                "positionY": pos_y,
                "fontSize": int(round(theme_profile.title_font_size_1080p * scale_factor)),
                "font": theme_profile.font_family,
                "fontFamily": theme_profile.font_family,
                "color": theme_profile.text_color_hex,
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
            })
            generated_sfx.append({
                "id": "ad_sfx_mid_summary",
                "type": "pop",
                "timestamp": mid_ts,
                "volume": 0.18,
            })

        # Eğer tek bölümlü kısa bir videoda hiç geçiş oluşmadıysa ve süre >= 10sn ise 1 adet doğal geçiş ekle
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
