"""OtoEdit Pillow Graphics Engine.
CapCut, Premiere Pro ve Photoshop tarzı şık kutucuklu (pill, rounded badge, highlight-marker, none),
çift konturlu (double stroke), neon ışıltılı (outer glow), lineer/radyal gradyan dolgulu,
dairesel yay (curved arc) ve 3D perspektif dönüşümlü metin katmanlarını
SHA-256 içerik adresli önbellekleme (zero-lag caching) ve 2x süper-örnekleme ile
yüksek çözünürlüklü şeffaf PNG olarak üretir.
"""
import os
import re
import math
import json
import shutil
import hashlib
import tempfile
import urllib.request
from typing import Optional, Tuple, Dict, Any, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.logger import get_logger

logger = get_logger(__name__)

_ASSETS_FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts"
)

# 35+ Profesyonel Font Eşleştirmesi (Linux, Yerel Assets ve Windows Fallback Destekli)
FONT_PATHS: Dict[str, str] = {
    "Montserrat": "/usr/share/fonts/truetype/custom/Montserrat.ttf",
    "Montserrat-Bold": "/usr/share/fonts/truetype/custom/Montserrat.ttf",
    "Montserrat-Black": "/usr/share/fonts/truetype/custom/Montserrat.ttf",
    "Poppins": "/usr/share/fonts/truetype/custom/Poppins-Bold.ttf",
    "Poppins-Bold": "/usr/share/fonts/truetype/custom/Poppins-Bold.ttf",
    "Poppins-Regular": "/usr/share/fonts/truetype/custom/Poppins-Regular.ttf",
    "Bebas Neue": "/usr/share/fonts/truetype/custom/BebasNeue.ttf",
    "BebasNeue": "/usr/share/fonts/truetype/custom/BebasNeue.ttf",
    "Anton": "/usr/share/fonts/truetype/custom/Anton.ttf",
    "Cinzel": "/usr/share/fonts/truetype/custom/Cinzel.ttf",
    "Outfit": "/usr/share/fonts/truetype/custom/Outfit.ttf",
    "Inter": "/usr/share/fonts/truetype/custom/Inter.ttf",
    "Inter-Bold": "/usr/share/fonts/truetype/custom/Inter.ttf",
    "Playfair Display": "/usr/share/fonts/truetype/custom/PlayfairDisplay-Bold.ttf",
    "Orbitron": "/usr/share/fonts/truetype/custom/Orbitron-Bold.ttf",
    "Pacifico": "/usr/share/fonts/truetype/custom/Pacifico-Regular.ttf",
    "Permanent Marker": "/usr/share/fonts/truetype/custom/PermanentMarker-Regular.ttf",
    "Caveat": "/usr/share/fonts/truetype/custom/Caveat-Bold.ttf",
    "Bangers": "/usr/share/fonts/truetype/custom/Bangers-Regular.ttf",
    "Righteous": "/usr/share/fonts/truetype/custom/Righteous-Regular.ttf",
    "JetBrains Mono": "/usr/share/fonts/truetype/custom/JetBrainsMono-Bold.ttf",
    "Space Grotesk": "/usr/share/fonts/truetype/custom/SpaceGrotesk-Bold.ttf",
    "Syne": "/usr/share/fonts/truetype/custom/Syne-ExtraBold.ttf",
    "Rubik Mono One": "/usr/share/fonts/truetype/custom/RubikMonoOne-Regular.ttf",
    "Press Start 2P": "/usr/share/fonts/truetype/custom/PressStart2P-Regular.ttf",
    "Oswald": "/usr/share/fonts/truetype/custom/Oswald-Bold.ttf",
    "Raleway": "/usr/share/fonts/truetype/custom/Raleway-ExtraBold.ttf",
    "Merriweather": "/usr/share/fonts/truetype/custom/Merriweather-Bold.ttf",
    "Lora": "/usr/share/fonts/truetype/custom/Lora-Bold.ttf",
    "Abril Fatface": "/usr/share/fonts/truetype/custom/AbrilFatface-Regular.ttf",
    "Comfortaa": "/usr/share/fonts/truetype/custom/Comfortaa-Bold.ttf",
    "Fredoka One": "/usr/share/fonts/truetype/custom/FredokaOne-Regular.ttf",
    "Lobster": "/usr/share/fonts/truetype/custom/Lobster-Regular.ttf",
    "Satisfy": "/usr/share/fonts/truetype/custom/Satisfy-Regular.ttf",
    "Titan One": "/usr/share/fonts/truetype/custom/TitanOne-Regular.ttf",
    "Creepster": "/usr/share/fonts/truetype/custom/Creepster-Regular.ttf",
    "Black Ops One": "/usr/share/fonts/truetype/custom/BlackOpsOne-Regular.ttf",
    "Russo One": "/usr/share/fonts/truetype/custom/RussoOne-Regular.ttf",
    "Chakra Petch": "/usr/share/fonts/truetype/custom/ChakraPetch-Bold.ttf",
    "Cormorant Garamond": "/usr/share/fonts/truetype/custom/CormorantGaramond-Bold.ttf",
    "Fira Code": "/usr/share/fonts/truetype/custom/FiraCode-Bold.ttf",
    "Roboto": "/usr/share/fonts/truetype/custom/Roboto-Bold.ttf",
    "Open Sans": "/usr/share/fonts/truetype/custom/OpenSans-ExtraBold.ttf",
    "Lato": "/usr/share/fonts/truetype/custom/Lato-Black.ttf",
    "Impact": "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "Arial": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "DejaVuSans": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

# Yerel assets/fonts eşleştirmeleri (Yalnızca fiziksel olarak mevcut 7 yerel font ailesi)
_LOCAL_ASSET_MAP: Dict[str, str] = {
    "montserrat": "Montserrat.ttf",
    "poppins": "Poppins-Bold.ttf",
    "poppins-regular": "Poppins-Regular.ttf",
    "bebas neue": "BebasNeue.ttf",
    "bebas": "BebasNeue.ttf",
    "anton": "Anton.ttf",
    "cinzel": "Cinzel.ttf",
    "outfit": "Outfit.ttf",
    "inter": "Inter.ttf",
}


def hex_to_rgba(hex_str: Optional[str], default: Tuple[int, int, int, int] = (255, 255, 255, 255)) -> Tuple[int, int, int, int]:
    """Hex (#RRGGBB, #RGB veya #RRGGBBAA) ya da rgba(...) metnini (R, G, B, A) tuple'a çevirir."""
    if not hex_str or not isinstance(hex_str, str):
        return default

    clean = hex_str.strip()
    if clean.lower() in ("transparent", "none"):
        return (0, 0, 0, 0)

    if clean.startswith("rgba"):
        match = re.search(r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d\.]+)\s*\)", clean)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            raw_a = float(match.group(4))
            a = int(raw_a * 255) if raw_a <= 1.0 else int(raw_a)
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), max(0, min(255, a)))
    elif clean.startswith("rgb"):
        match = re.search(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", clean)
        if match:
            return (
                max(0, min(255, int(match.group(1)))),
                max(0, min(255, int(match.group(2)))),
                max(0, min(255, int(match.group(3)))),
                255,
            )

    clean = clean.lstrip("#")
    try:
        if len(clean) == 3:
            r = int(clean[0] * 2, 16)
            g = int(clean[1] * 2, 16)
            b = int(clean[2] * 2, 16)
            return (r, g, b, 255)
        elif len(clean) == 6:
            return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), 255)
        elif len(clean) == 8:
            return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), int(clean[6:8], 16))
    except ValueError:
        pass
    return default


class PillowGraphicsEngine:
    """CapCut, Premiere Pro ve Photoshop Stili Tipografi ve Rozet Render Motoru."""

    _FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
    _MEM_BADGE_CACHE: Dict[str, bytes] = {}
    _FAILED_FONT_SLUGS: set = set()
    _NETWORK_UNREACHABLE: bool = False

    @classmethod
    def _ensure_google_font_ttf(cls, font_family: str) -> Optional[str]:
        """
        İstenen Google Font ailesinin .ttf dosyasını yerel assets/fonts/ veya /tmp/otoedit_fonts/
        içinde arar; yoksa Google Webfonts Helper API veya Google Fonts GitHub deposundan
        (3.5s zaman aşımı ile) indirip önbelleğe kaydeder. Çevrimdışıysa None döner.
        """
        if not font_family:
            return None

        clean_family = font_family.split(",")[0].strip().replace("'", "").replace('"', "")
        base_family = re.sub(
            r"-(Bold|Regular|Black|ExtraBold|SemiBold|Medium|Light|Italic)$",
            "",
            clean_family,
            flags=re.IGNORECASE,
        ).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", base_family.lower()).strip("-")
        if not slug:
            return None

        slug_no_dash = slug.replace("-", "")
        family_no_spaces = re.sub(r"[^A-Za-z0-9]", "", base_family)

        tmp_font_dir = os.path.join(tempfile.gettempdir(), "otoedit_fonts")
        search_dirs = [_ASSETS_FONT_DIR, tmp_font_dir, "/tmp/otoedit_fonts"]

        # 1. Yerel diskte mevcut mu kontrol et
        for d in search_dirs:
            if not d or not os.path.isdir(d):
                continue
            for fname in (f"{slug}.ttf", f"{family_no_spaces}.ttf", f"{family_no_spaces}-Bold.ttf", f"{family_no_spaces}-Regular.ttf"):
                candidate = os.path.join(d, fname)
                if os.path.isfile(candidate) and os.path.getsize(candidate) > 1024:
                    return candidate

        if slug in cls._FAILED_FONT_SLUGS or cls._NETWORK_UNREACHABLE:
            return None

        target_dir = _ASSETS_FONT_DIR if os.path.isdir(_ASSETS_FONT_DIR) else tmp_font_dir
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception:
            target_dir = tmp_font_dir
            os.makedirs(target_dir, exist_ok=True)

        target_path = os.path.join(target_dir, f"{slug}.ttf")

        # 2. Birincil Yöntem: Resmi Google Fonts CSS2 API üzerinden tam glifli (Türkçe latin-ext destekli) .ttf indirme
        encoded_fam = urllib.parse.quote(base_family).replace("%20", "+")
        for weight_suffix in (":wght@400;700;900", ":wght@700", ":wght@400", ""):
            css_url = f"https://fonts.googleapis.com/css2?family={encoded_fam}{weight_suffix}"
            try:
                req = urllib.request.Request(css_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    css_text = resp.read().decode("utf-8", errors="ignore")
                    ttf_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.(?:ttf|otf))\)", css_text)
                    if ttf_urls:
                        chosen_ttf_url = ttf_urls[-1]
                        ttf_req = urllib.request.Request(chosen_ttf_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(ttf_req, timeout=3.5) as ttf_resp:
                            ttf_bytes = ttf_resp.read()
                            if ttf_bytes and len(ttf_bytes) > 1024 and ttf_bytes[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
                                with open(target_path, "wb") as f_out:
                                    f_out.write(ttf_bytes)
                                logger.info(f"⬇️ Google Font otomatik indirildi (Google CSS2 TTF): {clean_family} -> {target_path}")
                                return target_path
            except urllib.error.HTTPError:
                continue
            except urllib.error.URLError:
                cls._NETWORK_UNREACHABLE = True
                break
            except Exception:
                continue

        # 3. Yedek: Google Fonts GitHub Raw URL'lerinden doğrudan .ttf indirmeyi dene
        raw_urls = [
            f"https://raw.githubusercontent.com/google/fonts/main/ofl/{slug_no_dash}/{family_no_spaces}-Bold.ttf",
            f"https://raw.githubusercontent.com/google/fonts/main/ofl/{slug_no_dash}/{family_no_spaces}-Regular.ttf",
            f"https://raw.githubusercontent.com/google/fonts/main/apache/{slug_no_dash}/{family_no_spaces}-Bold.ttf",
            f"https://raw.githubusercontent.com/google/fonts/main/apache/{slug_no_dash}/{family_no_spaces}-Regular.ttf",
        ]
        for url in raw_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "OtoEdit-FontLoader/1.0"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    data = resp.read()
                    if data and len(data) > 1024 and data[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
                        with open(target_path, "wb") as f_out:
                            f_out.write(data)
                        logger.info(f"⬇️ Google Font otomatik indirildi (GitHub): {clean_family} -> {target_path}")
                        return target_path
            except urllib.error.HTTPError:
                continue
            except urllib.error.URLError:
                cls._NETWORK_UNREACHABLE = True
                break
            except Exception:
                continue

        # 3. Google Webfonts Helper API yedek kontrolü
        if not cls._NETWORK_UNREACHABLE:
            gwfh_url = f"https://gwfh.mranftl.com/api/fonts/{slug}?subsets=latin,latin-ext"
            try:
                req = urllib.request.Request(gwfh_url, headers={"User-Agent": "OtoEdit-FontLoader/1.0"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    meta = json.loads(resp.read().decode("utf-8"))
                    variants = meta.get("variants") or []
                    ttf_url = None
                    for pref in ("700", "regular", "800", "600"):
                        for v in variants:
                            if v.get("id") == pref and v.get("ttf"):
                                ttf_url = v["ttf"]
                                break
                        if ttf_url:
                            break
                    if not ttf_url and variants:
                        ttf_url = variants[0].get("ttf")
                    if ttf_url:
                        with urllib.request.urlopen(ttf_url, timeout=3.5) as ttf_resp:
                            ttf_bytes = ttf_resp.read()
                            if ttf_bytes and len(ttf_bytes) > 1024:
                                with open(target_path, "wb") as f_out:
                                    f_out.write(ttf_bytes)
                                logger.info(f"⬇️ Google Font otomatik indirildi (GWFH): {clean_family} -> {target_path}")
                                return target_path
            except urllib.error.URLError:
                cls._NETWORK_UNREACHABLE = True
            except Exception as ex:
                logger.debug(f"Google Font indirilemedi ({clean_family}): {ex}")

        cls._FAILED_FONT_SLUGS.add(slug)
        return None

    @classmethod
    def get_font(cls, font_name: Optional[str] = "Inter", font_size: int = 48) -> ImageFont.FreeTypeFont:
        """Sistemdeki, yerel assets klasöründeki veya Google Fonts'tan indirilen TTF fontlarını yükler."""
        clean_name = (font_name or "Inter").split(",")[0].strip().replace("'", "").replace('"', "")
        cache_key = (clean_name.lower(), int(font_size))
        if cache_key in cls._FONT_CACHE:
            return cls._FONT_CACHE[cache_key]

        candidates: List[str] = []

        # 1. Tam eşleşme
        if clean_name in FONT_PATHS:
            candidates.append(FONT_PATHS[clean_name])

        # 2. Kısmi eşleşme (FONT_PATHS)
        lower_name = clean_name.lower()
        for k, p in FONT_PATHS.items():
            if lower_name in k.lower() or k.lower() in lower_name:
                candidates.append(p)

        # 3. Yerel assets/fonts dizini kontrolü (7 gerçek yerel font)
        if os.path.isdir(_ASSETS_FONT_DIR):
            direct_local = os.path.join(_ASSETS_FONT_DIR, f"{clean_name.replace(' ', '')}.ttf")
            candidates.append(direct_local)
            for key_sub, filename in _LOCAL_ASSET_MAP.items():
                if key_sub in lower_name:
                    candidates.append(os.path.join(_ASSETS_FONT_DIR, filename))

        # Önce doğrudan eşleşen yerel/sistem adaylarını dene
        for path in candidates:
            if path and os.path.isfile(path):
                try:
                    loaded = ImageFont.truetype(path, font_size)
                    cls._FONT_CACHE[cache_key] = loaded
                    return loaded
                except Exception:
                    continue

        # 4. Yerel olarak bulunamadıysa Google Fonts'tan otomatik .ttf indirmeyi dene
        downloaded_path = cls._ensure_google_font_ttf(clean_name)
        if downloaded_path and os.path.isfile(downloaded_path):
            try:
                loaded = ImageFont.truetype(downloaded_path, font_size)
                cls._FONT_CACHE[cache_key] = loaded
                return loaded
            except Exception:
                pass

        # 5. Genel yerel ve sistem (Linux / Windows) fallback'leri
        fallback_candidates = [
            os.path.join(_ASSETS_FONT_DIR, "Montserrat.ttf"),
            os.path.join(_ASSETS_FONT_DIR, "Inter.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

        for path in fallback_candidates:
            if path and os.path.isfile(path):
                try:
                    loaded = ImageFont.truetype(path, font_size)
                    cls._FONT_CACHE[cache_key] = loaded
                    return loaded
                except Exception:
                    continue

        logger.warning(f"Font yüklenemedi ({clean_name}), varsayılan PIL fontu kullanılacak")
        return ImageFont.load_default()

    @classmethod
    def _compute_cache_key(cls, params: Dict[str, Any]) -> str:
        """Verilen tüm görsel parametrelerden deterministik SHA-256 anahtarı üretir."""
        serialized = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def _generate_gradient_rgba(
        cls,
        width: int,
        height: int,
        color_start: Tuple[int, int, int, int],
        color_end: Tuple[int, int, int, int],
        fill_type: str = "gradient",
        angle_deg: float = 45.0,
        bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> np.ndarray:
        """NumPy ile pürüzsüz lineer veya radyal gradyan RGBA matrisi (H, W, 4) üretir."""
        bx1, by1, bx2, by2 = bbox if bbox else (0, 0, width, height)
        bw = max(1, bx2 - bx1)
        bh = max(1, by2 - by1)

        y_indices, x_indices = np.mgrid[0:height, 0:width].astype(np.float32)
        nx = (x_indices - bx1) / float(bw) - 0.5
        ny = (y_indices - by1) / float(bh) - 0.5

        if fill_type == "radial":
            dist = np.sqrt(nx * nx + ny * ny) * 2.0
            t = np.clip(dist, 0.0, 1.0)
        else:
            rad = math.radians(float(angle_deg))
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            proj = nx * cos_a + ny * sin_a
            max_span = max(0.001, (abs(cos_a) + abs(sin_a)) * 0.5)
            t = np.clip((proj / (2.0 * max_span)) + 0.5, 0.0, 1.0)

        t_3d = t[:, :, np.newaxis]
        c1 = np.array(color_start, dtype=np.float32).reshape((1, 1, 4))
        c2 = np.array(color_end, dtype=np.float32).reshape((1, 1, 4))
        grad = np.clip(c1 * (1.0 - t_3d) + c2 * t_3d, 0, 255).astype(np.uint8)
        return grad

    @classmethod
    def _apply_3d_perspective(
        cls,
        canvas: Image.Image,
        rotate_x: float = 0.0,
        rotate_y: float = 0.0,
        skew_x: float = 0.0,
        skew_y: float = 0.0
    ) -> Image.Image:
        """3D X/Y ekseni perspektif döndürme ve 2D eğim (skew) dönüşümünü uygular."""
        if (
            abs(rotate_x) <= 0.5
            and abs(rotate_y) <= 0.5
            and abs(skew_x) <= 0.5
            and abs(skew_y) <= 0.5
        ):
            return canvas

        bbox = canvas.getbbox()
        if not bbox:
            return canvas

        cropped = canvas.crop(bbox)
        w, h = cropped.size
        if w < 4 or h < 4:
            return canvas

        # 4 köşe noktası (merkez orijinli)
        hw, hh = w / 2.0, h / 2.0
        corners = np.array([
            [-hw, -hh, 0.0],
            [hw, -hh, 0.0],
            [hw, hh, 0.0],
            [-hw, hh, 0.0],
        ], dtype=np.float32)

        # 2D Skew
        tan_sx = math.tan(math.radians(max(-60.0, min(60.0, float(skew_x)))))
        tan_sy = math.tan(math.radians(max(-60.0, min(60.0, float(skew_y)))))
        for i in range(4):
            x0, y0 = corners[i, 0], corners[i, 1]
            corners[i, 0] = x0 + y0 * tan_sx
            corners[i, 1] = y0 + x0 * tan_sy

        # 3D Rotation (X ve Y eksenleri)
        rx = math.radians(max(-75.0, min(75.0, float(rotate_x))))
        ry = math.radians(max(-75.0, min(75.0, float(rotate_y))))

        cos_x, sin_x = math.cos(rx), math.sin(rx)
        cos_y, sin_y = math.cos(ry), math.sin(ry)

        focal = max(w, h) * 1.6
        projected = np.zeros((4, 2), dtype=np.float32)

        for i in range(4):
            x, y, z = corners[i]
            # X ekseni etrafında döndür
            y1 = y * cos_x - z * sin_x
            z1 = y * sin_x + z * cos_x
            x1 = x
            # Y ekseni etrafında döndür
            x2 = x1 * cos_y + z1 * sin_y
            y2 = y1
            z2 = -x1 * sin_y + z1 * cos_y

            denom = max(focal * 0.2, focal + z2)
            scale = focal / denom
            projected[i, 0] = hw + x2 * scale
            projected[i, 1] = hh + y2 * scale

        min_x = float(np.min(projected[:, 0]))
        max_x = float(np.max(projected[:, 0]))
        min_y = float(np.min(projected[:, 1]))
        max_y = float(np.max(projected[:, 1]))

        pad = 12
        out_w = max(4, int(math.ceil(max_x - min_x)) + pad * 2)
        out_h = max(4, int(math.ceil(max_y - min_y)) + pad * 2)

        dst_pts = projected - np.array([[min_x - pad, min_y - pad]], dtype=np.float32)
        src_pts = np.array([
            [0.0, 0.0],
            [float(w), 0.0],
            [float(w), float(h)],
            [0.0, float(h)],
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        src_np = np.array(cropped)
        warped_np = cv2.warpPerspective(
            src_np,
            matrix,
            (out_w, out_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )
        return Image.fromarray(warped_np, "RGBA")

    @classmethod
    def _render_curved_arc_layers(
        cls,
        text: str,
        font: ImageFont.FreeTypeFont,
        curve_bend: float,
        ss_font_size: int,
        ss_stroke_width: int,
        ss_outer_stroke_width: int,
        ss_letter_spacing: int,
        margin: int
    ) -> Tuple[Image.Image, Image.Image, Image.Image, Tuple[int, int, int, int]]:
        """
        Metni dairesel bir yay (arc) boyunca karakter karakter döndürerek:
        (outer_stroke_mask, primary_stroke_mask, glyph_fill_mask, text_bbox) üretir.
        """
        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)

        full_text = text.replace("\n", " ")
        total_pad_stroke = ss_stroke_width + ss_outer_stroke_width

        char_infos = []
        total_arc_len = 0.0
        for idx, ch in enumerate(full_text):
            bbox = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=0)
            adv_w = max(int(ss_font_size * 0.28), (bbox[2] - bbox[0]))
            step_w = adv_w + (ss_letter_spacing if idx < len(full_text) - 1 else 0)
            char_infos.append((ch, adv_w, step_w))
            total_arc_len += step_w

        total_arc_len = max(total_arc_len, float(ss_font_size))
        bend_clamped = max(-100.0, min(100.0, float(curve_bend)))
        sweep_angle = max(0.15, (abs(bend_clamped) / 100.0) * math.pi * 0.9)
        radius = max(total_arc_len / sweep_angle, ss_font_size * 1.25)

        char_box_dim = int(ss_font_size * 2.4 + total_pad_stroke * 4)
        canvas_w = int(max(total_arc_len, radius * 2.0) + char_box_dim * 2 + margin * 2)
        arc_sagitta = radius * (1.0 - math.cos(sweep_angle / 2.0))
        canvas_h = int(arc_sagitta + char_box_dim * 2 + margin * 2)

        outer_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        stroke_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        glyph_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        center_x = canvas_w / 2.0
        base_y = (margin + char_box_dim) if bend_clamped > 0 else (canvas_h - margin - char_box_dim)

        cursor_s = -total_arc_len / 2.0
        for ch, adv_w, step_w in char_infos:
            char_center_s = cursor_s + (adv_w / 2.0)
            cursor_s += step_w
            if not ch.strip():
                continue

            theta = char_center_s / radius
            if bend_clamped > 0:
                cx = center_x + radius * math.sin(theta)
                cy = base_y + radius * (1.0 - math.cos(theta))
                rot_deg = -math.degrees(theta)
            else:
                cx = center_x + radius * math.sin(theta)
                cy = base_y - radius * (1.0 - math.cos(theta))
                rot_deg = math.degrees(theta)

            stamp_center = char_box_dim // 2

            # 1. Outer Stroke Stamp
            if ss_outer_stroke_width > 0:
                ch_outer = Image.new("RGBA", (char_box_dim, char_box_dim), (0, 0, 0, 0))
                d_out = ImageDraw.Draw(ch_outer)
                d_out.text(
                    (stamp_center, stamp_center),
                    ch,
                    font=font,
                    anchor="mm",
                    fill=(255, 255, 255, 255),
                    stroke_width=total_pad_stroke,
                    stroke_fill=(255, 255, 255, 255),
                )
                ch_outer_rot = ch_outer.rotate(rot_deg, resample=Image.Resampling.BICUBIC, expand=False)
                outer_mask.alpha_composite(
                    ch_outer_rot, (int(round(cx - stamp_center)), int(round(cy - stamp_center)))
                )

            # 2. Primary Stroke Stamp
            if ss_stroke_width > 0:
                ch_stroke = Image.new("RGBA", (char_box_dim, char_box_dim), (0, 0, 0, 0))
                d_str = ImageDraw.Draw(ch_stroke)
                d_str.text(
                    (stamp_center, stamp_center),
                    ch,
                    font=font,
                    anchor="mm",
                    fill=(255, 255, 255, 255),
                    stroke_width=ss_stroke_width,
                    stroke_fill=(255, 255, 255, 255),
                )
                ch_stroke_rot = ch_stroke.rotate(rot_deg, resample=Image.Resampling.BICUBIC, expand=False)
                stroke_mask.alpha_composite(
                    ch_stroke_rot, (int(round(cx - stamp_center)), int(round(cy - stamp_center)))
                )

            # 3. Interior Glyph Stamp
            ch_glyph = Image.new("RGBA", (char_box_dim, char_box_dim), (0, 0, 0, 0))
            d_gly = ImageDraw.Draw(ch_glyph)
            d_gly.text(
                (stamp_center, stamp_center),
                ch,
                font=font,
                anchor="mm",
                fill=(255, 255, 255, 255),
                stroke_width=0,
            )
            ch_glyph_rot = ch_glyph.rotate(rot_deg, resample=Image.Resampling.BICUBIC, expand=False)
            glyph_mask.alpha_composite(
                ch_glyph_rot, (int(round(cx - stamp_center)), int(round(cy - stamp_center)))
            )

        text_bbox = glyph_mask.getbbox() or (0, 0, canvas_w, canvas_h)
        return outer_mask, stroke_mask, glyph_mask, text_bbox

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
        box_style: str = "pill",  # "pill", "rounded", "badge", "highlight-marker", "none"
        box_bg_color: str = "rgba(0, 0, 0, 0.75)",
        box_padding: int = 16,
        border_radius: int = 24,
        shadow: bool = True,
        shadow_blur: int = 4,
        all_caps: bool = False,
        letter_spacing: int = 0,
        # Photoshop / CapCut Pro Tipografi Özellikleri
        fill_type: str = "solid",  # "solid", "gradient", "radial"
        gradient_start: Optional[str] = None,
        gradient_end: Optional[str] = None,
        gradient_angle: float = 45.0,
        outer_stroke_width: int = 0,
        outer_stroke_color: Optional[str] = None,
        glow_enabled: bool = False,
        glow_color: Optional[str] = None,
        glow_radius: int = 0,
        shadow_distance: float = 4.0,
        shadow_angle: float = 90.0,
        curve_bend: float = 0.0,
        rotate_x: float = 0.0,
        rotate_y: float = 0.0,
        skew_x: float = 0.0,
        skew_y: float = 0.0,
        **kwargs
    ) -> str:
        """
        Metin katmanını kutu (pill/badge/highlight-marker/none), çift kontur, neon ışıltı,
        lineer/radyal gradyan dolgu, yönlü gölge, dairesel yay (curve_bend) ve 3D perspektif
        ile 2x süper-örnekleme kullanarak antialiased şeffaf PNG olarak üretir.
        Aynı parametrelerle çağrıldığında SHA-256 önbellekten <1ms içinde döner.
        """
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        # CamelCase kwargs uyumluluğu
        effective_font = font_family or kwargs.get("fontFamily") or font_name or "Montserrat"
        box_style = str(kwargs.get("boxStyle") or box_style or "none").lower().strip()
        box_bg_color = kwargs.get("boxBgColor") or kwargs.get("backgroundColor") or box_bg_color
        fill_type = str(kwargs.get("fillType") or fill_type or "solid").lower().strip()
        if kwargs.get("gradientEnabled") and fill_type == "solid":
            fill_type = "gradient"
        gradient_start = kwargs.get("gradientStart") or gradient_start or text_color
        gradient_end = kwargs.get("gradientEnd") or gradient_end or "#7928CA"
        gradient_angle = float(kwargs.get("gradientAngle") if kwargs.get("gradientAngle") is not None else gradient_angle)

        outer_stroke_width = int(float(kwargs.get("outerStrokeWidth") if kwargs.get("outerStrokeWidth") is not None else outer_stroke_width))
        outer_stroke_color = kwargs.get("outerStrokeColor") or outer_stroke_color or "#000000"

        glow_enabled = bool(kwargs.get("glowEnabled") if kwargs.get("glowEnabled") is not None else glow_enabled)
        glow_color = kwargs.get("glowColor") or glow_color or text_color
        glow_radius = int(float(kwargs.get("glowRadius") if kwargs.get("glowRadius") is not None else (glow_radius or (12 if glow_enabled else 0))))
        if glow_radius > 0:
            glow_enabled = True

        shadow_distance = float(kwargs.get("shadowDistance") if kwargs.get("shadowDistance") is not None else shadow_distance)
        shadow_angle = float(kwargs.get("shadowAngle") if kwargs.get("shadowAngle") is not None else shadow_angle)
        shadow_blur = int(float(kwargs.get("shadowBlur") if kwargs.get("shadowBlur") is not None else shadow_blur))
        shadow_color = kwargs.get("shadowColor") or shadow_color

        curve_bend = float(kwargs.get("curveBend") if kwargs.get("curveBend") is not None else curve_bend)
        rotate_x = float(kwargs.get("rotateX") if kwargs.get("rotateX") is not None else rotate_x)
        rotate_y = float(kwargs.get("rotateY") if kwargs.get("rotateY") is not None else rotate_y)
        skew_x = float(kwargs.get("skewX") if kwargs.get("skewX") is not None else skew_x)
        skew_y = float(kwargs.get("skewY") if kwargs.get("skewY") is not None else skew_y)

        # 0. SHA-256 Content-Addressed Caching (Zero-Lag)
        cache_Signature = {
            "text": text,
            "font": effective_font,
            "font_size": int(font_size),
            "text_color": text_color,
            "stroke_color": stroke_color,
            "stroke_width": int(stroke_width),
            "shadow_color": shadow_color,
            "box_style": box_style,
            "box_bg_color": box_bg_color,
            "box_padding": int(box_padding),
            "border_radius": int(border_radius),
            "shadow": bool(shadow),
            "shadow_blur": int(shadow_blur),
            "shadow_distance": round(shadow_distance, 2),
            "shadow_angle": round(shadow_angle, 2),
            "all_caps": bool(all_caps),
            "letter_spacing": int(letter_spacing),
            "fill_type": fill_type,
            "gradient_start": gradient_start,
            "gradient_end": gradient_end,
            "gradient_angle": round(gradient_angle, 2),
            "outer_stroke_width": outer_stroke_width,
            "outer_stroke_color": outer_stroke_color,
            "glow_enabled": glow_enabled,
            "glow_color": glow_color,
            "glow_radius": glow_radius,
            "curve_bend": round(curve_bend, 2),
            "rotate_x": round(rotate_x, 2),
            "rotate_y": round(rotate_y, 2),
            "skew_x": round(skew_x, 2),
            "skew_y": round(skew_y, 2),
        }
        cache_key = cls._compute_cache_key(cache_Signature)

        # Bellek önbelleği kontrolü (< 0.5ms)
        if cache_key in cls._MEM_BADGE_CACHE:
            with open(output_path, "wb") as f_out:
                f_out.write(cls._MEM_BADGE_CACHE[cache_key])
            return output_path

        # Disk önbelleği kontrolü
        disk_cache_dir = os.path.join(tempfile.gettempdir(), "otoedit_badge_cache")
        os.makedirs(disk_cache_dir, exist_ok=True)
        disk_cache_file = os.path.join(disk_cache_dir, f"{cache_key}.png")
        if os.path.isfile(disk_cache_file) and os.path.getsize(disk_cache_file) > 0:
            with open(disk_cache_file, "rb") as f_in:
                data = f_in.read()
            cls._MEM_BADGE_CACHE[cache_key] = data
            if os.path.abspath(disk_cache_file) != os.path.abspath(output_path):
                with open(output_path, "wb") as f_out:
                    f_out.write(data)
            return output_path

        # 2x süper-örnekleme (Pürüzsüz kenarlar için)
        ss = 2
        ss_font_size = max(16, int(font_size) * ss)
        ss_stroke_width = max(0, int(stroke_width) * ss)
        ss_outer_stroke_width = max(0, int(outer_stroke_width) * ss)
        ss_total_stroke = ss_stroke_width + ss_outer_stroke_width
        ss_box_padding = max(0, int(box_padding) * ss)
        ss_border_radius = max(0, int(border_radius) * ss)
        ss_letter_spacing = int(letter_spacing) * ss
        ss_glow_radius = max(0, int(glow_radius) * ss)
        ss_shadow_blur = max(0, int(shadow_blur) * ss)

        font = cls.get_font(effective_font, ss_font_size)

        display_text = text.upper() if all_caps else text
        max_w_cqi = int(kwargs.get("maxWidthCqi") or kwargs.get("max_width_cqi") or 30)
        max_line_px_ss = int(1920.0 * (max_w_cqi / 100.0) * 0.88 * ss)

        def _measure_str_px(s_val: str, d_ctx: ImageDraw.ImageDraw) -> int:
            if not s_val:
                return 0
            if ss_letter_spacing != 0:
                total_w = 0
                for ch_item in s_val:
                    bb = d_ctx.textbbox((0, 0), ch_item, font=font, stroke_width=ss_total_stroke)
                    total_w += (bb[2] - bb[0]) + ss_letter_spacing
                return max(1, total_w)
            bb = d_ctx.textbbox((0, 0), s_val, font=font, stroke_width=ss_total_stroke)
            return max(1, bb[2] - bb[0])

        probe_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe_img)

        if "\n" not in display_text and " " in display_text and abs(curve_bend) <= 1.0:
            full_px = _measure_str_px(display_text, probe_draw)
            if full_px > max_line_px_ss:
                words_list = display_text.split()
                if len(words_list) >= 2:
                    best_idx = 1
                    best_max_w = float("inf")
                    for split_i in range(1, len(words_list)):
                        l1 = " ".join(words_list[:split_i])
                        l2 = " ".join(words_list[split_i:])
                        cur_max = max(_measure_str_px(l1, probe_draw), _measure_str_px(l2, probe_draw))
                        if cur_max < best_max_w:
                            best_max_w = cur_max
                            best_idx = split_i
                    lines = [" ".join(words_list[:best_idx]), " ".join(words_list[best_idx:])]
                else:
                    lines = [display_text]
            else:
                lines = [display_text]
        else:
            lines = display_text.split("\n")

        text_rgba = hex_to_rgba(text_color, default=(255, 255, 255, 255))
        stroke_rgba = hex_to_rgba(stroke_color, default=(0, 0, 0, 255)) if ss_stroke_width > 0 else (0, 0, 0, 0)
        outer_stroke_rgba = hex_to_rgba(outer_stroke_color, default=(0, 0, 0, 255)) if ss_outer_stroke_width > 0 else (0, 0, 0, 0)
        glow_rgba = hex_to_rgba(glow_color, default=(0, 245, 212, 255))
        shadow_rgba = hex_to_rgba(shadow_color, default=(0, 0, 0, 185))

        # Yönlü gölge (Directional Drop Shadow) ofseti
        sh_rad = math.radians(shadow_angle)
        sh_dx = int(round(math.cos(sh_rad) * shadow_distance * ss))
        sh_dy = int(round(math.sin(sh_rad) * shadow_distance * ss))

        extra_effect_margin = max(ss_shadow_blur * 3, ss_glow_radius * 3) + int(abs(shadow_distance) * ss) + ss_total_stroke + 28

        # DURUM A: Dairesel Yay (Curved / Arc Text)
        if abs(curve_bend) > 1.0:
            outer_mask, stroke_mask, glyph_mask, text_bbox = cls._render_curved_arc_layers(
                text=display_text,
                font=font,
                curve_bend=curve_bend,
                ss_font_size=ss_font_size,
                ss_stroke_width=ss_stroke_width,
                ss_outer_stroke_width=ss_outer_stroke_width,
                ss_letter_spacing=ss_letter_spacing,
                margin=extra_effect_margin,
            )
            canvas_w, canvas_h = glyph_mask.size
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            base_sil = outer_mask if ss_outer_stroke_width > 0 else (stroke_mask if ss_stroke_width > 0 else glyph_mask)
        else:
            # DURUM B: Standart / Çok Satırlı Metin
            dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            dummy_draw = ImageDraw.Draw(dummy_img)

            line_measurements: List[Tuple[str, int]] = []
            max_line_w = 0
            line_height = int(ss_font_size * 1.25)

            for line in lines:
                line_w = 0
                if ss_letter_spacing != 0:
                    for ch in line:
                        bbox = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=ss_total_stroke)
                        cw = (bbox[2] - bbox[0]) + ss_letter_spacing
                        line_w += cw
                else:
                    bbox = dummy_draw.textbbox((0, 0), line, font=font, stroke_width=ss_total_stroke)
                    line_w = bbox[2] - bbox[0]

                line_measurements.append((line, max(1, line_w)))
                if line_w > max_line_w:
                    max_line_w = line_w

            max_line_w = max(1, max_line_w)
            total_text_h = max(1, len(lines) * line_height)

            has_box = box_style in ("pill", "rounded", "badge") and bool(box_bg_color)
            is_marker = box_style == "highlight-marker" and bool(box_bg_color)

            if has_box or is_marker:
                pad_x = int(round(ss_font_size * 0.58))
                pad_y = int(round(ss_font_size * 0.22))
            else:
                pad_x = ss_total_stroke + 12
                pad_y = ss_total_stroke + 12

            box_w = max_line_w + (pad_x * 2)
            box_h = total_text_h + (pad_y * 2)

            canvas_w = box_w + (extra_effect_margin * 2)
            canvas_h = box_h + (extra_effect_margin * 2)

            canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(canvas)

            box_x1 = extra_effect_margin
            box_y1 = extra_effect_margin
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h

            # 1. Kutu Gölgesi
            if shadow and has_box:
                shadow_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                shadow_draw = ImageDraw.Draw(shadow_canvas)
                s_rect = (box_x1 + sh_dx, box_y1 + sh_dy, box_x2 + sh_dx, box_y2 + sh_dy)
                radius = (box_h // 2) if box_style == "pill" else ss_border_radius
                shadow_draw.rounded_rectangle(s_rect, radius=radius, fill=(shadow_rgba[0], shadow_rgba[1], shadow_rgba[2], min(180, shadow_rgba[3])))
                if ss_shadow_blur > 0:
                    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(ss_shadow_blur))
                canvas = Image.alpha_composite(canvas, shadow_canvas)
                draw = ImageDraw.Draw(canvas)

            # 2. Arka Plan Kutusu (Pill / Rounded / Badge / Highlight-Marker)
            if has_box:
                box_rgba = hex_to_rgba(box_bg_color, default=(0, 0, 0, 190))
                radius = (box_h // 2) if box_style == "pill" else ss_border_radius
                draw.rounded_rectangle((box_x1, box_y1, box_x2, box_y2), radius=radius, fill=box_rgba)
            elif is_marker:
                marker_rgba = hex_to_rgba(box_bg_color, default=(255, 215, 0, 225))
                slant = int(8 * ss)
                for i, (_, lw) in enumerate(line_measurements):
                    lx1 = box_x1 + pad_x + ((max_line_w - lw) // 2) - int(10 * ss)
                    ly1 = box_y1 + pad_y + (i * line_height) - int(4 * ss)
                    lx2 = lx1 + lw + int(20 * ss)
                    ly2 = ly1 + line_height + int(4 * ss)
                    poly = [
                        (lx1 + slant, ly1),
                        (lx2 + slant, ly1),
                        (lx2 - slant, ly2),
                        (lx1 - slant, ly2),
                    ]
                    draw.polygon(poly, fill=marker_rgba)

            # 3. Metin Maskelerini Hazırla (Outer Stroke, Primary Stroke, Interior Glyph)
            outer_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            stroke_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            glyph_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

            d_outer = ImageDraw.Draw(outer_mask)
            d_stroke = ImageDraw.Draw(stroke_mask)
            d_glyph = ImageDraw.Draw(glyph_mask)

            def _draw_lines(target_draw: ImageDraw.ImageDraw, s_width: int):
                for i, (line, lw) in enumerate(line_measurements):
                    cur_x = box_x1 + pad_x + ((max_line_w - lw) // 2)
                    cur_y = box_y1 + pad_y + (i * line_height)
                    if ss_letter_spacing != 0:
                        cx = cur_x
                        for ch in line:
                            target_draw.text(
                                (cx, cur_y),
                                ch,
                                font=font,
                                fill=(255, 255, 255, 255),
                                stroke_width=s_width,
                                stroke_fill=(255, 255, 255, 255),
                            )
                            bbox = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=ss_total_stroke)
                            cx += (bbox[2] - bbox[0]) + ss_letter_spacing
                    else:
                        target_draw.text(
                            (cur_x, cur_y),
                            line,
                            font=font,
                            fill=(255, 255, 255, 255),
                            stroke_width=s_width,
                            stroke_fill=(255, 255, 255, 255),
                        )

            if ss_outer_stroke_width > 0:
                _draw_lines(d_outer, ss_total_stroke)
            if ss_stroke_width > 0:
                _draw_lines(d_stroke, ss_stroke_width)
            _draw_lines(d_glyph, 0)

            text_bbox = (box_x1 + pad_x, box_y1 + pad_y, box_x1 + pad_x + max_line_w, box_y1 + pad_y + total_text_h)
            base_sil = outer_mask if ss_outer_stroke_width > 0 else (stroke_mask if ss_stroke_width > 0 else glyph_mask)

        # 4. Yönlü Metin Gölgesi (Directional Drop Shadow - kutu yoksa veya eğrisel metinse)
        if shadow and (box_style not in ("pill", "rounded", "badge") or abs(curve_bend) > 1.0):
            sil_alpha = base_sil.split()[3]
            sh_layer = Image.new("RGBA", (canvas_w, canvas_h), (shadow_rgba[0], shadow_rgba[1], shadow_rgba[2], 0))
            sh_alpha_np = (np.array(sil_alpha, dtype=np.float32) * (shadow_rgba[3] / 255.0)).astype(np.uint8)
            sh_layer.putalpha(Image.fromarray(sh_alpha_np))
            shifted_sh = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            shifted_sh.paste(sh_layer, (sh_dx, sh_dy))
            if ss_shadow_blur > 0:
                shifted_sh = shifted_sh.filter(ImageFilter.GaussianBlur(ss_shadow_blur))
            canvas = Image.alpha_composite(canvas, shifted_sh)

        # 5. Neon Dış Işıltı (Outer Glow)
        if glow_enabled and ss_glow_radius > 0:
            sil_alpha = base_sil.split()[3]
            glow_layer = Image.new("RGBA", (canvas_w, canvas_h), (glow_rgba[0], glow_rgba[1], glow_rgba[2], 0))
            glow_layer.putalpha(sil_alpha)
            glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(ss_glow_radius))
            # Neon yoğunluğu için çift katmanlı ışıltı
            canvas = Image.alpha_composite(canvas, glow_blurred)
            canvas = Image.alpha_composite(canvas, glow_blurred)

        # 6. Çift Kontur (Outer Stroke) Katmanı
        if ss_outer_stroke_width > 0:
            outer_colored = Image.new("RGBA", (canvas_w, canvas_h), outer_stroke_rgba[:3] + (0,))
            outer_alpha = (np.array(outer_mask.split()[3], dtype=np.float32) * (outer_stroke_rgba[3] / 255.0)).astype(np.uint8)
            outer_colored.putalpha(Image.fromarray(outer_alpha))
            canvas = Image.alpha_composite(canvas, outer_colored)

        # 7. Birincil Kontur (Primary Stroke) Katmanı
        if ss_stroke_width > 0:
            stroke_colored = Image.new("RGBA", (canvas_w, canvas_h), stroke_rgba[:3] + (0,))
            stroke_alpha = (np.array(stroke_mask.split()[3], dtype=np.float32) * (stroke_rgba[3] / 255.0)).astype(np.uint8)
            stroke_colored.putalpha(Image.fromarray(stroke_alpha))
            canvas = Image.alpha_composite(canvas, stroke_colored)

        # 8. Metin İç Dolgusu (Solid / Linear Gradient / Radial Gradient)
        glyph_alpha_np = np.array(glyph_mask.split()[3], dtype=np.float32) / 255.0
        if fill_type in ("gradient", "radial"):
            c_start = hex_to_rgba(gradient_start, default=text_rgba)
            c_end = hex_to_rgba(gradient_end, default=(121, 40, 202, 255))
            grad_rgba = cls._generate_gradient_rgba(
                width=canvas_w,
                height=canvas_h,
                color_start=c_start,
                color_end=c_end,
                fill_type=fill_type,
                angle_deg=gradient_angle,
                bbox=text_bbox,
            )
            grad_rgba[:, :, 3] = (grad_rgba[:, :, 3].astype(np.float32) * glyph_alpha_np).astype(np.uint8)
            fill_layer = Image.fromarray(grad_rgba, "RGBA")
        else:
            fill_layer = Image.new("RGBA", (canvas_w, canvas_h), text_rgba[:3] + (0,))
            final_fill_alpha = (glyph_alpha_np * text_rgba[3]).astype(np.uint8)
            fill_layer.putalpha(Image.fromarray(final_fill_alpha))

        canvas = Image.alpha_composite(canvas, fill_layer)

        # 9. 3D Perspektif & Skew Dönüşümü
        canvas = cls._apply_3d_perspective(
            canvas,
            rotate_x=rotate_x,
            rotate_y=rotate_y,
            skew_x=skew_x,
            skew_y=skew_y,
        )

        # 10. Kırp ve 2x -> 1x ölçekle (LANCZOS downsampling)
        bbox = canvas.getbbox()
        if bbox:
            canvas = canvas.crop(bbox)

        final_w = max(1, canvas.width // ss)
        final_h = max(1, canvas.height // ss)
        final_img = canvas.resize((final_w, final_h), Image.Resampling.LANCZOS)
        final_img.save(output_path, "PNG")

        # Önbelleğe kaydet
        try:
            with open(output_path, "rb") as f_saved:
                png_bytes = f_saved.read()
            cls._MEM_BADGE_CACHE[cache_key] = png_bytes
            if os.path.abspath(disk_cache_file) != os.path.abspath(output_path):
                with open(disk_cache_file, "wb") as f_cache:
                    f_cache.write(png_bytes)
        except Exception as cache_err:
            logger.debug(f"Badge önbellek yazma uyarısı: {cache_err}")

        logger.info(f"[GRAPHICS_ENGINE] Text rozeti render edildi ({final_w}x{final_h}, box={box_style}, fill={fill_type}): {output_path}")
        return output_path
