import json
try:
    import importlib
    pika = importlib.import_module("pika")
except Exception:
    pika = None
from config import Config
from utils.constants import RabbitMQConstants
from utils.logger import get_logger

logger = get_logger(__name__)


class RabbitMQPublisher:
    """Python Worker'dan .NET API MassTransit Consumer'larına raw JSON event basar."""

    def __init__(self):
        self._connection = None
        self._channel = None

    def _get_connection(self):
        credentials = pika.PlainCredentials(Config.RABBITMQ_USERNAME, Config.RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=Config.RABBITMQ_HOST,
            port=Config.RABBITMQ_PORT,
            virtual_host=Config.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=300
        )
        return pika.BlockingConnection(parameters)

    def _get_channel(self):
        if self._connection is None or self._connection.is_closed:
            self._connection = self._get_connection()
            self._channel = self._connection.channel()
        elif self._channel is None or self._channel.is_closed:
            self._channel = self._connection.channel()
        return self._channel

    def publish(self, exchange_name: str, message_dict: dict):
        """Verilen exchange üzerine raw JSON mesajı yayınlar."""
        try:
            channel = self._get_channel()
            # MassTransit fanout exchange yapısını garantiye al
            channel.exchange_declare(exchange=exchange_name, exchange_type='fanout', durable=True)

            body = json.dumps(message_dict, ensure_ascii=False).encode('utf-8')
            properties = pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2  # Persistent mesaj
            )

            channel.basic_publish(
                exchange=exchange_name,
                routing_key='',
                body=body,
                properties=properties
            )
            logger.info(f"RabbitMQ event yayınlandı: exchange={exchange_name}")
        except Exception as e:
            logger.error(f"RabbitMQ yayın hatası (exchange={exchange_name}): {e}", exc_info=True)
            # Bağlantıyı sıfırla ki bir sonraki istekte yeniden denesin
            self._close()
            raise

    def publish_stage_changed(self, project_id: str, video_id: str, asama: str, yuzde: int, mesaj: str = ""):
        """Pipeline aşama ilerleme bildirimini .NET'e gönderir."""
        payload = {
            "projectId": project_id,
            "videoId": video_id,
            "asama": asama,
            "yuzde": yuzde,
            "mesaj": mesaj
        }
        self.publish(RabbitMQConstants.EXCHANGE_STAGE_CHANGED, payload)

    def publish_analysis_completed(self, project_id: str, video_id: str, edl_json: dict):
        """Analiz tamamlanma bildirimini ve nihai EDL'yi .NET'e gönderir."""
        payload = {
            "projectId": project_id,
            "videoId": video_id,
            "edlJson": edl_json
        }
        self.publish(RabbitMQConstants.EXCHANGE_ANALYSIS_COMPLETED, payload)

    def publish_pipeline_error(self, project_id: str, video_id: str, asama: str, hata_mesaji: str):
        """Pipeline hata bildirimini .NET'e gönderir."""
        payload = {
            "projectId": project_id,
            "videoId": video_id,
            "asama": asama,
            "hataMesaji": hata_mesaji
        }
        self.publish(RabbitMQConstants.EXCHANGE_PIPELINE_ERROR, payload)

    def publish_render_completed(self, render_job_id: str, project_id: str, indirme_url: str):
        """Render tamamlanma bildirimini ve indirme linkini .NET'e gönderir."""
        payload = {
            "renderJobId": render_job_id,
            "projectId": project_id,
            "indirmeUrl": indirme_url
        }
        self.publish(RabbitMQConstants.EXCHANGE_RENDER_COMPLETED, payload)
        logger.info(f"RenderCompletedEvent yayınlandı: RenderJobId={render_job_id}")

    def publish_render_progress(self, render_job_id: str, project_id: str, yuzde: int, mesaj: str = ""):
        """Render aşama ilerleme bildirimini .NET'e gönderir."""
        self.publish_stage_changed(project_id, render_job_id, PipelineStage.RENDER, yuzde, mesaj)

    def _close(self):
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.close()
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception:
            pass
        self._channel = None
        self._connection = None
