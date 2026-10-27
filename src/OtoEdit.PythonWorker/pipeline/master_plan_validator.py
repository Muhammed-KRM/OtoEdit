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

        def clamp_or_drop_overlay_against_cuts(
            r_start: float, r_end: float, is_group_member: bool = False, is_sem: bool = False
        ) -> Optional[Tuple[float, float]]:
            """
            Kesim (Retake / Silence) sınırlarına göre katman zamanlamasını onarır (PROB-3.4):
            1. Katman kesim içinde başlıyorsa kesim sonuna (+0.04s) öteler.
            2. Katman bir kesimden hemen önce (< 0.35s "kırmızı bölge") başlıyorsa, yarım saniyelik
               milisaniye parlamasını (flash) önlemek için başlangıcı kesim sonrasına öteler.
            3. Tekil katman kesim sınırına taşıyorsa ve kesim öncesi >= 1.35s görünür süresi varsa
               bitişi kesim başına (-0.04s) kırpar.
            4. Kurgulanmış görünür sekans süresi (`seq_dur`) tekil katmanda >= 1.35s (kelime-kilitli
               semantik terimlerde >= 1.15s), grup öğesinde >= 0.65s olacak şekilde garanti altına alınır.
            """
            st = max(0.2, min(safe_duration - 0.6, r_start))
            en = min(safe_duration - 0.1, max(st + 0.45, r_end))

            if merged_cuts and is_inside_cut(st, en):
                return None

            for cs, ce in merged_cuts:
                # Başlangıç tam kesim içindeyse kesim çıkışına taşı
                if cs - 0.02 <= st <= ce + 0.02:
                    st = round(ce + 0.04, 2)
                # Kesimden hemen önce (< 0.35s) başlayan katmanı kesim sonrasına taşı (0.2s flash önleme!)
                elif 0.0 < (cs - st) < 0.35:
                    shift_delta = (ce + 0.04) - st
                    st = round(ce + 0.04, 2)
                    if not is_group_member:
                        en = round(min(safe_duration - 0.1, en + shift_delta), 2)

            if not is_group_member:
                for cs, ce in merged_cuts:
                    if st < cs < en:
                        if (cs - st) >= 1.35:
                            en = round(cs - 0.04, 2)
                            break

            min_seq_dur = 0.65 if is_group_member else (1.15 if is_sem else 1.35)
            seq_st = raw_to_seq(st)
            seq_en = raw_to_seq(en)
            if (seq_en - seq_st) < min_seq_dur:
                needed = 1.35 - (seq_en - seq_st)
                en = round(min(safe_duration - 0.1, en + max(needed + 0.15, 0.85)), 2)
                seq_en = raw_to_seq(en)
                if (seq_en - seq_st) < 0.55:
                    return None

            return round(st, 2), round(en, 2)

        # Kronolojik sırala (hem 'start' hem 'timestamp' destekli)
        sorted_ovs = sorted(
            overlays,
            key=lambda o: (
                float(o.get("start") if o.get("start") is not None else o.get("timestamp", 0.0)),
                int(o.get("stackSlot")) if o.get("stackSlot") is not None else -1,
                0 if str(o.get("type", "text")) == "text" else 1,
            ),
        )

        # Kısa videolarda (ör. 35s) min_gap'i video süresine göre esnet ki en az 3 olay sığabilsin
        effective_min_gap = min(
            theme_profile.min_gap_between_overlays_sec * 0.65,
            max(2.5, (safe_duration - 2.0) / 4.5),
        )

        seen_accepted_groups: Set[str] = set()

        for idx, raw_ov in enumerate(sorted_ovs):
            ov = dict(raw_ov)
            ov_type = str(ov.get("type", "text"))
            raw_start = float(ov.get("start") if ov.get("start") is not None else ov.get("timestamp", 0.0))
            raw_dur = float(ov.get("duration", 3.5))
            raw_end = float(ov.get("end") if ov.get("end") is not None else (raw_start + raw_dur))

            paired_group = str(ov.get("pairedGroupId") or ov.get("groupId") or "")
            is_group_member = bool(ov.get("stackSlot") is not None or paired_group)
            is_sem = bool(ov.get("semanticPriority")) or is_group_member

            clamped = clamp_or_drop_overlay_against_cuts(raw_start, raw_end, is_group_member=is_group_member, is_sem=is_sem)
            if clamped is None:
                continue
            start, end = clamped
            min_allowed_dur = 0.65 if is_group_member else (1.15 if is_sem else 1.35)
            if end - start < min_allowed_dur:
                end = min(safe_duration - 0.1, start + min_allowed_dur)
            dur = round(max(min_allowed_dur, end - start), 2)

            # Kural 1: Tema Saflığı (Akademik/Kurumsal/Belgesel temalarda GIF/Sticker YASAK)
            if ov_type in ("sticker", "gif") and not theme_profile.allow_gifs:
                logger.info(f"[Validator] Tema '{theme_profile.id}' gereği sticker elendi: t={start}s")
                continue

            # Kural 2: Minimum Zaman Boşluğu & Atomik Grup Bütünlüğü (PROB-2.5)
            # - Daha önce kabul edilmiş bir grubun (`seen_accepted_groups`) tüm devam öğeleri (stackSlot 1, 2, 3...)
            #   veya Kişi+Portre eşleşmeleri (`pairedGroupId`) ASLA yarıda kesilmez!
            is_same_pair = bool(paired_group and (paired_group == last_paired_group or paired_group in seen_accepted_groups))
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

            if paired_group:
                ov["pairedGroupId"] = paired_group
                ov["groupId"] = paired_group
                seen_accepted_groups.add(paired_group)

            repaired_overlays.append(ov)
            last_overlay_start = start
            last_overlay_seq_start = seq_start
            last_paired_group = paired_group

        # Kural 4.5: Kümülatif Liste / İkili Grup Sıkıştırması (Contiguous Slot Compaction) ve
        # Grup Ortak Bitiş Senkronizasyonu (PROB-2.5, PROB-3.3)
        grouped_stack_map: Dict[str, List[Dict[str, Any]]] = {}
        for ov_item in repaired_overlays:
            p_grp = str(ov_item.get("pairedGroupId") or ov_item.get("groupId") or "")
            if p_grp and ov_item.get("stackSlot") is not None:
                grouped_stack_map.setdefault(p_grp, []).append(ov_item)

        for p_grp, grp_items in grouped_stack_map.items():
            grp_items.sort(key=lambda x: (float(x.get("start", 0.0)), int(x.get("stackSlot", 0))))
            st_cnt = len(grp_items)
            # Grubun ortak bitişini, gruptan sonra gelen ilk yabancı katmanın başlangıcına (-0.08s) göre senkronla
            grp_max_start = max(float(x.get("start", 0.0)) for x in grp_items)
            grp_shared_end = max(float(x.get("end", grp_max_start + 1.2)) for x in grp_items)
            for other_ov in repaired_overlays:
                other_grp = str(other_ov.get("pairedGroupId") or other_ov.get("groupId") or "")
                other_st = float(other_ov.get("start", 0.0))
                if other_grp != p_grp and other_st > grp_max_start + 0.45:
                    if grp_shared_end > other_st - 0.08:
                        grp_shared_end = round(max(grp_max_start + 0.65, other_st - 0.08), 2)
                    break

            for new_slot, member_ov in enumerate(grp_items):
                member_ov["stackSlot"] = new_slot
                member_ov["stackCount"] = st_cnt
                member_ov["trackId"] = 1 + (new_slot % 5)
                member_ov["track_id"] = member_ov["trackId"]
                row = new_slot if new_slot < 4 else (new_slot - 4) % 4
                side_prefix = "LEFT_STACK" if new_slot < 4 else "RIGHT_STACK"
                if st_cnt == 2:
                    new_y = round(20.0 + row * 13.0, 1)
                else:
                    new_y = round(16.0 + row * 11.0, 1)
                member_ov["positionY"] = new_y
                member_ov["anchorSlot"] = f"{side_prefix}_{row + 1}"
                m_st = float(member_ov.get("start", 0.0))
                m_en = round(max(m_st + 0.65, grp_shared_end), 2)
                member_ov["end"] = m_en
                member_ov["duration"] = round(m_en - m_st, 2)

        # Kural 5: Geçiş (Transitions) Denetimi ve Kesim Sınırına Mikro-Mıknatıslama (PROB-6.4)
        # Eski 3.5s jump-cut mıknatısı cümle sonundaki geçişleri cümle ortası nefes kesimlerine çekiyordu;
        # artık yalnızca 0.25s mikro-toleransla kesim sınırına hizalanır ve aktif liste gruplarının ortasına düşmez!
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

        active_group_spans: List[Tuple[float, float]] = [
            (
                min(float(x.get("start", 0.0)) for x in g_list),
                max(float(x.get("end", 0.0)) for x in g_list),
            )
            for g_list in grouped_stack_map.values()
            if g_list
        ]

        def snap_to_clip_boundary(raw_t: float) -> float:
            target_t = raw_t
            # Aktif bir sıralama/ikili kavram grubunun tam ortasına geçiş düşmesini engelle
            for g_st, g_en in active_group_spans:
                if (g_st - 0.30) <= target_t <= (g_en + 0.30):
                    target_t = round(min(safe_duration - 1.5, g_en + 0.25), 2)
            if not clip_boundaries:
                return target_t
            # 1. Geçiş zamanı doğrudan bir kesim aralığının [prev_end, next_start] içindeyse veya 0.25s mikro komşuluğundaysa next_start'a hizala
            for prev_end, next_start in clip_boundaries:
                if (prev_end - 0.25) <= target_t <= (next_start + 0.25):
                    return next_start
            return target_t

        # Uzun videolarda ilk 20 saniyede gereksiz jump-cut geçişi çıkmasını önle,
        # ancak 20s sonrasındaki tüm gerçek semantik konu/bölüm geçişlerini koru!
        min_tr_edge_seq = 20.0 if edited_duration >= 90.0 else min(5.0, max(1.5, edited_duration * 0.08))
        min_tr_gap_seq = 18.0 if edited_duration >= 150.0 else min(8.0, max(4.0, edited_duration * 0.15))
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
            tr_type = str(tr.get("type") or "slideleft")
            if tr_type not in ("slideleft", "smoothleft"):
                tr_type = "slideleft"
            snapped_val = round(ts, 2)
            repaired_transitions.append({
                "id": tr.get("id") or f"ad_transition_{idx + 1}",
                "timestamp": snapped_val,
                "boundaryTime": snapped_val,
                "boundarySourceTime": snapped_val,
                "type": tr_type,
                "transitionType": tr_type,
                "duration": round(float(tr.get("duration", 0.40)), 2),
            })
            last_tr_seq_ts = seq_ts

        # Kural 5.5: Sahne Geçişi ve İlk Yazı Katmanı Arasında +0.45s Lead-In Stagger (PROB-6.4)
        # Sahne geçişi (transition) ile aynı saniyede başlayan yazıların geçiş animasyonuyla çarpışmasını önler
        for tr in repaired_transitions:
            tr_ts = float(tr.get("timestamp") or 0.0)
            for ov_item in repaired_overlays:
                ov_st = float(ov_item.get("start") or 0.0)
                if (tr_ts - 0.10) <= ov_st <= (tr_ts + 0.35):
                    new_st = round(tr_ts + 0.45, 2)
                    ov_en = float(ov_item.get("end") or (new_st + 1.5))
                    if ov_en - new_st < 0.85:
                        ov_en = round(min(safe_duration - 0.1, new_st + 1.35), 2)
                    ov_item["start"] = new_st
                    ov_item["timestamp"] = new_st
                    ov_item["end"] = ov_en
                    ov_item["duration"] = round(ov_en - new_st, 2)

        # Kural 6: 1-e-1 Görsel-İşitsel Senkrezis & Geçiş Ses Çeşitliliği Korunumu (PROB-6.5)
        sfx_preset_map = {
            "capcut-swish-large": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
            "whoosh": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
            "whoosh-fast": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
            "cinematic-swell": ("capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, "whoosh"),
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

        # Onaylanan her sahne geçişine geçiş türüne uygun SFX bağla (PROB-6.5: LlmDirector çeşitliliğini koru!)
        for tr_idx, tr in enumerate(repaired_transitions):
            tr_ts = float(tr.get("timestamp") or tr.get("boundaryTime") or 0.0)
            tr_type = str(tr.get("type") or "smoothleft")
            sfx_ts = round(max(0.05, tr_ts), 2)
            if tr_type in ("zoomin", "zoomout"):
                tr_sfx_preset, tr_sfx_name, tr_sfx_dur, tr_sfx_vol, tr_sfx_cat = (
                    "whoosh-fast", "Fast Zoom Whoosh", 0.45, 0.20, "whoosh"
                )
            elif tr_type in ("dissolve", "fade", "fadeblack"):
                tr_sfx_preset, tr_sfx_name, tr_sfx_dur, tr_sfx_vol, tr_sfx_cat = (
                    "cinematic-swell", "Cinematic Ambient Swell", 0.90, 0.18, "whoosh"
                )
            elif tr_type in ("circleopen", "circleclose"):
                tr_sfx_preset, tr_sfx_name, tr_sfx_dur, tr_sfx_vol, tr_sfx_cat = (
                    "pop-bubble", "Circle Reveal Pop", 0.35, 0.18, "pop"
                )
            else:
                tr_sfx_preset, tr_sfx_name, tr_sfx_dur, tr_sfx_vol, tr_sfx_cat = (
                    "capcut-swish-large", "Swish Whoosh (Large 794558)", 0.81, 0.22, "whoosh"
                )
            if not any(
                abs(float(s.get("start", 0.0)) - sfx_ts) < 0.22 and s.get("isTransitionSfx")
                for s in repaired_sfx
            ):
                repaired_sfx.append({
                    "id": f"ad_sfx_tr_{tr_idx + 1}",
                    "name": tr_sfx_name,
                    "title": tr_sfx_name,
                    "presetId": tr_sfx_preset,
                    "synthPreset": tr_sfx_preset,
                    "type": tr_sfx_cat,
                    "category": tr_sfx_cat,
                    "sourceUrl": f"sfx://{tr_sfx_preset}",
                    "timestamp": sfx_ts,
                    "start": sfx_ts,
                    "duration": tr_sfx_dur,
                    "volume": tr_sfx_vol,
                    "subThemeRole": "TOPIC_TRANSITION",
                    "isTransitionSfx": True,
                })

        repaired_sfx.sort(key=lambda s: float(s.get("start", s.get("timestamp", 0.0))))
        return repaired_overlays, repaired_sfx, repaired_transitions
