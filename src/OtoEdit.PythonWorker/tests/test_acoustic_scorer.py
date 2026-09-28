from unittest.mock import MagicMock, patch
import pytest
from pipeline.acoustic_scorer import AcousticScorer, IAcousticScorer


def test_acoustic_scorer_implements_interface():
    scorer = AcousticScorer()
    assert isinstance(scorer, IAcousticScorer)


def test_acoustic_scorer_in_memory_caching():
    scorer = AcousticScorer()

    fake_segment = MagicMock()
    fake_segment.__len__.return_value = 60000  # 60 saniye
    fake_segment.frame_rate = 16000
    fake_segment.sample_width = 2

    # Dilimleme mock'u
    sliced_segment = MagicMock()
    sliced_segment.__len__.return_value = 5000
    sliced_segment.set_channels.return_value = sliced_segment
    sliced_segment.get_array_of_samples.return_value = [100, 200, 300, 400]
    sliced_segment.sample_width = 2
    fake_segment.__getitem__.return_value = sliced_segment

    with patch("pipeline.acoustic_scorer.AudioSegment.from_wav", return_value=fake_segment) as mock_load:
        # 1. çağrı: Diskten yükler
        res1 = scorer.score_audio_segment("audio_sample.wav", 10.0, 15.0)
        assert res1["clipping_score"] > 0
        assert mock_load.call_count == 1

        # 2. çağrı: Aynı dosya! Diskten yüklememeli (cache'den almalı)
        res2 = scorer.score_audio_segment("audio_sample.wav", 20.0, 25.0)
        assert res2["clipping_score"] > 0
        assert mock_load.call_count == 1  # Hala 1 olmalı!

        # 3. çağrı: 500 kere dilimleme yapılsa bile disk okuma sayısı 1 kalmalı
        for _ in range(50):
            scorer.score_audio_segment("audio_sample.wav", 1.0, 2.0)
        assert mock_load.call_count == 1

        # Önbellek temizleme
        scorer.clear_cache()
        assert scorer._cached_audio is None
        assert scorer._cached_path is None

        # Temizlendikten sonraki çağrı: Tekrar yüklemeli
        scorer.score_audio_segment("audio_sample.wav", 1.0, 2.0)
        assert mock_load.call_count == 2
