import os
import tempfile
import pytest
from unittest.mock import MagicMock
from render.video_renderer import VideoRenderer


def test_video_renderer_get_keep_segments():
    mock_minio = MagicMock()
    renderer = VideoRenderer(minio_client=mock_minio)

    cuts = [
        {"start": 10.0, "end": 15.0},
        {"start": 30.0, "end": 40.0}
    ]
    total_duration = 100.0

    keep = renderer._get_keep_segments(cuts, total_duration)
    assert keep == [(0.0, 10.0), (15.0, 30.0), (40.0, 100.0)]


def test_video_renderer_get_keep_segments_no_cuts():
    mock_minio = MagicMock()
    renderer = VideoRenderer(minio_client=mock_minio)

    cuts = []
    total_duration = 50.0
    keep = renderer._get_keep_segments(cuts, total_duration)
    assert keep == [(0.0, 50.0)]


def test_video_renderer_create_concat_file():
    mock_minio = MagicMock()
    renderer = VideoRenderer(minio_client=mock_minio)

    with tempfile.TemporaryDirectory() as tmpdir:
        concat_file = os.path.join(tmpdir, "concat.txt")
        segments = [(0.0, 10.0), (15.0, 25.0)]
        video_path = "/tmp/sample.mp4"

        renderer._create_concat_file(segments, video_path, concat_file)
        assert os.path.exists(concat_file)

        with open(concat_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 6
        assert "inpoint 0.0\n" in lines
        assert "outpoint 10.0\n" in lines
        assert "inpoint 15.0\n" in lines
        assert "outpoint 25.0\n" in lines
