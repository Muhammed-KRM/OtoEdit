"""OtoEdit Python Worker - Video & AI İşleme Motoru Giriş Noktası."""
import sys
import time
from config import Config
from utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("OtoEdit.PythonWorker")


def main():
    logger.info("==================================================")
    logger.info("🎬 OtoEdit Python Worker Başlatılıyor...")
    logger.info(f"📁 Temp Dizin: {Config.TEMP_DIR}")
    logger.info(f"🐰 RabbitMQ Host: {Config.RABBITMQ_HOST}:{Config.RABBITMQ_PORT}")
    logger.info(f"📦 MinIO Endpoint: {Config.MINIO_ENDPOINT}")
    logger.info("==================================================")

    Config.ensure_directories()

    try:
        from consumers.analysis_consumer import AnalysisConsumer
        consumer = AnalysisConsumer()
        logger.info("RabbitMQ AnalysisConsumer dinleme döngüsüne giriyor...")
        consumer.start()
    except ImportError:
        logger.info("Henüz pipeline modülleri yükleniyor (Kısım 1 tamamlandı). Bekleme moduna geçiliyor.")
        # Test ve yapı kontrolü için canlı tut
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Worker kullanıcı tarafından durduruldu.")
    except Exception as e:
        logger.critical(f"Worker beklenmeyen bir hata ile sonlandı: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
