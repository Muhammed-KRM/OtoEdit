import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """OtoEdit Python Worker Yapılandırma Sınıfı."""

    # Dizinler
    BASE_DIR = Path(__file__).resolve().parent
    TEMP_DIR = Path(os.getenv("TEMP_DIR", str(BASE_DIR / "temp")))

    # RabbitMQ
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USERNAME = os.getenv("RABBITMQ_USER") or os.getenv("RABBITMQ_USERNAME", "guest")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

    # MinIO S3
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET") or os.getenv("MINIO_BUCKET_NAME", "otoedit")
    MINIO_SECURE = (os.getenv("MINIO_SECURE") or os.getenv("MINIO_USE_SSL", "false")).lower() in ("true", "1", "yes")

    # Yapay Zeka ve Harici API Anahtarları
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

    # Performans ve Algılama Eşikleri
    GESTURE_FRAME_SKIP = int(os.getenv("GESTURE_FRAME_SKIP", "8"))
    GESTURE_CONFIDENCE = float(os.getenv("GESTURE_CONFIDENCE", "0.7"))
    SILENCE_MIN_LEN_MS = int(os.getenv("SILENCE_MIN_LEN_MS", "500"))
    SILENCE_THRESH_DBFS = int(os.getenv("SILENCE_THRESH_DBFS", "-40"))

    @classmethod
    def ensure_directories(cls):
        """Gerekli geçici dizinlerin var olduğundan emin olur."""
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        (cls.BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
