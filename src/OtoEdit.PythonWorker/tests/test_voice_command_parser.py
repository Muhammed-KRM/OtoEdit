from models.command_model import CommandType
from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp
from pipeline.voice_command_parser import VoiceCommandParser


def test_parse_start_command():
    parser = VoiceCommandParser()
    seg = TranscriptSegment(start=1.0, end=2.5, text="Tamam videoyu başlat şimdi")
    transcript = TranscriptResult(full_text="Tamam videoyu başlat şimdi", segments=[seg], duration=3.0)

    commands = parser.parse_transcript(transcript)

    assert len(commands) == 1
    assert commands[0].command_type == CommandType.START_MARKER
    assert commands[0].timestamp == 1.0


def test_parse_cut_command():
    parser = VoiceCommandParser()
    seg = TranscriptSegment(start=15.0, end=16.8, text="Yanlış söyledim burayı kes lütfen")
    transcript = TranscriptResult(full_text="Yanlış söyledim burayı kes lütfen", segments=[seg], duration=20.0)

    commands = parser.parse_transcript(transcript)

    assert len(commands) == 1
    assert commands[0].command_type == CommandType.CUT
    assert commands[0].timestamp == 15.0


def test_parse_add_text_command():
    parser = VoiceCommandParser()
    seg = TranscriptSegment(start=30.0, end=33.2, text="buraya Kanala Abone Ol yazısını yaz")
    transcript = TranscriptResult(full_text="buraya Kanala Abone Ol yazısını yaz", segments=[seg], duration=40.0)

    commands = parser.parse_transcript(transcript)

    assert len(commands) == 1
    assert commands[0].command_type == CommandType.ADD_TEXT
    assert commands[0].payload == "Kanala Abone Ol"


def test_parse_no_command():
    parser = VoiceCommandParser()
    seg = TranscriptSegment(start=5.0, end=8.0, text="Bugün hava gerçekten çok güzel ve güneşli")
    transcript = TranscriptResult(full_text="Bugün hava gerçekten çok güzel ve güneşli", segments=[seg], duration=10.0)

    commands = parser.parse_transcript(transcript)

    assert len(commands) == 0
