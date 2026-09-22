import pytest
from unittest.mock import MagicMock
from models.command_model import CommandType, ParsedCommand
from models.gesture_model import GestureResult, GestureType
from models.transcript_model import TranscriptResult
from pipeline.multimodal_command_engine import MultimodalCommandEngine


def test_multimodal_matching_gesture_and_voice_confirmed():
    engine = MultimodalCommandEngine(tolerance_seconds=2.0)

    # 10.0 saniyede Thumbs Down (dislike) el hareketi
    mock_gestures = [
        GestureResult(gesture_type=GestureType.THUMBS_DOWN, timestamp=10.0, confidence=0.9)
    ]
    # 11.0 saniyede "burayı kes" sesli komutu (fark 1.0s <= 2.0s)
    mock_voices = [
        ParsedCommand(command_type=CommandType.CUT, raw_text="burayı kes", timestamp=11.0, start=9.0, end=11.0)
    ]

    engine.gesture_detector.detect_gestures = MagicMock(return_value=mock_gestures)
    engine.voice_parser.parse_transcript = MagicMock(return_value=mock_voices)

    transcript = TranscriptResult(full_text="burayı kes", segments=[])
    confirmed = engine.detect("dummy_video.mp4", transcript)

    assert len(confirmed) == 1
    assert confirmed[0].command_type == CommandType.CUT
    assert confirmed[0].timestamp == 10.0
    assert confirmed[0].raw_text == "burayı kes"
    assert confirmed[0].start == 9.0
    assert confirmed[0].end == 11.0


def test_multimodal_type_mismatch_not_confirmed():
    engine = MultimodalCommandEngine(tolerance_seconds=2.0)

    mock_gestures = [
        GestureResult(gesture_type=GestureType.THUMBS_UP, timestamp=10.0, confidence=0.9)
    ]
    mock_voices = [
        ParsedCommand(command_type=CommandType.CUT, raw_text="burayı kes", timestamp=10.5)
    ]

    engine.gesture_detector.detect_gestures = MagicMock(return_value=mock_gestures)
    engine.voice_parser.parse_transcript = MagicMock(return_value=mock_voices)

    transcript = TranscriptResult(full_text="burayı kes", segments=[])
    confirmed = engine.detect("dummy_video.mp4", transcript)

    assert len(confirmed) == 0


def test_multimodal_time_tolerance_exceeded_not_confirmed():
    engine = MultimodalCommandEngine(tolerance_seconds=2.0)

    # Hareket 10.0s, ses komutu 15.0s (fark 5s > 2s)
    mock_gestures = [
        GestureResult(gesture_type=GestureType.THUMBS_DOWN, timestamp=10.0, confidence=0.9)
    ]
    mock_voices = [
        ParsedCommand(command_type=CommandType.CUT, raw_text="burayı kes", timestamp=15.0)
    ]

    engine.gesture_detector.detect_gestures = MagicMock(return_value=mock_gestures)
    engine.voice_parser.parse_transcript = MagicMock(return_value=mock_voices)

    transcript = TranscriptResult(full_text="burayı kes", segments=[])
    confirmed = engine.detect("dummy_video.mp4", transcript)

    assert len(confirmed) == 0
