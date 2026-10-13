"""
STT Dayanıklılık ve Kota İyileştirme Birim Testleri
- GeminiKeyRotator 429 soğuma ve bütçe kontrolü
- Transcriber parça bazlı hata izolasyonu ve kelime kurtarma
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from pipeline.stt.rate_limiter import GeminiKeyRotator
from pipeline.stt.base import Word
from pipeline.stt.chunker import AudioChunk
from pipeline.transcriber import Transcriber
from pipeline.audio_analysis import AudioAnalysis, SpeechRegion
import numpy as np


def test_key_rotator_cooling_down_and_recovery():
    # 2 anahtarlı rotator
    rotator = GeminiKeyRotator(api_keys=["key_A", "key_B"], max_rpm=5, max_wait_sec=10.0)

    # 1. İlk anahtarı al
    k1 = rotator.get_available_key(wait_if_needed=False)
    assert k1 == "key_A"

    # 2. key_A'ya 429 soğuma ver (1.5 sn)
    rotator.report_429("key_A", retry_delay_sec=1.5)

    # 3. Sıradaki istek key_B'ye yönlenmeli (key_A soğumada)
    k2 = rotator.get_available_key(wait_if_needed=False)
    assert k2 == "key_B"

    # 4. key_B de 429 alsın (0.2 sn)
    rotator.report_429("key_B", retry_delay_sec=0.2)

    # 5. wait_if_needed=True iken en erken soğuyan anahtarı (key_B: 0.2sn sonra) bekleyip vermeli
    t0 = time.time()
    k3 = rotator.get_available_key(wait_if_needed=True)
    elapsed = time.time() - t0

    assert k3 in ("key_A", "key_B")
    assert elapsed >= 0.15


def test_transcriber_chunk_isolation_preserves_words():
    transcriber = Transcriber()

    # Sahte 2 parça
    c1 = AudioChunk(index=1, start_sec=0.0, end_sec=10.0, audio_path="/dummy/c1.mp3", has_speech=True)
    c2 = AudioChunk(index=2, start_sec=10.0, end_sec=20.0, audio_path="/dummy/c2.mp3", has_speech=True)

    transcriber.chunker.split = MagicMock(return_value=[c1, c2])
    transcriber.chunker.cleanup_chunks = MagicMock()

    # Parça 1 başarılı olsun (2 kelime), Parça 2 RuntimeError (429 kota aşımı) versin
    w1 = Word(word="Mukayeseli", start=1.0, end=1.8, confidence=0.99)
    w2 = Word(word="Hukuk", start=2.0, end=2.6, confidence=0.98)

    def mock_transcribe(chunk):
        if chunk.index == 1:
            return [w1, w2], "gemini_transcribe"
        else:
            raise RuntimeError("Gemini API hatası (429): Quota exceeded")

    transcriber.chain.transcribe_chunk = MagicMock(side_effect=mock_transcribe)

    analysis = AudioAnalysis(
        duration=20.0,
        speech_regions=[SpeechRegion(start=1.0, end=3.0)],
        rms_envelope=np.zeros(2000, dtype=np.float32),
        peaks=[],
        rms_hop_ms=10.0,
        sample_rate=16000
    )
    transcriber.gap_filler.fill_gaps = MagicMock(side_effect=lambda media_path, analysis, words, chain: words)

    # Transkripsiyonu çalıştır
    with patch("os.path.exists", return_value=True):
        result = transcriber.transcribe("/dummy/video.mp4", analysis=analysis)

    # Parça 2 çökmesine rağmen Parça 1'in kelimeleri KORUNMALI!
    assert "[TRANSKRİPT ÇIKARILAMADI]" not in result.full_text
    assert "Mukayeseli Hukuk" in result.full_text
    assert len(result.words) == 2
    assert result.words[0].word == "Mukayeseli"
    assert result.words[1].word == "Hukuk"
