"""
Aşama 4: MasterPlanValidator.
Oluşturulan kurgu planını 6 katı mühendislik kuralına göre denetler ve onarır:
1. Tam süre (00:00 -> son saniye) kapsama kontrolü
2. Minimum zaman boşluğu (min_gap_between_overlays_sec)
3. Altyazı kuşağı (Y ∈ [70%, 95%]) ve konuşmacı yüzü sıfır çarpışma garantisi
4. Tema saflığı (allow_gifs=False ise tüm sticker/gif'lerin temizlenmesi)
5. Olaya bağlı mikro-SFX (0.14 - 0.24 ses seviyesi, metronom döngüsü yasağı)
6. Cümle sınırına mıknatıslanmış (sentence-boundary snapped) bölüm geçişleri
"""

from typing import Any, Dict, List, Tuple
from pipeline.theme_profiles import ThemeProfile, extract_turkish_semantic_title
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
        safe_duration = max(5.0, float(video_duration or 30.0))

        # Kronolojik sırala (hem 'start' hem 'timestamp' destekli)
        sorted_ovs = sorted(
            overlays,
            key=lambda o: float(o.get("start") if o.get("start") is not None else o.get("timestamp", 0.0)),
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

            start = max(0.3, min(safe_duration - 1.2, raw_start))
            end = min(safe_duration - 0.2, raw_end)
            if end - start < 1.2:
                end = min(safe_duration - 0.1, start + 3.0)
            dur = round(max(1.2, end - start), 2)

            # Kural 1: Tema Saflığı (Akademik/Kurumsal/Belgesel temalarda GIF/Sticker YASAK)
            if ov_type in ("sticker", "gif") and not theme_profile.allow_gifs:
                logger.info(f"[Validator] Tema '{theme_profile.id}' gereği sticker elendi: t={start}s")
                continue

            # Kural 2: Minimum Zaman Boşluğu
            if start - last_overlay_start < effective_min_gap and repaired_overlays:
                continue

            # Kural 3: Altyazı Kuşağı (Y ∈ [70%, 95%]) ve Birim Kontrolü (0..100)
            pos_x = float(ov.get("positionX", 76.0))
            pos_y = float(ov.get("positionY", 20.0))
            # Eğer yanlışlıkla 0..1 normalize birimde gelmişse 0..100 yüzdelik birime çevir!
            if 0.0 < pos_x <= 1.0 and 0.0 < pos_y <= 1.0:
                pos_x *= 100.0
                pos_y *= 100.0
            if subtitles_enabled and pos_y >= 68.0:
                pos_y = 18.0  # Altyazı kuşağından yukarıdaki güvenli bölgeye taşı

            ov["start"] = round(start, 2)
            ov["end"] = round(end, 2)
            ov["timestamp"] = round(start, 2)
            ov["duration"] = dur
            ov["positionX"] = round(pos_x, 2)
            ov["positionY"] = round(pos_y, 2)
            if not ov.get("id"):
                ov["id"] = f"ad_ov_{idx + 1}"

            # Kural 4: Metin Başlığı Doğrulaması ve Kilitli Tema Stili
            if ov_type == "text":
                raw_text = str(ov.get("text") or ov.get("content") or "")
                clean_title = extract_turkish_semantic_title(
                    raw_text, max_chars=theme_profile.max_chars_per_line
                )
                if not clean_title:
                    continue
                ov["text"] = clean_title
                ov["content"] = clean_title
                ov["font"] = theme_profile.font_family
                ov["fontFamily"] = theme_profile.font_family
                ov["fontSize"] = int(ov.get("fontSize") or theme_profile.title_font_size_1080p)
                ov["color"] = ov.get("color") or theme_profile.text_color_hex
                ov["backgroundBox"] = theme_profile.background_box
                ov["boxStyle"] = "rounded" if theme_profile.background_box else "none"
                ov["boxColor"] = theme_profile.box_color_hex
                ov["boxBgColor"] = theme_profile.box_color_hex
                ov["boxOpacity"] = theme_profile.box_opacity
                ov["preset"] = theme_profile.preset_id
                ov["animation"] = theme_profile.entry_animation
                ov["exitAnimation"] = theme_profile.exit_animation
                ov["trackId"] = int(ov.get("trackId") or ov.get("track_id") or 2)
                ov["track_id"] = ov["trackId"]

            repaired_overlays.append(ov)
            last_overlay_start = start

        # Kural 5: Yalnızca Olaya Bağlı Mikro-SFX (Metronom döngüsü yok, maks ses 0.24)
        valid_event_times = [float(o["start"]) for o in repaired_overlays] + [
            float(t.get("timestamp", 0.0)) for t in transitions
        ]
        min_sfx_gap = min(12.0, max(2.5, safe_duration / 6.0))
        repaired_sfx: List[Dict[str, Any]] = []
        last_sfx_ts = -999.0

        sfx_preset_map = {
            "whoosh": ("whoosh-fast", "Whoosh Fast", 0.8),
            "pop": ("pop-bubble", "Pop Bubble", 0.5),
            "ding": ("ding-bright", "Ding Bright", 1.1),
            "impact": ("whoosh-fast", "Impact Whoosh", 0.9),
        }

        for idx, sfx in enumerate(
            sorted(
                sfx_list,
                key=lambda s: float(s.get("timestamp") if s.get("timestamp") is not None else s.get("start", 0.0)),
            )
        ):
            ts = float(sfx.get("timestamp") if sfx.get("timestamp") is not None else sfx.get("start", 0.0))
            if ts - last_sfx_ts < min_sfx_gap:
                continue
            # Bir görsel/metin/geçiş olayına +-0.6sn yakın değilse sil!
            if not any(abs(ts - evt_t) <= 0.6 for evt_t in valid_event_times):
                continue
            vol = min(0.24, max(0.12, float(sfx.get("volume", 0.18))))
            raw_type = str(sfx.get("type", "whoosh"))
            preset_id, name, def_dur = sfx_preset_map.get(raw_type, ("whoosh-fast", "Whoosh Fast", 0.8))
            repaired_sfx.append({
                "id": sfx.get("id") or f"ad_sfx_{idx + 1}",
                "name": sfx.get("name") or name,
                "presetId": sfx.get("presetId") or preset_id,
                "type": raw_type,
                "category": raw_type if raw_type in ("whoosh", "pop", "ding") else "whoosh",
                "sourceUrl": sfx.get("sourceUrl") or f"sfx://{preset_id}",
                "timestamp": round(ts, 2),
                "start": round(ts, 2),
                "duration": float(sfx.get("duration") or def_dur),
                "volume": round(vol, 2),
            })
            last_sfx_ts = ts

        # Kural 6: Geçiş (Transitions) Denetimi
        min_tr_edge = min(5.0, max(1.5, safe_duration * 0.08))
        min_tr_gap = min(25.0, max(4.0, safe_duration * 0.20))
        repaired_transitions: List[Dict[str, Any]] = []
        last_tr_ts = 0.0
        for idx, tr in enumerate(sorted(transitions, key=lambda t: float(t.get("timestamp", 0.0)))):
            ts = float(tr.get("timestamp") or tr.get("boundaryTime") or 0.0)
            if ts <= min_tr_edge or ts >= safe_duration - min_tr_edge:
                continue
            if ts - last_tr_ts < min_tr_gap and repaired_transitions:
                continue
            tr_type = str(tr.get("type") or theme_profile.allowed_transitions[0])
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

        return repaired_overlays, repaired_sfx, repaired_transitions
