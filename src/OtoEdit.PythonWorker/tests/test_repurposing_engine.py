import pytest
from unittest.mock import MagicMock
from models.transcript_model import TranscriptResult
from pipeline.repurposing_engine import RepurposingEngine


def test_repurposing_engine_analyze_with_mock():
    engine = RepurposingEngine()

    mock_clips = [
        {
            "id": "clip_reels_1",
            "title": "Vurucu Giriş",
            "start": 5.0,
            "end": 35.0,
            "duration": 30.0,
            "targetFormat": "9:16",
            "viralityScore": 92,
            "reason": "Yüksek merak uyandıran soru"
        },
        {
            "id": "clip_shorts_1",
            "title": "Ana Fikir",
            "start": 60.0,
            "end": 120.0,
            "duration": 60.0,
            "targetFormat": "9:16",
            "viralityScore": 88,
            "reason": "Açıklayıcı örnek"
        }
    ]

    engine.gemini_client.find_viral_clips = MagicMock(return_value=mock_clips)

    transcript = TranscriptResult(
        full_text="Merhaba arkadaşlar bugün önemli bir konudan bahsedeceğiz...",
        duration=180.0,
        segments=[]
    )

    result = engine.analyze(transcript)

    assert result is not None
    assert len(result.clips) == 2
    assert result.clips[0].id == "clip_reels_1"
    assert result.clips[0].targetFormat == "9:16"
    assert result.clips[0].viralityScore == 92
    assert result.clips[1].duration == 60.0


def test_repurposing_engine_fallback_when_empty_clips():
    engine = RepurposingEngine()
    engine.gemini_client.find_viral_clips = MagicMock(return_value=[])

    transcript = TranscriptResult(
        full_text="Kısa video",
        duration=30.0,
        segments=[]
    )

    result = engine.analyze(transcript)
    assert result is not None
    assert len(result.clips) == 0
