import pytest
from unittest.mock import MagicMock, patch
from pipeline.retake_detector import RetakeDetector
from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp

def test_meta_speech_detection():
    detector = RetakeDetector()
    assert detector.is_meta_speech("Bu da olmadı başasar.") is True
    assert detector.is_meta_speech("Birinci öncül başasar.") is True
    assert detector.is_meta_speech("ve Allah konuşamadık.") is True
    assert detector.is_meta_speech("Birinci öncül bütün insanlar ölümlüdür.") is False

def test_ordinal_conflict_protection():
    detector = RetakeDetector()
    s1 = "Birinci öncül bütün insanlar ölümlüdür."
    s2 = "İkinci öncül Sokrates bir insandır."
    # Ordinal conflict means similarity must be 0.0, avoiding accidental false positive retake
    sim = detector.calculate_similarity(s1, s2)
    assert sim == 0.0

def test_exact_duplicate_detection():
    detector = RetakeDetector()
    s1 = "Aristot mantığı bağımsız bir bilim dalı olarak görmemiş."
    s2 = "Aristot mantığı bağımsız bir bilim dalı olarak görmemiş."
    sim = detector.calculate_similarity(s1, s2)
    assert sim >= 0.80

def test_retake_detector_identifies_meta_and_keeps_clean_speech():
    detector = RetakeDetector()
    # Mock scorer to avoid needing a real audio file
    detector.scorer = MagicMock()
    detector.scorer.score_audio_segment.return_value = {
        "composite_acoustic_score": 90.0,
        "clipping_score": 95.0,
        "current_rms_db": -20.0
    }

    segments = [
        TranscriptSegment(start=10.0, end=14.0, text="Bu da olmadı başasar."),
        TranscriptSegment(start=15.0, end=19.0, text="Birinci öncül bütün insanlar ölümlüdür."),
        TranscriptSegment(start=20.0, end=24.0, text="İkinci öncül Sokrates bir insandır.")
    ]
    transcript = TranscriptResult(
        full_text="Test",
        segments=segments,
        words=[],
        duration=30.0
    )

    cuts = detector.detect_retakes("dummy_audio.wav", transcript)
    
    # "Bu da olmadı başasar" must be cut
    cut_reasons = [c.command for c in cuts]
    assert any("Bu da olmadı başasar" in r for r in cut_reasons)
    
    # Neither premise 1 nor premise 2 should be cut
    assert not any("bütün insanlar ölümlüdür" in r for r in cut_reasons)
    assert not any("Sokrates bir insandır" in r for r in cut_reasons)
