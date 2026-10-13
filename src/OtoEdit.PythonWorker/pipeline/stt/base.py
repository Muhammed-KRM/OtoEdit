"""
OtoEdit STT Temel Veri Modelleri ve Arayüzü
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from pipeline.stt.chunker import AudioChunk


@dataclass
class Word:
    word: str
    start: float       # Mutlak video başlangıç saniyesi
    end: float         # Mutlak video bitiş saniyesi
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "confidence": round(self.confidence, 3)
        }


@dataclass
class TranscriptionResult:
    words: List[Word]
    text: str
    engine: str
    duration_sec: float = 0.0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "engine": self.engine,
            "duration_sec": round(self.duration_sec, 2),
            "words": [w.to_dict() for w in self.words]
        }


def parse_offset_sec(val: str | float | int) -> float:
    """Gemini API veya diğer STT offset dizgilerini ('5.600s', '8s', 5.6) float saniyeye çevirir."""
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().rstrip("sS")
    try:
        return float(val_str)
    except ValueError:
        return 0.0


class BaseSTTEngine(ABC):
    """Tüm STT motorlarının uygulaması gereken ortak arayüz."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_available(self) -> bool:
        """Motorun çalışması için gerekli anahtar/bağlantı hazır mı?"""
        pass

    @abstractmethod
    def transcribe_chunk(self, chunk: AudioChunk) -> List[Word]:
        """
        Verilen ses parçasını transkribe eder.
        Dönen Word nesneleri videonun mutlak başlangıç zamanına (chunk.start_sec eklenmiş) sahiptir.
        """
        pass
