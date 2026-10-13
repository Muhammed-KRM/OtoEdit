"""
GapFiller Birim Testleri
"""

from pipeline.stt.gap_filler import GapFiller
from pipeline.stt.base import Word
from pipeline.audio_analysis import AudioAnalysis, SpeechRegion
import numpy as np


def test_find_untranscribed_gaps():
    analysis = AudioAnalysis(
        duration=10.0,
        speech_regions=[
            SpeechRegion(start=1.0, end=2.5),  # 1.5s - kelime var
            SpeechRegion(start=3.0, end=4.0),  # 1.0s - KELİME YOK (şüpheli boşluk)
            SpeechRegion(start=5.0, end=5.2),  # 0.2s - kısa (<0.4s), elenmeli
            SpeechRegion(start=6.0, end=8.0),  # 2.0s - kelime var
        ],
        rms_envelope=np.zeros(1000, dtype=np.float32),
        peaks=[],
        rms_hop_ms=10.0,
        sample_rate=16000
    )

    words = [
        Word(word="Merhaba", start=1.2, end=1.8),
        Word(word="Dünya", start=6.5, end=7.2)
    ]

    filler = GapFiller(min_gap_sec=0.40)
    gaps = filler.find_untranscribed_gaps(analysis, words)

    assert len(gaps) == 1
    assert gaps[0] == (3.0, 4.0)
