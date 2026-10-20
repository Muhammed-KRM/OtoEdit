"""OtoEdit AI Background Removal & Image Sticker Studio.
rembg (u2net / isnet), OpenCV ve PIL destekli arka plan kaldırma, beyaz sticker konturu,
chroma keying, gelişmiş şekil maskeleme (circle, rounded, star, heart, hexagon, diamond + feather)
ve Photoshop katman ayarlamaları (parlaklık, kontrast, doygunluk, sıcaklık, ton, bulanıklık, keskinlik,
saydamlık, çevirme, gölge) servisi. İçerik adresli SHA-256 önbellekleme içerir.
"""
import os
import math
import json
import hashlib
import tempfile
from typing import Optional, Tuple, Dict, Any, List
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageEnhance
from utils.logger import get_logger

logger = get_logger(__name__)

# rembg modülü opsiyonel import (hata durumunda fallback)
try:
    from rembg import remove, new_session
    _REMBG_SESSION = None
    REMBG_AVAILABLE = True
except Exception as ex:
    logger.warning(f"rembg yüklenemedi, fallback kullanılacak: {ex}")
    REMBG_AVAILABLE = False
    _REMBG_SESSION = None


def _parse_hex_rgb(hex_color: str, default: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[int, int, int]:
    if not hex_color or not isinstance(hex_color, str):
        return default
    clean = hex_color.strip().lstrip("#")
    try:
        if len(clean) == 3:
            return (int(clean[0] * 2, 16), int(clean[1] * 2, 16), int(clean[2] * 2, 16))
        elif len(clean) >= 6:
            return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
    except ValueError:
        pass
    return default


class BackgroundRemoverService:
    """Yapay Zeka Destekli Arka Plan Kaldırma ve Photoshop Görsel Düzenleme Servisi."""

    _MEM_IMG_CACHE: Dict[str, bytes] = {}

    @classmethod
    def _get_cache_key(cls, op_name: str, image_path: str, params: Dict[str, Any]) -> str:
        """Görsel dosyasının içeriği/stat bilgisi ve işlem parametrelerinden SHA-256 anahtarı üretir."""
        abs_path = os.path.abspath(image_path)
        try:
            st = os.stat(abs_path)
            with open(abs_path, "rb") as f:
                head_bytes = f.read(8192)
            file_hash = hashlib.sha256(head_bytes + f":{st.st_size}:{st.st_mtime_ns}".encode("utf-8")).hexdigest()
        except Exception:
            file_hash = abs_path

        payload = {
            "op": op_name,
            "file": file_hash,
            "params": params,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @classmethod
    def _try_load_cached(cls, cache_key: str, output_path: str) -> Optional[str]:
        """Önbellekte varsa doğrudan hedef yola yazar ve döner."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        if cache_key in cls._MEM_IMG_CACHE:
            with open(output_path, "wb") as f_out:
                f_out.write(cls._MEM_IMG_CACHE[cache_key])
            return output_path

        cache_dir = os.path.join(tempfile.gettempdir(), "otoedit_img_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{cache_key}.png")
        if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0:
            with open(cache_file, "rb") as f_in:
                data = f_in.read()
            cls._MEM_IMG_CACHE[cache_key] = data
            if os.path.abspath(cache_file) != os.path.abspath(output_path):
                with open(output_path, "wb") as f_out:
                    f_out.write(data)
            return output_path
        return None

    @classmethod
    def _save_to_cache(cls, cache_key: str, output_path: str) -> None:
        """Üretilen görseli bellek ve disk önbelleğine yazar."""
        try:
            if not os.path.isfile(output_path):
                return
            with open(output_path, "rb") as f_in:
                data = f_in.read()
            cls._MEM_IMG_CACHE[cache_key] = data
            cache_dir = os.path.join(tempfile.gettempdir(), "otoedit_img_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{cache_key}.png")
            if os.path.abspath(cache_file) != os.path.abspath(output_path):
                with open(cache_file, "wb") as f_out:
                    f_out.write(data)
        except Exception as ex:
            logger.debug(f"Görsel önbellek kayıt uyarısı: {ex}")

    @classmethod
    def _get_rembg_session(cls):
        global _REMBG_SESSION
        if REMBG_AVAILABLE and _REMBG_SESSION is None:
            try:
                _REMBG_SESSION = new_session("u2netp")
            except Exception as e:
                logger.warning(f"rembg session başlatılamadı, varsayılan kullanılacak: {e}")
        return _REMBG_SESSION

    @classmethod
    def remove_background(
        cls,
        image_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Görselin arka planını AI ile şeffaf (transparent PNG) yapar.
        rembg (u2net) kullanılır, hata durumunda OpenCV GrabCut fallback çalışır.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Görsel bulunamadı: {image_path}")

        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_nobg.png")

        cache_key = cls._get_cache_key("remove_background", image_path, {})
        cached = cls._try_load_cached(cache_key, output_path)
        if cached:
            return cached

        if REMBG_AVAILABLE:
            try:
                session = cls._get_rembg_session()
                with open(image_path, "rb") as f_in:
                    input_bytes = f_in.read()

                output_bytes = remove(input_bytes, session=session) if session else remove(input_bytes)
                with open(output_path, "wb") as f_out:
                    f_out.write(output_bytes)

                cls._save_to_cache(cache_key, output_path)
                logger.info(f"[BG_REMOVE:AI] rembg ile başarıyla arka plan kaldırıldı: {output_path}")
                return output_path
            except Exception as ex:
                logger.error(f"[BG_REMOVE:AI_FAIL] rembg başarısız oldu, OpenCV fallback'e geçiliyor: {ex}")

        res_path = cls._fallback_grabcut_remove(image_path, output_path)
        cls._save_to_cache(cache_key, res_path)
        return res_path

    @classmethod
    def _fallback_grabcut_remove(cls, image_path: str, output_path: str) -> str:
        """OpenCV GrabCut ile merkez odaklı arka plan temizleme fallback'i."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Görsel OpenCV ile okunamadı: {image_path}")

        h, w = img.shape[:2]
        mask = np.zeros(img.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        rect = (max(1, int(w * 0.08)), max(1, int(h * 0.08)), max(2, int(w * 0.84)), max(2, int(h * 0.84)))
        try:
            cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
        except Exception:
            mask2 = np.ones(img.shape[:2], dtype=np.uint8)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        alpha = (mask2 * 255).astype(np.uint8)
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)

        rgba = np.dstack((img_rgb, alpha))
        pil_img = Image.fromarray(rgba)
        pil_img.save(output_path, "PNG")
        logger.info(f"[BG_REMOVE:FALLBACK] OpenCV GrabCut ile arka plan kaldırıldı: {output_path}")
        return output_path

    @classmethod
    def add_sticker_outline(
        cls,
        image_path: str,
        output_path: Optional[str] = None,
        outline_width: int = 8,
        outline_color_hex: str = "#FFFFFF",
        border_width: Optional[int] = None,
        border_color: Optional[str] = None,
        shadow: bool = True,
        **kwargs
    ) -> str:
        """
        Şeffaf PNG görselin etrafına CapCut / Canva tarzı beyaz çıkartma (sticker) konturu ve gölgesi ekler.
        """
        if border_width is not None:
            outline_width = border_width
        if border_color is not None:
            outline_color_hex = border_color
        outline_width = max(1, int(outline_width))

        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_sticker.png")

        cache_key = cls._get_cache_key(
            "add_sticker_outline",
            image_path,
            {"w": outline_width, "col": outline_color_hex, "shadow": bool(shadow)},
        )
        cached = cls._try_load_cached(cache_key, output_path)
        if cached:
            return cached

        src = Image.open(image_path).convert("RGBA")

        pad = outline_width * 3 + 20
        padded = Image.new("RGBA", (src.width + pad * 2, src.height + pad * 2), (0, 0, 0, 0))
        padded.paste(src, (pad, pad), src)

        alpha = np.array(padded.split()[3])
        r, g, b = _parse_hex_rgb(outline_color_hex, default=(255, 255, 255))

        kernel_size = outline_width * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated_alpha = cv2.dilate(alpha, kernel, iterations=1)
        dilated_alpha = cv2.GaussianBlur(dilated_alpha, (3, 3), 0)

        outline_layer = Image.new("RGBA", padded.size, (r, g, b, 0))
        outline_layer.putalpha(Image.fromarray(dilated_alpha))

        result = Image.new("RGBA", padded.size, (0, 0, 0, 0))

        if shadow:
            shadow_alpha = cv2.dilate(alpha, kernel, iterations=1)
            shadow_img = Image.new("RGBA", padded.size, (0, 0, 0, 120))
            shadow_img.putalpha(Image.fromarray(shadow_alpha))
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(max(1.0, outline_width * 0.8)))
            result.alpha_composite(shadow_img, (0, int(outline_width * 0.4)))

        result.alpha_composite(outline_layer)
        result.alpha_composite(padded)

        bbox = result.getbbox()
        if bbox:
            result = result.crop(bbox)

        result.save(output_path, "PNG")
        cls._save_to_cache(cache_key, output_path)
        logger.info(f"[STICKER] Sticker konturu oluşturuldu: {output_path}")
        return output_path

    @classmethod
    def apply_chroma_key(
        cls,
        image_path: str,
        output_path: Optional[str] = None,
        key_color_hex: str = "#00FF00",
        similarity: float = 0.35,
        smoothness: float = 0.1
    ) -> str:
        """
        Belirtilen renk tonunu (yeşil ekran / chroma key) görselden şeffaflaştırır.
        """
        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_chroma.png")

        cache_key = cls._get_cache_key(
            "apply_chroma_key",
            image_path,
            {"color": key_color_hex, "sim": round(float(similarity), 3), "smooth": round(float(smoothness), 3)},
        )
        cached = cls._try_load_cached(cache_key, output_path)
        if cached:
            return cached

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Görsel açılamadı: {image_path}")

        kr, kg, kb = _parse_hex_rgb(key_color_hex, default=(0, 255, 0))
        key_bgr = np.array([kb, kg, kr], dtype=np.uint8)

        img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        key_lab = cv2.cvtColor(np.uint8([[key_bgr]]), cv2.COLOR_BGR2LAB)[0][0]

        diff = np.linalg.norm(img_lab.astype(np.float32) - key_lab.astype(np.float32), axis=2)
        max_dist = 255.0

        threshold = float(similarity) * max_dist
        softness = max(1.0, float(smoothness) * max_dist)

        alpha = np.clip((diff - threshold) / softness, 0.0, 1.0) * 255.0
        alpha = alpha.astype(np.uint8)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgba = np.dstack((img_rgb, alpha))
        pil_img = Image.fromarray(rgba)
        pil_img.save(output_path, "PNG")
        cls._save_to_cache(cache_key, output_path)
        logger.info(f"[CHROMA_KEY] Chroma key uygulandı: {key_color_hex} -> {output_path}")
        return output_path

    @classmethod
    def apply_shape_mask(
        cls,
        image_path: str,
        output_path: Optional[str] = None,
        shape: str = "circle",
        corner_radius: int = 32,
        feather: int = 0,
        **kwargs
    ) -> str:
        """
        Görseli dairesel avatar, yuvarlatılmış kart, yıldız, kalp, altıgen veya elmas
        maskesi haline getirir; opsiyonel feather (kenar yumuşatma) uygular.
        Desteklenen şekiller: "circle", "rounded", "star", "heart", "hexagon", "diamond".
        """
        shape_clean = (shape or "circle").lower().strip()
        feather = int(kwargs.get("maskFeather") if kwargs.get("maskFeather") is not None else feather)

        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_{shape_clean}.png")

        cache_key = cls._get_cache_key(
            "apply_shape_mask",
            image_path,
            {"shape": shape_clean, "radius": int(corner_radius), "feather": int(feather)},
        )
        cached = cls._try_load_cached(cache_key, output_path)
        if cached:
            return cached

        src = Image.open(image_path).convert("RGBA")
        w, h = src.size

        # 4x süper-örnekleme ile kusursuz antialiased kenar maskesi
        scale = 4
        mw, mh = w * scale, h * scale
        cx, cy = mw / 2.0, mh / 2.0
        min_dim = min(mw, mh)

        mask = Image.new("L", (mw, mh), 0)
        draw = ImageDraw.Draw(mask)

        if shape_clean == "circle":
            left = (mw - min_dim) // 2
            top = (mh - min_dim) // 2
            draw.ellipse((left, top, left + min_dim, top + min_dim), fill=255)

        elif shape_clean == "rounded":
            draw.rounded_rectangle((0, 0, mw, mh), radius=max(1, int(corner_radius) * scale), fill=255)

        elif shape_clean == "diamond":
            pts = [(cx, 0), (mw, cy), (cx, mh), (0, cy)]
            draw.polygon(pts, fill=255)

        elif shape_clean == "hexagon":
            r = min_dim * 0.48
            pts = [
                (
                    cx + r * math.cos(math.radians(60 * i - 30)),
                    cy + r * math.sin(math.radians(60 * i - 30)),
                )
                for i in range(6)
            ]
            draw.polygon(pts, fill=255)

        elif shape_clean == "star":
            outer_r = min_dim * 0.48
            inner_r = outer_r * 0.40
            pts = []
            for i in range(10):
                r = outer_r if i % 2 == 0 else inner_r
                ang = math.radians(i * 36 - 90)
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            draw.polygon(pts, fill=255)

        elif shape_clean == "heart":
            pts = []
            scale_h = (min_dim * 0.45) / 16.0
            for i in range(120):
                t = (2.0 * math.pi * i) / 120.0
                hx = 16.0 * (math.sin(t) ** 3)
                hy = -(
                    13.0 * math.cos(t)
                    - 5.0 * math.cos(2.0 * t)
                    - 2.0 * math.cos(3.0 * t)
                    - math.cos(4.0 * t)
                )
                pts.append((cx + hx * scale_h, cy + (hy + 2.0) * scale_h))
            draw.polygon(pts, fill=255)

        else:
            draw.rectangle((0, 0, mw, mh), fill=255)

        mask = mask.resize((w, h), Image.Resampling.LANCZOS)
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=float(feather)))

        orig_alpha = src.split()[3]
        mask_np = np.array(mask, dtype=np.float32) / 255.0
        orig_np = np.array(orig_alpha, dtype=np.float32) / 255.0
        combined_alpha = Image.fromarray(np.clip(mask_np * orig_np * 255.0, 0, 255).astype(np.uint8))

        src.putalpha(combined_alpha)
        src.save(output_path, "PNG")
        cls._save_to_cache(cache_key, output_path)
        logger.info(f"[SHAPE_MASK] Şekil maskesi uygulandı: {shape_clean} (feather={feather}) -> {output_path}")
        return output_path

    @classmethod
    def apply_photoshop_adjustments(
        cls,
        image_path: str,
        output_path: Optional[str] = None,
        brightness: float = 0.0,
        contrast: float = 0.0,
        saturation: float = 0.0,
        warmth: float = 0.0,
        hue: float = 0.0,
        blur: float = 0.0,
        sharpen: float = 0.0,
        opacity: float = 100.0,
        flip_h: bool = False,
        flip_v: bool = False,
        drop_shadow: bool = False,
        shadow_color: str = "#000000",
        shadow_blur: int = 10,
        **kwargs
    ) -> str:
        """
        Görsel katmanına Photoshop düzeyinde renk, ışık, keskinlik, bulanıklık,
        aynalama (flip), opaklık ve derinlik gölgesi (drop shadow) ayarlarını uygular.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Görsel bulunamadı: {image_path}")

        flip_h = bool(kwargs.get("flipH") if kwargs.get("flipH") is not None else flip_h)
        flip_v = bool(kwargs.get("flipV") if kwargs.get("flipV") is not None else flip_v)
        drop_shadow = bool(kwargs.get("dropShadow") if kwargs.get("dropShadow") is not None else drop_shadow)
        shadow_color = kwargs.get("shadowColor") or shadow_color or "#000000"
        shadow_blur = int(float(kwargs.get("shadowBlur") if kwargs.get("shadowBlur") is not None else shadow_blur))

        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_ps.png")

        params_sig = {
            "brightness": round(float(brightness), 2),
            "contrast": round(float(contrast), 2),
            "saturation": round(float(saturation), 2),
            "warmth": round(float(warmth), 2),
            "hue": round(float(hue), 2),
            "blur": round(float(blur), 2),
            "sharpen": round(float(sharpen), 2),
            "opacity": round(float(opacity), 2),
            "flip_h": flip_h,
            "flip_v": flip_v,
            "drop_shadow": drop_shadow,
            "shadow_color": shadow_color,
            "shadow_blur": shadow_blur,
        }
        cache_key = cls._get_cache_key("apply_photoshop_adjustments", image_path, params_sig)
        cached = cls._try_load_cached(cache_key, output_path)
        if cached:
            return cached

        img = Image.open(image_path).convert("RGBA")

        # 1. Yatay / Dikey Çevirme (Flip H / V)
        if flip_h:
            img = ImageOps.mirror(img)
        if flip_v:
            img = ImageOps.flip(img)

        r_ch, g_ch, b_ch, a_ch = img.split()
        rgb_img = Image.merge("RGB", (r_ch, g_ch, b_ch))

        # 2. Parlaklık (Brightness: -100 .. +100)
        if abs(float(brightness)) > 0.1:
            factor = max(0.05, 1.0 + (float(brightness) / 100.0))
            rgb_img = ImageEnhance.Brightness(rgb_img).enhance(factor)

        # 3. Kontrast (Contrast: -100 .. +100)
        if abs(float(contrast)) > 0.1:
            factor = max(0.05, 1.0 + (float(contrast) / 100.0))
            rgb_img = ImageEnhance.Contrast(rgb_img).enhance(factor)

        # 4. Doygunluk (Saturation: -100 .. +100)
        if abs(float(saturation)) > 0.1:
            factor = max(0.0, 1.0 + (float(saturation) / 100.0))
            rgb_img = ImageEnhance.Color(rgb_img).enhance(factor)

        # 5. Keskinleştirme (Sharpen: 0 .. 100)
        if float(sharpen) > 0.1:
            factor = 1.0 + (float(sharpen) / 25.0)
            rgb_img = ImageEnhance.Sharpness(rgb_img).enhance(factor)

        # 6. Sıcaklık (Warmth: -100 .. +100) ve Ton (Hue: -180 .. +180)
        if abs(float(warmth)) > 0.1 or abs(float(hue)) > 0.1:
            rgb_np = np.array(rgb_img, dtype=np.float32)
            if abs(float(warmth)) > 0.1:
                shift = float(warmth) * 0.65
                rgb_np[:, :, 0] = np.clip(rgb_np[:, :, 0] + shift, 0, 255)
                rgb_np[:, :, 2] = np.clip(rgb_np[:, :, 2] - shift, 0, 255)

            rgb_u8 = rgb_np.astype(np.uint8)
            if abs(float(hue)) > 0.1:
                hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV).astype(np.int32)
                hsv[:, :, 0] = (hsv[:, :, 0] + int(round(float(hue) / 2.0))) % 180
                rgb_u8 = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

            rgb_img = Image.fromarray(rgb_u8, "RGB")

        # 7. Bulanıklık (Gaussian Blur: 0 .. 100)
        if float(blur) > 0.1:
            rgb_img = rgb_img.filter(ImageFilter.GaussianBlur(radius=float(blur) * 0.5))

        # 8. Opaklık (Opacity: 0 .. 100)
        if float(opacity) < 99.9:
            op_scale = max(0.0, min(1.0, float(opacity) / 100.0))
            a_np = (np.array(a_ch, dtype=np.float32) * op_scale).astype(np.uint8)
            a_ch = Image.fromarray(a_np)

        r_new, g_new, b_new = rgb_img.split()
        result = Image.merge("RGBA", (r_new, g_new, b_new, a_ch))

        # 9. Katman Gölgesi (Drop Shadow)
        if drop_shadow:
            s_blur = max(1, int(shadow_blur))
            pad = s_blur * 2 + 12
            padded = Image.new("RGBA", (result.width + pad * 2, result.height + pad * 2), (0, 0, 0, 0))
            sr, sg, sb = _parse_hex_rgb(shadow_color, default=(0, 0, 0))
            sh_layer = Image.new("RGBA", padded.size, (sr, sg, sb, 0))

            alpha_padded = Image.new("L", padded.size, 0)
            alpha_padded.paste(a_ch, (pad + int(s_blur * 0.35), pad + int(s_blur * 0.45)))
            alpha_blurred = alpha_padded.filter(ImageFilter.GaussianBlur(radius=float(s_blur)))
            sh_alpha = (np.array(alpha_blurred, dtype=np.float32) * 0.72).astype(np.uint8)
            sh_layer.putalpha(Image.fromarray(sh_alpha))

            padded = Image.alpha_composite(padded, sh_layer)
            padded.alpha_composite(result, (pad, pad))
            result = padded

        result.save(output_path, "PNG")
        cls._save_to_cache(cache_key, output_path)
        logger.info(f"[PS_ADJUST] Photoshop katman ayarları uygulandı: {output_path}")
        return output_path
