"""
video_renderer.py — EDL JSON'u okuyup kare ve ses örneği hassasiyetinde (frame-accurate)
FFmpeg trim + concat filtreleri ile ses-görüntü senkronunu koruyarak render eder.
"""
import os
import subprocess
from typing import Dict, Any, List, Tuple, Optional
from render.image_overlay import ImageOverlay
from render.template_applier import TemplateApplier
from render.text_overlay import TextOverlay
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

        # Subtitle ASS üretimi (Metin overlay'leri ve transkript altyazıları)
        overlays = edl_json.get("overlays", [])
        transcript = edl_json.get("transcript")
        text_overlays = [ov for ov in overlays if ov.get("type") == "text"]
        ass_path = None
        if text_overlays or transcript:
            candidate_ass = os.path.join(temp_dir, f"subtitles_{os.path.basename(output_path)}.ass")
            TextOverlay.generate_ass(
                overlays=text_overlays,
                transcript=transcript,
                output_path=candidate_ass
            )
            if os.path.isfile(candidate_ass):
                ass_path = candidate_ass

        settings = edl_json.get("settings", {})
        target_format = settings.get("targetFormat", "16:9")
        face_data = edl_json.get("repurposing", {}).get("faceTrackingData", [])

        # 1. Kesim Listesi Varsa: Frame-Accurate Trim + Concat Filter
        # Concat demuxer yerine filter_complex kullanılarak GOP / I-frame gecikmesi
        # ve AAC priming ses kayması (A/V desync) %100 engellenir.
        if keep_segments and len(keep_segments) > 0 and not (len(keep_segments) == 1 and keep_segments[0][0] == 0.0 and abs(keep_segments[0][1] - total_duration) < 0.1):
            logger.info(f"🚀 Frame-Accurate trim+concat filtresi uygulanıyor: {len(keep_segments)} korunan segment")
            filter_script_path = os.path.join(temp_dir, f"filter_{os.path.basename(output_path)}.txt")
            v_label, a_label = self._build_filter_script_file(
                keep_segments=keep_segments,
                script_path=filter_script_path,
                target_format=target_format,
                face_data=face_data,
                ass_path=ass_path
            )
            self._execute_ffmpeg_with_script(
                video_path=video_path,
                filter_script_path=filter_script_path,
                v_label=v_label,
                a_label=a_label,
                output_path=output_path
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

    def _build_filter_script_file(
        self,
        keep_segments: List[Tuple[float, float]],
        script_path: str,
        target_format: str = "16:9",
        face_data: Optional[List[Dict[str, Any]]] = None,
        ass_path: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        FFmpeg filter_complex_script dosyasını milisaniye hassasiyetli trim ve atrim filtreleri ile oluşturur.
        """
        v_parts = []
        a_parts = []
        labels = []

        for i, (s, e) in enumerate(keep_segments):
            # start ve end sürelerini 3 basamaklı float formatla
            v_parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}]")
            a_parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}]")
            labels.append(f"[v{i}][a{i}]")

        n = len(keep_segments)
        all_labels = "".join(labels)
        concat_line = f"{all_labels}concat=n={n}:v=1:a=1[v_cut][a_cut]"

        lines = v_parts + a_parts + [concat_line]
        current_v = "[v_cut]"

        # Format Dönüştürme (9:16 veya 1:1 Dinamik Yüz Merkezli Kırpma)
        if target_format == "9:16":
            crop_str = self._get_crop_str(face_data, "9:16")
            lines.append(f"{current_v}{crop_str}[v_crop]")
            current_v = "[v_crop]"
        elif target_format == "1:1":
            crop_str = self._get_crop_str(face_data, "1:1")
            lines.append(f"{current_v}{crop_str}[v_crop]")
            current_v = "[v_crop]"

        # Altyazı Kaplaması (.ass)
        if ass_path and os.path.isfile(ass_path):
            safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            lines.append(f"{current_v}ass='{safe_ass}'[v_sub]")
            current_v = "[v_sub]"

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(";\n".join(lines))

        return current_v, "[a_cut]"

    def _execute_ffmpeg_with_script(self, video_path: str, filter_script_path: str,
                                    v_label: str, a_label: str, output_path: str):
        """Donanım ivmeli (NVENC) veya CPU yedekli render komutunu çalıştırır."""
        # 1. Donanım Hızlandırmalı NVENC Dene
        nvenc_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex_script", filter_script_path,
            "-map", v_label,
            "-map", a_label,
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
                return
            logger.warning(f"NVENC render başarısız oldu (Hata: {res.stderr[:300]}). CPU moduna (libx264) geçiliyor.")
        except Exception as nvenc_err:
            logger.warning(f"NVENC başlatılamadı ({nvenc_err}). CPU moduna geçiliyor.")

        # 2. CPU Fallback
        cpu_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex_script", filter_script_path,
            "-map", v_label,
            "-map", a_label,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        res = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=7200)
        if res.returncode != 0:
            logger.error(f"FFmpeg CPU Render Hatası: {res.stderr}")
            raise RuntimeError(f"FFmpeg render hatası: {res.stderr[-500:]}")
        logger.info("✅ CPU render başarıyla tamamlandı.")

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
