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
        play_res_y: int = 1080,
        subtitle_style: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        EDL içerisindeki text overlay ve transkript bilgilerini ASS dosyası olarak yazar.
        """
        # Altyazı stili yapılandırması (SubtitleStyleConfig)
        sub_style = subtitle_style or {}
        preset = sub_style.get("preset", "tiktok_yellow")
        raw_sub_font = sub_style.get("fontFamily") or "Montserrat-Bold"
        sub_font = raw_sub_font.split(",")[0].strip().replace("'", "").replace('"', '')
        sub_size_px = int(sub_style.get("fontSize", 44))
        # 96 DPI CSS px -> 72 DPI ASS pt
        sub_fs = max(18, int(round(sub_size_px * (play_res_y / 1080.0) * (96.0 / 72.0))))

        primary_color = cls.hex_to_ass_color(sub_style.get("textColor", "#FFFFFF"), "&H00FFFFFF")
        highlight_color = cls.hex_to_ass_color(sub_style.get("highlightColor", "#FFD700"), "&H0000D7FF")
        stroke_color = cls.hex_to_ass_color(sub_style.get("strokeColor", "#000000"), "&H00000000")
        stroke_w = float(sub_style.get("strokeWidth", 3.0))
        shadow_color = cls.hex_to_ass_color(sub_style.get("shadowColor", "#00000080"), "&H80000000")
        shadow_dist = float(sub_style.get("shadowDistance", 2.0))

        vert_pos = float(sub_style.get("verticalPosition", 85.0))
        margin_v = max(20, int(round(play_res_y * (1.0 - vert_pos / 100.0))))
        letter_spacing = float(sub_style.get("letterSpacing", 0.0))

        # BorderStyle: 1 (Outline+Shadow), 3 (Opaque Banner Box)
        border_style = 3 if preset == "opaque_banner" else 1
        if preset == "opaque_banner":
            back_colour = cls.hex_to_ass_color(sub_style.get("backgroundColor", "#000000B0"), "&HB0000000")
            outline_w = int(sub_style.get("backgroundPadding", 10))
            shadow_dist = 0.0
        elif preset == "cinematic_shadow":
            border_style = 1
            back_colour = "&H90000000"
            outline_w = 1.0
            shadow_dist = 3.5
        elif preset == "neon_glow":
            border_style = 1
            stroke_color = "&H00FF00FF"  # Magenta parlama
            back_colour = "&H00FFFF00"   # Cyan parlama
            outline_w = 3.5
            shadow_dist = 3.5
        else:  # tiktok_yellow / custom
            back_colour = shadow_color
            outline_w = stroke_w

        subtitle_style_line = (
            f"Style: Subtitle,{sub_font},{sub_fs},{primary_color},{highlight_color},"
            f"{stroke_color},{back_colour},1,0,0,0,100,100,{int(letter_spacing)},0,"
            f"{border_style},{outline_w},{shadow_dist},2,40,40,{margin_v},1"
        )

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
            subtitle_style_line,
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
            raw_size = int(ov.get("fontSize", 48))
            # Editördeki font boyutu CSS pikseli (96 DPI) bazlıdır. ASS \fs ise FreeType pt (72 DPI) bazlıdır.
            # 96 / 72 = 4 / 3 ≈ 1.333333 oranı ile ölçeklendiğinde CSS pikseli ile ASS çıktı boyutu %100 birebir eşitlenir.
            size = max(12, int(round(raw_size * (96.0 / 72.0))))

            color_ass = cls.hex_to_ass_color(ov.get("color", "#FFFFFF"))
            align = cls.position_to_ass_alignment(ov.get("position", ["center", "bottom"]))
            animation = ov.get("animation", "pop-up")
            exit_animation = ov.get("exitAnimation") or ov.get("exit_animation") or "fade"
            
            posX = ov.get("positionX")
            posY = ov.get("positionY")

            px = int(float(posX) / 100.0 * play_res_x) if posX is not None else 0
            py = int(float(posY) / 100.0 * play_res_y) if posY is not None else 0
            
            has_custom_pos = (posX is not None and posY is not None)
            target_align = 5 if has_custom_pos else align

            anim_tags = AnimationEffects.get_ass_tags(
                animation, duration_sec, pos_x=px, pos_y=py, exit_anim_type=exit_animation
            )
            # ASS standardında \move ve \pos aynı anda kullanılamaz (\move koordinatları zaten yönetir)
            pos_tag = "" if ("\\move" in anim_tags or not has_custom_pos) else f"\\pos({px},{py})"

            logger.info(
                f"[TextOverlay:Trace] ov_id={ov.get('id')} raw_font='{raw_font}' -> mapped_font='{font}', "
                f"raw_size={raw_size} -> ass_size={size}, pos=({posX}%, {posY}%) -> px=({px if has_custom_pos else 'align'}, {py if has_custom_pos else 'align'}), align=\\an{target_align}"
            )

            # Özel stil tagleri (inline override)
            # \\c: font rengi, \\bord0: kaba siyah çizgiyi kaldır, \\shad4\\blur2\\4c&H000000&: CSS drop-shadow paritesi derin yumuşak siyah gölge
            shadow_tags = "\\bord0\\shad4\\blur2\\4c&H000000&"
            if pos_tag:
                inline_tags = f"{{\\an{target_align}\\b1\\fn{font}\\fs{size}\\c{color_ass}{shadow_tags}{pos_tag}{anim_tags}}}"
            else:
                inline_tags = f"{{\\an{target_align}\\b1\\fn{font}\\fs{size}\\c{color_ass}{shadow_tags}{anim_tags}}}"
                
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
                            w_disp = w["word"].upper() if sub_style.get("allCaps") else w["word"]
                            if j == i:
                                styled_parts.append(f"{{\\c{highlight_color}\\t(0,90,\\fscx110\\fscy110)}}{w_disp}{{\\c{primary_color}\\fscx100\\fscy100}}")
                            else:
                                styled_parts.append(w_disp)

                        word_line = " ".join(styled_parts)
                        dialogue_lines.append(
                            f"Dialogue: 1,{cls.seconds_to_ass_time(w_start_time)},{cls.seconds_to_ass_time(display_end)},Subtitle,,0,0,0,,{word_line}"
                        )

                        # Uzun duraklama varsa ara aralıkta tümü birincil renk
                        if next_start > display_end + 0.05:
                            all_white = " ".join([(w["word"].upper() if sub_style.get("allCaps") else w["word"]) for w in valid_words])
                            dialogue_lines.append(
                                f"Dialogue: 1,{cls.seconds_to_ass_time(display_end)},{cls.seconds_to_ass_time(next_start)},Subtitle,,0,0,0,,{all_white}"
                            )

                    # 3. Son kelimeden sonra kalan süre varsa tümü birincil renk
                    last_end = valid_words[-1]["end"]
                    if s_end > last_end + 0.05:
                        all_white = " ".join([(w["word"].upper() if sub_style.get("allCaps") else w["word"]) for w in valid_words])
                        dialogue_lines.append(
                            f"Dialogue: 1,{cls.seconds_to_ass_time(last_end)},{cls.seconds_to_ass_time(s_end)},Subtitle,,0,0,0,,{all_white}"
                        )
                else:
                    clean_text = text.replace("\n", " ").upper() if sub_style.get("allCaps") else text.replace("\n", " ")
                    dialogue_lines.append(f"Dialogue: 1,{start_ass},{end_ass},Subtitle,,0,0,0,,{clean_text}")

        # Dosyayı kaydet
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header) + "\n")
            f.write("\n".join(dialogue_lines) + "\n")

        logger.info(f"ASS dosyası başarıyla üretildi: {output_path} ({len(dialogue_lines)} satır)")
        return output_path
