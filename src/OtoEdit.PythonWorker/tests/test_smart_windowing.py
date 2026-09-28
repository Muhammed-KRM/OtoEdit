from unittest.mock import MagicMock
import pytest
from models.command_model import CommandType, ParsedCommand
from models.gesture_model import GestureResult, GestureType
from models.transcript_model import TranscriptResult
from pipeline.multimodal_command_engine import MultimodalCommandEngine


def test_smart_windowing_skips_when_no_voice_commands():
    engine = MultimodalCommandEngine(tolerance_seconds=2.0)
    engine.voice_parser.parse_transcript = MagicMock(return_value=[])
    engine.gesture_detector.detect_gestures = MagicMock()

    transcript = TranscriptResult(full_text="Normal konuşma yapılıyor...", segments=[])
    result = engine.detect("sample.mp4", transcript)

    # Sesli komut yoksa el hareketi taraması hiç çağrılmamalı (Tasarruf: %100)
    assert result == []
    engine.gesture_detector.detect_gestures.assert_not_called()


def test_smart_windowing_scans_only_target_windows():
    engine = MultimodalCommandEngine(tolerance_seconds=2.0)

    # 45.0 saniyede bir "burayı kes" komutu var
    candidate_vc = ParsedCommand(
        command_type=CommandType.CUT,
        raw_text="burayı kes",
        timestamp=45.0,
        start=44.0,
        end=46.0
    )
    engine.voice_parser.parse_transcript = MagicMock(return_value=[candidate_vc])

    # Mock jest dönüşü
    engine.gesture_detector.detect_gestures = MagicMock(return_value=[
        GestureResult(gesture_type=GestureType.THUMBS_DOWN, timestamp=45.2, confidence=0.9)
    ])

    transcript = TranscriptResult(full_text="burayı kes", segments=[])
    result = engine.detect("sample.mp4", transcript)

    # detect_gestures sadece hedeflenen pencere parametresi ile çağrılmalı!
    engine.gesture_detector.detect_gestures.assert_called_once()
    _, kwargs = engine.gesture_detector.detect_gestures.call_args
    target_windows = kwargs.get("target_windows")
    assert target_windows is not None
    assert len(target_windows) == 1

    win_start, win_end = target_windows[0]
    assert win_start <= 43.0  # 45.0 - 2.0 - 0.5 = 42.5
    assert win_end >= 47.0    # 45.0 + 2.0 + 0.5 = 47.5

    # Komut onaylanmalı
    assert len(result) == 1
    assert result[0].command_type == CommandType.CUT
