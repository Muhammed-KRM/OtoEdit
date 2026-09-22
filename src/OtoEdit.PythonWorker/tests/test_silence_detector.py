import pytest
from unittest.mock import MagicMock, patch
from pipeline.silence_detector import SilenceDetector


def test_silence_detector_detects_and_applies_padding():
    detector = SilenceDetector(min_silence_len=500, silence_thresh=-35, padding_sec=0.1)

    # 1.0s - 3.0s ve 5.0s - 8.0s aralarında sessizlik simüle ediyoruz
    mock_ranges = [
        (1000, 3000),  # 2000ms -> padding sonrası 1.1s - 2.9s (fark 1.8s >= 0.2s)
        (5000, 8000),  # 3000ms -> padding sonrası 5.1s - 7.9s (fark 2.8s >= 0.2s)
        (10000, 10250) # 250ms -> padding sonrası 10.1s - 10.15s (fark 0.05s < 0.2s, atlanmalı)
    ]

    with patch("pydub.AudioSegment.from_file") as mock_audio, \
         patch("pydub.silence.detect_silence", return_value=mock_ranges):
        
        cuts = detector.detect("sample.mp4")

        assert len(cuts) == 2
        assert cuts[0].id == "cut_silence_1"
        assert cuts[0].start == 1.1
        assert cuts[0].end == 2.9
        assert cuts[0].reason == "silence"

        assert cuts[1].id == "cut_silence_2"
        assert cuts[1].start == 5.1
        assert cuts[1].end == 7.9


def test_silence_detector_handles_exception_gracefully():
    detector = SilenceDetector()

    with patch("pydub.AudioSegment.from_file", side_effect=RuntimeError("Dosya bozuk")):
        cuts = detector.detect("corrupted.mp4")
        assert cuts == []
