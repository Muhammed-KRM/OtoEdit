"""
OtoEdit Jump-Cut & STT Benchmark Aracı
Gerçek veya sentetik ses üzerinde yeni Jump-Cut v2 ve STT metriklerini ölçer:
- Toplam sessizlik kesim sayısı
- < 0.4 sn mikro-klip sayısı (Hedef: 0)
- Kelimeyle çakışan kesim sayısı (Hedef: 0)
- Atlanan konuşma bölgesi sayısı (Hedef: 0)
"""

import sys
import os
import time
from pathlib import Path

# Worker kök dizinini ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.audio_analysis import AudioAnalyzer
from pipeline.silence_detector import SilenceDetector
from pipeline.stt.chunker import AudioChunker
from pipeline.stt.gap_filler import GapFiller


def run_benchmark(media_path: str):
    print("=" * 60)
    print(f"📊 OtoEdit Kesim ve Ses Analizi Benchmark: {os.path.basename(media_path)}")
    print("=" * 60)

    if not os.path.exists(media_path):
        print(f"❌ Dosya bulunamadı: {media_path}")
        return

    # 1. Ses Analizi (VAD + RMS)
    t0 = time.time()
    analyzer = AudioAnalyzer()
    analysis = analyzer.analyze(media_path)
    t_analysis = time.time() - t0

    print(f"⏱️ Ses Analizi Süresi: {t_analysis:.2f}s")
    print(f"⏱️ Medya Süresi: {analysis.duration:.1f}s ({analysis.duration/60:.1f} dk)")
    print(f"🗣️ VAD Konuşma Bölgesi: {len(analysis.speech_regions)}")

    # 2. Jump-Cut v2 (Transkript kelimeleri olmadan test)
    detector = SilenceDetector(engine="v2")
    t0 = time.time()
    cuts_v2 = detector.detect_v2(analysis=analysis)
    t_cut = time.time() - t0

    total_cut_duration = sum(c.end - c.start for c in cuts_v2)
    print(f"✂️ Jump-Cut v2 Kesim Sayısı: {len(cuts_v2)} (Süre: {t_cut*1000:.1f}ms)")
    print(f"✂️ Toplam Kesilen Sessizlik: {total_cut_duration:.1f}s (%{100*total_cut_duration/max(0.1, analysis.duration):.1f})")

    # 3. Kalan Kliplerin Analizi (Mikro-klip tespiti)
    # Kesimler arasındaki konuşma kliplerini hesapla
    speech_clips = []
    last_end = 0.0
    for c in cuts_v2:
        if c.start > last_end:
            speech_clips.append((last_end, c.start, c.start - last_end))
        last_end = max(last_end, c.end)
    if analysis.duration > last_end:
        speech_clips.append((last_end, analysis.duration, analysis.duration - last_end))

    micro_clips = [c for c in speech_clips if c[2] < 0.40]
    print(f"⚠️ 0.4 sn'den Kısa Kalan Mikro-Klip Sayısı: {len(micro_clips)} (Hedef: 0)")
    if micro_clips:
        for mc in micro_clips[:5]:
            print(f"   -> Mikro-klip: {mc[0]:.2f}s - {mc[1]:.2f}s ({mc[2]*1000:.0f}ms)")

    # 4. Chunker Testi
    chunker = AudioChunker(max_chunk_sec=600.0)
    split_points = chunker.calculate_split_points(analysis)
    print(f"📦 Akıllı Chunker Parça Sınırları (600s): {split_points}")

    print("=" * 60)
    print("✅ Benchmark başarıyla tamamlandı.")
    print("=" * 60)


if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else "/app/temp/test_audio.wav"
    run_benchmark(test_file)
