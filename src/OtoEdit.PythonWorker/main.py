"""OtoEdit Python Worker - Video & AI İşleme Motoru Giriş Noktası."""
import sys
import time
import threading
from config import Config
from utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("OtoEdit.PythonWorker")


def run_analysis_consumer():
    try:
        from consumers.analysis_consumer import AnalysisConsumer
        consumer = AnalysisConsumer()
        logger.info("AnalysisConsumer dinleme döngüsüne giriyor...")
        consumer.start()
    except Exception as ex:
        logger.error(f"AnalysisConsumer hatası: {ex}", exc_info=True)


def run_render_consumer():
    try:
        from consumers.render_consumer import RenderConsumer
        consumer = RenderConsumer()
        logger.info("RenderConsumer dinleme döngüsüne giriyor...")
        consumer.start()
    except Exception as ex:
        logger.error(f"RenderConsumer hatası: {ex}", exc_info=True)


def main():
    logger.info("==================================================")
    logger.info("🎬 OtoEdit Python Worker Başlatılıyor...")
    logger.info(f"📁 Temp Dizin: {Config.TEMP_DIR}")
    logger.info(f"🐰 RabbitMQ Host: {Config.RABBITMQ_HOST}:{Config.RABBITMQ_PORT}")
    logger.info(f"📦 MinIO Endpoint: {Config.MINIO_ENDPOINT}")
    logger.info("==================================================")

    Config.ensure_directories()

    try:
        # İki tüketiciyi ayrı arka plan iş parçacıklarında başlat
        t_analysis = threading.Thread(target=run_analysis_consumer, name="AnalysisConsumerThread", daemon=True)
        t_render = threading.Thread(target=run_render_consumer, name="RenderConsumerThread", daemon=True)

        t_analysis.start()
        t_render.start()

        logger.info("Tüm consumer iş parçacıkları başarıyla başlatıldı.")

        # Ana iş parçacığını canlı tut
        while t_analysis.is_alive() or t_render.is_alive():
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Worker kullanıcı tarafından durduruldu.")
    except Exception as e:
        logger.critical(f"Worker beklenmeyen bir hata ile sonlandı: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
