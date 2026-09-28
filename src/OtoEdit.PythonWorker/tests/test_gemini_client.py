import pytest
from services.gemini_client import GeminiClient


def test_gemini_client_extract_json_markdown():
    client = GeminiClient()
    markdown_text = """
    Tabii ki! İşte hazırladığım viral video klipleri:
    ```json
    [
      {
        "id": "clip_1",
        "title": "Harika An",
        "start": 10.0,
        "end": 40.0
      }
    ]
    ```
    Umarım beğenirsiniz!
    """
    res = client._safe_parse_json(markdown_text)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["id"] == "clip_1"


def test_gemini_client_extract_json_trailing_comma():
    client = GeminiClient()
    malformed_json = """
    [
      {
        "id": "clip_2",
        "title": "Trailing comma örneği",
      },
    ]
    """
    res = client._safe_parse_json(malformed_json)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["id"] == "clip_2"


def test_gemini_client_fallback_viral_clips():
    client = GeminiClient()
    clips = client._fallback_viral_clips(duration=120.0)
    assert len(clips) == 2
    assert clips[0]["targetFormat"] == "9:16"
    assert clips[0]["duration"] == 30.0
