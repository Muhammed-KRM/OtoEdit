import os
from pathlib import Path
try:
    import importlib
    dotenv = importlib.import_module("dotenv")
    dotenv.load_dotenv()
except Exception:
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
    GEMINI_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", "")).split(",") if k.strip()]
    GEMINI_TRANSCRIBE_RPM = int(os.getenv("GEMINI_TRANSCRIBE_RPM", "3"))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTIGRAVITY_PROXY_URL = os.getenv("ANTIGRAVITY_PROXY_URL", "http://host.docker.internal:8045/v1")
    ANTIGRAVITY_PROXY_KEY = os.getenv("ANTIGRAVITY_PROXY_KEY", "")
    ANTIGRAVITY_PROXY_MODEL = os.getenv("ANTIGRAVITY_PROXY_MODEL", "gemini-3.8-flash-tiered")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3.8-flash")
    AI_ACTIVE_PROVIDER = os.getenv("AI_ACTIVE_PROVIDER", "antigravity")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

    # STT Motor Zinciri ve Parçalama
    STT_ENGINE_ORDER = [e.strip() for e in os.getenv("STT_ENGINE_ORDER", "gemini_transcribe,groq,proxy_gemini,local_whisper").split(",") if e.strip()]
    STT_CHUNK_MAX_SEC = int(os.getenv("STT_CHUNK_MAX_SEC", "600"))
    LOCAL_WHISPER_MODEL = os.getenv("LOCAL_WHISPER_MODEL", "large-v3-turbo")

    # Ses Analizi & VAD Eşikleri
    VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.4"))
    VAD_MIN_SILENCE_MS = int(os.getenv("VAD_MIN_SILENCE_MS", "500"))

    # Jump-Cut v2 Parametreleri
    JUMPCUT_ENGINE = os.getenv("JUMPCUT_ENGINE", "v2")
    JUMPCUT_MIN_SILENCE_MS = int(os.getenv("JUMPCUT_MIN_SILENCE_MS", "700"))
    JUMPCUT_PAD_MS = int(os.getenv("JUMPCUT_PAD_MS", "200"))
    JUMPCUT_PAD_LEAD_MS = int(os.getenv("JUMPCUT_PAD_LEAD_MS", "350"))
    JUMPCUT_PAD_TRAILING_MS = int(os.getenv("JUMPCUT_PAD_TRAILING_MS", "200"))
    JUMPCUT_WORD_GUARD_MS = int(os.getenv("JUMPCUT_WORD_GUARD_MS", "150"))
    JUMPCUT_MIN_ISLAND_MS = int(os.getenv("JUMPCUT_MIN_ISLAND_MS", "300"))
    GEMINI_TRANSCRIBE_MAX_WAIT_SEC = float(os.getenv("GEMINI_TRANSCRIBE_MAX_WAIT_SEC", "180.0"))
    TEMP_RETENTION = os.getenv("TEMP_RETENTION", "after_job")

    # Redis Önbellek & Idempotency
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    ENABLE_ANALYSIS_CACHE = os.getenv("ENABLE_ANALYSIS_CACHE", "false").lower() in ("true", "1", "yes")

    # Backend API URL (Fail-Safe Pipeline Logging & SignalR)
    API_BASE_URL = os.getenv("API_BASE_URL", "http://host.docker.internal:5001")
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "SUPER_SECRET_OTOEDIT_KEY_123!")

    # Performans ve Algılama Eşikleri (Legacy / Gesture)
    GESTURE_FRAME_SKIP = int(os.getenv("GESTURE_FRAME_SKIP", "8"))
    GESTURE_CONFIDENCE = float(os.getenv("GESTURE_CONFIDENCE", "0.7"))
    SILENCE_MIN_LEN_MS = int(os.getenv("SILENCE_MIN_LEN_MS", "500"))
    SILENCE_THRESH_DBFS = int(os.getenv("SILENCE_THRESH_DBFS", "-40"))

    @classmethod
    def ensure_directories(cls):
        """Gerekli geçici dizinlerin var olduğundan emin olur."""
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        (cls.BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
