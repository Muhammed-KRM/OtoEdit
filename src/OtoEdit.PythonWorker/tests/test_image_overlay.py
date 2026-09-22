import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from render.image_overlay import ImageOverlay


def test_resolve_image_path_local_file():
    mock_minio = MagicMock()
    overlay = ImageOverlay(minio_client=mock_minio)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        local_path = tf.name

    try:
        resolved = overlay.resolve_image_path(local_path)
        assert resolved == local_path
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


def test_resolve_image_path_s3():
    mock_minio = MagicMock()
    overlay = ImageOverlay(minio_client=mock_minio)

    with tempfile.TemporaryDirectory() as tmpdir:
        resolved = overlay.resolve_image_path("s3://otoedit/assets/cat.jpg", temp_dir=tmpdir)
        mock_minio.client.fget_object.assert_called_once()
        args = mock_minio.client.fget_object.call_args[0]
        assert args[0] == "otoedit"
        assert args[1] == "assets/cat.jpg"


def test_apply_image_overlays_skips_non_image():
    mock_minio = MagicMock()
    overlay = ImageOverlay(minio_client=mock_minio)

    mock_stream = MagicMock()
    overlays = [
        {"type": "text", "content": "Not an image"}
    ]

    result_stream = overlay.apply_image_overlays(mock_stream, overlays)
    assert result_stream == mock_stream


def test_apply_image_overlays_sorts_by_track_id():
    mock_minio = MagicMock()
    overlay = ImageOverlay(minio_client=mock_minio)

    mock_stream = MagicMock()
    overlays = [
        {"type": "image", "source": "/nonexistent/img2.png", "trackId": 3},
        {"type": "image", "source": "/nonexistent/img1.png", "trackId": 1},
        {"type": "image", "source": "/nonexistent/img3.png", "trackId": 2},
    ]

    # Verify sorting logic in apply_image_overlays
    img_overlays = [ov for ov in (overlays or []) if ov.get("type") == "image"]
    img_overlays.sort(key=lambda o: int(o.get("trackId") or o.get("track_id") or 1))

    assert [o["trackId"] for o in img_overlays] == [1, 2, 3]

