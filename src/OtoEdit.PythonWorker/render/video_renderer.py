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

        # Zaman haritalama (Timeline Remapping) - Kesilmiş videonun zaman çizgisine uyarla
        if keep_segments and len(keep_segments) > 0:
            logger.info(f"⏱️ TimelineMapper uygulanıyor: {len(keep_segments)} segment baz alınarak altyazılar senkronlanıyor.")
            mapped_transcript = TimelineMapper.remap_transcript(transcript, keep_segments)
            mapped_overlays = TimelineMapper.remap_overlays(text_overlays, keep_segments)
        else:
            mapped_transcript = transcript
            mapped_overlays = text_overlays

        ass_path = None
        
        if mapped_overlays or mapped_transcript:
            candidate_ass = os.path.join(temp_dir, f"subtitles_{os.path.basename(output_path)}.ass")
            TextOverlay.generate_ass(
                overlays=mapped_overlays,
                transcript=mapped_transcript,
                output_path=candidate_ass
            )
            if os.path.isfile(candidate_ass):
                ass_path = candidate_ass
                logger.info(f"✅ Altyazı ASS dosyası üretildi: {ass_path}")

        settings = edl_json.get("settings", {})
        target_format = settings.get("targetFormat", "16:9")
        face_data = edl_json.get("repurposing", {}).get("faceTrackingData", [])

        # 1. Kesim Listesi Varsa: Paralel Frame-Accurate Trim + Concat + NVENC
        if keep_segments and len(keep_segments) > 0 and not (len(keep_segments) == 1 and keep_segments[0][0] == 0.0 and abs(keep_segments[0][1] - total_duration) < 0.1):
            logger.info(f"🚀 Frame-Accurate Concat uygulanıyor: {len(keep_segments)} korunan segment, tahmini süre={trimmed_duration:.1f}s")
            concat_txt_path = os.path.join(temp_dir, f"cuts_{os.path.basename(output_path)}.txt")
            self._create_concat_file(keep_segments, video_path, concat_txt_path)
            
            self._execute_ffmpeg_with_concat(
                concat_txt_path=concat_txt_path,
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

        logger.info(f"Render başarıyla tamamlandı: {output_path}")
        return output_path

    def _execute_ffmpeg_with_concat(self, concat_txt_path: str, target_format: str,
                                    face_data: Optional[List[Dict[str, Any]]], 
                                    ass_path: Optional[str], 
                                    output_path: str,
                                    trimmed_duration: float = 0.0):
        """
        Frame-accurate trim + concat render motoru.
        
        Her segment ThreadPoolExecutor ile paralel olarak frame-accurate kesilir (-ss input seeking + re-encode),
        ardından concat demuxer ile birleştirilir. Altyazı ASS filtresi doğrudan uygulanır.
        """
        temp_dir = os.path.dirname(concat_txt_path)
        
        # 1. Concat dosyasından segmentleri parse et
        segments = self._parse_concat_file(concat_txt_path)
        if not segments:
            raise RuntimeError("Concat dosyası boş veya okunamadı!")
        
        max_workers = min(os.cpu_count() or 4, 8)
        logger.info(f"🎬 Frame-accurate paralel kesim başlıyor: {len(segments)} segment, {max_workers} thread")
        
        def _cut_single_segment(item: Tuple[int, Tuple[str, float, float]]) -> Optional[Tuple[int, str]]:
            idx, (video_path, start, end) = item
            seg_out = os.path.join(temp_dir, f"seg_{idx:04d}.mp4")
            duration = end - start
            seg_cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-fps_mode", "cfr",
                "-avoid_negative_ts", "make_zero",
                seg_out
            ]
            res = subprocess.run(seg_cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0 and os.path.isfile(seg_out) and os.path.getsize(seg_out) > 1000:
                return (idx, seg_out)
            logger.warning(f"Segment {idx} kesimi başarısız: {res.stderr[-200:] if res.stderr else 'Bilinmeyen hata'}")
            return None

        # 2. Paralel kesim yürüt
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            cut_results = list(executor.map(_cut_single_segment, enumerate(segments)))

        valid_cuts = sorted([r for r in cut_results if r is not None], key=lambda x: x[0])
        segment_files = [path for _, path in valid_cuts]

        if not segment_files:
            raise RuntimeError("Hiçbir segment kesilemedi!")
        
        logger.info(f"✂ {len(segment_files)}/{len(segments)} segment başarıyla paralel kesildi.")
        
        # 3. Kesilmiş segmentleri birleştirmek için yeni concat dosyası oluştur
        merge_concat = os.path.join(temp_dir, "merge_concat.txt")
        with open(merge_concat, "w", encoding="utf-8") as f:
            f.write("ffconcat version 1.0\n")
            for seg_file in segment_files:
                clean_path = os.path.abspath(seg_file).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")
        
        # 4. VF hazırlığı (Kırpma + Doğrudan ASS Altyazı)
        vf = []
        if target_format == "9:16":
            crop_cmd = self._get_crop_str(face_data, "9:16").lstrip(",")
            if crop_cmd:
                vf.append(crop_cmd)
        elif target_format == "1:1":
            crop_cmd = self._get_crop_str(face_data, "1:1").lstrip(",")
            if crop_cmd:
                vf.append(crop_cmd)
        
        if ass_path and os.path.isfile(ass_path):
            safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            vf.append(f"ass='{safe_ass}'")
        
        # 5. Birleştirme komutu
        base_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", merge_concat
        ]
        
        if vf:
            base_cmd.extend(["-vf", ",".join(vf)])
            
        base_cmd.extend([
            "-fps_mode", "cfr",
            "-af", "aresample=async=1000"
        ])
        if trimmed_duration > 0:
            base_cmd.extend(["-t", str(trimmed_duration)])
        base_cmd.append("-shortest")
        
        # NVENC Denemesi
        nvenc_cmd = list(base_cmd) + [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-b:v", "6M",
            "-maxrate", "8M",
            "-bufsize", "12M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

        try:
            logger.info("Donanım hızlandırmalı (NVENC) render yürütülüyor...")
            res = subprocess.run(nvenc_cmd, capture_output=True, text=True, timeout=7200)
            if res.returncode == 0:
                logger.info("✅ Donanım hızlandırmalı (NVENC) render başarıyla tamamlandı.")
                self._cleanup_segment_files(segment_files, merge_concat)
                return
            logger.warning(f"NVENC render başarısız oldu. CPU moduna (libx264) geçiliyor. Hata: {res.stderr[-300:] if res.stderr else ''}")
        except Exception as nvenc_err:
            logger.warning(f"NVENC başlatılamadı ({nvenc_err}). CPU moduna geçiliyor.")

        # CPU Fallback
        cpu_cmd = list(base_cmd) + [
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        
        logger.info("CPU Fallback komutu yürütülüyor...")
        res = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=7200)
        self._cleanup_segment_files(segment_files, merge_concat)
        if res.returncode != 0:
            logger.error(f"FFmpeg CPU Render Hatası: {res.stderr[-500:]}")
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
