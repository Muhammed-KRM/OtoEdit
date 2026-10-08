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
            # Default: Kenarlıksız, doğal drop-shadow gölgeli (CSS drop-shadow paritesi)
            "Style: Default,Inter,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,0,3,5,40,40,60,1",
            # Subtitle: Göğüs hizasında (%80-85), yarı saydam şık siyah kapsül (BorderStyle: 3, BackColour: &HB0101010)
            "Style: Subtitle,Montserrat,44,&H00FFFFFF,&H0000FFFF,&H00000000,&HB0101010,1,0,0,0,100,100,0,0,3,10,0,2,30,30,160,1",
            "Style: TitleTop,Inter,56,&H0000D7FF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,0,3,8,40,40,40,1",
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

            raw_font = ov.get("font", "Inter")
            # CSS fallback'leri temizle (örn: "Cinzel, serif" -> "Cinzel")
            cleaned_font = raw_font.split(",")[0].strip().replace("'", "").replace('"', '')
            font_map = {
                "Inter": "Inter",
                "inter": "Inter",
                "Inter V": "Inter",
                "Montserrat": "Montserrat",
                "Cinzel": "Cinzel",
                "Bebas Neue": "Bebas Neue",
                "Anton": "Anton",
                "Poppins": "Poppins",
                "Outfit": "Outfit",
                "Arial": "DejaVu Sans"
            }
            font = font_map.get(cleaned_font, cleaned_font)
            size = int(ov.get("fontSize", 48))
            color_ass = cls.hex_to_ass_color(ov.get("color", "#FFFFFF"))
            align = cls.position_to_ass_alignment(ov.get("position", ["center", "bottom"]))
            animation = ov.get("animation", "pop-up")
            exit_animation = ov.get("exitAnimation") or ov.get("exit_animation") or "fade"
            
            posX = ov.get("positionX")
            posY = ov.get("positionY")

            anim_tags = AnimationEffects.get_ass_tags(animation, duration_sec, exit_anim_type=exit_animation)

            # Convert position to tag
            pos_tag = ""
            if posX is not None and posY is not None:
                px = int(float(posX) / 100.0 * play_res_x)
                py = int(float(posY) / 100.0 * play_res_y)
                pos_tag = f"\\pos({px},{py})"

            logger.info(
                f"[TextOverlay:Trace] ov_id={ov.get('id')} raw_font='{raw_font}' -> mapped_font='{font}', "
                f"size={size}, pos=({posX}%, {posY}%) -> px=({px if pos_tag else 'align'}, {py if pos_tag else 'align'})"
            )

            # Özel stil tagleri (inline override)
            # \\c: font rengi, \\bord0: kaba siyah çizgiyi kaldır, \\shad3\\4c&H90000000: CSS drop-shadow benzeri yumuşak gölge
            if pos_tag:
                inline_tags = f"{{\\an5\\b1\\fn{font}\\fs{size}\\c{color_ass}\\bord0\\shad3\\4c&H90000000{pos_tag}{anim_tags}}}"
            else:
                inline_tags = f"{{\\an{align}\\b1\\fn{font}\\fs{size}\\c{color_ass}\\bord0\\shad3\\4c&H90000000{anim_tags}}}"
                
            clean_content = content.replace("\n", "\\N")
            track_layer = int(ov.get("trackId") or ov.get("track_id") or 1)
            dialogue_lines.append(f"Dialogue: {track_layer},{start_ass},{end_ass},Default,,0,0,0,,{inline_tags}{clean_content}")

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

                # Kelime bazlı karaoke / dinamik vurgu (varsa)
                words = seg.get("words", [])
                valid_words = []
                for w in words or []:
                    w_text = w.get("word", "").strip()
                    if not w_text:
                        continue
                    w_s = float(w.get("start", s_start))
                    w_e = float(w.get("end", w_s + 0.1))
                    if w_e <= w_s:
                        w_e = w_s + 0.1
                    valid_words.append({"word": w_text, "start": w_s, "end": w_e})

                if valid_words and len(valid_words) > 0:
                    # TikTok / Reels / CapCut tarzı hareketli kelime vurgusu:
                    # 1. İlk kelimeden önce boşluk varsa tümü beyaz
                    first_start = valid_words[0]["start"]
                    if first_start > s_start + 0.05:
                        all_white = " ".join([w["word"] for w in valid_words])
                        dialogue_lines.append(
                            f"Dialogue: 1,{cls.seconds_to_ass_time(s_start)},{cls.seconds_to_ass_time(first_start)},Subtitle,,0,0,0,,{all_white}"
                        )

                    # 2. Her bir kelime için o kelimenin telaffuz edildiği aralıkta sarı vurgu
                    for i, cur_w in enumerate(valid_words):
                        w_start_time = max(s_start, cur_w["start"])
                        w_end_time = min(s_end, cur_w["end"])

                        next_start = valid_words[i + 1]["start"] if (i + 1 < len(valid_words)) else s_end

                        # Küçük duraklamaları bir sonraki kelimeye kadar uzat (altyazı kutusunun titremesini önle)
                        if next_start > w_end_time and (next_start - w_end_time) < 0.25:
                            display_end = next_start
                        else:
                            display_end = w_end_time

                        if display_end <= w_start_time:
                            display_end = w_start_time + 0.05

                        styled_parts = []
                        for j, w in enumerate(valid_words):
                            if j == i:
                                styled_parts.append(f"{{\\c&H0000FFFF&}}{w['word']}{{\\c&H00FFFFFF&}}")
                            else:
                                styled_parts.append(w["word"])

                        word_line = " ".join(styled_parts)
                        dialogue_lines.append(
                            f"Dialogue: 1,{cls.seconds_to_ass_time(w_start_time)},{cls.seconds_to_ass_time(display_end)},Subtitle,,0,0,0,,{word_line}"
                        )

                        # Uzun duraklama varsa ara aralıkta tümü beyaz
                        if next_start > display_end + 0.05:
                            all_white = " ".join([w["word"] for w in valid_words])
                            dialogue_lines.append(
                                f"Dialogue: 1,{cls.seconds_to_ass_time(display_end)},{cls.seconds_to_ass_time(next_start)},Subtitle,,0,0,0,,{all_white}"
                            )

                    # 3. Son kelimeden sonra kalan süre varsa tümü beyaz
                    last_end = valid_words[-1]["end"]
                    if s_end > last_end + 0.05:
                        all_white = " ".join([w["word"] for w in valid_words])
                        dialogue_lines.append(
                            f"Dialogue: 1,{cls.seconds_to_ass_time(last_end)},{cls.seconds_to_ass_time(s_end)},Subtitle,,0,0,0,,{all_white}"
                        )
                else:
                    clean_text = text.replace("\n", " ")
                    dialogue_lines.append(f"Dialogue: 1,{start_ass},{end_ass},Subtitle,,0,0,0,,{clean_text}")

        # Dosyayı kaydet
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header) + "\n")
            f.write("\n".join(dialogue_lines) + "\n")

        logger.info(f"ASS dosyası başarıyla üretildi: {output_path} ({len(dialogue_lines)} satır)")
        return output_path
