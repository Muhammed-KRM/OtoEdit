import json
try:
    import importlib
    pika = importlib.import_module("pika")
except Exception:
    pika = None
import scipy.io.wavfile as wavfile
import numpy as np
from config import Config
from pipeline.audio_enhancer import AudioEnhancer
from pipeline.edl_builder import EdlBuilder
from pipeline.face_tracker import FaceTracker
from pipeline.multimodal_command_engine import MultimodalCommandEngine
from pipeline.repurposing_engine import RepurposingEngine
from pipeline.retake_detector import RetakeDetector
from pipeline.auto_broll_engine import AutoBrollEngine
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
        self.retake_detector = RetakeDetector()
        self.auto_broll_engine = AutoBrollEngine()
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
            heartbeat=0,
            blocked_connection_timeout=0
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Worker kuyruğu tanımla
        channel.queue_declare(queue=RabbitMQConstants.QUEUE_VIDEO_UPLOADED, durable=True)

        # Hem sade hem MassTransit tam isimli exchange'lere bağla
        for ex in [RabbitMQConstants.EXCHANGE_VIDEO_UPLOADED, f"OtoEdit.Business.Events:{RabbitMQConstants.EXCHANGE_VIDEO_UPLOADED}"]:
            channel.exchange_declare(exchange=ex, exchange_type='fanout', durable=True)
            channel.queue_bind(queue=RabbitMQConstants.QUEUE_VIDEO_UPLOADED, exchange=ex)

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

        # 🚀 2026 Akıllı Yönetmen Bayrakları
        auto_jumpcut = bool(msg.get("autoJumpcutEnabled", True))
        auto_retake = bool(msg.get("autoRetakeEnabled", True))
        auto_broll = bool(msg.get("autoBrollEnabled", True))
        auto_subtitles = bool(msg.get("autoSubtitlesEnabled", False))

        logger.info(f"🎬 VideoUploadedEvent alındı: VideoId={video_id}, ProjectId={project_id}, Format={video_format}, JumpCut={auto_jumpcut}, Retake={auto_retake}, BRoll={auto_broll}, Subs={auto_subtitles}")

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
            silence_cuts = []
            if auto_jumpcut:
                self._publish_progress(project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 40, "Sessiz aralıklar tespit ediliyor...")
                silence_cuts = self.silence_detector.detect(clean_audio_path)

            # 5. Aşama 2.5: Akıllı Hatalı Tekrar (Retake) ve Akustik Puanlama
            retake_cuts = []
            if auto_retake:
                self._publish_progress(project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 50, "Akıllı tekrar ve ses patlaması analizi yapılıyor...")
                retake_cuts = self.retake_detector.detect_retakes(clean_audio_path, transcript, silence_cuts=silence_cuts)

            # 6. Aşama 3: Çoklu-Modal Komut Algılama (El Hareketi + Ses)
            commands = []
            if gesture_enabled:
                self._publish_progress(project_id, video_id, PipelineStage.KOMUT_ALGILAMA, 60, "El hareketleri ve sesli komutlar taranıyor...")
                commands = self.command_engine.detect(local_video_path, transcript)

            # 7. Aşama 4: Yüz Takibi (Dikey/Kare Format İse)
            face_data = []
            if video_format in (1, 2):  # 9:16 veya 1:1
                self._publish_progress(project_id, video_id, PipelineStage.YUZ_TAKIBI, 70, "Dikey kadraj için yüz takibi yapılıyor...")
                face_data = self.face_tracker.track(local_video_path)

            # 8. Aşama 5: Repurposing (Viral Klip Tespiti)
            self._publish_progress(project_id, video_id, PipelineStage.REPURPOSING, 80, "Yapay zeka ile viral anlar belirleniyor...")
            repurposing_data = self.repurposing.analyze(transcript)

            # 9. Aşama 6: Akıllı B-Roll ve Görsel/Metin Öneri Motoru
            self._publish_progress(project_id, video_id, PipelineStage.ONERI_OLUSTURMA, 88, "Görsel ve metin önerileri hazırlanıyor...")
            suggestions = self.suggestion_engine.generate_suggestions(transcript)

            # 10. Aşama 6.5: Otomatik B-Roll Stok Görsel Katmanı
            broll_overlays = []
            if auto_broll:
                self._publish_progress(project_id, video_id, PipelineStage.ONERI_OLUSTURMA, 92, "Pexels ile ilgili stok görseller yerleştiriliyor...")
                from utils.constants import VideoFormat
                fmt_str = VideoFormat.TO_STRING.get(video_format, "16:9")
                broll_overlays = self.auto_broll_engine.generate_broll_overlays(transcript, video_format_str=fmt_str)

            # 11. Aşama 7: EDL Oluşturma (Tüm sonuçları birleştir)
            self._publish_progress(project_id, video_id, PipelineStage.EDL_OLUSTURMA, 96, "Nihai EDL karar listesi derleniyor...")
            audio_peaks = self._extract_audio_peaks(clean_audio_path)
            edl_dict = self.edl_builder.build(
                project_id=project_id,
                video_id=video_id,
                transcript=transcript,
                silence_cuts=silence_cuts,
                commands=commands,
                face_data=face_data,
                repurposing_data=repurposing_data,
                suggestions=suggestions,
                video_format=video_format,
                extra_cuts=retake_cuts,
                extra_overlays=broll_overlays,
                audio_peaks=audio_peaks
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

    def _extract_audio_peaks(self, audio_path: str, num_peaks: int = 1000) -> list:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            data = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            if audio.channels > 1:
                data = data.reshape((-1, audio.channels))
                data = data.mean(axis=1)
                
            chunk_size = max(1, len(data) // num_peaks)
            peaks = []
            for i in range(num_peaks):
                chunk = data[i * chunk_size : (i+1) * chunk_size]
                if len(chunk) > 0:
                    peak = np.sqrt(np.mean(chunk**2))
                    peaks.append(float(peak))
            max_val = max(peaks) if peaks and max(peaks) > 0 else 1
            return [p / max_val for p in peaks]
        except Exception as e:
            logger.error(f"Waveform çıkarılamadı: {e}")
            return []

    def _publish_progress(self, project_id: str, video_id: str, asama: str, yuzde: int, mesaj: str):
        try:
            self.publisher.publish_stage_changed(project_id, video_id, asama, yuzde, mesaj)
        except Exception as ex:
            logger.warning(f"İlerleme bildirimi gönderilemedi: {ex}")
