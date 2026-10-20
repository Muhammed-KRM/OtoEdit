import json
import pytest
from unittest.mock import MagicMock, patch
from consumers.analysis_consumer import AnalysisConsumer
from utils.constants import PipelineStage


@pytest.fixture
def mock_consumer():
    with patch("consumers.analysis_consumer.MinioClient"), \
         patch("consumers.analysis_consumer.RabbitMQPublisher"), \
         patch("consumers.analysis_consumer.PipelineLogger"), \
         patch("consumers.analysis_consumer.AnalysisCacheService"), \
         patch("consumers.analysis_consumer.AudioEnhancer"), \
         patch("consumers.analysis_consumer.AudioAnalyzer"), \
         patch("consumers.analysis_consumer.Transcriber"), \
         patch("consumers.analysis_consumer.SilenceDetector"), \
         patch("consumers.analysis_consumer.RetakeDetector"), \
         patch("consumers.analysis_consumer.MultimodalCommandEngine"), \
         patch("consumers.analysis_consumer.FaceTracker"), \
         patch("consumers.analysis_consumer.RepurposingEngine"), \
         patch("consumers.analysis_consumer.SuggestionEngine"), \
         patch("consumers.analysis_consumer.AutoBrollEngine"), \
         patch("consumers.analysis_consumer.EdlBuilder"):
        consumer = AnalysisConsumer()
        return consumer


def test_consumer_cache_hit_bypasses_pipeline(mock_consumer):
    # Setup mock channel and method
    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 101

    payload = {
        "videoId": "vid-1",
        "projectId": "proj-1",
        "videoFormati": 0,
        "dosyaYolu": "videos/proj-1/vid-1.mp4"
    }
    body = json.dumps(payload).encode("utf-8")

    # Minio mock
    mock_consumer.minio.download_video.return_value = "/tmp/fake.mp4"

    # Cache hit mock
    mock_consumer.cache.compute_video_hash.return_value = "fake_sha256"
    mock_consumer.cache.get_cached_edl.return_value = {"edl": "cached_version_1"}

    # Mock heartbeat keeper
    with patch("consumers.analysis_consumer.RabbitHeartbeatKeeper"), \
         patch("consumers.analysis_consumer.Config.ENABLE_ANALYSIS_CACHE", True):
        mock_consumer._on_message(mock_ch, mock_method, None, body)

    # Verify: Transcriber or heavy steps should NOT be called on cache hit
    mock_consumer.transcriber.transcribe.assert_not_called()
    mock_consumer.silence_detector.detect_v2.assert_not_called()

    # Verify: Completed event published and message acknowledged
    mock_consumer.publisher.publish_analysis_completed.assert_called_once_with(
        "proj-1", "vid-1", {"edl": "cached_version_1"}
    )
    mock_ch.basic_ack.assert_called_once_with(delivery_tag=101)


def test_consumer_full_parallel_pipeline_execution(mock_consumer):
    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 202

    payload = {
        "videoId": "vid-2",
        "projectId": "proj-2",
        "videoFormati": 1,  # 9:16 (triggers face tracker)
        "dosyaYolu": "videos/proj-2/vid-2.mp4",
        "audioEnhancementEnabled": True,
        "autoJumpcutEnabled": True,
        "autoRetakeEnabled": True,
        "autoBrollEnabled": True
    }
    body = json.dumps(payload).encode("utf-8")

    mock_consumer.minio.download_video.return_value = "/tmp/video.mp4"
    mock_consumer.cache.compute_video_hash.return_value = "fresh_hash_456"
    mock_consumer.cache.get_cached_edl.return_value = None  # Cache miss

    # Pipeline mock returns
    mock_analysis = MagicMock()
    mock_analysis.peaks = [0.1, 0.5]
    mock_consumer.audio_analyzer.analyze.return_value = mock_analysis

    mock_transcript = MagicMock()
    mock_transcript.words = []
    mock_transcript.segments = []
    mock_consumer.audio_enhancer.enhance.return_value = "/tmp/clean.wav"
    mock_consumer.transcriber.transcribe.return_value = mock_transcript
    mock_consumer.silence_detector.detect_v2.return_value = [{"start": 2.1, "end": 3.5}]
    mock_consumer.face_tracker.track.return_value = [{"time": 1.0, "box": [10, 10, 50, 50]}]
    mock_consumer.retake_detector.detect_retakes.return_value = []
    mock_consumer.command_engine.detect.return_value = []
    mock_consumer.repurposing.analyze.return_value = []
    mock_consumer.suggestion_engine.generate_suggestions.return_value = []
    mock_consumer.auto_broll_engine.generate_broll_overlays.return_value = []
    mock_consumer.edl_builder.build.return_value = {"status": "ok", "tracks": []}

    with patch("consumers.analysis_consumer.RabbitHeartbeatKeeper"), \
         patch("consumers.analysis_consumer.Config.ENABLE_ANALYSIS_CACHE", True):
        mock_consumer._on_message(mock_ch, mock_method, None, body)

    # All parallel components must have been executed
    mock_consumer.transcriber.transcribe.assert_called_once()
    mock_consumer.silence_detector.detect_v2.assert_called_once()
    mock_consumer.face_tracker.track.assert_called_once()
    mock_consumer.retake_detector.detect_retakes.assert_called_once()
    mock_consumer.command_engine.detect.assert_called_once()
    mock_consumer.repurposing.analyze.assert_called_once()
    mock_consumer.suggestion_engine.generate_suggestions.assert_called_once()
    mock_consumer.auto_broll_engine.generate_broll_overlays.assert_called_once()
    mock_consumer.edl_builder.build.assert_called_once()

    # Cached for future requests with composite cache key
    expected_cache_key = "fresh_hash_456:fmt=1:jc=1:rt=1:br=1:sub=1:au=1:gs=1:ad=1"
    mock_consumer.cache.set_cached_edl.assert_called_once_with(expected_cache_key, {"status": "ok", "tracks": []})
    mock_consumer.publisher.publish_analysis_completed.assert_called_once()
    mock_ch.basic_ack.assert_called_once_with(delivery_tag=202)


def test_consumer_direct_to_editor_fast_path(mock_consumer):
    """Verify directToEditor=True skips STT, Retake, Silence, Face, Gesture, Repurposing, and B-Roll."""
    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 303

    payload = {
        "videoId": "vid-fast",
        "projectId": "proj-fast",
        "videoFormati": 0,
        "dosyaYolu": "videos/proj-fast/vid-fast.mp4",
        "directToEditor": True,
    }
    body = json.dumps(payload).encode("utf-8")

    mock_consumer.minio.download_video.return_value = "/tmp/fast.mp4"
    mock_consumer.cache.compute_video_hash.return_value = "fast_hash_789"
    mock_consumer.cache.get_cached_edl.return_value = None

    mock_analysis = MagicMock()
    mock_analysis.duration = 42.5
    mock_analysis.peaks = [0.12, 0.45, 0.78]
    mock_consumer.audio_analyzer.analyze.return_value = mock_analysis
    mock_consumer.edl_builder.build.return_value = {"projectId": "proj-fast", "duration": 42.5}

    with patch("consumers.analysis_consumer.RabbitHeartbeatKeeper"), \
         patch("consumers.analysis_consumer.Config.ENABLE_ANALYSIS_CACHE", True):
        mock_consumer._on_message(mock_ch, mock_method, None, body)

    mock_consumer.audio_analyzer.analyze.assert_called_once_with("/tmp/fast.mp4")
    mock_consumer.transcriber.transcribe.assert_not_called()
    mock_consumer.retake_detector.detect_retakes.assert_not_called()
    mock_consumer.silence_detector.detect_v2.assert_not_called()
    mock_consumer.face_tracker.track.assert_not_called()
    mock_consumer.command_engine.detect.assert_not_called()
    mock_consumer.auto_broll_engine.generate_broll_overlays.assert_not_called()

    build_kwargs = mock_consumer.edl_builder.build.call_args.kwargs
    assert build_kwargs["subtitles_enabled"] is False
    assert build_kwargs["auto_director"] is False
    mock_consumer.publisher.publish_analysis_completed.assert_called_once()
    mock_ch.basic_ack.assert_called_once_with(delivery_tag=303)
