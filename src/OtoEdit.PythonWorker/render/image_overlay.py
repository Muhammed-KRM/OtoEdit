"""OtoEdit Image Overlay - FFmpeg overlay ile görsel ve logo yerleştirme."""
import os
import urllib.request
from typing import Dict, Any, List, Optional
from render.animation_effects import AnimationEffects
from services.minio_client import MinioClient
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    ffmpeg = importlib.import_module("ffmpeg")
except Exception:
    ffmpeg = None


class ImageOverlay:
    """EDL içindeki resim, sticker ve logo kaplamalarını FFmpeg filtrelerine dönüştürür."""

    def __init__(self, minio_client: Optional[MinioClient] = None):
        self.minio = minio_client or MinioClient()

    def resolve_image_path(self, source: str, temp_dir: str = "/app/temp") -> Optional[str]:
        """
        Görsel kaynağını (MinIO s3://, yerel dosya veya HTTP URL) yerel dosya yoluna indirir/çözer.
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
            # S3 / MinIO URI
            if source.startswith("s3://") or "otoedit" in source:
                clean_key = source.replace("s3://", "").lstrip("/")
                if "/" in clean_key:
                    bucket, key = clean_key.split("/", 1)
                else:
                    bucket, key = "otoedit", clean_key
                logger.info(f"MinIO'dan görsel indiriliyor: bucket={bucket}, key={key}")
                self.minio.client.fget_object(bucket, key, local_target)
                return local_target

            # HTTP / HTTPS URL
            elif source.startswith("http://") or source.startswith("https://"):
                logger.info(f"URL'den görsel indiriliyor: {source}")
                urllib.request.urlretrieve(source, local_target)
                return local_target

        except Exception as ex:
            logger.warning(f"Görsel kaynağı çözülemedi ({source}): {ex}")
            return None

        return None

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

        for ov in (overlays or []):
            if ov.get("type") != "image":
                continue

            source = ov.get("source", "")
            local_path = self.resolve_image_path(source, temp_dir=temp_dir)
            if not local_path or not os.path.isfile(local_path):
                logger.warning(f"Görsel bulunamadığı için atlandı: {source}")
                continue

            start_t = float(ov.get("timestamp", 0.0))
            duration = float(ov.get("duration", 4.0))
            end_t = start_t + duration
            scale = float(ov.get("scale", 0.3))
            position = ov.get("position", ["center", "center"])
            animation = ov.get("animation", "fade")

            img_input = ffmpeg.input(local_path)

            # Ölçeklendirme
            if scale > 0 and scale != 1.0:
                scale_w = int(base_w * scale)
                # Çift sayıya yuvarlama (FFmpeg gereksinimi)
                scale_w = scale_w if scale_w % 2 == 0 else scale_w + 1
                img_input = img_input.filter("scale", scale_w, -1)

            # Konum ve animasyon
            pos_x = ov.get("positionX")
            pos_y = ov.get("positionY")
            if pos_x is not None and pos_y is not None:
                # 0.0 - 1.0 normalize koordinatları piksele çevir (merkezi hizala)
                center_px_x = int(float(pos_x) * base_w)
                center_px_y = int(float(pos_y) * base_h)
                x_expr = f"{center_px_x} - (w/2)"
                y_expr = f"{center_px_y} - (h/2)"
            else:
                x_expr, y_expr = AnimationEffects.get_ffmpeg_overlay_coords(
                    position=position,
                    base_w=base_w,
                    base_h=base_h,
                    anim_type=animation,
                    start_time=start_t,
                    duration=duration
                )

            enable_expr = f"between(t,{start_t:.2f},{end_t:.2f})"

            logger.info(f"Image overlay ekleniyor: {os.path.basename(local_path)} [{start_t}s - {end_t}s]")
            v = ffmpeg.overlay(v, img_input, x=x_expr, y=y_expr, enable=enable_expr)

        return v
