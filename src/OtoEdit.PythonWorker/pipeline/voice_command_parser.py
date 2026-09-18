import re
from typing import List, Optional
from models.command_model import CommandType, ParsedCommand
from models.transcript_model import TranscriptResult
from utils.logger import get_logger

logger = get_logger(__name__)


class VoiceCommandParser:
    """Whisper transkriptindeki sesli komut kalıplarını regex ve anahtar kelimelerle ayrıştıran motor."""

    # Regex Kalıpları
    PATTERNS = [
        # 1. Başlat / Devam
        (re.compile(r"\b(videoyu\s+)?(başlat|başlayalım|devam\s+et|kayda\s+başla)\b", re.IGNORECASE), CommandType.START_MARKER),
        # 2. Kes / Durdur
        (re.compile(r"\b(burayı\s+kes|kes\s+burayı|keselim|durdur|burası\s+olmadı)\b", re.IGNORECASE), CommandType.CUT),
        # 3. Metin Yazısı Ekle
        (re.compile(r"\b(buraya\s+)?(.+?)\s+(yazısını\s+yaz|yazısı\s+koy|başlığını\s+ekle)\b", re.IGNORECASE), CommandType.ADD_TEXT),
        # 4. Resim Ekle
        (re.compile(r"\b(buraya\s+)?(.+?)\s+(resmi\s+koy|görseli\s+ekle|fotoğrafı\s+koy)\b", re.IGNORECASE), CommandType.ADD_IMAGE),
        # 5. Geriye Sar / Sil
        (re.compile(r"\b(geriye\s+)?(.+?)(?:\s+cümlesine|\s+kelimesine|\s+kısmına)?\s+(kadar\s+sil|kadar\s+sar|başa\s+al)\b", re.IGNORECASE), CommandType.REWIND_CUT)
    ]

    def parse_transcript(self, transcript: TranscriptResult) -> List[ParsedCommand]:
        """Transkriptteki tüm olası sesli komut adaylarını tespit eder."""
        commands = []

        for seg in transcript.segments:
            text = seg.text.strip()
            if not text:
                continue

            for pattern, cmd_type in self.PATTERNS:
                match = pattern.search(text)
                if match:
                    payload = None
                    if cmd_type == CommandType.ADD_TEXT and len(match.groups()) >= 2:
                        payload = match.group(2).strip()
                    elif cmd_type == CommandType.ADD_IMAGE and len(match.groups()) >= 2:
                        payload = match.group(2).strip()
                    elif cmd_type == CommandType.REWIND_CUT and len(match.groups()) >= 2:
                        payload = match.group(2).strip()

                    cmd = ParsedCommand(
                        command_type=cmd_type,
                        timestamp=round(seg.start, 2),
                        start=round(seg.start, 2),
                        end=round(seg.end, 2),
                        payload=payload,
                        raw_text=text
                    )
                    commands.append(cmd)
                    logger.info(f"Sesli komut adayı tespit edildi: {cmd_type.value} @ {cmd.timestamp}s ('{text}')")

        return commands
