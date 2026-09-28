import pytest
from unittest.mock import MagicMock, patch
from services.pipeline_logger import PipelineLogger
from utils.constants import PipelineStage


def test_pipeline_logger_success_flow():
    mock_publisher = MagicMock()
    logger_service = PipelineLogger(
        api_base_url="http://mock-api.local",
        api_key="test-key",
        publisher=mock_publisher
    )

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200

        logger_service.log_progress(
            project_id="proj-123",
            video_id="vid-456",
            stage_name=PipelineStage.STT,
            progress_pct=25,
            status="InProgress",
            message="Transkripsiyon yapılıyor..."
        )

        # 2. Katman: RabbitMQ yayınlandı mı?
        mock_publisher.publish_stage_changed.assert_called_once_with(
            project_id="proj-123",
            video_id="vid-456",
            asama=PipelineStage.STT,
            yuzde=25,
            mesaj="Transkripsiyon yapılıyor..."
        )

        # 3. Katman: HTTP REST API çağrıldı mı?
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["projectId"] == "proj-123"
        assert call_kwargs["json"]["stage"] == PipelineStage.STT
        assert call_kwargs["headers"]["X-API-Key"] == "test-key"


def test_pipeline_logger_error_flow():
    mock_publisher = MagicMock()
    logger_service = PipelineLogger(
        api_base_url="http://mock-api.local",
        publisher=mock_publisher
    )

    with patch("requests.post") as mock_post:
        logger_service.log_progress(
            project_id="proj-123",
            video_id="vid-456",
            stage_name="Analiz",
            progress_pct=0,
            status="Failed",
            message="Kritik hata",
            error_message="Video formatı desteklenmiyor"
        )

        mock_publisher.publish_pipeline_error.assert_called_once_with(
            project_id="proj-123",
            video_id="vid-456",
            asama="Analiz",
            hata_mesaji="Video formatı desteklenmiyor"
        )


def test_pipeline_logger_api_failure_fail_safe():
    mock_publisher = MagicMock()
    logger_service = PipelineLogger(
        api_base_url="http://unreachable-host:9999",
        publisher=mock_publisher
    )

    with patch("requests.post", side_effect=Exception("Network Connection Refused")):
        # API çökse veya ulaşılamasa dahi metod HATA FIRLATMAMALIDIR (Fail-Safe)
        logger_service.log_progress(
            project_id="proj-123",
            video_id="vid-456",
            stage_name=PipelineStage.RENDER,
            progress_pct=50
        )
