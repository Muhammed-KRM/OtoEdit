"""
Gemini Transcribe Parser Birim Testi
"""

import json
from pathlib import Path
from pipeline.stt.gemini_transcribe import GeminiTranscribeEngine


def test_gemini_transcribe_parser_with_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "gemini_transcribe_response.json"
    assert fixture_path.exists(), "Fixture dosyası bulunamadı!"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    engine = GeminiTranscribeEngine(api_keys=["test_dummy_key"])
    words = engine.parse_response(data, chunk_offset=10.0)

    # 1. Kelime sayısı doğrulaması
    assert len(words) >= 400

    # 2. Bismillah doğrulaması (Bulgu 2)
    first_word = words[0]
    assert "Bismillahirrahmanirrahim" in first_word.word
    assert first_word.start == 12.100  # 10.0s offset + 2.100s
    assert first_word.end == 13.200    # 10.0s offset + 3.200s
