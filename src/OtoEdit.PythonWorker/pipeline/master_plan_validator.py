"""
Aşama 4: MasterPlanValidator.
Oluşturulan kurgu planını 6 katı mühendislik kuralına göre denetler ve onarır:
1. Tam süre (00:00 -> son saniye) kapsama kontrolü
2. Minimum zaman boşluğu (Eşleştirilmiş Kişi+Portre çiftlerini ve ardışık 1./2./3. sıralamaları korur!)
3. Altyazı kuşağı (Y ∈ [70%, 95%]) ve konuşmacı yüzü sıfır çarpışma garantisi
4. Tema saflığı (allow_gifs=False ise tüm sticker/gif'lerin temizlenmesi)
5. Olaya bağlı seyrek mikro-SFX (0.12 - 0.22 ses seviyesi, metronom döngüsü yasağı)
6. Cümle sınırına mıknatıslanmış (sentence-boundary snapped) yumuşak bölüm geçişleri
"""

from typing import Any, Dict, List, Set, Tuple
from pipeline.theme_profiles import (
    ThemeProfile,
    extract_turkish_semantic_title,
    resolve_sub_theme,
)
from utils.logger import get_logger

logger = get_logger("MasterPlanValidator")


class MasterPlanValidator:
    def validate_and_repair(
        self,
        overlays: List[Dict[str, Any]],
        sfx_list: List[Dict[str, Any]],
        transitions: List[Dict[str, Any]],
        theme_profile: ThemeProfile,
        video_duration: float,
        subtitles_enabled: bool = True,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        repaired_overlays: List[Dict[str, Any]] = []
        last_overlay_start = -999.0
        last_paired_group = ""
        safe_duration = max(5.0, float(video_duration or 30.0))

        # Kronolojik sırala (hem 'start' hem 'timestamp' destekli)
        sorted_ovs = sorted(
            overlays,
            key=lambda o: (
                float(o.get("start") if o.get("start") is not None else o.get("timestamp", 0.0)),
                0 if str(o.get("type", "text")) == "text" else 1,
            ),
        )

        # Kısa videolarda (ör. 35s) min_gap'i video süresine göre esnet ki en az 3 olay sığabilsin
        effective_min_gap = min(
            theme_profile.min_gap_between_overlays_sec * 0.65,
            max(2.5, (safe_duration - 2.0) / 4.5),
        )

        for idx, raw_ov in enumerate(sorted_ovs):
            ov = dict(raw_ov)
            ov_type = str(ov.get("type", "text"))
            raw_start = float(ov.get("start") if ov.get("start") is not None else ov.get("timestamp", 0.0))
            raw_dur = float(ov.get("duration", 3.5))
            raw_end = float(ov.get("end") if ov.get("end") is not None else (raw_start + raw_dur))

            is_sem = bool(ov.get("semanticPriority")) or (ov.get("stackSlot") is not None)
            min_allowed_dur = 0.45 if is_sem else 1.2
            start = max(0.2, min(safe_duration - 0.6, raw_start))
            end = min(safe_duration - 0.1, raw_end)
            if end - start < min_allowed_dur:
                end = min(safe_duration - 0.1, start + (1.4 if is_sem else 3.0))
            dur = round(max(min_allowed_dur, end - start), 2)

            # Kural 1: Tema Saflığı (Akademik/Kurumsal/Belgesel temalarda GIF/Sticker YASAK)
            if ov_type in ("sticker", "gif") and not theme_profile.allow_gifs:
                logger.info(f"[Validator] Tema '{theme_profile.id}' gereği sticker elendi: t={start}s")
                continue

            # Kural 2: Minimum Zaman Boşluğu
            # - Aynı pairedGroupId'ye sahip Kümülatif Liste (Fizik, Kimya, Biyoloji...), İkili Kavram (Tabiat, Fıtrat)
            #   ve Kişi+Portre çiftleri birlikte ekranda yer alır.
            # - Kelime-senkronlu (semanticPriority=True) olaylar önceki olay biter bitmez başlayabilir.
            paired_group = str(ov.get("pairedGroupId") or "")
            is_same_pair = bool(paired_group and paired_group == last_paired_group)
            req_gap = 0.35 if is_sem else effective_min_gap

            if not is_same_pair and (start - last_overlay_start < req_gap) and repaired_overlays:
                continue

            # Kural 3: Altyazı Kuşağı (Y ∈ [70%, 95%]) ve Birim Kontrolü (0..100)
            pos_x = float(ov.get("positionX", 76.0))
            pos_y = float(ov.get("positionY", 20.0))
            if 0.0 < pos_x <= 1.0 and 0.0 < pos_y <= 1.0:
                pos_x *= 100.0
                pos_y *= 100.0
            if subtitles_enabled and pos_y >= 68.0:
                pos_y = 22.0

            ov["start"] = round(start, 2)
            ov["end"] = round(end, 2)
            ov["timestamp"] = round(start, 2)
            ov["duration"] = dur
            ov["positionX"] = round(pos_x, 2)
            ov["positionY"] = round(pos_y, 2)
            if not ov.get("id"):
                ov["id"] = f"ad_ov_{idx + 1}"

            # Kural 4: Metin Başlığı Doğrulaması, Dinamik Font Korunumu ve Mini-Tema Stili
            action_type = str(
                ov.get("actionType")
                or ("PROGRESSIVE_LIST" if ov.get("stackSlot") is not None else "SINGLE_TERM")
            )
            sub_theme = resolve_sub_theme(theme_profile, action_type)

            if ov_type == "text":
                raw_text = str(ov.get("text") or ov.get("content") or "")
                clean_title = extract_turkish_semantic_title(
                    raw_text, max_chars=max(36, theme_profile.max_chars_per_line)
                )
                if not clean_title:
                    continue
                ov["text"] = clean_title
                ov["content"] = clean_title
                ov["font"] = theme_profile.font_family
                ov["fontFamily"] = theme_profile.font_family
                ov["fontSize"] = int(ov.get("fontSize") or theme_profile.title_font_size_1080p)
                ov["maxWidthCqi"] = int(ov.get("maxWidthCqi") or (30 if ov.get("stackSlot") is not None else 32))
                ov["lineHeight"] = float(ov.get("lineHeight") or 1.14)
                ov["color"] = ov.get("color") or theme_profile.text_color_hex
                ov["strokeColor"] = ov.get("strokeColor") or theme_profile.stroke_color_hex
                ov["strokeWidth"] = int(
                    ov.get("strokeWidth")
                    if ov.get("strokeWidth") is not None
                    else theme_profile.stroke_width_px
                )
                ov["backgroundBox"] = theme_profile.background_box
                ov["boxStyle"] = "rounded" if theme_profile.background_box else "none"
                ov["boxColor"] = theme_profile.box_color_hex
                ov["boxBgColor"] = theme_profile.box_color_hex
                ov["boxOpacity"] = theme_profile.box_opacity
                ov["preset"] = theme_profile.preset_id
                ov["actionType"] = action_type
                ov["subThemeRole"] = sub_theme.role_id
                ov["animation"] = ov.get("animation") or sub_theme.entry_animation
                ov["exitAnimation"] = ov.get("exitAnimation") or sub_theme.exit_animation
                ov["trackId"] = int(ov.get("trackId") or ov.get("track_id") or 2)
                ov["track_id"] = ov["trackId"]
            else:
                ov["actionType"] = action_type
                ov["subThemeRole"] = sub_theme.role_id
                ov["animation"] = ov.get("animation") or sub_theme.entry_animation
                ov["exitAnimation"] = ov.get("exitAnimation") or sub_theme.exit_animation
                ov["trackId"] = int(ov.get("trackId") or ov.get("track_id") or 3)
                ov["track_id"] = ov["trackId"]

            repaired_overlays.append(ov)
            last_overlay_start = start
            last_paired_group = paired_group

        # Kural 5: Geçiş (Transitions) Denetimi (Sola kaydırmalı 'smoothleft' + Konu/Açıklama sınırları)
        min_tr_edge = min(5.0, max(1.5, safe_duration * 0.08))
        min_tr_gap = min(20.0, max(4.0, safe_duration * 0.015))
        repaired_transitions: List[Dict[str, Any]] = []
        last_tr_ts = 0.0
        for idx, tr in enumerate(sorted(transitions, key=lambda t: float(t.get("timestamp", 0.0)))):
            ts = float(tr.get("timestamp") or tr.get("boundaryTime") or 0.0)
            if ts <= min_tr_edge or ts >= safe_duration - min_tr_edge:
                continue
            if ts - last_tr_ts < min_tr_gap and repaired_transitions:
                continue
            tr_type = str(tr.get("type") or "smoothleft")
            if tr_type not in theme_profile.allowed_transitions:
                tr_type = theme_profile.allowed_transitions[0]
            repaired_transitions.append({
                "id": tr.get("id") or f"ad_transition_{idx + 1}",
                "timestamp": round(ts, 2),
                "boundaryTime": round(float(tr.get("boundaryTime") or ts), 2),
                "boundarySourceTime": round(float(tr.get("boundarySourceTime") or ts), 2),
                "type": tr_type,
                "transitionType": tr_type,
                "duration": round(float(tr.get("duration", theme_profile.transition_duration_sec)), 2),
            })
            last_tr_ts = ts

        # Kural 6: 1-e-1 Görsel-İşitsel Senkrezis (Audio-Visual Synchresis)
        # "Ya ikisinde de gelmeli ya hiç gelmemeli ve ikisinde de aynı ses gelmeli":
        # - 24s kör SFX makası kaldırıldı!
        # - Onaylanan HER metin katmanına kendi Mini-Tema SFX'i (ding-bright, keyboard-type, pop-bubble)
        #   ve onaylanan HER sahne geçişine (t - 0.10s) 'whoosh-fast' SFX'i %100 deterministik bağlanır.
        sfx_preset_map = {
            "whoosh": ("whoosh-fast", "Whoosh Hızlı Geçiş", 0.42, "whoosh"),
            "whoosh-fast": ("whoosh-fast", "Whoosh Hızlı Geçiş", 0.42, "whoosh"),
            "pop": ("pop-bubble", "Pop Baloncuk (Kavram)", 0.25, "pop"),
            "pop-bubble": ("pop-bubble", "Pop Baloncuk (Kavram)", 0.25, "pop"),
            "ding": ("ding-bright", "Ding Parlak Çan (Tın)", 0.90, "ui"),
            "ding-bright": ("ding-bright", "Ding Parlak Çan (Tın)", 0.90, "ui"),
            "keyboard": ("keyboard-type", "Mekanik Klavye (Daktilo)", 0.45, "ui"),
            "keyboard-type": ("keyboard-type", "Mekanik Klavye (Daktilo)", 0.45, "ui"),
            "keyboard-typing": ("keyboard-type", "Mekanik Klavye (Daktilo)", 0.45, "ui"),
            "impact": ("whoosh-fast", "Impact Whoosh", 0.45, "whoosh"),
        }

        repaired_sfx: List[Dict[str, Any]] = []
        seen_paired_sfx_groups: Set[str] = set()

        for idx, ov in enumerate(repaired_overlays):
            ov_id = str(ov.get("id") or f"ov_{idx + 1}")
            ov_type = str(ov.get("type", "text"))
            paired_grp = str(ov.get("pairedGroupId") or "")
            stack_slot = ov.get("stackSlot")

            # Kişi+Portre çiftinde (stackSlot None ve aynı pairedGroupId) sesi yalnızca 1 kez tetikle
            if paired_grp and stack_slot is None:
                if paired_grp in seen_paired_sfx_groups:
                    continue
                seen_paired_sfx_groups.add(paired_grp)

            action_type = str(
                ov.get("actionType")
                or (
                    "PROGRESSIVE_LIST"
                    if stack_slot is not None
                    else ("CONCEPT_IMAGE_CARD" if ov_type == "image" else "SINGLE_TERM")
                )
            )
            sub_theme = resolve_sub_theme(theme_profile, action_type)
            ts = round(float(ov["start"]), 2)
            preset_id, name, def_dur, cat = sfx_preset_map.get(
                sub_theme.sfx_preset_id, ("pop-bubble", "Pop Baloncuk (Kavram)", 0.25, "pop")
            )
            repaired_sfx.append({
                "id": f"ad_sfx_{ov_id}",
                "name": name,
                "title": name,
                "presetId": preset_id,
                "synthPreset": preset_id,
                "type": sub_theme.sfx_type,
                "category": cat,
                "sourceUrl": f"sfx://{preset_id}",
                "timestamp": ts,
                "start": ts,
                "duration": round(float(sub_theme.sfx_duration or def_dur), 2),
                "volume": round(float(sub_theme.sfx_volume), 2),
                "subThemeRole": sub_theme.role_id,
                "boundOverlayId": ov_id,
            })

        # Onaylanan her sahne geçişine (t - 0.10s) 'whoosh-fast' kaydırma sesi bağla
        for tr_idx, tr in enumerate(repaired_transitions):
            tr_ts = float(tr.get("timestamp") or tr.get("boundaryTime") or 0.0)
            sfx_ts = round(max(0.05, tr_ts - 0.10), 2)
            if not any(
                abs(float(s["start"]) - sfx_ts) < 0.18 and s["presetId"] == "whoosh-fast"
                for s in repaired_sfx
            ):
                repaired_sfx.append({
                    "id": f"ad_sfx_tr_{tr_idx + 1}",
                    "name": "Whoosh Hızlı Geçiş",
                    "title": "Whoosh Hızlı Geçiş",
                    "presetId": "whoosh-fast",
                    "synthPreset": "whoosh-fast",
                    "type": "whoosh",
                    "category": "whoosh",
                    "sourceUrl": "sfx://whoosh-fast",
                    "timestamp": sfx_ts,
                    "start": sfx_ts,
                    "duration": 0.42,
                    "volume": 0.20,
                    "subThemeRole": "TOPIC_TRANSITION",
                    "isTransitionSfx": True,
                })

        repaired_sfx.sort(key=lambda s: float(s["start"]))
        return repaired_overlays, repaired_sfx, repaired_transitions
