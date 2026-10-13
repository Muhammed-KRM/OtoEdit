"""
Jump-Cut v2 Birim Testleri
"""

import numpy as np
import pytest
from pipeline.audio_analysis import AudioAnalysis, SpeechRegion
from pipeline.silence_detector import SilenceDetector


def create_synthetic_analysis(duration: float, speech_intervals: list) -> AudioAnalysis:
    """Sentetik konuşma ve RMS zarfı üreten yardımcı fonksiyon."""
    speech_regions = [SpeechRegion(start=s, end=e) for s, e in speech_intervals]
    num_rms = int(duration * 100)  # 100 Hz (10ms hop)
    rms_envelope = np.zeros(num_rms, dtype=np.float32)

    # Konuşma bölgelerinde RMS = 0.5, sessizlikte RMS = 0.001
    rms_envelope[:] = 0.001
    for s, e in speech_intervals:
        idx_s = int(s * 100)
        idx_e = min(num_rms, int(e * 100))
        rms_envelope[idx_s:idx_e] = 0.5

    return AudioAnalysis(
        duration=duration,
        speech_regions=speech_regions,
        rms_envelope=rms_envelope,
        peaks=[0.5] * 1000,
        rms_hop_ms=10.0,
        sample_rate=16000
    )


def test_jumpcut_v2_padding_and_min_silence():
    # 0 - 2s: sessiz, 2 - 5s: konuşma, 5 - 5.4s: kısa sessizlik (400ms), 5.4 - 8s: konuşma, 8 - 10s: sessizlik (2s)
    analysis = create_synthetic_analysis(
        duration=10.0,
        speech_intervals=[(2.0, 5.0), (5.4, 8.0)]
    )

    detector = SilenceDetector(engine="v2")
    # min_silence=700ms, pad=200ms
    detector.min_silence_ms = 700
    detector.pad_sec = 0.20

    cuts = detector.detect_v2(analysis=analysis)

    # 5.0 - 5.4s (400ms) elenmeli çünkü min_silence 700ms altında (doğal nefes)
    # 0 - 2s (2s) ve 8 - 10s (2s) kesim olmalı
    # 0 - 2s: pad sonrası 0.2 -> 1.8
    # 8 - 10s: pad sonrası 8.2 -> 9.8
    assert len(cuts) == 2

    c1 = cuts[0]
    assert c1.start == 0.0
    assert 1.70 <= c1.end <= 1.90

    c2 = cuts[1]
    assert 8.10 <= c2.start <= 8.30
    assert c2.end == 10.0


def test_jumpcut_v2_word_guard():
    # 0 - 4s: sessiz, 4 - 8s: konuşma
    analysis = create_synthetic_analysis(
        duration=10.0,
        speech_intervals=[(4.0, 8.0)]
    )

    detector = SilenceDetector(engine="v2")
    detector.min_silence_ms = 700
    detector.pad_sec = 0.20
    detector.word_guard_sec = 0.15

    # Erken fısıltı / kelime: 1.5 - 2.0s
    class MockWord:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    words = [MockWord(1.5, 2.0)]
    cuts = detector.detect_v2(analysis=analysis, transcript_words=words)

    # 0 - 4s arasındaki kesim kelime nedeniyle iki parçaya bölünmeli veya kelime aralığı [1.35, 2.15] korunmalı
    for cut in cuts:
        # Hiçbir kesim [1.35, 2.15] içine girmemeli!
        assert not (cut.start < 2.0 and cut.end > 1.5), f"Cut {cut.start}-{cut.end} kelimeyle çakışıyor!"


def test_jumpcut_v2_micro_island_merging():
    # İki sessizlik arasında sadece 150ms'lik minik bir gürültü/ada var (3.0 - 3.15s)
    # 0 - 3.0s: sessizlik, 3.0 - 3.15s: ada, 3.15 - 6.0s: sessizlik, 6.0 - 10.0s: konuşma
    analysis = create_synthetic_analysis(
        duration=10.0,
        speech_intervals=[(3.0, 3.15), (6.0, 10.0)]
    )

    detector = SilenceDetector(engine="v2")
    detector.min_silence_ms = 700
    detector.pad_sec = 0.20
    detector.min_island_sec = 0.30

    cuts = detector.detect_v2(analysis=analysis, transcript_words=[])

    # 150ms'lik ada kelimesiz olduğu için iki kesim birleşmeli
    # Tek bir büyük kesim olmalı: 0.20 -> 5.80
    assert len(cuts) == 1
    assert cuts[0].start <= 0.3
    assert cuts[0].end >= 5.7


def test_jumpcut_v2_asymmetric_padding():
    # 0 - 3.0s: sessiz, 3.0 - 7.0s: konuşma, 7.0 - 10.0s: sessiz
    analysis = create_synthetic_analysis(
        duration=10.0,
        speech_intervals=[(3.0, 7.0)]
    )

    detector = SilenceDetector(engine="v2")
    detector.min_silence_ms = 700
    # Asimetrik: konuşma öncesi 350ms (pad_lead), konuşma sonrası 200ms (pad_trailing)
    detector.pad_lead_sec = 0.35
    detector.pad_trailing_sec = 0.20

    cuts = detector.detect_v2(analysis=analysis, transcript_words=[])
    assert len(cuts) == 2

    # 1. Kesim: 0.0 -> 3.0 öncesi kesim.
    # Konuşma 3.0s'de başladığı için kesim en geç 3.0 - 0.35 = 2.65s'de bitmeli!
    c1 = cuts[0]
    assert c1.start == 0.0
    assert c1.end <= 2.68
    assert (3.0 - c1.end) >= 0.32  # En az 320ms konuşma öncesi nefes payı kalmalı!

    # 2. Kesim: 7.0 sonrası kesim.
    # Konuşma 7.0s'de bittiği için kesim en erken 7.0 + 0.20 = 7.20s'de başlamalı!
    c2 = cuts[1]
    assert c2.start >= 7.18
    assert c2.end == 10.0


def test_find_energy_minimum_directions():
    analysis = create_synthetic_analysis(
        duration=10.0,
        speech_intervals=[(5.0, 8.0)]
    )

    # 5.0s konuşma başlangıcı.
    # backward_only araması asla 5.0'dan ileriye (konuşmanın içine) geçmemeli!
    snapped_back = analysis.find_energy_minimum(center_sec=4.8, search_window_sec=0.1, direction="backward_only")
    assert snapped_back <= 4.8

    # forward_only araması asla 4.8'den geriye geçmemeli!
    snapped_fwd = analysis.find_energy_minimum(center_sec=4.8, search_window_sec=0.1, direction="forward_only")
    assert snapped_fwd >= 4.8
