"""OtoEdit AI Background Removal & Image Sticker Studio.
rembg (u2net / isnet) ve OpenCV destekli arka plan kaldırma, beyaz sticker konturu,
chroma keying ve şekil maskeleme servisi.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw
from typing import Optional, Tuple
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


class BackgroundRemoverService:
    """Yapay Zeka Destekli Arka Plan Kaldırma ve Görsel Düzenleme Servisi."""

    @classmethod
    def _get_rembg_session(cls):
        global _REMBG_SESSION
        if REMBG_AVAILABLE and _REMBG_SESSION is None:
            try:
                # Hafif ve hızlı u2netp veya u2net modeli
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

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if REMBG_AVAILABLE:
            try:
                session = cls._get_rembg_session()
                with open(image_path, "rb") as f_in:
                    input_bytes = f_in.read()
                
                output_bytes = remove(input_bytes, session=session) if session else remove(input_bytes)
                with open(output_path, "wb") as f_out:
                    f_out.write(output_bytes)
                
                logger.info(f"[BG_REMOVE:AI] rembg ile başarıyla arka plan kaldırıldı: {output_path}")
                return output_path
            except Exception as ex:
                logger.error(f"[BG_REMOVE:AI_FAIL] rembg başarısız oldu, OpenCV fallback'e geçiliyor: {ex}")

        # Fallback: OpenCV GrabCut tabanlı arka plan çıkarma
        return cls._fallback_grabcut_remove(image_path, output_path)

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

        # Çerçevenin %10 içinden dikdörtgen belirle
        rect = (int(w * 0.08), int(h * 0.08), int(w * 0.84), int(h * 0.84))
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

        # Alpha kanalını oluştur
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        alpha = (mask2 * 255).astype(np.uint8)
        
        # Kenarları yumuşat (feathering)
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
        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_sticker.png")

        src = Image.open(image_path).convert("RGBA")
        
        # Kenarlarda kontur taşmasın diye padding ekle
        pad = outline_width * 3 + 20
        padded = Image.new("RGBA", (src.width + pad * 2, src.height + pad * 2), (0, 0, 0, 0))
        padded.paste(src, (pad, pad), src)

        alpha = np.array(padded.split()[3])

        # Kontur rengini parse et (RGB)
        clean_hex = outline_color_hex.lstrip("#")
        if len(clean_hex) == 6:
            r = int(clean_hex[0:2], 16)
            g = int(clean_hex[2:4], 16)
            b = int(clean_hex[4:6], 16)
        else:
            r, g, b = 255, 255, 255

        # Morfolojik genişletme (Dilation) ile kontur maskesi oluştur
        kernel_size = outline_width * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated_alpha = cv2.dilate(alpha, kernel, iterations=1)
        dilated_alpha = cv2.GaussianBlur(dilated_alpha, (3, 3), 0)

        # Kontur katmanı
        outline_layer = Image.new("RGBA", padded.size, (r, g, b, 0))
        outline_layer.putalpha(Image.fromarray(dilated_alpha))

        # Sonuç kompozisyonu
        result = Image.new("RGBA", padded.size, (0, 0, 0, 0))

        if shadow:
            # Hafif derinlik gölgesi
            shadow_alpha = cv2.dilate(alpha, kernel, iterations=1)
            shadow_img = Image.new("RGBA", padded.size, (0, 0, 0, 120))
            shadow_img.putalpha(Image.fromarray(shadow_alpha))
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(outline_width * 0.8))
            result.alpha_composite(shadow_img, (0, int(outline_width * 0.4)))

        result.alpha_composite(outline_layer)
        result.alpha_composite(padded)

        # Fazla boşlukları kırp
        bbox = result.getbbox()
        if bbox:
            result = result.crop(bbox)

        result.save(output_path, "PNG")
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

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Görsel açılamadı: {image_path}")

        # Hex rengini BGR'ye çevir
        hex_clean = key_color_hex.lstrip("#")
        kr = int(hex_clean[0:2], 16)
        kg = int(hex_clean[2:4], 16)
        kb = int(hex_clean[4:6], 16)
        key_bgr = np.array([kb, kg, kr], dtype=np.uint8)

        # Renk farkını normalize et (LAB uzayı renk ayrımı için en doğrusudur)
        img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        key_lab = cv2.cvtColor(np.uint8([[key_bgr]]), cv2.COLOR_BGR2LAB)[0][0]

        diff = np.linalg.norm(img_lab.astype(np.float32) - key_lab.astype(np.float32), axis=2)
        max_dist = 255.0

        threshold = similarity * max_dist
        softness = max(1.0, smoothness * max_dist)

        alpha = np.clip((diff - threshold) / softness, 0.0, 1.0) * 255.0
        alpha = alpha.astype(np.uint8)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgba = np.dstack((img_rgb, alpha))
        pil_img = Image.fromarray(rgba)
        pil_img.save(output_path, "PNG")
        logger.info(f"[CHROMA_KEY] Chroma key uygulandı: {key_color_hex} -> {output_path}")
        return output_path

    @classmethod
    def apply_shape_mask(
        cls,
        image_path: str,
        output_path: Optional[str] = None,
        shape: str = "circle",
        corner_radius: int = 32
    ) -> str:
        """
        Görseli dairesel avatar veya yuvarlatılmış kart maskesi haline getirir.
        """
        if not output_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}_{shape}.png")

        src = Image.open(image_path).convert("RGBA")
        w, h = src.size

        # 4x süper-örnekleme ile kusursuz antialiased kenar maskesi
        scale = 4
        mask = Image.new("L", (w * scale, h * scale), 0)
        draw = ImageDraw.Draw(mask)

        if shape == "circle":
            min_dim = min(w, h) * scale
            left = (w * scale - min_dim) // 2
            top = (h * scale - min_dim) // 2
            draw.ellipse((left, top, left + min_dim, top + min_dim), fill=255)
        elif shape == "rounded":
            draw.rounded_rectangle((0, 0, w * scale, h * scale), radius=corner_radius * scale, fill=255)
        else:
            draw.rectangle((0, 0, w * scale, h * scale), fill=255)

        mask = mask.resize((w, h), Image.Resampling.LANCZOS)
        
        # Orijinal alpha ile birleştir
        orig_alpha = src.split()[3]
        final_alpha = ImageOps.invert(ImageOps.invert(orig_alpha))
        # Maskeleri çarp
        mask_np = np.array(mask).astype(np.float32) / 255.0
        orig_np = np.array(orig_alpha).astype(np.float32) / 255.0
        combined_alpha = Image.fromarray((mask_np * orig_np * 255.0).astype(np.uint8))

        src.putalpha(combined_alpha)
        src.save(output_path, "PNG")
        logger.info(f"[SHAPE_MASK] Şekil maskesi uygulandı: {shape} -> {output_path}")
        return output_path
