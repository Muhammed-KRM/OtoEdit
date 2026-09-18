"""video_renderer.py — EDL JSON'u okuyup FFmpeg filter_complex ile videoyu render eder."""
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
    import ffmpeg
except ImportError:
    ffmpeg = None


class VideoRenderer:
    """EDL JSON'u okuyarak FFmpeg filter_complex ile donanım destekli ve dayanıklı render eder."""

    def __init__(self, minio_client: Optional[MinioClient] = None):
        self.minio = minio_client or MinioClient()
        self.image_overlay = ImageOverlay(self.minio)

    def render(self, edl_json: Dict[str, Any], video_path: str, output_path: str, temp_dir: str = "/app/temp") -> str:
        """EDL JSON'a göre video render eder ve çıktı dosya yolunu döner."""
        logger.info(f"Render başlıyor: kaynak={video_path}, hedef={output_path}")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if not ffmpeg:
            raise RuntimeError("ffmpeg-python modülü yüklü değil!")

        # 0. Şablon verisini EDL'e işle
        edl_json = TemplateApplier.enrich_edl_with_template(edl_json)

        # Toplam süre tespiti (EDL'de yoksa ffprobe ile sorgula)
        total_duration = float(edl_json.get("duration", 0.0))
        if total_duration <= 0:
            total_duration = self._probe_video_duration(video_path)

        # 1. Cuts uygula (Concat Demuxer ile kesintisiz birleştirme)
        cuts = edl_json.get("cuts", [])
        concat_file_path = os.path.join(temp_dir, f"concat_{os.path.basename(output_path)}.txt")

        if cuts and total_duration > 0:
            keep_segments = self._get_keep_segments(cuts, total_duration)
            if keep_segments:
                self._create_concat_file(keep_segments, video_path, concat_file_path)
                logger.info(f"Concat demuxer kullanılıyor: {len(keep_segments)} korunan segment")
                inp = ffmpeg.input(concat_file_path, format='concat', safe=0)
            else:
                logger.warning("Tüm video kesilmiş görünüyor! Doğrudan kaynak video kullanılıyor.")
                inp = ffmpeg.input(video_path)
        else:
            inp = ffmpeg.input(video_path)

        v = inp.video
        a = inp.audio

        # 2. Format Dönüştürme (9:16 veya 1:1 Crop)
        settings = edl_json.get("settings", {})
        target_format = settings.get("targetFormat", "16:9")
        if target_format in ["9:16", "1:1"]:
            face_data = edl_json.get("repurposing", {}).get("faceTrackingData", [])
            v = self._apply_smooth_crop(v, face_data, target_format)

        # 3. Görsel Kaplamalar (Image & Logo)
        overlays = edl_json.get("overlays", [])
        v = self.image_overlay.apply_image_overlays(
            base_stream=v,
            overlays=overlays,
            temp_dir=temp_dir
        )

        # 4. Text ve Altyazı Kaplaması (.ass dosyası ile)
        transcript = edl_json.get("transcript")
        text_overlays = [ov for ov in overlays if ov.get("type") == "text"]

        if text_overlays or transcript:
            ass_path = os.path.join(temp_dir, f"subtitles_{os.path.basename(output_path)}.ass")
            TextOverlay.generate_ass(
                overlays=text_overlays,
                transcript=transcript,
                output_path=ass_path
            )
            # FFmpeg ASS filtresi
            if os.path.isfile(ass_path):
                # Linux/Windows path uyumluluğu için escape
                safe_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
                v = v.filter('ass', safe_ass_path)
                logger.info(f"ASS altyazı filtresi video akışına eklendi: {safe_ass_path}")

        # 5. FFmpeg Render Çalıştırma (Donanım NVENC -> Fallback libx264)
        self._execute_ffmpeg(v, a, output_path)

        logger.info(f"Render başarıyla tamamlandı: {output_path}")
        return output_path

    def _execute_ffmpeg(self, v_stream: Any, a_stream: Any, output_path: str):
        """Önce donanım hızlandırmalı (h264_nvenc) dener, GPU yoksa libx264 ile devam eder."""
        try:
            logger.info("Donanım hızlandırmalı (NVENC) render deneniyor...")
            out = ffmpeg.output(
                v_stream, a_stream, output_path,
                vcodec='h264_nvenc', preset='p4',
                acodec='aac', audio_bitrate='192k'
            )
            out.run(overwrite_output=True, quiet=True)
            return
        except Exception as nvenc_err:
            logger.warning(f"NVENC render başarısız oldu veya GPU bulunamadı ({nvenc_err}). libx264 (CPU) moduna geçiliyor.")

        # CPU Fallback
        try:
            out_cpu = ffmpeg.output(
                v_stream, a_stream, output_path,
                vcodec='libx264', preset='veryfast', crf=22,
                acodec='aac', audio_bitrate='192k',
                pix_fmt='yuv420p'
            )
            out_cpu.run(overwrite_output=True, quiet=True)
        except ffmpeg.Error as e:
            err_msg = e.stderr.decode('utf-8', errors='ignore') if hasattr(e, 'stderr') and e.stderr else str(e)
            logger.error(f"FFmpeg CPU Render Hatası: {err_msg}")
            raise RuntimeError(f"FFmpeg render hatası: {err_msg}")

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
        segments = []
        current = 0.0

        for start, end in cut_ranges:
            if current < start:
                segments.append((round(current, 2), round(start, 2)))
            current = max(current, end)

        if total_duration > 0 and current < total_duration:
            segments.append((round(current, 2), round(total_duration, 2)))

        return segments

    def _create_concat_file(self, segments: List[Tuple[float, float]], video_path: str, out_file: str):
        """FFmpeg concat demuxer için inpoint/outpoint içeren txt dosyası üretir."""
        # Ters bölü çizgilerini normalize et
        clean_video_path = os.path.abspath(video_path).replace("\\", "/")
        with open(out_file, 'w', encoding='utf-8') as f:
            for start, end in segments:
                f.write(f"file '{clean_video_path}'\n")
                f.write(f"inpoint {start}\n")
                f.write(f"outpoint {end}\n")

    def _apply_smooth_crop(self, video_stream: Any, face_data: List[Dict[str, Any]], target_format: str) -> Any:
        """9:16 ve 1:1 format dönüşümü için yüz merkezli dinamik veya ortalanmış crop uygular."""
        if target_format == "9:16":
            # 9:16 Dikey kadraj: Genişlik = yükseklik * 9 / 16
            target_w = "ih*9/16"

            # Yüz takibi verisi varsa ortalama X merkezini hesapla
            if face_data and len(face_data) > 0:
                valid_x = [f.get("x", 0.5) for f in face_data if isinstance(f.get("x"), (int, float))]
                avg_face_x = sum(valid_x) / len(valid_x) if valid_x else 0.5
                # X koordinatı: yüz merkezine göre kırp, sınırları aşma
                crop_x = f"max(0, min(iw - ow, iw*{avg_face_x:.3f} - ow/2))"
            else:
                crop_x = "(iw-ow)/2"

            return video_stream.filter('crop', w=target_w, h='ih', x=crop_x, y=0)

        elif target_format == "1:1":
            # 1:1 Kare kadraj: Genişlik ve Yükseklik = min(iw, ih)
            return video_stream.filter('crop', w='ih', h='ih', x='(iw-ow)/2', y=0)

        return video_stream

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
