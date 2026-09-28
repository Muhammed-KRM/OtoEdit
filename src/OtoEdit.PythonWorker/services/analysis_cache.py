"""
src/OtoEdit.PythonWorker/services/analysis_cache.py
Video Analiz Sonuçları için Redis Idempotency ve Önbellek Yöneticisi
"""

import hashlib
import json
import os
from typing import Optional, Dict, Any
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisCacheService:
    """
    Video analizi sonuçlarını Redis üzerinde önbelleğe alan ve
    mükerrer analizleri (idempotency) önleyen fail-safe önbellek servisi.
    """

    def __init__(self,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 password: Optional[str] = None,
                 db: Optional[int] = None):
        self._host = host or Config.REDIS_HOST
        self._port = port or Config.REDIS_PORT
        self._password = password or Config.REDIS_PASSWORD or None
        self._db = db or Config.REDIS_DB
        self._client = None
        self._is_available = None

    def _get_client(self):
        """Redis istemcisini tembel (lazy) başlatır."""
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    db=self._db,
                    socket_timeout=3.0,
                    socket_connect_timeout=3.0,
                    decode_responses=True
                )
                self._client.ping()
                self._is_available = True
                logger.info(f"✅ Redis önbellek servisine bağlanıldı ({self._host}:{self._port})")
            except Exception as ex:
                logger.warning(f"⚠️ Redis bağlantısı kurulamadı (Önbellek devre dışı kalacak): {ex}")
                self._client = None
                self._is_available = False
        return self._client

    @staticmethod
    def compute_video_hash(file_path: str, chunk_size: int = 10 * 1024 * 1024) -> str:
        """
        Video dosyasının hızlı ve deterministik SHA-256 özetini çıkarır.
        Çok büyük dosyalarda (1 GB+) baş, orta ve son 10 MB'lık blokları + dosya boyutunu
        harmanlayarak saniyeler içinde benzersiz karma oluşturur.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video dosyası bulunamadı: {file_path}")

        file_size = os.path.getsize(file_path)
        sha256 = hashlib.sha256()
        sha256.update(str(file_size).encode('utf-8'))

        with open(file_path, "rb") as f:
            if file_size <= chunk_size * 3:
                # 30 MB ve daha küçük dosyalarda tümünü oku
                while chunk := f.read(chunk_size):
                    sha256.update(chunk)
            else:
                # Büyük videolarda: İlk 10MB, Orta 10MB, Son 10MB
                sha256.update(f.read(chunk_size))
                f.seek(file_size // 2)
                sha256.update(f.read(chunk_size))
                f.seek(max(0, file_size - chunk_size))
                sha256.update(f.read(chunk_size))

        digest = sha256.hexdigest()
        logger.info(f"Video SHA-256 hash hesaplandı: {digest} (Boyut: {file_size / (1024*1024):.2f} MB)")
        return digest

    def get_cached_edl(self, video_hash: str) -> Optional[Dict[str, Any]]:
        """
        Daha önce analiz edilmiş bir videonun EDL sonucunu döner.
        Redis erişilemez ise veya anahtar yoksa None döner (Fail-Safe).
        """
        try:
            client = self._get_client()
            if not client:
                return None

            key = f"otoedit:analysis:edl:{video_hash}"
            cached_data = client.get(key)
            if cached_data:
                logger.info(f"🎯 Redis Önbellek İSABETİ (Cache Hit)! Hash: {video_hash}")
                return json.loads(cached_data)
        except Exception as ex:
            logger.warning(f"Redis get_cached_edl okuma hatası (ihmal edildi): {ex}")
        return None

    def set_cached_edl(self, video_hash: str, edl_data: Dict[str, Any], ttl_seconds: int = 604800) -> bool:
        """
        Analiz EDL sonucunu Redis'e yazar (Varsayılan 7 gün TTL).
        Başarısız olursa False döner ancak hata fırlatmaz.
        """
        try:
            client = self._get_client()
            if not client:
                return False

            key = f"otoedit:analysis:edl:{video_hash}"
            payload = json.dumps(edl_data, ensure_ascii=False)
            client.set(key, payload, ex=ttl_seconds)
            logger.info(f"💾 Redis önbelleğe kaydedildi: Hash={video_hash}, TTL={ttl_seconds}sn")
            return True
        except Exception as ex:
            logger.warning(f"Redis set_cached_edl yazma hatası (ihmal edildi): {ex}")
            return False
