"""OtoEdit Image Overlay - FFmpeg overlay ile görsel, sticker, animasyonlu GIF ve logo yerleştirme."""
import os
import urllib.request
from typing import Dict, Any, List, Optional
from render.animation_effects import AnimationEffects
from services.minio_client import MinioClient
from services.bg_remover import BackgroundRemoverService
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    ffmpeg = importlib.import_module("ffmpeg")
except Exception:
    ffmpeg = None

_SUPPORTED_SHAPES = {"circle", "rounded", "star", "heart", "hexagon", "diamond"}


class ImageOverlay:
    """EDL içindeki resim, sticker, GIF ve logo kaplamalarını FFmpeg filtrelerine dönüştürür."""

    def __init__(self, minio_client: Optional[MinioClient] = None):
        self.minio = minio_client or MinioClient()

    def resolve_image_path(self, source: str, temp_dir: str = "/app/temp") -> Optional[str]:
        """
        Görsel veya ses kaynağını (MinIO s3://, yerel dosya veya HTTP URL) yerel dosya yoluna indirir/çözer.
        """
        if not source:
            return None

        # Yerel dosya kontrolü
        if os.path.isfile(source):
            return source

        os.makedirs(temp_dir, exist_ok=True)
        filename = os.path.basename(source.split("?")[0]) or "overlay_img.png"
        local_target = os.path.join(temp_dir, f"img_{filename}")

        if os.path.isfile(local_target):
            return local_target

        try:
            from urllib.parse import urlparse

            # Eğer URL ise ve otoedit bucket adını içeriyorsa (presigned url) SDK ile indir
            if source.startswith("http") and "otoedit" in source:
                parsed = urlparse(source.split("?")[0])
                path_parts = parsed.path.lstrip("/").split("/", 1)
                if len(path_parts) == 2:
                    bucket = path_parts[0]
                    key = path_parts[1]
                    logger.info(f"MinIO SDK ile presigned URL indiriliyor: bucket={bucket}, key={key}")
                    self.minio.client.fget_object(bucket, key, local_target)
                    return local_target

            # HTTP / HTTPS URL (dış bağlantılar)
            if source.startswith("http://") or source.startswith("https://"):
                logger.info(f"URL'den görsel indiriliyor: {source}")
                urllib.request.urlretrieve(source, local_target)
                return local_target

            # S3 / MinIO URI
            elif source.startswith("s3://"):
                clean_key = source.replace("s3://", "").lstrip("/")
                if "/" in clean_key:
                    bucket, key = clean_key.split("/", 1)
                else:
                    bucket, key = "otoedit", clean_key
                logger.info(f"MinIO'dan görsel indiriliyor: bucket={bucket}, key={key}")
                self.minio.client.fget_object(bucket, key, local_target)
                return local_target

        except Exception as ex:
            logger.warning(f"Görsel kaynağı çözülemedi ({source}): {ex}")
            return None

        return None

    @staticmethod
    def _has_photoshop_adjustments(ov: Dict[str, Any]) -> bool:
        """Overlay üzerinde varsayılan dışı Photoshop katman ayarı olup olmadığını kontrol eder."""
        if any(abs(float(ov.get(k) or 0.0)) > 0.1 for k in ("brightness", "contrast", "saturation", "warmth", "hue", "blur", "sharpen")):
            return True
        opacity_val = float(ov.get("opacity") if ov.get("opacity") is not None else 100.0)
        if opacity_val < 99.9:
            return True
        if any(bool(ov.get(k)) for k in ("flipH", "flip_h", "flipV", "flip_v", "dropShadow", "drop_shadow")):
            return True
        return False

    def apply_image_overlays(
        self,
        base_stream: Any,
        overlays: List[Dict[str, Any]],
        temp_dir: str = "/app/temp",
        base_w: int = 1920,
        base_h: int = 1080
    ) -> Any:
        """
        Verilen video akışına tüm görsel overlay'lerini FFmpeg filter zinciri olarak uygular.
        """
        if not ffmpeg:
            logger.warning("ffmpeg-python yüklü değil, görsel kaplamaları atlanıyor.")
            return base_stream

        v = base_stream

        # Katman hiyerarşisi (Z-Index): Küçük trackId altta, büyük trackId üstte render edilir
        img_overlays = [
            ov for ov in (overlays or [])
            if ov.get("type") in ("image", "video", "sticker", "gif")
        ]
        img_overlays.sort(key=lambda o: int(o.get("trackId") or o.get("track_id") or 1))

        for ov in img_overlays:
            source = ov.get("source") or ov.get("sourceUrl") or ov.get("url") or ""
            local_path = self.resolve_image_path(source, temp_dir=temp_dir)
            if not local_path or not os.path.isfile(local_path):
                logger.warning(f"Görsel/Video bulunamadığı için atlandı: {source}")
                continue

            lower_path = local_path.lower()
            is_video = lower_path.endswith((".mp4", ".mov", ".webm", ".mkv"))
            is_animated = lower_path.endswith((".gif", ".webp", ".apng"))

            # Statik görsellerde PIL / OpenCV ön işlemelerini (Pre-baked <10ms) uygula
            if not is_animated and not is_video:
                # 1. AI Arka Plan Kaldırma (Background Removal)
                if ov.get("removeBg") or ov.get("remove_bg"):
                    try:
                        local_path = BackgroundRemoverService.remove_background(local_path)
                    except Exception as ex:
                        logger.warning(f"Arka plan kaldırma başarısız: {ex}")

                # 2. Renk Anahtarlama (Chroma Key - Yeşil Ekran Temizleme)
                if ov.get("chromaKeyColor"):
                    try:
                        sim = float(ov.get("chromaKeySimilarity") or 0.35)
                        smooth = float(ov.get("chromaKeySmoothness") or 0.10)
                        local_path = BackgroundRemoverService.apply_chroma_key(
                            local_path, key_color_hex=ov.get("chromaKeyColor"), similarity=sim, smoothness=smooth
                        )
                    except Exception as ex:
                        logger.warning(f"Chroma key uygulanamadı: {ex}")

                # 3. Şekil Maskesi (Dairesel Avatar / Yuvarlatılmış Kart / Yıldız / Kalp / Altıgen / Elmas)
                mask_shape = str(ov.get("maskShape") or "").lower().strip()
                if mask_shape in _SUPPORTED_SHAPES:
                    try:
                        radius = int(ov.get("borderRadius") or 32)
                        feather = int(ov.get("maskFeather") or ov.get("feather") or 0)
                        local_path = BackgroundRemoverService.apply_shape_mask(
                            local_path, shape=mask_shape, corner_radius=radius, feather=feather
                        )
                    except Exception as ex:
                        logger.warning(f"Şekil maskesi uygulanamadı: {ex}")

                # 4. Photoshop Katman Ayarlamaları (Brightness, Contrast, Saturation, Warmth, Hue, Blur, Sharpen, Opacity, Flip, DropShadow)
                if self._has_photoshop_adjustments(ov):
                    try:
                        local_path = BackgroundRemoverService.apply_photoshop_adjustments(
                            local_path,
                            brightness=float(ov.get("brightness") or 0.0),
                            contrast=float(ov.get("contrast") or 0.0),
                            saturation=float(ov.get("saturation") or 0.0),
                            warmth=float(ov.get("warmth") or 0.0),
                            hue=float(ov.get("hue") or 0.0),
                            blur=float(ov.get("blur") or 0.0),
                            sharpen=float(ov.get("sharpen") or 0.0),
                            opacity=float(ov.get("opacity") if ov.get("opacity") is not None else 100.0),
                            flip_h=bool(ov.get("flipH") or ov.get("flip_h")),
                            flip_v=bool(ov.get("flipV") or ov.get("flip_v")),
                            drop_shadow=bool(ov.get("dropShadow") or ov.get("drop_shadow")),
                            shadow_color=str(ov.get("shadowColor") or "#000000"),
                            shadow_blur=int(ov.get("shadowBlur") or 10),
                        )
                    except Exception as ex:
                        logger.warning(f"Photoshop katman ayarları uygulanamadı: {ex}")

                # 5. Beyaz Sticker Çıkartma Konturu (Sticker Outline)
                if ov.get("stickerBorder") or ov.get("sticker_border"):
                    try:
                        outline_w = int(ov.get("stickerBorderWidth") or 6)
                        outline_col = ov.get("stickerBorderColor") or "#FFFFFF"
                        local_path = BackgroundRemoverService.add_sticker_outline(
                            local_path, outline_width=outline_w, outline_color_hex=outline_col
                        )
                    except Exception as ex:
                        logger.warning(f"Sticker konturu eklenemedi: {ex}")

            start_t = float(ov.get("timestamp", 0.0))
            duration = float(ov.get("duration", 4.0))
            end_t = start_t + duration
            scale = float(ov.get("scale", 0.3))
            is_fullscreen = bool(ov.get("fullScreen") or ov.get("full_screen"))
            trim_start = max(0.0, float(ov.get("trimStart") or ov.get("trim_start") or 0.0))
            position = ov.get("position", ["center", "center"])
            animation = ov.get("animation", "fade")
            loop_anim = ov.get("loopAnimation") or ov.get("loop_anim")
            keyframes = ov.get("keyframes")

            if is_video:
                img_input = ffmpeg.input(local_path, ss=trim_start, t=duration)
                img_input = img_input.filter("setpts", f"PTS-STARTPTS+{start_t:.3f}/TB")
            elif is_animated:
                img_input = ffmpeg.input(local_path, ignore_loop=0)
            else:
                img_input = ffmpeg.input(local_path)

            if is_fullscreen:
                scale_w = base_w if base_w % 2 == 0 else base_w + 1
                img_input = img_input.filter("scale", max(2, scale_w), -1)
            else:
                # UI'da scale=1.0 demek, 860px genişliğindeki player'da 160px genişlik kaplamak demek (160/860 = ~%18.6).
                base_ui_ratio = (200.0 / 860.0) if is_video else (160.0 / 860.0)
                scale_w = int(base_w * base_ui_ratio * scale)
                scale_w = scale_w if scale_w % 2 == 0 else scale_w + 1
                img_input = img_input.filter("scale", max(2, scale_w), -1)

            # Döndürme (Rotation)
            rotation_deg = float(ov.get("rotation") or 0.0)
            if abs(rotation_deg) > 0.1 and not is_fullscreen:
                rad = rotation_deg * 3.14159265 / 180.0
                img_input = img_input.filter("rotate", f"{rad:.4f}", ow="rotw(iw)", oh="roth(ih)", c="none")

            # Konum, Giriş/Döngü Animasyonu ve Keyframe Yörüngesi
            pos_x = ov.get("positionX")
            pos_y = ov.get("positionY")
            has_dynamic_motion = (
                bool(keyframes)
                or (loop_anim and str(loop_anim).lower() != "none")
                or (animation and str(animation).lower() not in ("", "none", "fade"))
            )

            if is_fullscreen:
                x_expr = "(W-w)/2"
                y_expr = "(H-h)/2"
            elif pos_x is not None and pos_y is not None and not has_dynamic_motion:
                center_px_x = int((float(pos_x) / 100.0) * base_w)
                center_px_y = int((float(pos_y) / 100.0) * base_h)
                x_expr = f"{center_px_x} - (w/2)"
                y_expr = f"{center_px_y} - (h/2)"
            else:
                x_expr, y_expr = AnimationEffects.get_ffmpeg_overlay_coords(
                    position=position,
                    base_w=base_w,
                    base_h=base_h,
                    anim_type=animation,
                    start_time=start_t,
                    duration=duration,
                    loop_anim=loop_anim,
                    keyframes=keyframes,
                    pos_x=pos_x,
                    pos_y=pos_y,
                )

            enable_expr = f"between(t,{start_t:.2f},{end_t:.2f})"

            logger.info(f"Image overlay ekleniyor: {os.path.basename(local_path)} [{start_t}s - {end_t}s] rot={rotation_deg}°")
            v = ffmpeg.overlay(v, img_input, x=x_expr, y=y_expr, enable=enable_expr)

        return v
