import pytest
from unittest.mock import MagicMock
from pipeline.transcript_verifier import TranscriptVerifier
from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp


def test_transcript_verifier_cuts_semantic_retakes():
    # Mock GeminiClient
    mock_gemini = MagicMock()
    mock_gemini.is_available.return_value = True
    mock_gemini.generate_json.return_value = [
        {
            "group_id": "GRP_A1",
            "cut_start_word_id": 5,
            "cut_end_word_id": 7,
            "keep_start_word_id": 8,
            "keep_end_word_id": 14,
            "confidence": 0.92,
            "reason": "Konuşmacı kekeleyip vazgeçti, sonraki cümlede düzeltti.",
        }
    ]

    verifier = TranscriptVerifier(gemini_client=mock_gemini)

    seg0 = TranscriptSegment(
        start=0.0,
        end=3.0,
        text="Bugün mukayeseli hukuka giriş yapacağız.",
        words=[
            WordTimestamp("Bugün", 0.0, 0.5),
            WordTimestamp("mukayeseli", 0.6, 1.2),
            WordTimestamp("hukuka", 1.3, 1.8),
            WordTimestamp("giriş", 1.9, 2.3),
            WordTimestamp("yapacağız.", 2.4, 2.9)
        ]
    )
    seg1 = TranscriptSegment(
        start=3.5,
        end=5.0,
        text="Şimdi ceza hukukunda...",
        words=[
            WordTimestamp("Şimdi", 3.5, 3.8),
            WordTimestamp("ceza", 3.9, 4.3),
            WordTimestamp("hukukunda...", 4.4, 4.9)
        ]
    )
    seg2 = TranscriptSegment(
        start=5.5,
        end=9.0,
        text="Ceza hukuku alanındaki temel prensipleri ele alalım.",
        words=[
            WordTimestamp("Ceza", 5.5, 5.9),
            WordTimestamp("hukuku", 6.0, 6.4),
            WordTimestamp("alanındaki", 6.5, 7.1),
            WordTimestamp("temel", 7.2, 7.6),
            WordTimestamp("prensipleri", 7.7, 8.3),
            WordTimestamp("ele", 8.4, 8.6),
            WordTimestamp("alalım.", 8.7, 9.0)
        ]
    )

    transcript = TranscriptResult(
        full_text="Test",
        segments=[seg0, seg1, seg2],
        duration=10.0
    )

    cuts = verifier.audit_transcript(transcript)

    assert len(cuts) == 1
    cut = cuts[0]
    assert cut.id == "cut_ai_retake_5"
    assert cut.start == 3.5
    assert abs(cut.end - 4.92) <= 0.05
    assert "retake" in cut.reason


def test_transcript_verifier_skips_when_empty_or_no_findings():
    mock_gemini = MagicMock()
    mock_gemini.audit_transcript_coherence.return_value = []

    verifier = TranscriptVerifier(gemini_client=mock_gemini)
    transcript = TranscriptResult(
        full_text="Test",
        segments=[
            TranscriptSegment(start=0.0, end=3.0, text="Temiz bir cümle.")
        ],
        duration=5.0
    )

    cuts = verifier.audit_transcript(transcript)
    assert cuts == []
