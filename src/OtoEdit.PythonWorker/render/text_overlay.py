"""OtoEdit Text Overlay - .ass dosyası ve drawtext ile yazı ve altyazı motoru."""
import os
import re
from typing import List, Dict, Any, Optional
from render.animation_effects import AnimationEffects
from utils.logger import get_logger

logger = get_logger(__name__)


class TextOverlay:
    """Yazı kaplamalarını ve altyazıları (karaoke dahil) .ass dosyasına dönüştürür."""

    @staticmethod
    def hex_to_ass_color(hex_color: str, default: str = "&H00FFFFFF") -> str:
        """
        #RRGGBB veya #RRGGBBAA formatındaki rengi ASS formatına (&HAABBGGRR) dönüştürür.
        Örn: #FFFFFF -> &H00FFFFFF (Tam opak beyaz)
             #00000080 -> &H80000000 (%50 saydam siyah)
        """
        if not hex_color:
            return default

        clean = hex_color.replace("#", "").strip()
        if len(clean) == 6:
            r = clean[0:2]
            g = clean[2:4]
            b = clean[4:6]
            a = "00"
            return f"&H{a}{b}{g}{r}".upper()
        elif len(clean) == 8:
            r = clean[0:2]
            g = clean[2:4]
            b = clean[4:6]
            a = clean[6:8]
            return f"&H{a}{b}{g}{r}".upper()
        return default

    @staticmethod
    def position_to_ass_alignment(position: Any) -> int:
        """
        ["center", "bottom"] gibi liste pozisyonunu ASS sayısal alignment (1-9) değerine dönüştürür.
        """
        if isinstance(position, list) and len(position) >= 2:
            h_pos, v_pos = str(position[0]).lower(), str(position[1]).lower()
        else:
            h_pos, v_pos = "center", "bottom"

        # Dikey katman
        if v_pos in ["top", "ust", "üst"]:
            if h_pos in ["left", "sol"]:
                return 7
            elif h_pos in ["right", "sag", "sağ"]:
                return 9
            return 8
        elif v_pos in ["center", "middle", "orta"]:
            if h_pos in ["left", "sol"]:
                return 4
            elif h_pos in ["right", "sag", "sağ"]:
                return 6
            return 5
        else:  # bottom
            if h_pos in ["left", "sol"]:
                return 1
            elif h_pos in ["right", "sag", "sağ"]:
                return 3
            return 2

    @staticmethod
    def seconds_to_ass_time(seconds: float) -> str:
        """Saniyeyi 'H:MM:SS.cs' formatına dönüştürür."""
        if seconds < 0:
            seconds = 0.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int(round((seconds - int(seconds)) * 100))
        if centisecs >= 100:
            centisecs = 99
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    @classmethod
    def generate_ass(
        cls,
        overlays: List[Dict[str, Any]],
        transcript: Optional[Dict[str, Any]] = None,
        output_path: str = "temp_overlays.ass",
        play_res_x: int = 1920,
        play_res_y: int = 1080
    ) -> str:
        """
        EDL içerisindeki text overlay ve transkript bilgilerini ASS dosyası olarak yazar.
        """
        header = [
            "[Script Info]",
            "Title: OtoEdit Dynamic Subtitles & Overlays",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.601",
            f"PlayResX: {play_res_x}",
            f"PlayResY: {play_res_y}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding",
            # Varsayılan şablon stilleri
            "Style: Default,Montserrat-Bold,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,40,40,60,1",
            "Style: Subtitle,Montserrat-Bold,42,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,30,30,40,1",
            "Style: TitleTop,Montserrat-Bold,56,&H0000D7FF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,3,3,8,40,40,40,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        dialogue_lines = []

        # 1. Text Overlay'leri işle
        for idx, ov in enumerate(overlays or []):
            if ov.get("type") != "text":
                continue

            content = ov.get("content", "").strip()
            if not content:
                continue

            start_sec = float(ov.get("timestamp", 0.0))
            duration_sec = float(ov.get("duration", 4.0))
            end_sec = start_sec + duration_sec

            start_ass = cls.seconds_to_ass_time(start_sec)
            end_ass = cls.seconds_to_ass_time(end_sec)

            font = ov.get("font", "Montserrat-Bold")
            size = int(ov.get("fontSize", 48))
            color_ass = cls.hex_to_ass_color(ov.get("color", "#FFFFFF"))
            bg_ass = cls.hex_to_ass_color(ov.get("backgroundColor", "#00000080"))
            align = cls.position_to_ass_alignment(ov.get("position", ["center", "bottom"]))
            animation = ov.get("animation", "pop-up")

            anim_tags = AnimationEffects.get_ass_tags(animation, duration_sec)

            # Özel stil tagleri (inline override)
            inline_tags = f"{{\\an{align}\\fn{font}\\fs{size}\\c{color_ass}\\4c{bg_ass}{anim_tags}}}"
            clean_content = content.replace("\n", "\\N")
            dialogue_lines.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{inline_tags}{clean_content}")

        # 2. Transkript altyazılarını işle (varsa)
        if transcript and isinstance(transcript, dict):
            segments = transcript.get("segments", [])
            for seg in segments:
                s_start = float(seg.get("start", 0.0))
                s_end = float(seg.get("end", 0.0))
                if s_end <= s_start:
                    continue

                text = seg.get("text", "").strip()
                if not text:
                    continue

                start_ass = cls.seconds_to_ass_time(s_start)
                end_ass = cls.seconds_to_ass_time(s_end)

                # Kelime bazlı karaoke (varsa)
                words = seg.get("words", [])
                if words and len(words) > 0:
                    karaoke_text = ""
                    for w in words:
                        w_text = w.get("word", "")
                        w_dur_cs = int(round((w.get("end", s_end) - w.get("start", s_start)) * 100))
                        w_dur_cs = max(10, min(500, w_dur_cs))
                        karaoke_text += f"{{\\k{w_dur_cs}}}{w_text} "
                    dialogue_lines.append(f"Dialogue: 1,{start_ass},{end_ass},Subtitle,,0,0,0,,{karaoke_text.strip()}")
                else:
                    dialogue_lines.append(f"Dialogue: 1,{start_ass},{end_ass},Subtitle,,0,0,0,,{text}")

        # Dosyayı kaydet
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header) + "\n")
            f.write("\n".join(dialogue_lines) + "\n")

        logger.info(f"ASS dosyası başarıyla üretildi: {output_path} ({len(dialogue_lines)} satır)")
        return output_path
