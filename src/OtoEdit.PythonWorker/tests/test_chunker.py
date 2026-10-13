"""
Chunker Birim Testleri
"""

from pipeline.stt.chunker import AudioChunker
from pipeline.audio_analysis import AudioAnalysis, SpeechRegion
import numpy as np


def test_chunker_splits_at_silence():
    # 1200 saniye (20 dk) toplam süre
    # Hedef 600 sn civarı. 590 - 610 sn arasında belirgin bir sessizlik olsun (ör. 595 - 605s)
    # Konuşmalar: 0-595s ve 605-1200s
    speech_regions = [
        SpeechRegion(start=0.0, end=595.0),
        SpeechRegion(start=605.0, end=1200.0)
    ]
    analysis = AudioAnalysis(
        duration=1200.0,
        speech_regions=speech_regions,
        rms_envelope=np.zeros(120000, dtype=np.float32),
        peaks=[],
        rms_hop_ms=10.0,
        sample_rate=16000
    )

    chunker = AudioChunker(max_chunk_sec=600.0)
    split_points = chunker.calculate_split_points(analysis)

    assert len(split_points) == 2
    # İlk sınır 595 - 605 arasındaki sessizliğin tam ortasına (600.0s) düşmeli
    assert 598.0 <= split_points[0] <= 602.0
    assert split_points[1] == 1200.0
