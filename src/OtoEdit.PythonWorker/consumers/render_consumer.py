"""RenderConsumer — RabbitMQ'dan RenderRequestedEvent dinler ve FFmpeg ile render işlemini yürütür."""
import json
import os
try:
    import importlib
    pika = importlib.import_module("pika")
except Exception:
    pika = None
from config import Config
from render.video_renderer import VideoRenderer
from services.minio_client import MinioClient
from services.rabbitmq_publisher import RabbitMQPublisher
from utils.constants import PipelineStage, RabbitMQConstants
from utils.logger import get_logger

logger = get_logger(__name__)


class RenderConsumer:
    """RabbitMQ'dan RenderRequestedEvent dinler, EDL JSON'a göre FFmpeg render yapar ve sonucu MinIO'ya yükler."""

    def __init__(self):
        self.minio = MinioClient()
        self.publisher = RabbitMQPublisher()
        self.renderer = VideoRenderer(self.minio)

    def start(self):
        """RabbitMQ bağlantısını kurar, kuyruğu exchange'e bağlar ve dinlemeye başlar."""
        credentials = pika.PlainCredentials(Config.RABBITMQ_USERNAME, Config.RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=Config.RABBITMQ_HOST,
            port=Config.RABBITMQ_PORT,
            virtual_host=Config.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=300
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # MassTransit Publish<RenderRequestedEvent> fanout exchange üretir
        channel.exchange_declare(
            exchange=RabbitMQConstants.EXCHANGE_RENDER_REQUESTED,
            exchange_type='fanout',
            durable=True
        )

        # Worker render kuyruğunu tanımla ve exchange'e bağla
        channel.queue_declare(queue=RabbitMQConstants.QUEUE_RENDER_REQUESTED, durable=True)
        channel.queue_bind(
            queue=RabbitMQConstants.QUEUE_RENDER_REQUESTED,
            exchange=RabbitMQConstants.EXCHANGE_RENDER_REQUESTED
        )

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=RabbitMQConstants.QUEUE_RENDER_REQUESTED,
            on_message_callback=self._on_message,
            auto_ack=False
        )

        logger.info(f"RenderConsumer başlatıldı. Kuyruk: '{RabbitMQConstants.QUEUE_RENDER_REQUESTED}' dinleniyor...")
        channel.start_consuming()

    def _on_message(self, ch, method, properties, body):
        try:
            msg = json.loads(body.decode('utf-8'))
        except Exception as ex:
            logger.error(f"Render isteği JSON parse edilemedi: {ex}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        render_job_id = str(msg.get("renderJobId", ""))
        project_id = str(msg.get("projectId", ""))
        edl_json = msg.get("edlJson", {})

        # Eğer edlJson string ise dict'e dönüştür
        if isinstance(edl_json, str):
            try:
                edl_json = json.loads(edl_json)
            except Exception:
                edl_json = {}

        logger.info(f"🎬 RenderRequestedEvent alındı: RenderJobId={render_job_id}, ProjectId={project_id}")

        try:
            self._publish_progress(render_job_id, project_id, 10, "Kaynak video indiriliyor...")

            # 1. Kaynak videoyu MinIO'dan indir
            source_url = edl_json.get("sourceVideoUrl", "")
            video_id = edl_json.get("videoId", "")
            local_video_path = self._resolve_source_video(project_id, video_id, source_url)

            # 2. Çıktı yollarını ayarla
            temp_dir = str(Config.TEMP_DIR / f"render_{render_job_id}")
            os.makedirs(temp_dir, exist_ok=True)
            output_filename = f"render_{render_job_id}.mp4"
            local_output_path = os.path.join(temp_dir, output_filename)

            # 3. FFmpeg ile Render İşlemini Başlat
            self._publish_progress(render_job_id, project_id, 30, "Video render ediliyor (kesimler, kadraj ve kaplamalar)...")
            self.renderer.render(
                edl_json=edl_json,
                video_path=local_video_path,
                output_path=local_output_path,
                temp_dir=temp_dir
            )

            # 4. Render Edilen Videoyu MinIO'ya Yükle
            self._publish_progress(render_job_id, project_id, 85, "Render çıktısı bulut depolamaya yükleniyor...")
            uploaded_key = self.minio.upload_render_output(project_id, render_job_id, local_output_path)

            # 5. Tamamlanma Event'ini .NET API'ye Gönder
            self.publisher.publish_render_completed(
                render_job_id=render_job_id,
                project_id=project_id,
                indirme_url=uploaded_key
            )
            self._publish_progress(render_job_id, project_id, 100, "Render işlemi başarıyla tamamlandı!")

            logger.info(f"🎉 Render görevi başarıyla tamamlandı: RenderJobId={render_job_id}, Key={uploaded_key}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"❌ Render işlemi başarısız oldu (RenderJobId={render_job_id}): {e}", exc_info=True)
            self.publisher.publish_pipeline_error(project_id, render_job_id, "Render", str(e))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _resolve_source_video(self, project_id: str, video_id: str, source_url: str) -> str:
        """MinIO veya yerel yoldan kaynak videoyu temin eder."""
        if source_url and os.path.isfile(source_url):
            return source_url

        if source_url:
            clean_key = source_url.replace("s3://", "").lstrip("/")
            if clean_key.startswith(f"{self.minio.bucket_name}/"):
                clean_key = clean_key[len(self.minio.bucket_name) + 1:]
            return self.minio.download_file(clean_key)

        return self.minio.download_video(project_id, video_id)

    def _publish_progress(self, render_job_id: str, project_id: str, yuzde: int, mesaj: str):
        try:
            self.publisher.publish_render_progress(render_job_id, project_id, yuzde, mesaj)
        except Exception as ex:
            logger.warning(f"Render ilerleme bildirimi gönderilemedi: {ex}")
