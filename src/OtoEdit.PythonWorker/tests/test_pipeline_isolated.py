#!/usr/bin/env python3
"""
OtoEdit İzole Pipeline Test Paketi
===================================
Her özelliği bağımsız olarak test eder ve sonuçları JSON raporu olarak kaydeder.
Kullanım: docker exec otoedit-dev-worker python /app/tests/test_pipeline_isolated.py
"""
import json
import os
import subprocess
import sys
import time
import traceback
from typing import Dict, Any, List, Tuple

# Proje modüllerini yükle
sys.path.insert(0, "/app")

RESULTS: List[Dict[str, Any]] = []
# Container'daki mevcut 1 saatlik video
SOURCE_VIDEO = "/app/temp/978e5ced-3e6b-441c-8c80-bfa55d214810.mp4"
TEST_DIR = "/app/temp/_isolated_tests"
os.makedirs(TEST_DIR, exist_ok=True)

# 2 dakikalık test klibi (60s - 180s arası => konuşma olan bölge)
TEST_CLIP = os.path.join(TEST_DIR, "test_clip_2min.mp4")
TEST_AUDIO = os.path.join(TEST_DIR, "test_clip_2min.mp3")


def log(msg: str):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def record_result(test_name: str, passed: bool, details: str, duration_sec: float = 0.0, data: Any = None):
    result = {
        "test": test_name,
        "passed": passed,
        "details": details,
        "duration_sec": round(duration_sec, 2),
    }
    if data:
        result["data"] = data
    RESULTS.append(result)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n  {status}: {test_name}")
    print(f"  Detay: {details}")
    if duration_sec > 0:
        print(f"  Süre: {duration_sec:.2f}s")


# ============================================================
# TEST 0: Test Klibi Hazırlama (2 dk)
# ============================================================
def test_0_prepare_clip():
    """1 saatlik videodan 60s-180s arasını keserek 2 dakikalık test klibi oluşturur."""
    log("TEST 0: Test Klibi Hazırlama (2 dk)")
    t0 = time.time()

    if os.path.isfile(TEST_CLIP) and os.path.getsize(TEST_CLIP) > 1_000_000:
        record_result("Test Klibi Hazırlama", True, "Mevcut klip kullanılıyor.", time.time() - t0)
        return True

    if not os.path.isfile(SOURCE_VIDEO):
        record_result("Test Klibi Hazırlama", False, f"Kaynak video bulunamadı: {SOURCE_VIDEO}")
        return False

    cmd = [
        "ffmpeg", "-y",
        "-ss", "60", "-t", "120",
        "-i", SOURCE_VIDEO,
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        TEST_CLIP
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        record_result("Test Klibi Hazırlama", False, f"FFmpeg hata: {res.stderr[-300:]}")
        return False

    # Audio çıkar
    cmd_audio = [
        "ffmpeg", "-y",
        "-i", TEST_CLIP,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        TEST_AUDIO
    ]
    subprocess.run(cmd_audio, capture_output=True, text=True, timeout=60)

    dur = _probe_duration(TEST_CLIP)
    record_result("Test Klibi Hazırlama", True,
                   f"Klip oluşturuldu: {os.path.getsize(TEST_CLIP) / 1024 / 1024:.1f} MB, süre: {dur:.1f}s",
                   time.time() - t0, {"clip_duration": dur})
    return True


# ============================================================
# TEST 1: FFprobe — Video Bilgisi Doğrulama
# ============================================================
def test_1_ffprobe():
    """Videonun codec, çözünürlük, FPS ve ses bilgilerini doğrular."""
    log("TEST 1: FFprobe Video Bilgisi")
    t0 = time.time()
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            TEST_CLIP
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        info = json.loads(res.stdout)

        video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
        audio_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)

        details = []
        data = {}
        if video_stream:
            data["video_codec"] = video_stream.get("codec_name")
            data["resolution"] = f"{video_stream.get('width')}x{video_stream.get('height')}"
            data["fps"] = video_stream.get("r_frame_rate")
            data["pix_fmt"] = video_stream.get("pix_fmt")
            details.append(f"Video: {data['video_codec']} {data['resolution']} @ {data['fps']}")
        if audio_stream:
            data["audio_codec"] = audio_stream.get("codec_name")
            data["sample_rate"] = audio_stream.get("sample_rate")
            data["channels"] = audio_stream.get("channels")
            details.append(f"Audio: {data['audio_codec']} {data['sample_rate']}Hz {data['channels']}ch")

        record_result("FFprobe Video Bilgisi", True, " | ".join(details), time.time() - t0, data)
    except Exception as e:
        record_result("FFprobe Video Bilgisi", False, str(e), time.time() - t0)


# ============================================================
# TEST 2: Transkript (faster-whisper)
# ============================================================
def test_2_transcript():
    """faster-whisper ile transkript çıkarır ve kelime zaman damgalarını doğrular."""
    log("TEST 2: Transkript (faster-whisper)")
    t0 = time.time()
    try:
        from pipeline.transcriber import Transcriber
        tr = Transcriber()
        audio_path = TEST_AUDIO if os.path.isfile(TEST_AUDIO) else TEST_CLIP
        result = tr.transcribe(audio_path, video_id="test_isolated")

        is_fallback = "[TRANSKRİPT ÇIKARILAMADI]" in result.full_text
        word_count = len(result.words)
        seg_count = len(result.segments)

        data = {
            "word_count": word_count,
            "segment_count": seg_count,
            "duration": result.duration,
            "is_fallback": is_fallback,
            "first_100_chars": result.full_text[:100],
            "sample_words": [
                {"word": w.word, "start": w.start, "end": w.end}
                for w in result.words[:5]
            ] if result.words else []
        }

        if is_fallback:
            record_result("Transkript (faster-whisper)", False,
                           "Transkript fallback moduna düştü - GPU/Model hatası!", time.time() - t0, data)
        elif word_count < 5:
            record_result("Transkript (faster-whisper)", False,
                           f"Sadece {word_count} kelime çıktı - muhtemelen hata var", time.time() - t0, data)
        else:
            record_result("Transkript (faster-whisper)", True,
                           f"{word_count} kelime, {seg_count} segment, süre: {result.duration:.1f}s",
                           time.time() - t0, data)

        # Transkript sonucunu kaydet (diğer testler kullanacak)
        with open(os.path.join(TEST_DIR, "transcript_result.json"), "w", encoding="utf-8") as f:
            json.dump({
                "full_text": result.full_text,
                "segments": [{"start": s.start, "end": s.end, "text": s.text,
                              "words": [{"word": w.word, "start": w.start, "end": w.end, "confidence": w.confidence}
                                        for w in (s.words or [])]}
                             for s in result.segments],
                "words": [{"word": w.word, "start": w.start, "end": w.end, "confidence": w.confidence}
                          for w in result.words],
                "duration": result.duration
            }, f, ensure_ascii=False, indent=2)

        return result if not is_fallback else None
    except Exception as e:
        record_result("Transkript (faster-whisper)", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)
        return None


# ============================================================
# TEST 3: Sessizlik Algılama
# ============================================================
def test_3_silence(audio_path: str = None):
    """Sessizlik bölgelerini tespit eder."""
    log("TEST 3: Sessizlik Algılama")
    t0 = time.time()
    try:
        from pipeline.silence_detector import SilenceDetector
        sd = SilenceDetector()
        ap = audio_path or TEST_AUDIO
        if not os.path.isfile(ap):
            ap = TEST_CLIP
        cuts = sd.detect(ap)

        data = {
            "cut_count": len(cuts),
            "cuts": [{"id": c.id, "start": c.start, "end": c.end, "reason": c.reason} for c in cuts[:10]]
        }
        total_silence = sum(c.end - c.start for c in cuts)

        if len(cuts) == 0:
            record_result("Sessizlik Algılama", False, "Hiç sessizlik bulunamadı - 2 dk'lık klipte bu anormal.", time.time() - t0, data)
        else:
            record_result("Sessizlik Algılama", True,
                           f"{len(cuts)} sessiz bölge, toplam {total_silence:.1f}s sessizlik kesilecek.",
                           time.time() - t0, data)
        return cuts
    except Exception as e:
        record_result("Sessizlik Algılama", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)
        return []


# ============================================================
# TEST 4: Retake (Hatalı Tekrar) Tespiti
# ============================================================
def test_4_retake(transcript_result=None, silence_cuts=None, audio_path: str = None):
    """Retake/hatalı tekrar tespitini doğrular."""
    log("TEST 4: Retake (Hatalı Tekrar) Tespiti")
    t0 = time.time()
    try:
        if transcript_result is None:
            record_result("Retake Tespiti", False, "Transkript sonucu yok, retake testi atlanıyor.", time.time() - t0)
            return []

        from pipeline.retake_detector import RetakeDetector
        rd = RetakeDetector()
        ap = audio_path or TEST_AUDIO
        if not os.path.isfile(ap):
            ap = TEST_CLIP
        cuts = rd.detect_retakes(ap, transcript_result, silence_cuts=silence_cuts)

        data = {
            "retake_count": len(cuts),
            "retakes": [{"id": c.id, "start": c.start, "end": c.end, "reason": c.reason, "command": c.command} for c in cuts[:10]]
        }

        record_result("Retake Tespiti", True,
                       f"{len(cuts)} hatalı tekrar tespit edildi.",
                       time.time() - t0, data)
        return cuts
    except Exception as e:
        record_result("Retake Tespiti", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)
        return []


# ============================================================
# TEST 5: Concat Demuxer ile Video Kesme (Ses Kayması Kontrolü)
# ============================================================
def test_5_concat_cut():
    """3 farklı segmenti keser, birleştirir ve A/V senkronunu doğrular."""
    log("TEST 5: Concat Demuxer Kesim + A/V Senkron")
    t0 = time.time()
    try:
        from render.video_renderer import VideoRenderer

        vr = VideoRenderer.__new__(VideoRenderer)

        segments = [
            (5.0, 25.0),
            (40.0, 70.0),
            (90.0, 110.0),
        ]

        concat_txt = os.path.join(TEST_DIR, "test_concat.txt")
        vr._create_concat_file(segments, TEST_CLIP, concat_txt)

        with open(concat_txt, "r") as f:
            concat_content = f.read()
        print(f"  Concat dosyası:\n{concat_content}")

        output = os.path.join(TEST_DIR, "test_concat_output.mp4")
        expected_dur = sum(e - s for s, e in segments)

        # Frame-Accurate Concat Motoru
        vr._execute_ffmpeg_with_concat(
            concat_txt_path=concat_txt,
            target_format="16:9",
            face_data=[],
            ass_path=None,
            output_path=output,
            trimmed_duration=expected_dur
        )

        out_dur = _probe_duration(output)
        expected_dur = sum(e - s for s, e in segments)
        diff = abs(out_dur - expected_dur)
        av_sync = _check_av_sync(output)

        data = {
            "expected_duration": expected_dur,
            "actual_duration": out_dur,
            "duration_diff": diff,
            "av_sync_offset_sec": av_sync,
            "output_size_mb": os.path.getsize(output) / 1024 / 1024
        }

        issues = []
        if diff > 1.0:
            issues.append(f"Süre farkı çok büyük: {diff:.2f}s (beklenen: {expected_dur:.1f}s, gerçek: {out_dur:.1f}s)")
        if av_sync is not None and abs(av_sync) > 0.1:
            issues.append(f"A/V senkron kayması: {av_sync:.3f}s")

        if issues:
            record_result("Concat Demuxer Kesim", False,
                           " | ".join(issues), time.time() - t0, data)
        else:
            record_result("Concat Demuxer Kesim", True,
                           f"Süre: {out_dur:.1f}s (beklenen: {expected_dur:.1f}s, fark: {diff:.2f}s) | A/V sync: {av_sync:.3f}s",
                           time.time() - t0, data)
        return True
    except Exception as e:
        record_result("Concat Demuxer Kesim", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)
        return False


# ============================================================
# TEST 6: NVENC GPU Encode (h264_nvenc)
# ============================================================
def test_6_nvenc():
    """GPU encode (h264_nvenc) çalışıp çalışmadığını test eder."""
    log("TEST 6: NVENC GPU Encode")
    t0 = time.time()
    try:
        output = os.path.join(TEST_DIR, "test_nvenc.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", TEST_CLIP,
            "-t", "10",
            "-c:v", "h264_nvenc", "-preset", "p4",
            "-b:v", "6M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            output
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if res.returncode == 0:
            size = os.path.getsize(output) / 1024
            record_result("NVENC GPU Encode", True,
                           f"NVENC çalışıyor! Çıktı: {size:.0f} KB", time.time() - t0)
            return True
        else:
            record_result("NVENC GPU Encode", False,
                           f"NVENC başarısız: {res.stderr[-300:]}", time.time() - t0)
            return False
    except Exception as e:
        record_result("NVENC GPU Encode", False, f"Exception: {e}", time.time() - t0)
        return False


# ============================================================
# TEST 7: Overlay (Altyazı Birleştirme)
# ============================================================
def test_7_overlay():
    """ASS altyazı oluşturup overlay ile birleştirmeyi test eder."""
    log("TEST 7: Altyazı Overlay (CPU Overlay + Encode)")
    t0 = time.time()
    try:
        from render.text_overlay import TextOverlay

        test_transcript = {
            "segments": [
                {"start": 1.0, "end": 3.0, "text": "Merhaba dünya", "words": [
                    {"word": "Merhaba", "start": 1.0, "end": 1.8},
                    {"word": "dünya", "start": 1.8, "end": 3.0}
                ]},
                {"start": 5.0, "end": 8.0, "text": "Bu bir test altyazısıdır", "words": [
                    {"word": "Bu", "start": 5.0, "end": 5.3},
                    {"word": "bir", "start": 5.3, "end": 5.6},
                    {"word": "test", "start": 5.6, "end": 6.2},
                    {"word": "altyazısıdır", "start": 6.2, "end": 8.0}
                ]}
            ]
        }

        ass_path = os.path.join(TEST_DIR, "test_subtitles.ass")
        TextOverlay.generate_ass(overlays=[], transcript=test_transcript, output_path=ass_path)

        if not os.path.isfile(ass_path):
            record_result("Altyazı Overlay", False, "ASS dosyası üretilemedi.", time.time() - t0)
            return False

        with open(ass_path, "r", encoding="utf-8") as f:
            ass_content = f.read()
        print(f"  ASS dosyası ({len(ass_content)} byte):\n{ass_content[:500]}")

        output = os.path.join(TEST_DIR, "test_overlay_output.mp4")
        safe_ass = ass_path.replace(":", "\\:")
        overlay_cmd = [
            "ffmpeg", "-y",
            "-i", TEST_CLIP,
            "-t", "15",
            "-vf", f"ass='{safe_ass}'",
            "-c:v", "h264_nvenc", "-preset", "p4",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            output
        ]
        print(f"  Overlay komutu: {' '.join(overlay_cmd)}")
        res = subprocess.run(overlay_cmd, capture_output=True, text=True, timeout=120)

        if res.returncode != 0:
            print("  NVENC basarisiz, CPU fallback deneniyor...")
            overlay_cmd_cpu = [
                "ffmpeg", "-y",
                "-i", TEST_CLIP,
                "-t", "15",
                "-vf", f"ass='{safe_ass}'",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                output
            ]
            res = subprocess.run(overlay_cmd_cpu, capture_output=True, text=True, timeout=120)

        if res.returncode != 0:
            record_result("Altyazı Overlay", False,
                           f"Overlay hatası: {res.stderr[-500:]}", time.time() - t0)
            return False

        data = {
            "ass_lines": ass_content.count("Dialogue:"),
            "cpu_overlay_ok": True,
            "output_size_mb": os.path.getsize(output) / 1024 / 1024
        }

        record_result("Altyazı Overlay", True,
                       f"CPU overlay basarili | Boyut: {data['output_size_mb']:.1f} MB",
                       time.time() - t0, data)
        return True
    except Exception as e:
        record_result("Altyazı Overlay", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)
        return False


# ============================================================
# TEST 8: Tam Pipeline Render (End-to-End)
# ============================================================
def test_8_full_render(transcript_result=None, silence_cuts=None, retake_cuts=None):
    """Tam pipeline render: Concat + Overlay + Encode"""
    log("TEST 8: Tam Pipeline Render (End-to-End)")
    t0 = time.time()
    try:
        from render.video_renderer import VideoRenderer

        all_cuts = []
        if silence_cuts:
            all_cuts.extend([{"start": c.start, "end": c.end, "reason": c.reason} for c in silence_cuts])
        if retake_cuts:
            all_cuts.extend([{"start": c.start, "end": c.end, "reason": c.reason} for c in retake_cuts])

        transcript_dict = None
        if transcript_result and hasattr(transcript_result, "segments"):
            transcript_dict = {
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text,
                     "words": [{"word": w.word, "start": w.start, "end": w.end} for w in (s.words or [])]}
                    for s in transcript_result.segments[:5]
                ]
            }

        edl_json = {
            "duration": _probe_duration(TEST_CLIP),
            "cuts": all_cuts[:20] if all_cuts else [],
            "overlays": [],
            "transcript": transcript_dict,
            "settings": {"targetFormat": "16:9"}
        }

        output = os.path.join(TEST_DIR, "test_full_render.mp4")
        temp_render_dir = os.path.join(TEST_DIR, "render_temp")
        os.makedirs(temp_render_dir, exist_ok=True)

        vr = VideoRenderer()
        vr.render(edl_json, TEST_CLIP, output, temp_dir=temp_render_dir)

        if not os.path.isfile(output) or os.path.getsize(output) < 10000:
            record_result("Tam Pipeline Render", False, "Çıktı dosyası oluşmadı veya çok küçük.", time.time() - t0)
            return False

        out_dur = _probe_duration(output)
        clip_dur = _probe_duration(TEST_CLIP)
        av_sync = _check_av_sync(output)

        if all_cuts:
            total_cut = sum(c["end"] - c["start"] for c in all_cuts[:20])
            expected_dur = clip_dur - total_cut
        else:
            expected_dur = clip_dur

        data = {
            "input_duration": clip_dur,
            "output_duration": out_dur,
            "expected_duration": expected_dur,
            "cuts_applied": len(all_cuts[:20]),
            "av_sync_offset": av_sync,
            "output_size_mb": os.path.getsize(output) / 1024 / 1024
        }

        issues = []
        if abs(out_dur - expected_dur) > 3.0:
            issues.append(f"Süre farkı: {abs(out_dur - expected_dur):.1f}s")
        if av_sync is not None and abs(av_sync) > 0.15:
            issues.append(f"A/V desync: {av_sync:.3f}s")

        if issues:
            record_result("Tam Pipeline Render", False,
                           f"Sorunlar: {' | '.join(issues)}", time.time() - t0, data)
        else:
            record_result("Tam Pipeline Render", True,
                           f"Giris: {clip_dur:.1f}s -> Cikis: {out_dur:.1f}s | {len(all_cuts[:20])} kesim uygulandı | Boyut: {data['output_size_mb']:.1f} MB",
                           time.time() - t0, data)
        return True
    except Exception as e:
        record_result("Tam Pipeline Render", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)
        return False


# ============================================================
# TEST 9: Concat + Overlay + NVENC Birlikte (Gerçek Render Komutu)
# ============================================================
def test_9_concat_overlay_combo():
    """Concat demuxer + overlay + NVENC: Render'ın gerçek tam komutu."""
    log("TEST 9: Concat + Overlay + NVENC (Gercek Render Komutu)")
    t0 = time.time()
    try:
        from render.video_renderer import VideoRenderer
        vr = VideoRenderer.__new__(VideoRenderer)

        segments = [(5.0, 25.0), (40.0, 70.0), (90.0, 110.0)]
        concat_txt = os.path.join(TEST_DIR, "test_combo_concat.txt")
        vr._create_concat_file(segments, TEST_CLIP, concat_txt)

        ass_path = os.path.join(TEST_DIR, "test_subtitles.ass")
        output = os.path.join(TEST_DIR, "test_combo_output.mp4")
        expected_dur = sum(e - s for s, e in segments)

        # GERCEK RENDER MOTORU: Paralel Frame-Accurate Concat + Direct ASS + NVENC
        vr._execute_ffmpeg_with_concat(
            concat_txt_path=concat_txt,
            target_format="16:9",
            face_data=[],
            ass_path=ass_path if os.path.isfile(ass_path) else None,
            output_path=output,
            trimmed_duration=expected_dur
        )

        if os.path.isfile(output) and os.path.getsize(output) > 1000:
            out_dur = _probe_duration(output)
            expected_dur = sum(e - s for s, e in segments)
            av_sync = _check_av_sync(output)
            data = {
                "expected_duration": expected_dur,
                "actual_duration": out_dur,
                "av_sync": av_sync,
                "output_size_mb": os.path.getsize(output) / 1024 / 1024
            }
            issues = []
            if abs(out_dur - expected_dur) > 1.5:
                issues.append(f"Süre farkı: {abs(out_dur - expected_dur):.1f}s")
            if av_sync is not None and abs(av_sync) > 0.15:
                issues.append(f"A/V desync: {av_sync:.3f}s")

            if issues:
                record_result("Concat + Overlay + Encode", False,
                               f"Sorunlar: {' | '.join(issues)}", time.time() - t0, data)
            else:
                record_result("Concat + Overlay + Encode", True,
                               f"Basarili! Sure: {out_dur:.1f}s | Boyut: {data['output_size_mb']:.1f} MB",
                               time.time() - t0, data)
        else:
            record_result("Concat + Overlay + Encode", False,
                           "Çıktı dosyası üretilemedi veya çok küçük.", time.time() - t0)

    except Exception as e:
        record_result("Concat + Overlay + Encode", False, f"Exception: {e}\n{traceback.format_exc()}", time.time() - t0)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================
def _probe_duration(path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return float(res.stdout.strip())
    except:
        return 0.0


def _check_av_sync(path: str) -> float:
    """Video ve ses başlangıç zamanları arasındaki farkı ölçer."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=start_time",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ]
        res_v = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        v_start = float(res_v.stdout.strip()) if res_v.stdout.strip() else 0.0

        cmd[3] = "a:0"
        res_a = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        a_start = float(res_a.stdout.strip()) if res_a.stdout.strip() else 0.0

        return round(v_start - a_start, 4)
    except:
        return None


# ============================================================
# ANA ÇALIŞTIRICI
# ============================================================
if __name__ == "__main__":
    log("OtoEdit Izole Pipeline Test Paketi Basliyor")
    total_start = time.time()

    # Test 0: Klip hazırla
    if not test_0_prepare_clip():
        print("\n\nTest klibi hazirlanamadi. Testler durduruluyor.")
        sys.exit(1)

    # Test 1: Video bilgisi
    test_1_ffprobe()

    # Test 2: Transkript
    transcript = test_2_transcript()

    # Test 3: Sessizlik
    silence_cuts = test_3_silence()

    # Test 4: Retake
    retake_cuts = test_4_retake(transcript, silence_cuts)

    # Test 5: Concat demuxer kesim
    test_5_concat_cut()

    # Test 6: NVENC
    test_6_nvenc()

    # Test 7: Overlay
    test_7_overlay()

    # Test 8: Tam pipeline render
    test_8_full_render(transcript, silence_cuts, retake_cuts)

    # Test 9: Concat + overlay + NVENC
    test_9_concat_overlay_combo()

    total_time = time.time() - total_start

    # SONUC RAPORU
    log("TEST SONUC RAPORU")
    passed = sum(1 for r in RESULTS if r["passed"])
    failed = sum(1 for r in RESULTS if not r["passed"])

    for r in RESULTS:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['test']}: {r['details'][:80]}")

    print(f"\n  Toplam: {passed} gecti / {failed} kaldi / {len(RESULTS)} test")
    print(f"  Toplam sure: {total_time:.1f}s")

    # JSON rapor kaydet
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_tests": len(RESULTS),
        "passed": passed,
        "failed": failed,
        "total_time_sec": round(total_time, 1),
        "results": RESULTS
    }
    report_path = os.path.join(TEST_DIR, "test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  Detayli rapor: {report_path}")

    if failed > 0:
        print(f"\n  {failed} TEST BASARISIZ! Detaylar yukarida.")
        sys.exit(1)
    else:
        print(f"\n  TUM TESTLER GECTI!")
        sys.exit(0)
