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
from pipeline.audio_analysis import AudioAnalyzer, AudioAnalysis
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
        self.audio_analyzer = AudioAnalyzer()
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
        auto_subtitles = bool(msg.get("autoSubtitlesEnabled", True))
        auto_director = bool(msg.get("autoDirectorEnabled", True))
        direct_to_editor = bool(msg.get("directToEditor", False))

        logger.info(
            f"🎬 VideoUploadedEvent alındı: VideoId={video_id}, ProjectId={project_id}, "
            f"Format={video_format}, JumpCut={auto_jumpcut}, Retake={auto_retake}, "
            f"BRoll={auto_broll}, Subs={auto_subtitles}, AutoDirector={auto_director}, "
            f"DirectToEditor={direct_to_editor}"
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

            # 🚀 REDIS IDEMPOTENCY KONTROLÜ (SHA-256 + Pipeline Bayrakları İle Bileşik Anahtar)
            video_hash = self.cache.compute_video_hash(local_video_path)
            cache_key = (
                f"v4:{video_hash}:fmt={video_format}:jc={int(auto_jumpcut)}:rt={int(auto_retake)}"
                f":br={int(auto_broll)}:sub={int(auto_subtitles)}:au={int(audio_enhancement)}"
                f":gs={int(gesture_enabled)}:ad={int(auto_director)}"
            )
            if Config.ENABLE_ANALYSIS_CACHE:
                cached_edl = self.cache.get_cached_edl(cache_key)
                if cached_edl:
                    logger.info(f"⚡ Mükerrer dosya/ayar kombinasyonu tespit edildi! Redis önbelleğinden anında sonuç dönülüyor (VideoId={video_id})")
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

            # ⚡ DIRECT-TO-EDITOR HIZLI GEÇİŞ YOLU (Fast Path)
            if direct_to_editor or not any([
                auto_jumpcut, auto_retake, auto_broll, auto_subtitles, audio_enhancement, gesture_enabled
            ]):
                logger.info(f"⚡ Direct-to-Editor Hızlı Geçiş (Fast Path) aktif! STT ve ağır analizler atlanıyor (VideoId={video_id})")
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.SES_IYILESTIRME, 40,
                    message="Hızlı Editör Modu: Ses dalga formu (Waveform) çıkarılıyor..."
                )
                analysis = self.audio_analyzer.analyze(local_video_path)
                from models.transcript_model import TranscriptResult
                from models.edl_model import RepurposingData
                minimal_transcript = TranscriptResult(
                    full_text="",
                    duration=float(getattr(analysis, "duration", 0.0)),
                    segments=[],
                    words=[],
                )
                edl_dict = self.edl_builder.build(
                    project_id=project_id,
                    video_id=video_id,
                    transcript=minimal_transcript,
                    silence_cuts=[],
                    commands=[],
                    face_data=[],
                    repurposing_data=RepurposingData(clips=[]),
                    suggestions=[],
                    video_format=video_format,
                    extra_cuts=[],
                    extra_overlays=[],
                    audio_peaks=analysis.peaks,
                    video_duration=getattr(analysis, "duration", None),
                    subtitles_enabled=False,
                    auto_director=False,
                )
                if Config.ENABLE_ANALYSIS_CACHE:
                    self.cache.set_cached_edl(cache_key, edl_dict)
                self.publisher.publish_analysis_completed(project_id, video_id, edl_dict)
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.TAMAMLANDI, 100,
                    status="Completed",
                    message="Video doğrudan editöre hazırlandı!"
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

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
            # 🚀 ADIM 1: SES ANALİZİ (VAD + RMS Zarfı + Waveform Peaks)
            # Orijinal videodan tek seferde PCM ve Silero VAD analizi yapılır
            # -------------------------------------------------------------
            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.SES_IYILESTIRME, 18,
                message="Akustik enerji ve VAD ses analizi yapılıyor..."
            )
            analysis = self.audio_analyzer.analyze(local_video_path)
            audio_peaks = analysis.peaks

            # -------------------------------------------------------------
            # 🚀 FAZ 3.1: PARALEL GRUP 1 (STT + Yüz Takibi)
            # -------------------------------------------------------------
            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.STT, 25,
                message="Eşzamanlı analiz grubu 1 başlatıldı (Transkripsiyon, Kadraj)..."
            )

            transcript = None
            face_data = []

            def on_stt_progress(current_chunk: int, total_chunks: int, msg: str):
                pct = int(25 + (current_chunk / max(1, total_chunks)) * 30)
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.STT, pct,
                    message=f"Transkripsiyon: {msg}"
                )

            def _run_transcribe():
                logger.info("🧵 Thread: STT orkestrasyonu başladı")
                res = self.transcriber.transcribe(
                    clean_audio_path,
                    analysis=analysis,
                    video_id=video_id,
                    on_progress=on_stt_progress
                )
                logger.info("🧵 Thread: STT orkestrasyonu bitti")
                return res

            def _run_face():
                if video_format not in (1, 2) and not auto_director:
                    return []
                logger.info("🧵 Thread: Yüz takibi başladı")
                sample_interval = 1.5 if video_format not in (1, 2) else 0.4
                res = self.face_tracker.track(local_video_path, sample_interval_sec=sample_interval)
                logger.info(f"🧵 Thread: Yüz takibi bitti ({len(res)} veri)")
                return res

            with concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="AnalysisGroup1") as executor:
                f_transcribe = executor.submit(_run_transcribe)
                f_face = executor.submit(_run_face)

                transcript = f_transcribe.result()
                face_data = f_face.result()

            self.pipeline_logger.log_progress(
                project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 60,
                message="Jump-Cut v2: Konuşma korumalı sessizlik kesimleri yapılıyor..."
            )

            # -------------------------------------------------------------
            # 🚀 FAZ 3.2: RETAKE, JUMP-CUT v3 VE PARALEL ANALİZLER
            # -------------------------------------------------------------
            # 1. Aşama: Akıllı Retake Taraması (Take-Aware v3)
            retake_cuts = []
            if auto_retake:
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 65,
                    message="Akıllı Yönetmen: Çekim tekrarları (Take-Aware Retake) taranıyor..."
                )
                logger.info("🎬 Akıllı Retake analizi başladı")
                retake_cuts = self.retake_detector.detect_retakes(
                    clean_audio_path,
                    transcript,
                    analysis=analysis
                )
                logger.info(f"🎬 Akıllı Retake analizi bitti ({len(retake_cuts)} kesim)")

            # 2. Aşama: Jump-Cut v3 (Korunan Kelimeler Arası Boşluk Sıkıştırma)
            silence_cuts = []
            if auto_jumpcut:
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.SESSIZLIK_ALGILAMA, 75,
                    message="Jump-Cut v3: Korunan kelimeler arası duraklamalar sıkıştırılıyor..."
                )
                logger.info("✂️ Jump-Cut v3 hesaplanıyor (korunan kelimeler arası)...")
                silence_cuts = self.silence_detector.detect_v2(
                    analysis=analysis,
                    transcript_words=transcript.words,
                    existing_cuts=retake_cuts
                )
                logger.info(f"✂️ Jump-Cut v3 bitti ({len(silence_cuts)} kesim)")

            # 3. Aşama: Altyazı Segmentlerini Kesim Sınırlarına Göre Yeniden Üret
            all_detected_cuts = retake_cuts + silence_cuts
            if all_detected_cuts and transcript.words:
                logger.info("📝 Altyazı mikro-segmentleri kesim sınırlarına göre güncelleniyor...")
                transcript.segments = self.transcriber.regenerate_segments_with_cuts(
                    words=transcript.words,
                    cuts=all_detected_cuts
                )

            # 4. Aşama: Geri Kalan Paralel İşler (Gestures, Repurposing, Suggestions, BRoll)
            commands = []
            repurposing_data = []
            suggestions = []
            broll_overlays = []
            fmt_str = VideoFormat.TO_STRING.get(video_format, "16:9")

            def _run_commands():
                if not gesture_enabled:
                    return []
                logger.info("🧵 Thread: Jest ve komut motoru başladı")
                res = self.command_engine.detect(local_video_path, transcript)
                logger.info(f"🧵 Thread: Jest ve komut motoru bitti ({len(res)} komut)")
                return res

            def _run_repurposing():
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.REPURPOSING, 85,
                    message="Viral klip (Reels / Shorts) anları seçiliyor..."
                )
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
                self.pipeline_logger.log_progress(
                    project_id, video_id, PipelineStage.ONERI_OLUSTURMA, 88,
                    message="Yapay Zeka: B-Roll görsel ve vurgu önerileri üretiliyor..."
                )
                logger.info("🧵 Thread: Öneri motoru başladı")
                try:
                    res = self.suggestion_engine.generate_suggestions(transcript)
                    logger.info(f"🧵 Thread: Öneri motoru bitti ({len(res) if isinstance(res, list) else 0} öneri)")
                    return res
                except Exception as ex:
                    logger.warning(f"Öneri motoru hatası (ihmal edildi): {ex}")
                    return []

            def _run_broll():
                if not auto_broll or auto_director:
                    return []
                logger.info("🧵 Thread: B-Roll katmanı başladı")
                try:
                    res = self.auto_broll_engine.generate_broll_overlays(transcript, video_format_str=fmt_str)
                    logger.info(f"🧵 Thread: B-Roll katmanı bitti ({len(res) if isinstance(res, list) else 0} katman)")
                    return res
                except Exception as ex:
                    logger.warning(f"B-Roll katmanı hatası (ihmal edildi): {ex}")
                    return []

            with concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="AnalysisGroup2") as executor:
                f_cmd = executor.submit(_run_commands)
                f_repurpose = executor.submit(_run_repurposing)
                f_sugg = executor.submit(_run_suggestions)
                f_broll = executor.submit(_run_broll)

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
                audio_peaks=audio_peaks,
                video_duration=getattr(analysis, "duration", None),
                subtitles_enabled=auto_subtitles,
                auto_director=auto_director,
                video_path=local_video_path,
            )

            # 💾 REDIS ÖNBELLEĞE KAYDET
            if Config.ENABLE_ANALYSIS_CACHE:
                self.cache.set_cached_edl(cache_key, edl_dict)

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
            if getattr(Config, "TEMP_RETENTION", "after_job") == "after_job":
                from utils.janitor import cleanup_files
                to_clean = []
                if 'clean_audio_path' in locals() and clean_audio_path != local_video_path:
                    to_clean.append(clean_audio_path)
                if 'local_video_path' in locals():
                    to_clean.append(local_video_path)
                cleanup_files(*to_clean)

