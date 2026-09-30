import os
import sys

# Proje kök dizinini sys.path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from render.timeline_mapper import TimelineMapper


def test_remap_timestamp_basic():
    # 0-5 sn korunuyor, 5-10 kesiliyor (5 sn atıldı), 10-15 korunuyor
    keep_segments = [(0.0, 5.0), (10.0, 15.0)]

    # 1. Sahnenin İçi (Aynı kalmalı)
    assert TimelineMapper.remap_timestamp(2.0, keep_segments) == 2.0
    assert TimelineMapper.remap_timestamp(0.0, keep_segments) == 0.0
    assert TimelineMapper.remap_timestamp(5.0, keep_segments) == 5.0

    # 2. Sahnenin İçi (Kesilen 5 saniye boşluk çıkarılarak kaymalı: 12 -> 7)
    assert TimelineMapper.remap_timestamp(12.0, keep_segments) == 7.0
    assert TimelineMapper.remap_timestamp(10.0, keep_segments) == 5.0
    assert TimelineMapper.remap_timestamp(15.0, keep_segments) == 10.0

    # Kesilen Bölgenin İçi (None dönmeli)
    assert TimelineMapper.remap_timestamp(8.0, keep_segments) is None
    assert TimelineMapper.remap_timestamp(6.5, keep_segments) is None


def test_remap_timestamp_empty_segments():
    # Kesim yoksa veya liste boşsa orijinal zamanı korur
    assert TimelineMapper.remap_timestamp(25.5, []) == 25.5


def test_remap_overlays_filters_cut_content():
    keep_segments = [(0.0, 5.0), (10.0, 15.0)]
    overlays = [
        {"type": "text", "timestamp": 2.0, "duration": 3.0, "content": "Başarılı Sahne 1"},
        {"type": "image", "timestamp": 8.0, "duration": 2.0, "source": "logo.png"},  # Kesilen alan!
        {"type": "text", "timestamp": 12.0, "duration": 2.5, "content": "Başarılı Sahne 2"}
    ]

    remapped = TimelineMapper.remap_overlays(overlays, keep_segments)

    # logo.png (8. saniye) otomatik elenmeli
    assert len(remapped) == 2
    assert remapped[0]["timestamp"] == 2.0
    assert remapped[0]["duration"] == 3.0
    assert remapped[0]["content"] == "Başarılı Sahne 1"

    # 12.0 olan timestamp 7.0'a kaymalı
    assert remapped[1]["timestamp"] == 7.0
    assert remapped[1]["duration"] == 2.5
    assert remapped[1]["content"] == "Başarılı Sahne 2"


def test_remap_transcript_with_karaoke():
    keep_segments = [(0.0, 5.0), (10.0, 15.0)]
    test_transcript = {
        "segments": [
            {
                "start": 1.0,
                "end": 3.0,
                "text": "Merhaba dünya",
                "words": [
                    {"word": "Merhaba", "start": 1.0, "end": 1.8},
                    {"word": "dünya", "start": 1.8, "end": 3.0}
                ]
            },
            {
                # Kesilen bölgede konuşma
                "start": 6.0,
                "end": 9.0,
                "text": "Bu kısım sessizlik ve atılmalı",
                "words": [
                    {"word": "Bu", "start": 6.0, "end": 6.5},
                    {"word": "kısım", "start": 6.5, "end": 9.0}
                ]
            },
            {
                # 2. sahnede konuşma (10-15 orijinal -> 5-10 yeni)
                "start": 11.0,
                "end": 14.0,
                "text": "İkinci sahne konuşması",
                "words": [
                    {"word": "İkinci", "start": 11.0, "end": 12.0},
                    {"word": "sahne", "start": 12.0, "end": 13.0},
                    {"word": "konuşması", "start": 13.0, "end": 14.0}
                ]
            }
        ]
    }

    remapped = TimelineMapper.remap_transcript(test_transcript, keep_segments)
    assert remapped is not None
    segments = remapped.get("segments", [])

    # 2. segment silinmiş olmalı, geriye 2 segment kalmalı
    assert len(segments) == 2

    # 1. Segment doğrulaması
    seg1 = segments[0]
    assert seg1["start"] == 1.0
    assert seg1["end"] == 3.0
    assert seg1["words"][0]["start"] == 1.0
    assert seg1["words"][0]["end"] == 1.8
    assert seg1["words"][1]["start"] == 1.8
    assert seg1["words"][1]["end"] == 3.0

    # 2. Segment doğrulaması (11-14 -> 6-9)
    seg2 = segments[1]
    assert seg2["start"] == 6.0
    assert seg2["end"] == 9.0
    assert seg2["words"][0]["start"] == 6.0
    assert seg2["words"][0]["end"] == 7.0
    assert seg2["words"][1]["start"] == 7.0
    assert seg2["words"][1]["end"] == 8.0
    assert seg2["words"][2]["start"] == 8.0
    assert seg2["words"][2]["end"] == 9.0


def test_remap_range_boundary_clamping():
    keep_segments = [(0.0, 5.0), (10.0, 15.0)]
    
    # Kelime segment sınırında kesiliyor (4.5 - 5.5) -> 4.5 - 5.0 olarak kırpılmalı
    res = TimelineMapper.remap_range(4.5, 5.5, keep_segments)
    assert res == (4.5, 5.0)

    # Kelime sonraki segmentin başında başlıyor (9.5 - 10.5) -> 5.0 - 5.5 olarak kırpılmalı
    res2 = TimelineMapper.remap_range(9.5, 10.5, keep_segments)
    assert res2 == (5.0, 5.5)


def test_end_to_end_ass_generation_with_remapping():
    import tempfile
    from render.text_overlay import TextOverlay

    keep_segments = [(0.0, 5.0), (10.0, 15.0)]
    overlays = [
        {"type": "text", "timestamp": 12.0, "duration": 2.0, "content": "Mantıklı"}
    ]
    transcript = {
        "segments": [
            {"start": 1.0, "end": 4.0, "text": "Birinci sahne konuşması"},
            {"start": 7.0, "end": 9.0, "text": "Sessizlikteki konuşma silinmeli"},
            {"start": 11.0, "end": 14.0, "text": "İkinci sahne konuşması"}
        ]
    }
    mapped_overlays = TimelineMapper.remap_overlays(overlays, keep_segments)
    mapped_transcript = TimelineMapper.remap_transcript(transcript, keep_segments)

    with tempfile.TemporaryDirectory() as tmpdir:
        ass_path = os.path.join(tmpdir, "test_out.ass")
        TextOverlay.generate_ass(
            overlays=mapped_overlays,
            transcript=mapped_transcript,
            output_path=ass_path
        )
        assert os.path.isfile(ass_path)
        with open(ass_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Orijinalde 12.0 olan "Mantıklı" yazısı 7.0 saniyede olmalı (0:00:07.00)
        assert "0:00:07.00" in content
        assert "Mantıklı" in content

        # Orijinalde 11.0 olan 2. sahne altyazısı 6.0 saniyede başlamalı (0:00:06.00)
        assert "0:00:06.00" in content
        assert "İkinci sahne konuşması" in content

        # Silinen konuşma ASS dosyasında OLMAMALI
        assert "Sessizlikteki konuşma silinmeli" not in content


if __name__ == "__main__":
    print("Testler calistiriliyor...")
    test_remap_timestamp_basic()
    print("[OK] test_remap_timestamp_basic gecti.")
    test_remap_timestamp_empty_segments()
    print("[OK] test_remap_timestamp_empty_segments gecti.")
    test_remap_overlays_filters_cut_content()
    print("[OK] test_remap_overlays_filters_cut_content gecti.")
    test_remap_transcript_with_karaoke()
    print("[OK] test_remap_transcript_with_karaoke gecti.")
    test_remap_range_boundary_clamping()
    print("[OK] test_remap_range_boundary_clamping gecti.")
    test_end_to_end_ass_generation_with_remapping()
    print("[OK] test_end_to_end_ass_generation_with_remapping gecti.")
    print(">>> TUM TIMELINE MAPPER BIRIM VE ENTEGRASYON TESTLERI BASARIYLA GECTI! <<<")
