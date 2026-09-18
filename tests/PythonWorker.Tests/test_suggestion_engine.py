import pytest
from unittest.mock import MagicMock
from models.transcript_model import TranscriptResult
from pipeline.suggestion_engine import SuggestionEngine


def test_suggestion_engine_generates_broll_and_text():
    engine = SuggestionEngine()

    mock_raw_suggestions = [
        {
            "id": "sug_1",
            "type": "image_broll",
            "title": "Doğa Manzarası",
            "content": "forest nature landscape",
            "timestamp": 12.0,
            "duration": 4.0,
            "reason": "Ormanlardan bahsedildiği an"
        },
        {
            "id": "sug_2",
            "type": "text_highlight",
            "title": "Önemli Alıntı",
            "content": "Gelecek Burada Başlıyor",
            "timestamp": 45.0,
            "duration": 5.0,
            "reason": "Vurucu slogan"
        }
    ]

    engine.gemini_client.generate_content_suggestions = MagicMock(return_value=mock_raw_suggestions)
    engine.pexels_client.search_photo = MagicMock(return_value="https://images.pexels.com/forest.jpg")

    transcript = TranscriptResult(
        full_text="Doğa ve teknoloji geleceği şekillendiriyor...",
        duration=90.0,
        segments=[]
    )

    suggestions = engine.generate_suggestions(transcript)

    assert len(suggestions) == 2

    # İlk öneri: görsel b-roll
    assert suggestions[0].id == "sug_1"
    assert suggestions[0].type == "image_broll"
    assert suggestions[0].sourceUrl == "https://images.pexels.com/forest.jpg"
    assert suggestions[0].status == "pending"

    # İkinci öneri: metin vurgusu
    assert suggestions[1].id == "sug_2"
    assert suggestions[1].type == "text_highlight"
    assert suggestions[1].content == "Gelecek Burada Başlıyor"
    assert suggestions[1].sourceUrl is None
