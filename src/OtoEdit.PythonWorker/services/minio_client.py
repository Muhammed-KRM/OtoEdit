import os
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class MinioClient:
    """MinIO S3 dosya indirme ve yükleme operasyonlarını yönetir."""

    def __init__(self):
        self.endpoint = Config.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        self.bucket_name = Config.MINIO_BUCKET_NAME
        self.client = Minio(
            self.endpoint,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Hedef bucket yoksa oluşturur."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"MinIO bucket oluşturuldu: {self.bucket_name}")
        except Exception as e:
            logger.warning(f"MinIO bucket kontrolünde uyarı: {e}")

    def download_file(self, object_key: str, local_path: str | None = None) -> str:
        """MinIO'dan belirtilen nesneyi yerel geçici dizine indirir."""
        Config.ensure_directories()
        if not local_path:
            filename = Path(object_key).name
            local_path = str(Config.TEMP_DIR / filename)

        try:
            logger.info(f"MinIO indirme başlıyor: {object_key} -> {local_path}")
            self.client.fget_object(self.bucket_name, object_key, local_path)
            logger.info(f"MinIO indirme tamamlandı: {local_path}")
            return local_path
        except S3Error as e:
            logger.error(f"MinIO indirme hatası ({object_key}): {e}")
            raise

    def download_video(self, project_id: str, video_id: str, object_key: str | None = None) -> str:
        """Video dosyasını indirir."""
        if not object_key:
            object_key = f"videos/{project_id}/{video_id}.mp4"
        return self.download_file(object_key)

    def upload_file(self, local_path: str, object_key: str, content_type: str = "application/octet-stream") -> str:
        """Yerel bir dosyayı MinIO S3 bucket'ına yükler."""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Yüklenecek dosya bulunamadı: {local_path}")

        try:
            logger.info(f"MinIO yükleme başlıyor: {local_path} -> {object_key}")
            self.client.fput_object(
                self.bucket_name,
                object_key,
                local_path,
                content_type=content_type
            )
            logger.info(f"MinIO yükleme tamamlandı: {object_key}")
            return object_key
        except S3Error as e:
            logger.error(f"MinIO yükleme hatası ({object_key}): {e}")
            raise

    def upload_clean_audio(self, project_id: str, video_id: str, local_audio_path: str) -> str:
        """Temizlenmiş ses dosyasını yükler."""
        ext = Path(local_audio_path).suffix or ".mp3"
        content_type = "audio/mpeg" if ext == ".mp3" else "audio/wav"
        object_key = f"audio/{project_id}/{video_id}_clean{ext}"
        return self.upload_file(local_audio_path, object_key, content_type=content_type)

    def upload_render_output(self, project_id: str, render_job_id: str, local_video_path: str) -> str:
        """Render edilen nihai video dosyasını yükler."""
        object_key = f"renders/{project_id}/{render_job_id}.mp4"
        return self.upload_file(local_video_path, object_key, content_type="video/mp4")
