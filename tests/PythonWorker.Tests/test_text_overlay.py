import os
import tempfile
import pytest
from render.text_overlay import TextOverlay


def test_hex_to_ass_color():
    # Beyaz tam opak
    assert TextOverlay.hex_to_ass_color("#FFFFFF") == "&H00FFFFFF"
    # Kırmızı tam opak
    assert TextOverlay.hex_to_ass_color("#FF0000") == "&H000000FF"
    # Yarı saydam siyah
    assert TextOverlay.hex_to_ass_color("#00000080") == "&H80000000"


def test_position_to_ass_alignment():
    assert TextOverlay.position_to_ass_alignment(["center", "bottom"]) == 2
    assert TextOverlay.position_to_ass_alignment(["center", "center"]) == 5
    assert TextOverlay.position_to_ass_alignment(["center", "top"]) == 8
    assert TextOverlay.position_to_ass_alignment(["left", "top"]) == 7
    assert TextOverlay.position_to_ass_alignment(["right", "top"]) == 9


def test_seconds_to_ass_time():
    assert TextOverlay.seconds_to_ass_time(0.0) == "0:00:00.00"
    assert TextOverlay.seconds_to_ass_time(65.5) == "0:01:05.50"
    assert TextOverlay.seconds_to_ass_time(3661.25) == "1:01:01.25"


def test_generate_ass_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        ass_path = os.path.join(tmpdir, "test.ass")
        overlays = [
            {
                "id": "text_1",
                "type": "text",
                "content": "Abone Ol!",
                "font": "Montserrat-Bold",
                "fontSize": 48,
                "color": "#FFFFFF",
                "backgroundColor": "#00000080",
                "timestamp": 2.5,
                "duration": 4.0,
                "animation": "pop-up",
                "position": ["center", "bottom"]
            }
        ]
        transcript = {
            "segments": [
                {
                    "start": 1.0,
                    "end": 3.0,
                    "text": "Merhaba dünya",
                    "words": [
                        {"word": "Merhaba", "start": 1.0, "end": 2.0},
                        {"word": "dünya", "start": 2.0, "end": 3.0}
                    ]
                }
            ]
        }

        result_path = TextOverlay.generate_ass(
            overlays=overlays,
            transcript=transcript,
            output_path=ass_path
        )

        assert os.path.exists(result_path)
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "Abone Ol!" in content
        assert "Merhaba" in content
        assert "{\\k" in content  # Karaoke etiketi


def test_generate_ass_file_with_track_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        ass_path = os.path.join(tmpdir, "test_track.ass")
        overlays = [
            {
                "type": "text",
                "content": "En Üst Katman",
                "trackId": 5,
                "timestamp": 1.0,
                "duration": 2.0
            }
        ]

        TextOverlay.generate_ass(overlays=overlays, output_path=ass_path)
        with open(ass_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Dialogue satırının Layer parametresi 5 olmalı: Dialogue: 5,...
        assert "Dialogue: 5," in content
        assert "En Üst Katman" in content

