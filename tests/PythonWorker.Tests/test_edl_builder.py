from models.command_model import CommandType, ParsedCommand
from models.edl_model import CutItem, RepurposingData, SuggestionItem
from models.transcript_model import TranscriptResult, TranscriptSegment
from pipeline.edl_builder import EdlBuilder


def test_merge_overlapping_cuts():
    cuts = [
        CutItem(id="c1", start=5.0, end=10.0, reason="silence"),
        CutItem(id="c2", start=8.0, end=14.0, reason="gesture_dislike"),
        CutItem(id="c3", start=20.0, end=25.0, reason="silence")
    ]

    merged = EdlBuilder._merge_overlapping_cuts(cuts)

    assert len(merged) == 2
    assert merged[0].start == 5.0
    assert merged[0].end == 14.0
    assert "silence" in merged[0].reason
    assert "gesture_dislike" in merged[0].reason
    assert merged[1].start == 20.0
    assert merged[1].end == 25.0


def test_edl_builder_full_assembly():
    builder = EdlBuilder()
    transcript = TranscriptResult(
        full_text="Test videosu konuşması",
        segments=[TranscriptSegment(start=0.0, end=10.0, text="Test videosu konuşması")],
        duration=10.0
    )

    silence_cuts = [CutItem(id="cut_1", start=2.0, end=4.0, reason="silence")]
    commands = [
        ParsedCommand(
            command_type=CommandType.ADD_TEXT,
            timestamp=5.0,
            start=4.8,
            end=5.5,
            payload="Önemli Başlık",
            raw_text="buraya Önemli Başlık yazısını yaz"
        )
    ]
    face_data = [{"timestamp": 0.0, "smoothed_crop_x": 0.5}]
    repurposing_data = RepurposingData()
    suggestions = [
        SuggestionItem(
            id="s1",
            type="text_callout",
            title="Tavsiye",
            content="Sabırlı ol",
            timestamp=6.0,
            reason="Vurgu"
        )
    ]

    edl = builder.build(
        project_id="proj-123",
        video_id="vid-456",
        transcript=transcript,
        silence_cuts=silence_cuts,
        commands=commands,
        face_data=face_data,
        repurposing_data=repurposing_data,
        suggestions=suggestions,
        video_format=1  # 9:16
    )

    assert edl["projectId"] == "proj-123"
    assert edl["videoId"] == "vid-456"
    assert edl["settings"]["targetFormat"] == "9:16"
    assert edl["settings"]["faceTrackingEnabled"] is True
    assert len(edl["cuts"]) >= 2  # silence cut + command moment cut
    assert len(edl["overlays"]) == 1
    assert edl["overlays"][0]["content"] == "Önemli Başlık"
    assert len(edl["suggestions"]) == 1
    assert edl["suggestions"][0]["content"] == "Sabırlı ol"
