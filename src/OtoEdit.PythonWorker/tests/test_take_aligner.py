"""
TakeAligner ve Jump-Cut v3 Birim Testleri
"""
import pytest
from pipeline.take_aligner import TakeAligner, WordRef
from pipeline.silence_detector import SilenceDetector
from pipeline.edl_builder import EdlBuilder
from models.edl_model import CutItem


def test_take_aligner_exact_restart():
    aligner = TakeAligner()

    # Senaryo: "hatta vefat sonrası ölenin hatırına saygıya kadar" (hata)
    # [5s duraklama]
    # "hatta vefat sonrası ölenin hatırasına saygıya kadar" (doğru)
    words = [
        {"word": "hatta", "start": 70.0, "end": 70.3},
        {"word": "vefat", "start": 70.4, "end": 70.8},
        {"word": "sonrası", "start": 70.9, "end": 71.3},
        {"word": "ölenin", "start": 71.4, "end": 71.8},
        {"word": "hatırına", "start": 71.9, "end": 72.4},
        {"word": "saygıya", "start": 72.5, "end": 72.9},
        {"word": "kadar", "start": 73.0, "end": 73.5},
        # 5 saniye duraklama (73.5 -> 78.5)
        {"word": "hatta", "start": 78.5, "end": 78.8},
        {"word": "vefat", "start": 78.9, "end": 79.3},
        {"word": "sonrası", "start": 79.4, "end": 79.8},
        {"word": "ölenin", "start": 79.9, "end": 80.3},
        {"word": "hatırasına", "start": 80.4, "end": 80.9},
        {"word": "saygıya", "start": 81.0, "end": 81.4},
        {"word": "kadar", "start": 81.5, "end": 82.0},
        {"word": "insan", "start": 82.2, "end": 82.6},
        {"word": "hayatını", "start": 82.7, "end": 83.2}
    ]

    cuts = aligner.detect_retakes(words)
    assert len(cuts) >= 1

    first_cut = cuts[0]
    # İlk take (70.0) kesilmeli, son take (78.5) korunmalı
    assert 69.9 <= first_cut.start <= 70.1
    assert 78.4 <= first_cut.end <= 78.6
    assert first_cut.reason == "smart_retake"


def test_take_aligner_turkish_fuzzy_match():
    aligner = TakeAligner()

    # bürhandır ile hürhandır (1 harf farkı, kök uyumu)
    assert aligner.is_word_match("bürhandır", "hürhandır") is True
    # yöneltir ile yöneldir
    assert aligner.is_word_match("yöneltir", "yöneldir") is True
    # hükümlerinin ile bölümlerinin (kökleri farklı, ekleri aynı - EŞLEŞMEMELİ!)
    assert aligner.is_word_match("hükümlerinin", "bölümlerinin") is False


def test_take_aligner_outtake_and_false_start():
    aligner = TakeAligner()

    words = [
        {"word": "Asıl", "start": 10.0, "end": 10.4},
        {"word": "zihin", "start": 10.5, "end": 10.9},
        {"word": "ameliyat", "start": 11.0, "end": 11.6},
        # 3 saniye duraklama
        {"word": "Asıl", "start": 14.6, "end": 15.0},
        {"word": "zihni", "start": 15.1, "end": 15.5},
        {"word": "ameliyat", "start": 15.6, "end": 16.2},
        # outtake
        {"word": "başa", "start": 20.0, "end": 20.4},
        {"word": "sar", "start": 20.5, "end": 20.9}
    ]

    cuts = aligner.detect_retakes(words)
    # Hem restart hem outtake yakalanmalı
    reasons = [c.reason for c in cuts]
    assert "smart_retake" in reasons
    # 10.0 - 14.6 aralığı kesilmeli
    assert any(c.start <= 10.1 and c.end >= 14.5 for c in cuts)
    # 20.0 - 20.9 aralığı (başa sar) kesilmeli
    assert any(c.start <= 20.1 and c.end >= 20.8 for c in cuts)


def test_edl_builder_separate_reasons():
    # Bitişik veya çakışan retake ve silence kesimleri birleştirilmemeli
    cuts = [
        CutItem(id="c1", start=10.0, end=13.0, reason="silence", source="auto"),
        CutItem(id="c2", start=13.0, end=18.0, reason="smart_retake", source="auto"),
        CutItem(id="c3", start=25.0, end=27.0, reason="silence", source="auto"),
        CutItem(id="c4", start=26.5, end=30.0, reason="silence", source="auto")  # Aynı sebep birleşmeli
    ]

    merged = EdlBuilder._merge_overlapping_cuts(cuts)

    # c1 ve c2 farklı sebep olduğu için ayrı kalmalı!
    assert len(merged) == 3
    assert merged[0].reason == "silence"
    assert merged[0].start == 10.0 and merged[0].end == 13.0
    assert merged[1].reason == "smart_retake"
    assert merged[1].start == 13.0 and merged[1].end == 18.0

    # c3 ve c4 aynı sebep olduğu için birleşmeli (25.0 -> 30.0)
    assert merged[2].reason == "silence"
    assert merged[2].start == 25.0 and merged[2].end == 30.0
