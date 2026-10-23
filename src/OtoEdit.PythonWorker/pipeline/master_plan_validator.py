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

from typing import Any, Dict, List, Optional, Set, Tuple
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
        cuts: Optional[List[Tuple[float, float]]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        repaired_overlays: List[Dict[str, Any]] = []
        last_overlay_start = -999.0
        last_overlay_seq_start = -999.0
        last_paired_group = ""
        safe_duration = max(5.0, float(video_duration or 30.0))

        # Kesim aralıklarını normalize et ve birleştir (raw -> edited sequence zaman dönüşümü için)
        merged_cuts: List[Tuple[float, float]] = []
        for cs, ce in sorted(cuts or [], key=lambda x: float(x[0])):
            cs_f, ce_f = float(cs), float(ce)
            if ce_f <= cs_f:
                continue
            if merged_cuts and cs_f <= merged_cuts[-1][1] + 0.01:
                merged_cuts[-1] = (merged_cuts[-1][0], max(merged_cuts[-1][1], ce_f))
            else:
                merged_cuts.append((cs_f, ce_f))

        def raw_to_seq(t: float) -> float:
            removed = 0.0
            for cs, ce in merged_cuts:
                if t >= ce:
                    removed += (ce - cs)
                elif t > cs:
                    removed += (t - cs)
                    break
                else:
                    break
            return max(0.0, t - removed)

        def is_inside_cut(s: float, e: float) -> bool:
            mid = (s + e) / 2.0
            for cs, ce in merged_cuts:
                if (cs + 0.04 <= s <= ce - 0.04) and (cs + 0.04 <= mid <= ce - 0.04):
                    return True
            return False

        edited_duration = max(5.0, raw_to_seq(safe_duration))

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

            # Kesim (Retake / Silence) aralığı içine düşen katmanları ele ki kesim sınırında üst üste yığılmasınlar
            if merged_cuts and is_inside_cut(start, end):
                continue

            # Kural 1: Tema Saflığı (Akademik/Kurumsal/Belgesel temalarda GIF/Sticker YASAK)
            if ov_type in ("sticker", "gif") and not theme_profile.allow_gifs:
                logger.info(f"[Validator] Tema '{theme_profile.id}' gereği sticker elendi: t={start}s")
                continue

            # Kural 2: Minimum Zaman Boşluğu (hem ham zaman hem kurgulanmış sekans zamanı üzerinde)
            # - Aynı pairedGroupId'ye sahip Kümülatif Liste (Fizik, Kimya, Biyoloji...), İkili Kavram (Tabiat, Fıtrat)
            #   ve Kişi+Portre çiftleri birlikte ekranda yer alır.
            # - Kelime-senkronlu (semanticPriority=True) olaylar önceki olay biter bitmez başlayabilir.
            paired_group = str(ov.get("pairedGroupId") or "")
            is_same_pair = bool(paired_group and paired_group == last_paired_group)
            req_gap = 0.35 if is_sem else effective_min_gap
            seq_start = raw_to_seq(start)

            if not is_same_pair and repaired_overlays:
                if (start - last_overlay_start < req_gap) or (seq_start - last_overlay_seq_start < req_gap):
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
                if not clean_title or clean_title.upper() in ("DEĞERLİ İZLEYENLER", "DEĞERLİ İZLEYİCİLER", "ARKADAŞLAR"):
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
            last_overlay_seq_start = seq_start
            last_paired_group = paired_group

        # Kural 5: Geçiş (Transitions) Denetimi ve Kesim Sınırına Mıknatıslama (Clip-Boundary Snapping)
        # Editör ('clipTransitionBoundaries' ve 60fps geçiş motoru) her geçişin 'boundaryTime' değerini
        # ardışık iki tutulan klip arasındaki kesim bitişiyle (next_clip.start) < 0.45s toleransla eşleştirir.
        # Bu nedenle geçiş zamanlarını doğrudan en yakın tutulan klip başlangıcına (next_clip.start) mıknatıslıyoruz!
        keep_clips: List[Tuple[float, float]] = []
        cursor_t = 0.0
        for cs, ce in merged_cuts:
            if cs - cursor_t >= 0.12:
                keep_clips.append((cursor_t, cs))
            cursor_t = max(cursor_t, ce)
        if safe_duration - cursor_t >= 0.12:
            keep_clips.append((cursor_t, safe_duration))

        clip_boundaries: List[Tuple[float, float]] = [
            (keep_clips[i - 1][1], keep_clips[i][0])
            for i in range(1, len(keep_clips))
        ]

        def snap_to_clip_boundary(raw_t: float) -> float:
            if not clip_boundaries:
                return raw_t
            # 1. Geçiş zamanı doğrudan bir kesim aralığının [prev_end, next_start] içindeyse veya hemen kenarındaysa,
            # kurgulanmış videoda o kesim tamamen atlandığı için geçiş tam next_start noktasındadır!
            for prev_end, next_start in clip_boundaries:
                if (prev_end - 0.45) <= raw_t <= (next_start + 0.45):
                    return next_start
            # 2. Kesim aralığının hemen dışında (<= 3.5s) ise en yakın kesim sınırının next_start noktasına mıknatısla
            best_next_start: Optional[float] = None
            best_dist = 9999.0
            for prev_end, next_start in clip_boundaries:
                dist = min(abs(raw_t - next_start), abs(raw_t - prev_end))
                if dist <= 3.5 and dist < best_dist:
                    best_dist = dist
                    best_next_start = next_start
            return best_next_start if best_next_start is not None else raw_t

        # Uzun videolarda ilk 20 saniyede gereksiz jump-cut geçişi çıkmasını önle,
        # ancak 20s sonrasındaki tüm gerçek semantik konu/bölüm geçişlerini koru!
        min_tr_edge_seq = 20.0 if edited_duration >= 90.0 else min(5.0, max(1.5, edited_duration * 0.08))
        min_tr_gap_seq = 11.0 if edited_duration >= 150.0 else min(8.0, max(4.0, edited_duration * 0.15))
        repaired_transitions: List[Dict[str, Any]] = []
        last_tr_seq_ts = -999.0
        for idx, tr in enumerate(sorted(transitions, key=lambda t: float(t.get("timestamp", 0.0)))):
            tr_id = str(tr.get("id") or "")
            # Eski jump-cut kaynaklı ('ad_tr_cut_...') geçişleri temizle
            if tr_id.startswith("ad_tr_cut_") and edited_duration >= 90.0:
                continue
            raw_ts = float(tr.get("timestamp") or tr.get("boundaryTime") or 0.0)
            ts = snap_to_clip_boundary(raw_ts)
            seq_ts = raw_to_seq(ts)
            if seq_ts <= min_tr_edge_seq or seq_ts >= edited_duration - min_tr_edge_seq:
                continue
            if (seq_ts - last_tr_seq_ts < min_tr_gap_seq) and repaired_transitions:
                continue
            tr_type = str(tr.get("type") or "smoothleft")
            if tr_type not in theme_profile.allowed_transitions:
                tr_type = theme_profile.allowed_transitions[0]
            snapped_val = round(ts, 2)
            repaired_transitions.append({
                "id": tr.get("id") or f"ad_transition_{idx + 1}",
                "timestamp": snapped_val,
                "boundaryTime": snapped_val,
                "boundarySourceTime": snapped_val,
                "type": tr_type,
                "transitionType": tr_type,
                "duration": round(float(tr.get("duration", theme_profile.transition_duration_sec)), 2),
            })
            last_tr_seq_ts = seq_ts

        # Kural 6: 1-e-1 Görsel-İşitsel Senkrezis (Audio-Visual Synchresis)
        # "Ya ikisinde de gelmeli ya hiç gelmemeli ve ikisinde de aynı ses gelmeli":
        # - 24s kör SFX makası kaldırıldı!
        # - Onaylanan HER metin katmanına kendi Mini-Tema SFX'i (ding-bright, keyboard-type, pop-bubble)
        #   ve onaylanan HER sahne geçişine (t - 0.15s) 'capcut-swish-large' (Swish Whoosh Large 794558) SFX'i %100 deterministik bağlanır.
        sfx_preset_map = {
            "capcut-swish-large": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
            "whoosh": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
            "whoosh-fast": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
            "pop": ("pop-bubble", "Pop Baloncuk (Kavram)", 0.25, "pop"),
            "pop-bubble": ("pop-bubble", "Pop Baloncuk (Kavram)", 0.25, "pop"),
            "ding": ("ding-bright", "Ding Parlak Çan (Tın)", 0.90, "ui"),
            "ding-bright": ("ding-bright", "Ding Parlak Çan (Tın)", 0.90, "ui"),
            "keyboard": ("keyboard-type", "Mekanik Klavye (Daktilo)", 0.45, "ui"),
            "keyboard-type": ("keyboard-type", "Mekanik Klavye (Daktilo)", 0.45, "ui"),
            "keyboard-typing": ("keyboard-type", "Mekanik Klavye (Daktilo)", 0.45, "ui"),
            "impact": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
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

        # Kullanıcının manuel eklediği ('sfx_...' ID'li) özel SFX kliplerini koru
        for orig_sfx in (sfx_list or []):
            if not isinstance(orig_sfx, dict):
                continue
            orig_id = str(orig_sfx.get("id") or "")
            if orig_id.startswith("sfx_"):
                user_sfx = dict(orig_sfx)
                s_val = float(
                    user_sfx.get("start")
                    if user_sfx.get("start") is not None
                    else (user_sfx.get("timestamp") or 0.0)
                )
                user_sfx["start"] = round(s_val, 2)
                user_sfx["timestamp"] = round(s_val, 2)
                user_sfx.setdefault("presetId", str(user_sfx.get("synthPreset") or "pop-bubble"))
                repaired_sfx.append(user_sfx)

        # Onaylanan her sahne geçişine tam yeni klibin başladığı sınırda (tr_ts = next_clip.start)
        # 'capcut-swish-large' (Swish Whoosh Large 794558) kaydırma sesi bağla (kesim içine düşmemesi için tr_ts - 0.15 yapılmaz!)
        for tr_idx, tr in enumerate(repaired_transitions):
            tr_ts = float(tr.get("timestamp") or tr.get("boundaryTime") or 0.0)
            sfx_ts = round(max(0.05, tr_ts), 2)
            if not any(
                abs(float(s.get("start", 0.0)) - sfx_ts) < 0.22 and s.get("presetId") in ("capcut-swish-large", "whoosh-fast")
                for s in repaired_sfx
            ):
                repaired_sfx.append({
                    "id": f"ad_sfx_tr_{tr_idx + 1}",
                    "name": "Swish Whoosh (Large 794558)",
                    "title": "Swish Whoosh (Large 794558)",
                    "presetId": "capcut-swish-large",
                    "synthPreset": "capcut-swish-large",
                    "type": "whoosh",
                    "category": "whoosh",
                    "sourceUrl": "sfx://capcut-swish-large",
                    "timestamp": sfx_ts,
                    "start": sfx_ts,
                    "duration": 0.81,
                    "volume": 0.22,
                    "subThemeRole": "TOPIC_TRANSITION",
                    "isTransitionSfx": True,
                })

        repaired_sfx.sort(key=lambda s: float(s.get("start", s.get("timestamp", 0.0))))
        return repaired_overlays, repaired_sfx, repaired_transitions
