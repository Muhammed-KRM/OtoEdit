"""
video_renderer.py — EDL JSON'u okuyup kare ve ses örneği hassasiyetinde (frame-accurate)
FFmpeg trim + concat filtreleri ile ses-görüntü senkronunu koruyarak render eder.
"""
import os
import subprocess
import concurrent.futures
from typing import Dict, Any, List, Tuple, Optional
from render.image_overlay import ImageOverlay
from render.template_applier import TemplateApplier
from render.text_overlay import TextOverlay
from render.timeline_mapper import TimelineMapper
from services.minio_client import MinioClient
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    ffmpeg = importlib.import_module("ffmpeg")
except Exception:
    ffmpeg = None


class VideoRenderer:
    """EDL JSON'a göre frame-accurate ve sıfır desync ile video render eden motor."""

    def __init__(self, minio_client: Optional[MinioClient] = None):
        self.minio = minio_client or MinioClient()
        self.image_overlay = ImageOverlay(self.minio)

    def render(self, edl_json: Dict[str, Any], video_path: str, output_path: str, temp_dir: str = "/app/temp") -> str:
        """EDL JSON'a göre video render eder ve çıktı dosya yolunu döner."""
        logger.info(f"Render başlıyor: kaynak={video_path}, hedef={output_path}")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 0. Şablon verisini EDL'e işle
        edl_json = TemplateApplier.enrich_edl_with_template(edl_json)

        # Fontları Logla (Sorun Teşhisi İçin Sadece Bir Kere)
        try:
            fc_match = subprocess.run(["fc-match", "Inter V"], capture_output=True, text=True)
            fc_match_cinzel = subprocess.run(["fc-match", "Cinzel"], capture_output=True, text=True)
            logger.info(f"[DEBUG-FONT] fc-match 'Inter V': {fc_match.stdout.strip()}")
            logger.info(f"[DEBUG-FONT] fc-match 'Cinzel': {fc_match_cinzel.stdout.strip()}")
        except Exception as e:
            logger.warning(f"[DEBUG-FONT] Font kontrolü başarısız: {e}")

        # Toplam süre tespiti
        total_duration = float(edl_json.get("duration", 0.0))
        if total_duration <= 0:
            total_duration = self._probe_video_duration(video_path)

        cuts = edl_json.get("cuts", [])
        keep_segments = self._get_keep_segments(cuts, total_duration) if cuts and total_duration > 0 else []
        trimmed_duration = sum(end - start for start, end in keep_segments) if keep_segments else total_duration

        # Subtitle ASS üretimi (Metin overlay'leri ve transkript altyazıları)
        overlays = edl_json.get("overlays", [])
        transcript = edl_json.get("transcript")
        text_overlays = [ov for ov in overlays if ov.get("type") == "text"]
        image_overlays = [ov for ov in overlays if ov.get("type") == "image"]

        # 1. Segmentleri Kes ve Gerçek Süreleri Ölç
        actual_durations = None
        segment_files = []
        merge_concat = None
        
        has_cuts = keep_segments and len(keep_segments) > 0 and not (len(keep_segments) == 1 and keep_segments[0][0] == 0.0 and abs(keep_segments[0][1] - total_duration) < 0.1)

        if has_cuts:
            logger.info(f"🚀 Frame-Accurate Kesim başlıyor: {len(keep_segments)} korunan segment")
            concat_txt_path = os.path.join(temp_dir, f"cuts_{os.path.basename(output_path)}.txt")
            self._create_concat_file(keep_segments, video_path, concat_txt_path)
            
            segment_files, actual_durations, merge_concat = self._cut_segments(
                concat_txt_path=concat_txt_path,
                temp_dir=temp_dir
            )
            trimmed_duration = sum(actual_durations) if actual_durations else trimmed_duration

        # Zaman haritalama (Timeline Remapping) - Kesilmiş videonun zaman çizgisine uyarla
        if keep_segments and len(keep_segments) > 0:
            logger.info(f"⏱️ TimelineMapper uygulanıyor: {len(keep_segments)} segment baz alınarak altyazılar senkronlanıyor.")
            mapped_transcript = TimelineMapper.remap_transcript(transcript, keep_segments, actual_durations)
            mapped_text_overlays = TimelineMapper.remap_overlays(text_overlays, keep_segments, actual_durations)
            mapped_image_overlays = TimelineMapper.remap_overlays(image_overlays, keep_segments, actual_durations)
        else:
            mapped_transcript = transcript
            mapped_text_overlays = text_overlays
            mapped_image_overlays = image_overlays

        ass_path = None
        
        if mapped_text_overlays or mapped_transcript:
            candidate_ass = os.path.join(temp_dir, f"subtitles_{os.path.basename(output_path)}.ass")
            TextOverlay.generate_ass(
                overlays=mapped_text_overlays,
                transcript=mapped_transcript,
                output_path=candidate_ass
            )
            if os.path.isfile(candidate_ass):
                ass_path = candidate_ass
                logger.info(f"✅ Altyazı ASS dosyası üretildi: {ass_path}")

        settings = edl_json.get("settings", {})
        target_format = settings.get("targetFormat", "16:9")
        face_data = edl_json.get("repurposing", {}).get("faceTrackingData", [])

        # 2. Birleştirme (Concat) İşlemi
        if has_cuts and segment_files and merge_concat:
            logger.info(f"🚀 Birleştirme ve Render uygulanıyor, tahmini süre={trimmed_duration:.1f}s")
            self._concat_segments(
                merge_concat=merge_concat,
                segment_files=segment_files,
                target_format=target_format,
                face_data=face_data,
                ass_path=ass_path,
                output_path=output_path,
                trimmed_duration=trimmed_duration
            )
        else:
            logger.info("Kesim listesi yok veya tüm video korunuyor. Doğrudan kaynak video işleniyor.")
            self._execute_ffmpeg_direct(
                video_path=video_path,
                target_format=target_format,
                face_data=face_data,
                ass_path=ass_path,
                output_path=output_path
            )

        logger.info(f"Base render tamamlandı: {output_path}")

        # 2. İkinci Geçiş (Görsel Overlay'leri Varsa)
        if mapped_image_overlays:
            logger.info(f"🎨 {len(mapped_image_overlays)} görsel overlay için ikinci pass yürütülüyor...")
            temp_no_images = os.path.join(temp_dir, f"no_img_{os.path.basename(output_path)}")
            if os.path.exists(output_path):
                os.rename(output_path, temp_no_images)
                try:
                    if ffmpeg is None:
                        raise ImportError("ffmpeg-python modülü yüklü değil")
                    probe = ffmpeg.probe(temp_no_images)
                    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                    base_w = int(video_info['width'])
                    base_h = int(video_info['height'])

                    in_node = ffmpeg.input(temp_no_images)
                    v_stream = in_node.video
                    a_stream = in_node.audio

                    v_stream = self.image_overlay.apply_image_overlays(
                        v_stream, 
                        mapped_image_overlays, 
                        temp_dir=temp_dir,
                        base_w=base_w,
                        base_h=base_h
                    )

                    out_cmd_nvenc = ffmpeg.output(
                        v_stream, a_stream, output_path,
                        vcodec="h264_nvenc", preset="p4", video_bitrate="6M", maxrate="8M", bufsize="12M",
                        acodec="copy", shortest=None
                    ).overwrite_output().compile()

                    out_cmd_cpu = ffmpeg.output(
                        v_stream, a_stream, output_path,
                        vcodec="libx264", preset="veryfast", crf="22",
                        acodec="copy", shortest=None
                    ).overwrite_output().compile()

                    logger.info("Donanım hızlandırmalı (NVENC) image overlay yürütülüyor...")
                    res = subprocess.run(out_cmd_nvenc, capture_output=True, text=True, timeout=7200)
                    if res.returncode == 0:
                        logger.info("✅ Görsel kaplamalar eklendi (NVENC).")
                        os.remove(temp_no_images)
                    else:
                        logger.warning("NVENC overlay başarısız oldu. CPU moduna geçiliyor.")
                        res_cpu = subprocess.run(out_cmd_cpu, capture_output=True, text=True, timeout=7200)
                        if res_cpu.returncode == 0:
                            logger.info("✅ Görsel kaplamalar eklendi (CPU).")
                            os.remove(temp_no_images)
                        else:
                            raise RuntimeError("CPU overlay pass başarısız oldu.")
                except Exception as e:
                    logger.error(f"Görsel overlay eklenirken hata: {e}")
                    if os.path.exists(temp_no_images):
                        os.rename(temp_no_images, output_path)

        logger.info(f"Render tamamen başarıyla tamamlandı: {output_path}")
        return output_path

    def _cut_segments(self, concat_txt_path: str, temp_dir: str) -> Tuple[List[str], List[float], str]:
        """
        Segmentleri keser ve sürelerini ölçer. 
        Geri dönüş: (segment_files, actual_durations, merge_concat_path)
        """
        segments = self._parse_concat_file(concat_txt_path)
        if not segments:
            raise RuntimeError("Concat dosyası boş veya okunamadı!")
        
        # NVIDIA consumer GPU'lar genellikle en fazla 3-8 eşzamanlı NVENC session destekler.
        # Çok fazla thread açılırsa session limiti aşılır ve sistem gizlice (fallback) CPU'ya geçer, bu da render'ı 45 dakikaya uzatır!
        # Limiti 2'de tutarak NVENC'in tüm segmentleri çok yüksek hızda, CPU'ya düşmeden işlemesini sağlıyoruz.
        max_workers = 2
        logger.info(f"🎬 Frame-accurate paralel kesim başlıyor: {len(segments)} segment, {max_workers} thread (NVENC limiti koruması)")
        
        def _cut_single_segment(item: Tuple[int, Tuple[str, float, float]]) -> Optional[Tuple[int, str]]:
            idx, (video_path, start, end) = item
            seg_out = os.path.join(temp_dir, f"seg_{idx:04d}.mp4")
            duration = end - start
            
            base_args = ["ffmpeg", "-y", "-ss", str(start), "-i", video_path, "-t", str(duration)]
            
            nvenc_cmd = base_args + ["-c:v", "h264_nvenc", "-preset", "p1", "-b:v", "8M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-fps_mode", "cfr", "-avoid_negative_ts", "make_zero", seg_out]
            res = subprocess.run(nvenc_cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.isfile(seg_out) and os.path.getsize(seg_out) > 1000:
                return (idx, seg_out)
                
            cpu_cmd = base_args + ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-fps_mode", "cfr", "-avoid_negative_ts", "make_zero", seg_out]
            res_cpu = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=300)
            if res_cpu.returncode == 0 and os.path.isfile(seg_out) and os.path.getsize(seg_out) > 1000:
                return (idx, seg_out)
                
            if os.path.isfile(seg_out):
                try: os.remove(seg_out)
                except Exception: pass
                
            logger.warning(f"Segment {idx} kesimi başarısız: {res_cpu.stderr[-200:] if res_cpu.stderr else ''}")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            cut_results = list(executor.map(_cut_single_segment, enumerate(segments)))

        valid_cuts = sorted([r for r in cut_results if r is not None], key=lambda x: x[0])
        segment_files = [path for _, path in valid_cuts]

        if not segment_files:
            raise RuntimeError("Hiçbir segment kesilemedi!")
        
        logger.info(f"✂ {len(segment_files)}/{len(segments)} segment başarıyla paralel kesildi.")
        
        actual_durations = []
        for idx, seg_file in enumerate(segment_files):
            try:
                probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", seg_file]
                result = subprocess.run(probe_cmd, capture_output=True, text=True)
                actual_dur = float(result.stdout.strip()) if result.stdout.strip() else 0.0
                expected_dur = segments[idx][2] - segments[idx][1]
                drift = abs(actual_dur - expected_dur)
                if drift > 0.05:
                    logger.warning(f"[SYNC-DRIFT] Segment {idx}: beklenen={expected_dur:.3f}s, gerçek={actual_dur:.3f}s, sapma={drift:.3f}s")
                else:
                    logger.debug(f"[SYNC-OK] Segment {idx}: {actual_dur:.3f}s ≈ {expected_dur:.3f}s")
                actual_durations.append(actual_dur)
            except Exception as e:
                logger.warning(f"[SYNC-CHECK] Segment {idx} kontrol edilemedi: {e}")
                actual_durations.append(segments[idx][2] - segments[idx][1])
        
        merge_concat = os.path.join(temp_dir, "merge_concat.txt")
        with open(merge_concat, "w", encoding="utf-8") as f:
            f.write("ffconcat version 1.0\n")
            for seg_file in segment_files:
                f.write(f"file '{os.path.abspath(seg_file).replace(chr(92), '/')}'\n")
                
        return segment_files, actual_durations, merge_concat

    def _concat_segments(self, merge_concat: str, segment_files: List[str], target_format: str, face_data: Optional[List[Dict[str, Any]]], ass_path: Optional[str], output_path: str, trimmed_duration: float):
        """Hazırlanan segmentleri FFmpeg concat demuxer ve filtreler ile birleştirir."""
        vf = []
        if target_format == "9:16":
            crop_cmd = self._get_crop_str(face_data, "9:16").lstrip(",")
            if crop_cmd: vf.append(crop_cmd)
        elif target_format == "1:1":
            crop_cmd = self._get_crop_str(face_data, "1:1").lstrip(",")
            if crop_cmd: vf.append(crop_cmd)
        
        if ass_path and os.path.isfile(ass_path):
            safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            vf.append(f"ass='{safe_ass}'")
        
        base_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", merge_concat]
        if vf:
            base_cmd.extend(["-vf", ",".join(vf)])
            
        base_cmd.extend(["-fps_mode", "cfr", "-af", "aresample=async=1000"])
        if trimmed_duration > 0:
            base_cmd.extend(["-t", str(trimmed_duration)])
        base_cmd.append("-shortest")
        
        nvenc_cmd = base_cmd + ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "6M", "-maxrate", "8M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", output_path]

        try:
            logger.info("Donanım hızlandırmalı (NVENC) render yürütülüyor...")
            res = subprocess.run(nvenc_cmd, capture_output=True, text=True, timeout=7200)
            if res.returncode == 0:
                logger.info("✅ Donanım hızlandırmalı (NVENC) render başarıyla tamamlandı.")
                self._cleanup_segment_files(segment_files, merge_concat)
                return
            logger.warning(f"NVENC render başarısız oldu. CPU moduna geçiliyor. Hata: {res.stderr[-300:] if res.stderr else ''}")
        except Exception as err:
            logger.warning(f"NVENC başlatılamadı ({err}). CPU moduna geçiliyor.")

        cpu_cmd = base_cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", output_path]
        logger.info("CPU Fallback komutu yürütülüyor...")
        res = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=7200)
        self._cleanup_segment_files(segment_files, merge_concat)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg render hatası: {res.stderr[-500:]}")
        logger.info("✅ CPU render başarıyla tamamlandı.")
    
    def _parse_concat_file(self, concat_path: str) -> List[Tuple[str, float, float]]:
        """ffconcat dosyasını parse edip (video_path, start, end) listesi döner."""
        segments = []
        current_file = None
        current_inpoint = 0.0
        
        with open(concat_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("file "):
                    current_file = line.split("'")[1] if "'" in line else line[5:].strip()
                elif line.startswith("inpoint "):
                    current_inpoint = float(line.split()[1])
                elif line.startswith("outpoint "):
                    outpoint = float(line.split()[1])
                    if current_file:
                        segments.append((current_file, current_inpoint, outpoint))
        return segments
    
    def _cleanup_segment_files(self, segment_files: List[str], merge_concat: str):
        """Geçici segment dosyalarını temizler."""
        for f in segment_files:
            try:
                os.remove(f)
            except Exception:
                pass
        try:
            os.remove(merge_concat)
        except Exception:
            pass

    def _execute_ffmpeg_direct(self, video_path: str, target_format: str,
                               face_data: List[Dict[str, Any]], ass_path: Optional[str], output_path: str):
        """Kesim olmadan yalnızca format veya altyazı varsa çalışan doğrudan komut."""
        vf = []
        if target_format == "9:16":
            vf.append(self._get_crop_str(face_data, "9:16").lstrip(","))
        elif target_format == "1:1":
            vf.append(self._get_crop_str(face_data, "1:1").lstrip(","))

        if ass_path and os.path.isfile(ass_path):
            safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            vf.append(f"ass='{safe_ass}'")

        base_cmd = ["ffmpeg", "-y", "-i", video_path]
        if vf:
            base_cmd.extend(["-vf", ",".join(vf)])

        # NVENC
        nvenc_cmd = base_cmd + [
            "-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "6M",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", output_path
        ]
        try:
            res = subprocess.run(nvenc_cmd, capture_output=True, text=True, timeout=7200)
            if res.returncode == 0:
                logger.info("✅ Doğrudan NVENC render başarıyla tamamlandı.")
                return
        except Exception:
            pass

        # CPU Fallback
        cpu_cmd = base_cmd + [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", output_path
        ]
        res = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=7200)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg doğrudan render hatası: {res.stderr[-500:]}")

    def _get_crop_str(self, face_data: Optional[List[Dict[str, Any]]], target_format: str) -> str:
        """Kırpma filtre ifadesini döner."""
        if target_format == "9:16":
            target_w = "ih*9/16"
            if face_data and len(face_data) > 0:
                valid_x = [f.get("x", 0.5) for f in face_data if isinstance(f.get("x"), (int, float))]
                avg_face_x = sum(valid_x) / len(valid_x) if valid_x else 0.5
                crop_x = f"max(0, min(iw - ow, iw*{avg_face_x:.3f} - ow/2))"
            else:
                crop_x = "(iw-ow)/2"
            return f"crop={target_w}:ih:{crop_x}:0"
        elif target_format == "1:1":
            return "crop=ih:ih:(iw-ow)/2:0"
        return ""

    def _get_keep_segments(self, cuts: List[Dict[str, Any]], total_duration: float) -> List[Tuple[float, float]]:
        """Kesilecek kısımları ayıklayıp tutulacak aralıkları döner."""
        valid_cuts = []
        for c in cuts:
            try:
                s = float(c.get("start", 0.0))
                e = float(c.get("end", 0.0))
                if e > s:
                    valid_cuts.append((s, e))
            except (ValueError, TypeError):
                continue

        cut_ranges = sorted(valid_cuts, key=lambda x: x[0])
        # Çakışan kesimleri birleştir
        merged_cuts = []
        for s, e in cut_ranges:
            if not merged_cuts:
                merged_cuts.append([s, e])
            else:
                if s <= merged_cuts[-1][1]:
                    merged_cuts[-1][1] = max(merged_cuts[-1][1], e)
                else:
                    merged_cuts.append([s, e])

        segments = []
        current = 0.0

        for start, end in merged_cuts:
            if current < start:
                segments.append((round(current, 3), round(start, 3)))
            current = max(current, end)

        if total_duration > 0 and current < total_duration:
            segments.append((round(current, 3), round(total_duration, 3)))

        return segments

    def _create_concat_file(self, segments: List[Tuple[float, float]], video_path: str, out_file: str):
        """Birim testleri ve geriye dönük uyumluluk için korunan concat demuxer dosyası üretici."""
        clean_video_path = os.path.abspath(video_path).replace("\\", "/")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write("ffconcat version 1.0\n")
            for start, end in segments:
                f.write(f"file '{clean_video_path}'\n")
                f.write(f"inpoint {start}\n")
                f.write(f"outpoint {end}\n")

    def _probe_video_duration(self, video_path: str) -> float:
        """ffprobe ile videonun süresini saniye cinsinden sorgular."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"ffprobe süresi okunamadı ({video_path}): {e}")
            return 0.0
