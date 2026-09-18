from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float
    confidence: Optional[float] = 1.0


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: List[WordTimestamp] = field(default_factory=list)


@dataclass
class TranscriptResult:
    full_text: str
    segments: List[TranscriptSegment] = field(default_factory=list)
    words: List[WordTimestamp] = field(default_factory=list)
    duration: float = 0.0
