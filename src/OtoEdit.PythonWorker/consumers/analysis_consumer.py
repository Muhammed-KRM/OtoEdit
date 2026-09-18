import json
import pika
from config import Config
from pipeline.audio_enhancer import AudioEnhancer
from pipeline.edl_builder import EdlBuilder
from pipeline.face_tracker import FaceTracker
from pipeline.multimodal_command_engine import MultimodalCommandEngine
from pipeline.repurposing_engine import RepurposingEngine
from pipeline.silence_detector import SilenceDetector
from pipeline.suggestion_engine import SuggestionEngine
from pipeline.transcriber import Transcriber
from services.minio_client import MinioClient
from services.rabbitmq_publisher import RabbitMQPublisher
from utils.constants import PipelineStage, RabbitMQConstants
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisConsumer:
    """RabbitMQ'dan VideoUploadedEvent dinler ve tam otomatik analiz pipeline'ını yürütür."""

    def __init__(self):
        self.minio = MinioClient()
        self.publisher = RabbitMQPublisher()
        self.audio_enhancer = AudioEnhancer()
        self.transcriber = Transcriber()
        self.silence_detector = SilenceDetector()
        self.command_engine = MultimodalCommandEngine()
        self.face_tracker = FaceTracker()
        self.repurposing = RepurposingEngine()
        self.suggestion_engine = SuggestionEngine()
        self.edl_builder = EdlBuilder()

    def start(self):
        """RabbitMQ bağlantısını açar, exchange ve kuyruğu bağlar ve dinlemeye başlar."""
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

        # MassTransit Publish<VideoUploadedEvent> fanout exchange üretir
        channel.exchange_declare(
            exchange=RabbitMQConstants.EXCHANGE_VIDEO_UPLOADED,
            exchange_type='fanout',
            durable=True
        )

        # Worker kuyruğu tanımla ve exchange'e bağla
        channel.queue_declare(queue=RabbitMQConstants.QUEUE_VIDEO_UPLOADED, durable=True)
        channel.queue_bind(
            queue=RabbitMQConstants.QUEUE_VIDEO_UPLOADED,
            exchange=RabbitMQConstants.EXCHANGE_VIDEO_UPLOADED
        )

        # Qos: Her seferde 1 mesaj al
        channel.basic_qos(prefetch_count=1)

        channel.basic_consume(
            queue=RabbitMQConstants.QUEUE_VIDEO_UPLOADED,
            on_message_callback=self._on_message,
            auto_ack=False
        )

        logger.info(f"AnalysisConsumer başlatıldı. Kuyruk: '{RabbitMQConstants.QUEUE_VIDEO_UPLOADED}' dinleniyor...")
        channel.start_consuming()

    def _on_message(self, ch, method, properties, body):
        try:
            msg = json.loads(body.decode('utf-8'))
        except Exception as ex:
            logger.error(f"Mesaj JSON parse edilemedi: {ex}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        video_id = str(msg.get("videoId", ""))
        project_id = str(msg.get("projectId", ""))
        video_format = int(msg.get("videoFormati", 0))
        dosya_yolu = msg.get("dosyaYolu", "")
        gesture_enabled = bool(msg.get("gestureCommandsEnabled", True))
        audio_enhancement = bool(msg.get("audioEnhancementEnabled", True))

        logger.info(f"🎬 VideoUploadedEvent alındı: VideoId={video_id}, ProjectId={project_id}, Format={video_format}")

        try:
            # 1. Ham videoyu MinIO'dan indir
            self._publish_progress(project_id, video_id, PipelineStage.SES_IYILESTIRME, 0, "Video depolamadan indiriliyor...")
            local_video_path = self.minio.download_video(project_id, video_id, object_key=dosya_yolu)

            # 2. Aşama 0: Ses İyileştirme (Opsiyonel)
            clean_audio_path = local_video_path
            if audio_enhancement:
                self._publish_progress(project_id, video_id, PipelineStage.SES_IYILESTIRME, 10, "Gürültü ve yankı temizleniyor...")
                clean_audio_path = self.audio_enhancer.enhance(local_video_path)
                try:
                    self.minio.upload_clean_audio(project_id, video_id, clean_audio_path)
                except Exception as ex:
                    logger.warning(f"Temiz ses MinIO'ya yüklenirken uyarı: {ex}")

            # 3. Aşama 1: STT (Whisper Transkripsiyon)
            self._publish_progress(project_id, video_id, PipelineStage.STT, 25, "Konuşmalar metne dönüştürülüyor (Whisper)...")
            transcript = self.transcriber.transcribe(clean_audio_path, video_id=video_id)

            # 4. Aşama 2: Sessizlik Algılama (Jump-cut)
            self._publish_progress(project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 45, "Sessiz aralıklar tespit ediliyor...")
            silence_cuts = self.silence_detector.detect(clean_audio_path)

            # 5. Aşama 3: Çoklu-Modal Komut Algılama (El Hareketi + Ses)
            commands = []
            if gesture_enabled:
                self._publish_progress(project_id, video_id, PipelineStage.KOMUT_ALGILAMA, 60, "El hareketleri ve sesli komutlar taranıyor...")
                commands = self.command_engine.detect(local_video_path, transcript)

            # 6. Aşama 4: Yüz Takibi (Dikey/Kare Format İse)
            face_data = []
            if video_format in (1, 2):  # 9:16 veya 1:1
                self._publish_progress(project_id, video_id, PipelineStage.YUZ_TAKIBI, 70, "Dikey kadraj için yüz takibi yapılıyor...")
                face_data = self.face_tracker.track(local_video_path)

            # 7. Aşama 5: Repurposing (Viral Klip Tespiti)
            self._publish_progress(project_id, video_id, PipelineStage.REPURPOSING, 80, "Yapay zeka ile viral anlar belirleniyor...")
            repurposing_data = self.repurposing.analyze(transcript)

            # 8. Aşama 6: Akıllı B-Roll ve Görsel/Metin Öneri Motoru
            self._publish_progress(project_id, video_id, PipelineStage.ONERI_OLUSTURMA, 90, "Görsel ve metin önerileri hazırlanıyor...")
            suggestions = self.suggestion_engine.generate_suggestions(transcript)

            # 9. Aşama 7: EDL Oluşturma (Tüm sonuçları birleştir)
            self._publish_progress(project_id, video_id, PipelineStage.EDL_OLUSTURMA, 95, "Nihai EDL karar listesi derleniyor...")
            edl_dict = self.edl_builder.build(
                project_id=project_id,
                video_id=video_id,
                transcript=transcript,
                silence_cuts=silence_cuts,
                commands=commands,
                face_data=face_data,
                repurposing_data=repurposing_data,
                suggestions=suggestions,
                video_format=video_format
            )

            # 10. Tamamlandı Bildirimi ve EDL'yi .NET API'ye Gönder
            self.publisher.publish_analysis_completed(project_id, video_id, edl_dict)
            self._publish_progress(project_id, video_id, PipelineStage.TAMAMLANDI, 100, "Analiz başarıyla tamamlandı!")

            logger.info(f"🎉 Pipeline analizi başarıyla tamamlandı: VideoId={video_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"❌ Analiz pipeline hatası (VideoId={video_id}): {e}", exc_info=True)
            self.publisher.publish_pipeline_error(project_id, video_id, "Analiz", str(e))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _publish_progress(self, project_id: str, video_id: str, asama: str, yuzde: int, mesaj: str):
        try:
            self.publisher.publish_stage_changed(project_id, video_id, asama, yuzde, mesaj)
        except Exception as ex:
            logger.warning(f"İlerleme bildirimi gönderilemedi: {ex}")
