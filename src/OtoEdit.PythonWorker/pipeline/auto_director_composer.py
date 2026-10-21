"""
auto_director_composer.py — Otonom Yönetmen Kurgu Kompozitörü (AutoDirectorComposer).
Özellikle kullanıcının önceden kestiği veya doğrudan yüklediği videoları
otomatik olarak:
1. Açılış Hook Başlığı (0.3s - 3.5s, trackId=2, Montserrat 58pt, #FACC15)
2. 20-30s aralıklı Anahtar Kelime Vurgu Başlıkları (trackId=2, #22D3EE / #4ADE80 / #FACC15)
3. Google Noto Animasyonlu Emoji / Sticker Katmanları (trackId=3, 512.gif)
4. Sahne Geçişleri (fade, smoothleft, zoomin) ve Senkronize SFX Klipleri (whoosh-fast, pop-bubble, ding-bright)
ile zenginleştirir.
"""
import re
from typing import Any, Dict, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

NOTO_ANIMATED_EMOJIS: List[Dict[str, str]] = [
    {"codepoint": "1f525", "emoji": "🔥", "label": "Fire"},
    {"codepoint": "1f4a1", "emoji": "💡", "label": "Idea"},
    {"codepoint": "1f680", "emoji": "🚀", "label": "Rocket"},
    {"codepoint": "26a1", "emoji": "⚡", "label": "Zap"},
    {"codepoint": "1f3af", "emoji": "🎯", "label": "Target"},
    {"codepoint": "1f4af", "emoji": "💯", "label": "100"},
]

HIGHLIGHT_COLORS: List[str] = ["#22D3EE", "#4ADE80", "#FACC15"]
HIGHLIGHT_ANIMATIONS: List[str] = ["bounce", "slide-up"]
TRANSITION_CYCLE: List[str] = ["fade", "smoothleft", "zoomin"]
SFX_PRESETS: List[Dict[str, Any]] = [
    {"presetId": "whoosh-fast", "name": "Whoosh Fast", "category": "whoosh", "duration": 0.8, "volume": 0.75},
    {"presetId": "pop-bubble", "name": "Pop Bubble", "category": "pop", "duration": 0.5, "volume": 0.80},
    {"presetId": "ding-bright", "name": "Ding Bright", "category": "ding", "duration": 1.1, "volume": 0.70},
]


class _ComposerDict(dict):
    """Hem sözlük (d['k']) hem nesne (d.k) erişimini destekleyen sözlük."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'dict' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class AutoDirectorComposer:
    """Videoyu otomatik katmanlar, sticker'lar, geçişler ve ses efektleriyle zenginleştiren motor."""

    @staticmethod
    def _extract_segments(transcript: Any) -> List[Dict[str, Any]]:
        """TranscriptResult veya dict içerisinden segment listesini normalize eder."""
        if not transcript:
            return []
        raw_segs = (
            transcript.get("segments", [])
            if isinstance(transcript, dict)
            else getattr(transcript, "segments", [])
        ) or []
        normalized: List[Dict[str, Any]] = []
        for s in raw_segs:
            if isinstance(s, dict):
                start = float(s.get("start", 0.0))
                end = float(s.get("end", start + 3.0))
                text = str(s.get("text", "")).strip()
            else:
                start = float(getattr(s, "start", 0.0))
                end = float(getattr(s, "end", start + 3.0))
                text = str(getattr(s, "text", "")).strip()
            if text:
                normalized.append({"start": start, "end": end, "text": text})
        return normalized

    @staticmethod
    def _extract_impact_phrase(text: str, min_words: int = 2, max_words: int = 4) -> str:
        """Metin segmentinden kelime/tamlama ortasından kesilmeyen anlamlı bir Türkçe başlık çıkarır."""
        if not text:
            return "ÖNEMLİ DETAY"
        from pipeline.theme_profiles import extract_turkish_semantic_title
        semantic = extract_turkish_semantic_title(text, max_chars=32)
        if semantic:
            return semantic
        cleaned = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ!?]", "", text).strip()
        words = [w for w in cleaned.split() if len(w) > 1]
        if not words:
            return "ÖNEMLİ DETAY"
        selected = words[:max(min_words, min(len(words), max_words))]
        return " ".join(selected).upper()

    @classmethod
    def compose(
        cls,
        transcript: Any,
        cuts: Optional[List[Any]] = None,
        existing_overlays: Optional[List[Any]] = None,
        video_duration: float = 0.0,
        target_format: str = "16:9",
        enable_text_hooks: bool = True,
        enable_stickers: bool = True,
        enable_transitions: bool = True,
        enable_sfx: bool = True,
    ) -> Dict[str, List[Any]]:
        """
        Transkript ve kesim noktalarını analiz ederek otomatik yönetmen katmanları üretir.
        Dönüş: {"overlays": [...], "transitions": [...], "sfxClips": [...]}
        """
        segments = cls._extract_segments(transcript)
        cut_list = list(cuts or [])
        norm_cuts: List[Dict[str, float]] = []
        for c in cut_list:
            cs = float(c.get("start", 0.0) if isinstance(c, dict) else getattr(c, "start", 0.0))
            ce = float(c.get("end", 0.0) if isinstance(c, dict) else getattr(c, "end", 0.0))
            if ce > cs:
                norm_cuts.append({"start": cs, "end": ce})
        norm_cuts.sort(key=lambda x: x["start"])

        def _is_in_cut(t: float) -> bool:
            return any(c["start"] - 0.05 <= t <= c["end"] + 0.05 for c in norm_cuts)

        def _to_seq_ts(raw_t: float) -> float:
            remapped = raw_t
            for c in norm_cuts:
                if c["end"] <= raw_t:
                    remapped -= (c["end"] - c["start"])
                elif c["start"] < raw_t < c["end"]:
                    remapped -= (raw_t - c["start"])
                    break
            return round(max(0.0, remapped), 2)

        keep_segments = [s for s in segments if not _is_in_cut((s["start"] + s["end"]) * 0.5)]
        active_segments = keep_segments if keep_segments else segments

        full_text = ""
        if isinstance(transcript, dict):
            full_text = str(transcript.get("fullText") or transcript.get("full_text") or "").strip()
        elif transcript is not None:
            full_text = str(getattr(transcript, "full_text", getattr(transcript, "fullText", "")) or "").strip()

        eff_duration = float(video_duration or 0.0)
        if eff_duration <= 0.0 and segments:
            eff_duration = float(segments[-1]["end"])
        if eff_duration <= 0.0 and transcript is not None:
            eff_duration = float(
                transcript.get("duration", 0.0)
                if isinstance(transcript, dict)
                else getattr(transcript, "duration", 0.0)
            )
        if eff_duration <= 0.0:
            eff_duration = 30.0

        generated_overlays: List[Dict[str, Any]] = []
        generated_transitions: List[Dict[str, Any]] = []
        generated_sfx: List[Dict[str, Any]] = []

        # 1. Hook Title Overlay (0.3s - 3.5s, trackId=2)
        if enable_text_hooks and (active_segments or full_text):
            first_text = active_segments[0]["text"] if active_segments else full_text
            hook_ts = round(float(active_segments[0]["start"]) if (active_segments and _is_in_cut(0.3)) else 0.3, 2)
            hook_seq_ts = _to_seq_ts(hook_ts)
            hook_phrase = cls._extract_impact_phrase(first_text, min_words=2, max_words=4)
            hook_dur = round(min(3.2, max(1.5, eff_duration - 0.3)), 2)
            hook_ov = _ComposerDict({
                "id": "ad_hook_title_1",
                "type": "text",
                "content": hook_phrase,
                "timestamp": hook_ts,
                "seqTimestamp": hook_seq_ts,
                "duration": hook_dur,
                "font": "Montserrat",
                "fontSize": 58,
                "color": "#FACC15",
                "strokeColor": "#000000",
                "strokeWidth": 4,
                "boxStyle": "none",
                "animation": "pop-up",
                "allCaps": True,
                "position": ["center", "top"],
                "positionX": 50.0,
                "positionY": 18.0,
                "trackId": 2,
                "track_id": 2,
            })
            generated_overlays.append(hook_ov)

            if enable_sfx:
                w_preset = SFX_PRESETS[0]
                generated_sfx.append(_ComposerDict({
                    "id": "ad_sfx_hook_1",
                    "name": w_preset["name"],
                    "presetId": w_preset["presetId"],
                    "type": w_preset["presetId"],
                    "category": w_preset["category"],
                    "sourceUrl": f"sfx://{w_preset['presetId']}",
                    "timestamp": hook_ts,
                    "start": hook_ts,
                    "duration": w_preset["duration"],
                    "volume": w_preset["volume"],
                }))

        # 2. Key Phrase Highlight Overlays (trackId=2, her ~20-30s'de bir)
        if enable_text_hooks and len(active_segments) >= 2:
            interval = 22.0 if eff_duration >= 45.0 else max(4.0, eff_duration / 3.0)
            last_ts = float(active_segments[0]["start"]) if active_segments else 0.3
            highlight_idx = 0

            for seg in active_segments[1:]:
                seg_start = float(seg["start"])
                if seg_start - last_ts >= interval or (highlight_idx == 0 and seg_start >= 3.8):
                    phrase = cls._extract_impact_phrase(seg["text"], min_words=2, max_words=4)
                    color = HIGHLIGHT_COLORS[highlight_idx % len(HIGHLIGHT_COLORS)]
                    anim = HIGHLIGHT_ANIMATIONS[highlight_idx % len(HIGHLIGHT_ANIMATIONS)]
                    hl_dur = round(min(3.2, max(2.0, float(seg["end"]) - seg_start)), 2)

                    hl_ov = _ComposerDict({
                        "id": f"ad_highlight_text_{highlight_idx + 1}",
                        "type": "text",
                        "content": phrase,
                        "timestamp": round(seg_start, 2),
                        "seqTimestamp": _to_seq_ts(seg_start),
                        "duration": hl_dur,
                        "font": "Montserrat",
                        "fontSize": 50,
                        "color": color,
                        "strokeColor": "#000000",
                        "strokeWidth": 4,
                        "boxStyle": "none",
                        "animation": anim,
                        "allCaps": True,
                        "position": ["center", "top"],
                        "positionX": 50.0,
                        "positionY": 22.0,
                        "trackId": 2,
                        "track_id": 2,
                    })
                    generated_overlays.append(hl_ov)

                    if enable_sfx:
                        s_preset = SFX_PRESETS[(highlight_idx + 1) % len(SFX_PRESETS)]
                        generated_sfx.append(_ComposerDict({
                            "id": f"ad_sfx_hl_{highlight_idx + 1}",
                            "name": s_preset["name"],
                            "presetId": s_preset["presetId"],
                            "type": s_preset["presetId"],
                            "category": s_preset["category"],
                            "sourceUrl": f"sfx://{s_preset['presetId']}",
                            "timestamp": round(seg_start, 2),
                            "start": round(seg_start, 2),
                            "duration": s_preset["duration"],
                            "volume": s_preset["volume"],
                        }))

                    last_ts = seg_start
                    highlight_idx += 1

        # 3. Animated Emoji / Sticker Callouts (trackId=3, 2 ila 6 adet Noto Animated Emoji)
        if enable_stickers and eff_duration >= 3.0:
            if eff_duration < 25.0:
                target_sticker_count = 2
            elif eff_duration < 60.0:
                target_sticker_count = 3
            elif eff_duration < 120.0:
                target_sticker_count = 4
            else:
                target_sticker_count = 6

            target_sticker_count = max(2, min(6, target_sticker_count))
            step = max(2.5, (eff_duration - 2.0) / float(target_sticker_count))

            for idx in range(target_sticker_count):
                emoji_meta = NOTO_ANIMATED_EMOJIS[idx % len(NOTO_ANIMATED_EMOJIS)]
                codepoint = emoji_meta["codepoint"]
                gif_url = f"https://fonts.gstatic.com/s/e/notoemoji/latest/{codepoint}/512.gif"

                if active_segments:
                    seg_idx = min(
                        len(active_segments) - 1,
                        int(round(idx * (len(active_segments) - 1) / max(1, target_sticker_count - 1))),
                    )
                    raw_ts = float(active_segments[seg_idx]["start"]) + 0.4
                else:
                    raw_ts = 1.2 + idx * step

                sticker_ts = round(min(max(0.5, raw_ts), max(0.5, eff_duration - 2.2)), 2)
                sticker_ov = _ComposerDict({
                    "id": f"ad_sticker_emoji_{idx + 1}",
                    "type": "sticker",
                    "content": emoji_meta["emoji"],
                    "source": gif_url,
                    "sourceUrl": gif_url,
                    "timestamp": sticker_ts,
                    "seqTimestamp": _to_seq_ts(sticker_ts),
                    "duration": 2.4,
                    "position": ["right", "top"],
                    "positionX": 82.0,
                    "positionY": 24.0,
                    "scale": 0.85,
                    "animation": "pop-up",
                    "trackId": 3,
                    "track_id": 3,
                })
                generated_overlays.append(sticker_ov)

                if enable_sfx and idx < 3:
                    pop_preset = SFX_PRESETS[1]  # pop-bubble
                    generated_sfx.append(_ComposerDict({
                        "id": f"ad_sfx_sticker_{idx + 1}",
                        "name": pop_preset["name"],
                        "presetId": pop_preset["presetId"],
                        "type": pop_preset["presetId"],
                        "category": pop_preset["category"],
                        "sourceUrl": f"sfx://{pop_preset['presetId']}",
                        "timestamp": sticker_ts,
                        "start": sticker_ts,
                        "duration": pop_preset["duration"],
                        "volume": pop_preset["volume"],
                    }))

        # 4. Sahne Geçişleri (Transitions: fade, smoothleft, zoomin)
        if enable_transitions:
            if norm_cuts:
                for c_idx, c in enumerate(norm_cuts[:6]):
                    c_start = c["start"]
                    c_end = c["end"]
                    tr_type = TRANSITION_CYCLE[c_idx % len(TRANSITION_CYCLE)]
                    generated_transitions.append(_ComposerDict({
                        "id": f"ad_transition_{c_idx + 1}",
                        "type": tr_type,
                        "transitionType": tr_type,
                        "timestamp": round(c_start, 2),
                        "boundaryTime": round(c_end, 2),
                        "boundarySourceTime": round(c_end, 2),
                        "segmentIndex": c_idx,
                        "duration": 0.45,
                    }))
            elif eff_duration >= 6.0:
                # Önceden kesilmiş / kesimsiz videolarda da sahne geçişi önerileri oluştur
                num_tr = min(3, max(1, int(eff_duration // 10.0)))
                for t_idx in range(num_tr):
                    tr_ts = round((eff_duration / float(num_tr + 1)) * (t_idx + 1), 2)
                    tr_type = TRANSITION_CYCLE[t_idx % len(TRANSITION_CYCLE)]
                    generated_transitions.append(_ComposerDict({
                        "id": f"ad_transition_{t_idx + 1}",
                        "type": tr_type,
                        "transitionType": tr_type,
                        "timestamp": tr_ts,
                        "boundaryTime": tr_ts,
                        "boundarySourceTime": tr_ts,
                        "segmentIndex": t_idx,
                        "duration": 0.45,
                    }))

        logger.info(
            f"🎬 AutoDirectorComposer tamamlandı: {len(generated_overlays)} katman, "
            f"{len(generated_transitions)} geçiş, {len(generated_sfx)} SFX üretildi."
        )
        return {
            "overlays": generated_overlays,
            "transitions": generated_transitions,
            "sfxClips": generated_sfx,
        }
