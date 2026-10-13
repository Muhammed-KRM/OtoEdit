"""OtoEdit Pillow Graphics Engine.
CapCut ve Premiere Pro tarzı şık kutucuklu (pill, rounded badge, lower-third),
çift konturlu ve gölgeli metin katmanlarını yüksek çözünürlüklü şeffaf PNG olarak üretir.
"""
import os
import re
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.logger import get_logger

logger = get_logger(__name__)

# Öncelikli font eşleştirmeleri
FONT_PATHS = {
    "Montserrat": "/usr/share/fonts/truetype/custom/Montserrat.ttf",
    "Montserrat-Bold": "/usr/share/fonts/truetype/custom/Montserrat.ttf",
    "Poppins": "/usr/share/fonts/truetype/custom/Poppins-Bold.ttf",
    "Poppins-Bold": "/usr/share/fonts/truetype/custom/Poppins-Bold.ttf",
    "Poppins-Regular": "/usr/share/fonts/truetype/custom/Poppins-Regular.ttf",
    "Bebas Neue": "/usr/share/fonts/truetype/custom/BebasNeue.ttf",
    "BebasNeue": "/usr/share/fonts/truetype/custom/BebasNeue.ttf",
    "Anton": "/usr/share/fonts/truetype/custom/Anton.ttf",
    "Cinzel": "/usr/share/fonts/truetype/custom/Cinzel.ttf",
    "Outfit": "/usr/share/fonts/truetype/custom/Outfit.ttf",
    "Inter": "/usr/share/fonts/truetype/custom/Inter.ttf",
    "DejaVuSans": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}


def hex_to_rgba(hex_str: str, default: Tuple[int, int, int, int] = (255, 255, 255, 255)) -> Tuple[int, int, int, int]:
    """Hex (#RRGGBB veya #RRGGBBAA) ya da rgba(...) metnini (R, G, B, A) tuple'a çevirir."""
    if not hex_str:
        return default

    clean = hex_str.strip()
    if clean.startswith("rgba"):
        # rgba(r, g, b, a)
        match = re.search(r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d\.]+)\s*\)", clean)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            a = int(float(match.group(4)) * 255)
            return (r, g, b, max(0, min(255, a)))
    elif clean.startswith("rgb"):
        match = re.search(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", clean)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)), 255)

    clean = clean.replace("#", "")
    if len(clean) == 6:
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), 255)
    elif len(clean) == 8:
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), int(clean[6:8], 16))
    return default


class PillowGraphicsEngine:
    """CapCut Stili Tipografi ve Rozet Render Motoru."""

    @classmethod
    def get_font(cls, font_name: Optional[str] = "Inter", font_size: int = 48) -> ImageFont.FreeTypeFont:
        """Sistemdeki mevcut TTF fontlarını bulur ve yükler."""
        clean_name = (font_name or "Inter").split(",")[0].strip().replace("'", "").replace('"', '')
        path = FONT_PATHS.get(clean_name)
        
        if not path or not os.path.isfile(path):
            # Arama yap
            for k, p in FONT_PATHS.items():
                if clean_name.lower() in k.lower() and os.path.isfile(p):
                    path = p
                    break

        if not path or not os.path.isfile(path):
            path = FONT_PATHS.get("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

        try:
            return ImageFont.truetype(path, font_size)
        except Exception as ex:
            logger.warning(f"Font yüklenemedi ({path}): {ex}, varsayılan font kullanılacak")
            return ImageFont.load_default()

    @classmethod
    def render_text_badge(
        cls,
        text: str,
        output_path: str,
        font_name: str = "Montserrat",
        font_family: Optional[str] = None,
        font_size: int = 48,
        text_color: str = "#FFFFFF",
        stroke_color: Optional[str] = "#000000",
        stroke_width: int = 2,
        shadow_color: Optional[str] = None,
        box_style: str = "pill",  # "pill", "rounded", "badge", "none"
        box_bg_color: str = "rgba(0, 0, 0, 0.75)",
        box_padding: int = 16,
        border_radius: int = 24,
        shadow: bool = True,
        shadow_blur: int = 4,
        all_caps: bool = False,
        letter_spacing: int = 0,
        **kwargs
    ) -> str:
        """
        Metin katmanını yuvarlatılmış kutu (pill/badge), kontur ve gölgesiyle birlikte
        2x süper-örnekleme ile antialiased şeffaf PNG olarak üretir.
        """
        effective_font = font_family or font_name or "Montserrat"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        display_text = text.upper() if all_caps else text
        lines = display_text.split("\n")

        # 2x süper-örnekleme (Pürüzsüz kenarlar için)
        ss = 2
        ss_font_size = font_size * ss
        ss_stroke_width = stroke_width * ss
        ss_box_padding = box_padding * ss
        ss_border_radius = border_radius * ss
        ss_letter_spacing = letter_spacing * ss

        font = cls.get_font(effective_font, ss_font_size)

        # Metin boyutunu ölç
        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)

        line_measurements = []
        max_line_w = 0
        total_text_h = 0
        line_height = int(ss_font_size * 1.25)

        for line in lines:
            line_w = 0
            if ss_letter_spacing > 0:
                for ch in line:
                    bbox = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=ss_stroke_width)
                    cw = (bbox[2] - bbox[0]) + ss_letter_spacing
                    line_w += cw
            else:
                bbox = dummy_draw.textbbox((0, 0), line, font=font, stroke_width=ss_stroke_width)
                line_w = bbox[2] - bbox[0]

            line_measurements.append((line, line_w))
            if line_w > max_line_w:
                max_line_w = line_w

        total_text_h = len(lines) * line_height

        # Kutu boyutları
        has_box = (box_style in ["pill", "rounded", "badge"] and box_bg_color)
        if has_box:
            pad_x = int(ss_box_padding * 1.6)
            pad_y = int(ss_box_padding * 1.0)
            box_w = max_line_w + (pad_x * 2)
            box_h = total_text_h + (pad_y * 2)
        else:
            pad_x = ss_stroke_width + 10
            pad_y = ss_stroke_width + 10
            box_w = max_line_w + (pad_x * 2)
            box_h = total_text_h + (pad_y * 2)

        # Kanvas boyutunu gölge marjı ile belirle
        margin = (shadow_blur * ss * 3) + 20
        canvas_w = box_w + (margin * 2)
        canvas_h = box_h + (margin * 2)

        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        box_x1 = margin
        box_y1 = margin
        box_x2 = box_x1 + box_w
        box_y2 = box_y1 + box_h

        # 1. Kutu Gölgesi
        if shadow and has_box:
            shadow_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_canvas)
            shadow_y_offset = int(4 * ss)
            s_rect = (box_x1, box_y1 + shadow_y_offset, box_x2, box_y2 + shadow_y_offset)
            
            radius = (box_h // 2) if box_style == "pill" else ss_border_radius
            shadow_draw.rounded_rectangle(s_rect, radius=radius, fill=(0, 0, 0, 140))
            shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(shadow_blur * ss))
            canvas = Image.alpha_composite(canvas, shadow_canvas)
            draw = ImageDraw.Draw(canvas)

        # 2. Arka Plan Kutusu (Pill / Rounded / Badge)
        if has_box:
            box_rgba = hex_to_rgba(box_bg_color, default=(0, 0, 0, 190))
            radius = (box_h // 2) if box_style == "pill" else ss_border_radius
            draw.rounded_rectangle((box_x1, box_y1, box_x2, box_y2), radius=radius, fill=box_rgba)

        # 3. Metin Çizimi
        text_rgba = hex_to_rgba(text_color, default=(255, 255, 255, 255))
        stroke_rgba = hex_to_rgba(stroke_color, default=(0, 0, 0, 255)) if ss_stroke_width > 0 else None

        # Text drop-shadow (kutu yoksa metin gölgesi çiz)
        if shadow and not has_box:
            shadow_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            s_draw = ImageDraw.Draw(shadow_canvas)
            for i, (line, lw) in enumerate(line_measurements):
                cur_x = box_x1 + pad_x + ((max_line_w - lw) // 2)
                cur_y = box_y1 + pad_y + (i * line_height) + int(3 * ss)
                if ss_letter_spacing > 0:
                    cx = cur_x
                    for ch in line:
                        s_draw.text((cx, cur_y), ch, font=font, fill=(0, 0, 0, 200), stroke_width=ss_stroke_width, stroke_fill=(0, 0, 0, 200))
                        bbox = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=ss_stroke_width)
                        cx += (bbox[2] - bbox[0]) + ss_letter_spacing
                else:
                    s_draw.text((cur_x, cur_y), line, font=font, fill=(0, 0, 0, 200), stroke_width=ss_stroke_width, stroke_fill=(0, 0, 0, 200))
            shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(shadow_blur * ss))
            canvas = Image.alpha_composite(canvas, shadow_canvas)
            draw = ImageDraw.Draw(canvas)

        for i, (line, lw) in enumerate(line_measurements):
            cur_x = box_x1 + pad_x + ((max_line_w - lw) // 2)
            cur_y = box_y1 + pad_y + (i * line_height)
            if ss_letter_spacing > 0:
                cx = cur_x
                for ch in line:
                    draw.text((cx, cur_y), ch, font=font, fill=text_rgba, stroke_width=ss_stroke_width, stroke_fill=stroke_rgba)
                    bbox = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=ss_stroke_width)
                    cx += (bbox[2] - bbox[0]) + ss_letter_spacing
            else:
                draw.text((cur_x, cur_y), line, font=font, fill=text_rgba, stroke_width=ss_stroke_width, stroke_fill=stroke_rgba)

        # 4. Kırp ve 2x -> 1x ölçekle (LANCZOS downsampling)
        bbox = canvas.getbbox()
        if bbox:
            canvas = canvas.crop(bbox)

        final_w = max(1, canvas.width // ss)
        final_h = max(1, canvas.height // ss)
        final_img = canvas.resize((final_w, final_h), Image.Resampling.LANCZOS)
        final_img.save(output_path, "PNG")

        logger.info(f"[GRAPHICS_ENGINE] Text rozeti render edildi ({final_w}x{final_h}): {output_path}")
        return output_path
