import json
import concurrent.futures
try:
    import importlib
    pika = importlib.import_module("pika")
except Exception:
    pika = None
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
from services.analysis_cache import AnalysisCacheService
from services.minio_client import MinioClient
from services.pipeline_logger import PipelineLogger
from services.rabbitmq_publisher import RabbitMQPublisher
from consumers.heartbeat_manager import RabbitHeartbeatKeeper
from utils.constants import PipelineStage, RabbitMQConstants, VideoFormat
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisConsumer:
    """
    RabbitMQ'dan VideoUploadedEvent dinler ve paralel, Redis önbellekli,
    donanım hızlandırmalı tam otomatik analiz pipeline'ını yürütür.
    """

    def __init__(self):
        self._connection = None
        self.minio = MinioClient()
        self.publisher = RabbitMQPublisher()
        self.pipeline_logger = PipelineLogger(publisher=self.publisher)
        self.cache = AnalysisCacheService()
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

        self._connection = pika.BlockingConnection(parameters)
        connection = self._connection
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

        logger.info(
            f"🎬 VideoUploadedEvent alındı: VideoId={video_id}, ProjectId={project_id}, "
            f"Format={video_format}, JumpCut={auto_jumpcut}, Retake={auto_retake}, "
            f"BRoll={auto_broll}, Subs={auto_subtitles}"
        )

        # 💓 RabbitMQ Arka Plan Nabız Koruyucusu (Uzun analizlerde soket kopmasını önler)
        heartbeat = RabbitHeartbeatKeeper(self._connection, interval_sec=10.0)
        heartbeat.start()

        try:
            # 1. Ham videoyu MinIO'dan indir
            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.SES_IYILESTIRME, 5,
                message="Video depolamadan indiriliyor..."
            )
            local_video_path = self.minio.download_video(project_id, video_id, object_key=dosya_yolu)

            # 🚀 REDIS IDEMPOTENCY KONTROLÜ (SHA-256 İle Mükerrer Analizi Önleme)
            video_hash = self.cache.compute_video_hash(local_video_path)
            if Config.ENABLE_ANALYSIS_CACHE:
                cached_edl = self.cache.get_cached_edl(video_hash)
                if cached_edl:
                    logger.info(f"⚡ Mükerrer dosya tespit edildi! Redis önbelleğinden anında sonuç dönülüyor (VideoId={video_id})")
                    self.publisher.publish_analysis_completed(project_id, video_id, cached_edl)
                    self.pipeline_logger.log_progress(
                        project_id, video_id, PipelineStage.TAMAMLANDI, 100,
                        status="Completed",
                        message="Analiz sonucu önbellekten (Redis) anında yüklendi!"
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
            else:
                logger.info(f"ℹ️ Redis analiz önbelleği devre dışı (ENABLE_ANALYSIS_CACHE=False). Sıfırdan taze analiz yürütülüyor...")

            # 2. Aşama 0: Ses İyileştirme (Opsiyonel)
            clean_audio_path = local_video_path
            if audio_enhancement:
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.SES_IYILESTIRME, 12,
                    message="Gürültü ve yankı temizleniyor..."
                )
                clean_audio_path = self.audio_enhancer.enhance(local_video_path)
                try:
                    self.minio.upload_clean_audio(project_id, video_id, clean_audio_path)
                except Exception as ex:
                    logger.warning(f"Temiz ses MinIO'ya yüklenirken uyarı: {ex}")

            # -------------------------------------------------------------
            # 🚀 FAZ 3.1: PARALEL GRUP 1 (STT, Sessizlik, Yüz Takibi, Waveform)
            # Bağımsız ilk analiz aşamalarını eşzamanlı olarak paralel koştur
            # -------------------------------------------------------------
            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.STT, 20,
                message="Eşzamanlı analiz grubu 1 başlatıldı (Transkripsiyon, Sessizlik, Kadraj)..."
            )

            transcript = []
            silence_cuts = []
            face_data = []
            audio_peaks = []

            def _run_transcribe():
                logger.info("🧵 Thread: Whisper transkripsiyon başladı")
                res = self.transcriber.transcribe(clean_audio_path, video_id=video_id)
                logger.info("🧵 Thread: Whisper transkripsiyon bitti")
                return res

            def _run_silence():
                if not auto_jumpcut:
                    return []
                logger.info("🧵 Thread: Sessizlik tespiti başladı")
                res = self.silence_detector.detect(clean_audio_path)
                logger.info(f"🧵 Thread: Sessizlik tespiti bitti ({len(res)} kesik)")
                return res

            def _run_face():
                if video_format not in (1, 2):  # Yalnızca 9:16 veya 1:1 formatında yüz takibi gerekir
                    return []
                logger.info("🧵 Thread: Yüz takibi başladı")
                res = self.face_tracker.track(local_video_path)
                logger.info(f"🧵 Thread: Yüz takibi bitti ({len(res)} veri)")
                return res

            def _run_peaks():
                logger.info("🧵 Thread: Dalga formu (Audio peaks) çıkarımı başladı")
                res = self._extract_audio_peaks(clean_audio_path)
                logger.info("🧵 Thread: Dalga formu çıkarımı bitti")
                return res

            with concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="AnalysisGroup1") as executor:
                f_transcribe = executor.submit(_run_transcribe)
                f_silence = executor.submit(_run_silence)
                f_face = executor.submit(_run_face)
                f_peaks = executor.submit(_run_peaks)

                transcript = f_transcribe.result()
                silence_cuts = f_silence.result()
                face_data = f_face.result()
                audio_peaks = f_peaks.result()

            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 50,
                message="Grup 1 tamamlandı. Yapay zeka ve öneri motorları başlatılıyor..."
            )

            # -------------------------------------------------------------
            # 🚀 FAZ 3.1: PARALEL GRUP 2 (Retake, Gestures, Repurposing, Suggestions, BRoll)
            # Transkript bağımlı yapay zeka modellerini eşzamanlı olarak paralel koştur
            # -------------------------------------------------------------
            retake_cuts = []
            commands = []
            repurposing_data = []
            suggestions = []
            broll_overlays = []
            fmt_str = VideoFormat.TO_STRING.get(video_format, "16:9")

            def _run_retakes():
                if not auto_retake:
                    return []
                logger.info("🧵 Thread: Akıllı retake analizi başladı")
                res = self.retake_detector.detect_retakes(clean_audio_path, transcript, silence_cuts=silence_cuts)
                logger.info(f"🧵 Thread: Akıllı retake analizi bitti ({len(res)} kesik)")
                return res

            def _run_commands():
                if not gesture_enabled:
                    return []
                logger.info("🧵 Thread: Jest ve komut motoru başladı")
                res = self.command_engine.detect(local_video_path, transcript)
                logger.info(f"🧵 Thread: Jest ve komut motoru bitti ({len(res)} komut)")
                return res

            def _run_repurposing():
                logger.info("🧵 Thread: Repurposing (viral klip) analizi başladı")
                try:
                    res = self.repurposing.analyze(transcript)
                    clip_count = len(res.clips) if hasattr(res, 'clips') else (len(res) if isinstance(res, list) else 0)
                    logger.info(f"🧵 Thread: Repurposing bitti ({clip_count} klip)")
                    return res
                except Exception as ex:
                    logger.warning(f"Repurposing analizi sırasında hata (fallback uygulandı): {ex}")
                    from models.edl_model import RepurposingData
                    return RepurposingData(clips=[])

            def _run_suggestions():
                logger.info("🧵 Thread: Öneri motoru başladı")
                try:
                    res = self.suggestion_engine.generate_suggestions(transcript)
                    logger.info(f"🧵 Thread: Öneri motoru bitti ({len(res) if isinstance(res, list) else 0} öneri)")
                    return res
                except Exception as ex:
                    logger.warning(f"Öneri motoru hatası (ihmal edildi): {ex}")
                    return []

            def _run_broll():
                if not auto_broll:
                    return []
                logger.info("🧵 Thread: B-Roll katmanı başladı")
                try:
                    res = self.auto_broll_engine.generate_broll_overlays(transcript, video_format_str=fmt_str)
                    logger.info(f"🧵 Thread: B-Roll katmanı bitti ({len(res) if isinstance(res, list) else 0} katman)")
                    return res
                except Exception as ex:
                    logger.warning(f"B-Roll katmanı hatası (ihmal edildi): {ex}")
                    return []

            with concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="AnalysisGroup2") as executor:
                f_retake = executor.submit(_run_retakes)
                f_cmd = executor.submit(_run_commands)
                f_repurpose = executor.submit(_run_repurposing)
                f_sugg = executor.submit(_run_suggestions)
                f_broll = executor.submit(_run_broll)

                retake_cuts = f_retake.result()
                commands = f_cmd.result()
                repurposing_data = f_repurpose.result()
                suggestions = f_sugg.result()
                broll_overlays = f_broll.result()

            from models.edl_model import RepurposingData
            if not isinstance(repurposing_data, RepurposingData):
                repurposing_data = RepurposingData(clips=[])

            # -------------------------------------------------------------
            # EDL Oluşturma (Tüm paralel sonuçları birleştir)
            # -------------------------------------------------------------
            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.EDL_OLUSTURMA, 95,
                message="Nihai EDL karar listesi derleniyor..."
            )
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

            # 💾 REDIS ÖNBELLEĞE KAYDET
            if Config.ENABLE_ANALYSIS_CACHE:
                self.cache.set_cached_edl(video_hash, edl_dict)

            # 10. Tamamlandı Bildirimi ve EDL'yi .NET API'ye Gönder
            self.publisher.publish_analysis_completed(project_id, video_id, edl_dict)
            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.TAMAMLANDI, 100,
                status="Completed",
                message="Analiz başarıyla tamamlandı!"
            )

            logger.info(f"🎉 Pipeline analizi başarıyla tamamlandı: VideoId={video_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"❌ Analiz pipeline hatası (VideoId={video_id}): {e}", exc_info=True)
            self.pipeline_logger.log_progress(
                project_id, video_id, "Analiz", 0,
                status="Failed",
                message=f"Hata: {str(e)}",
                error_message=str(e)
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        finally:
            heartbeat.stop()

    def _extract_audio_peaks(self, audio_path: str, num_peaks: int = 1000) -> list:
        try:
            # 🚀 Önbellekteki ses varsa diskten tekrar okuma
            cached_audio = getattr(self.retake_detector.scorer, "_cached_audio", None)
            cached_path = getattr(self.retake_detector.scorer, "_cached_path", None)
            if cached_audio is not None and cached_path == audio_path:
                audio = cached_audio
            else:
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
