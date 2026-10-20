"""
video_renderer.py — EDL JSON'u okuyup kare ve ses örneği hassasiyetinde (frame-accurate)
FFmpeg trim + concat + xfade filtreleri, PillowGraphicsEngine tipografisi,
global renk düzenleme (Color Grading), Smart Punch-In ve çok kanallı SFX/Loudnorm
ile ses-görüntü senkronunu koruyarak render eder.
"""
import os
import subprocess
import concurrent.futures
from typing import Dict, Any, List, Tuple, Optional
from render.image_overlay import ImageOverlay
from render.template_applier import TemplateApplier
from render.text_overlay import TextOverlay
from render.timeline_mapper import TimelineMapper
from render.pillow_graphics_engine import PillowGraphicsEngine
from render.audio_mixer import AudioMixer
from services.minio_client import MinioClient
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import importlib
    ffmpeg = importlib.import_module("ffmpeg")
except Exception:
    ffmpeg = None

XFADE_TRANSITION_MAP: Dict[str, str] = {
    "fade": "fade",
    "crossfade": "dissolve",
    "dissolve": "dissolve",
    "fadeblack": "fadeblack",
    "fade-black": "fadeblack",
    "dip-to-black": "fadeblack",
    "fadewhite": "fadewhite",
    "fade-white": "fadewhite",
    "dip-to-white": "fadewhite",
    "wipeleft": "wipeleft",
    "wipe-left": "wipeleft",
    "wiperight": "wiperight",
    "wipe-right": "wiperight",
    "wipeup": "wipeup",
    "wipe-up": "wipeup",
    "wipedown": "wipedown",
    "wipe-down": "wipedown",
    "slideleft": "slideleft",
    "slide-left": "slideleft",
    "slideright": "slideright",
    "slide-right": "slideright",
    "slideup": "slideup",
    "slide-up": "slideup",
    "slidedown": "slidedown",
    "slide-down": "slidedown",
    "circleopen": "circleopen",
    "circle-open": "circleopen",
    "iris": "circleopen",
    "circleclose": "circleclose",
    "zoomin": "zoomin",
    "zoom-in": "zoomin",
    "smoothleft": "smoothleft",
    "smooth-left": "smoothleft",
    "smoothright": "smoothright",
    "smooth-right": "smoothright",
}


class VideoRenderer:
    """EDL JSON'a göre frame-accurate ve sıfır desync ile video render eden motor."""

    def __init__(self, minio_client: Optional[MinioClient] = None):
        self.minio = minio_client or MinioClient()
        self.image_overlay = ImageOverlay(self.minio)

    @classmethod
    def should_render_text_via_pillow(cls, ov: Dict[str, Any]) -> bool:
        """
        Bir metin katmanının standart ASS yerine PillowGraphicsEngine ile
        yüksek çözünürlüklü PNG olarak render edilip edilmeyeceğini belirler.
        """
        if not ov or not str(ov.get("content", "")).strip():
            return False

        box_style = str(ov.get("boxStyle") or ov.get("box_style") or "none").lower().strip()
        if box_style in ("pill", "rounded", "badge", "highlight-marker"):
            return True

        fill_type = str(ov.get("fillType") or ov.get("fill_type") or "solid").lower().strip()
        if fill_type in ("gradient", "radial") or bool(ov.get("gradientEnabled")):
            return True

        if abs(float(ov.get("curveBend") or ov.get("curve_bend") or 0.0)) > 1.0:
            return True

        if float(ov.get("outerStrokeWidth") or ov.get("outer_stroke_width") or 0.0) > 0:
            return True

        if bool(ov.get("glowEnabled") or ov.get("glow_enabled")) or float(ov.get("glowRadius") or ov.get("glow_radius") or 0.0) > 0:
            return True

        if any(
            abs(float(ov.get(k) or 0.0)) > 0.5
            for k in ("rotateX", "rotate_x", "rotateY", "rotate_y", "skewX", "skew_x", "skewY", "skew_y")
        ):
            return True

        if float(ov.get("strokeWidth") or ov.get("stroke_width") or 0.0) > 0:
            return True

        if bool(ov.get("allCaps") or ov.get("all_caps")):
            return True

        return False

    @classmethod
    def _get_color_grading_filters(cls, color_grading: Optional[Dict[str, Any]]) -> List[str]:
        """
        Global renk düzenleme (Color Grading) ayarlarını FFmpeg eq ve hue filtre dizisine dönüştürür.
        """
        if not color_grading or not isinstance(color_grading, dict):
            return []

        filters: List[str] = []
        raw_b = float(color_grading.get("brightness") or 0.0)
        raw_c = color_grading.get("contrast")
        raw_s = color_grading.get("saturation")
        raw_temp = float(
            color_grading.get("temperature")
            if color_grading.get("temperature") is not None
            else (color_grading.get("warmth") or 0.0)
        )
        raw_hue = float(color_grading.get("hue") or 0.0)

        # Parlaklık (-100..100 veya -1.0..1.0 -> -1.0..1.0)
        b_val = (raw_b / 100.0) if abs(raw_b) > 1.0 else raw_b
        b_val = max(-1.0, min(1.0, b_val))

        # Kontrast (-100..100 -> 0.0..2.0 veya doğrudan çarpan)
        if raw_c is None or float(raw_c) == 0.0:
            c_val = 1.0
        else:
            fc = float(raw_c)
            if abs(fc) > 3.0 or fc < 0.0:
                c_val = max(0.0, 1.0 + (fc / 100.0))
            else:
                c_val = fc

        # Doygunluk (-100..100 -> 0.0..3.0 veya doğrudan çarpan)
        if raw_s is None or float(raw_s) == 0.0:
            s_val = 1.0
        else:
            fs = float(raw_s)
            if abs(fs) > 3.0 or fs < 0.0:
                s_val = max(0.0, 1.0 + (fs / 100.0))
            else:
                s_val = fs

        if abs(b_val) > 0.001 or abs(c_val - 1.0) > 0.001 or abs(s_val - 1.0) > 0.001:
            filters.append(f"eq=brightness={b_val:.3f}:contrast={c_val:.3f}:saturation={s_val:.3f}")

        if abs(raw_temp) > 0.1 or abs(raw_hue) > 0.1:
            hue_shift = raw_hue if abs(raw_hue) > 0.1 else (raw_temp * 0.35)
            filters.append(f"hue=h={hue_shift:.2f}")

        return filters

    @classmethod
    def apply_transitions_between_segments(
        cls,
        segment_files: List[str],
        actual_durations: List[float],
        keep_segments: List[Tuple[float, float]],
        transitions: List[Dict[str, Any]],
        temp_dir: str
    ) -> Tuple[List[str], List[float], str]:
        """
        Kesilen segment sınırlarında eşleşen sahne geçişlerini (transitions)
        FFmpeg xfade (video) ve acrossfade (audio) filtreleri ile birleştirir.
        """
        os.makedirs(temp_dir, exist_ok=True)
        merge_concat_path = os.path.join(temp_dir, "merge_concat.txt")

        if not segment_files or len(segment_files) < 2 or not transitions:
            with open(merge_concat_path, "w", encoding="utf-8") as f:
                f.write("ffconcat version 1.0\n")
                for seg_file in segment_files:
                    f.write(f"file '{os.path.abspath(seg_file).replace(chr(92), '/')}'\n")
            return segment_files, actual_durations, merge_concat_path

        # Hangi segment sınırı i (seg_i ile seg_{i+1} arası) için hangi transition var?
        boundary_transitions: Dict[int, Dict[str, Any]] = {}
        accum_time = 0.0
        boundary_timeline_times: List[float] = []
        for idx in range(len(segment_files) - 1):
            dur_i = actual_durations[idx] if idx < len(actual_durations) else (
                (keep_segments[idx][1] - keep_segments[idx][0]) if idx < len(keep_segments) else 2.0
            )
            accum_time += dur_i
            boundary_timeline_times.append(accum_time)

        for tr in transitions:
            if not isinstance(tr, dict):
                continue
            explicit_idx = tr.get("segmentIndex")
            if explicit_idx is None:
                explicit_idx = tr.get("afterSegmentIndex")
            if explicit_idx is None:
                explicit_idx = tr.get("boundaryIndex")

            if explicit_idx is not None:
                b_idx = int(explicit_idx)
                if 0 <= b_idx < len(segment_files) - 1:
                    boundary_transitions[b_idx] = tr
                    continue

            if tr.get("timestamp") is not None:
                ts = float(tr["timestamp"])
                best_idx = None
                best_dist = 1.5  # Sınır eşleşme toleransı (saniye)
                for b_idx in range(len(segment_files) - 1):
                    candidates = [boundary_timeline_times[b_idx]]
                    if b_idx < len(keep_segments):
                        candidates.append(keep_segments[b_idx][1])
                    if b_idx + 1 < len(keep_segments):
                        candidates.append(keep_segments[b_idx + 1][0])
                    dist = min(abs(ts - c) for c in candidates)
                    if dist <= best_dist:
                        best_dist = dist
                        best_idx = b_idx
                if best_idx is not None:
                    boundary_transitions[best_idx] = tr

        if not boundary_transitions:
            with open(merge_concat_path, "w", encoding="utf-8") as f:
                f.write("ffconcat version 1.0\n")
                for seg_file in segment_files:
                    f.write(f"file '{os.path.abspath(seg_file).replace(chr(92), '/')}'\n")
            return segment_files, actual_durations, merge_concat_path

        out_files: List[str] = [segment_files[0]]
        out_durations: List[float] = [
            actual_durations[0] if actual_durations else (keep_segments[0][1] - keep_segments[0][0])
        ]

        for b_idx in range(len(segment_files) - 1):
            next_file = segment_files[b_idx + 1]
            next_dur = (
                actual_durations[b_idx + 1]
                if (b_idx + 1) < len(actual_durations)
                else ((keep_segments[b_idx + 1][1] - keep_segments[b_idx + 1][0]) if (b_idx + 1) < len(keep_segments) else 2.0)
            )

            tr = boundary_transitions.get(b_idx)
            if not tr:
                out_files.append(next_file)
                out_durations.append(next_dur)
                continue

            cur_file = out_files[-1]
            cur_dur = out_durations[-1]
            raw_type = str(tr.get("type") or tr.get("transitionType") or "fade").lower().strip()
            xfade_name = XFADE_TRANSITION_MAP.get(raw_type, "fade")
            req_dur = float(tr.get("duration") or 0.5)
            trans_dur = max(0.1, min(req_dur, cur_dur * 0.45, next_dur * 0.45))
            offset = max(0.05, cur_dur - trans_dur)

            merged_seg = os.path.join(temp_dir, f"xfade_seg_{b_idx:04d}.mp4")
            filter_complex = (
                f"[0:v][1:v]xfade=transition={xfade_name}:duration={trans_dur:.3f}:offset={offset:.3f}[v];"
                f"[0:a][1:a]acrossfade=d={trans_dur:.3f}[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", cur_file,
                "-i", next_file,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                merged_seg,
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                if res.returncode == 0 and os.path.isfile(merged_seg) and os.path.getsize(merged_seg) > 500:
                    out_files[-1] = merged_seg
                    out_durations[-1] = round(cur_dur + next_dur - trans_dur, 3)
                    logger.info(f"✨ Sahne geçişi uygulandı ({xfade_name}, {trans_dur:.2f}s) -> {merged_seg}")
                else:
                    logger.warning(f"xfade geçişi başarısız oldu, düz birleştirmeye dönülüyor: {res.stderr[-200:] if res.stderr else ''}")
                    out_files.append(next_file)
                    out_durations.append(next_dur)
            except Exception as ex:
                logger.warning(f"xfade yürütme hatası ({ex}), düz birleştirmeye dönülüyor.")
                out_files.append(next_file)
                out_durations.append(next_dur)

        with open(merge_concat_path, "w", encoding="utf-8") as f:
            f.write("ffconcat version 1.0\n")
            for seg_file in out_files:
                f.write(f"file '{os.path.abspath(seg_file).replace(chr(92), '/')}'\n")

        return out_files, out_durations, merge_concat_path

    def render(self, edl_json: Dict[str, Any], video_path: str, output_path: str, temp_dir: str = "/app/temp") -> str:
        """EDL JSON'a göre video render eder ve çıktı dosya yolunu döner."""
        logger.info(f"Render başlıyor: kaynak={video_path}, hedef={output_path}")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 0. Şablon verisini EDL'e işle
        edl_json = TemplateApplier.enrich_edl_with_template(edl_json)

        # Fontları Logla
        try:
            fc_match = subprocess.run(["fc-match", "Inter V"], capture_output=True, text=True)
            fc_match_cinzel = subprocess.run(["fc-match", "Cinzel"], capture_output=True, text=True)
            logger.info(f"[DEBUG-FONT] fc-match 'Inter V': {fc_match.stdout.strip()}")
            logger.info(f"[DEBUG-FONT] fc-match 'Cinzel': {fc_match_cinzel.stdout.strip()}")
        except Exception as e:
            logger.warning(f"[DEBUG-FONT] Font kontrolü başarısız: {e}")

        settings = edl_json.get("settings") or {}
        if not isinstance(settings, dict):
            settings = getattr(settings, "__dict__", {})

        # Toplam süre tespiti
        total_duration = float(edl_json.get("duration", 0.0))
        if total_duration <= 0:
            total_duration = self._probe_video_duration(video_path)

        cuts = edl_json.get("cuts", [])
        keep_segments = self._get_keep_segments(cuts, total_duration) if cuts and total_duration > 0 else []
        trimmed_duration = sum(end - start for start, end in keep_segments) if keep_segments else total_duration

        overlays = edl_json.get("overlays", [])
        transcript = edl_json.get("transcript")
        transitions = edl_json.get("transitions") or settings.get("transitions") or []
        text_overlays = [ov for ov in overlays if ov.get("type") == "text"]
        image_overlays = [ov for ov in overlays if ov.get("type") == "image"]

        # 1. Segmentleri Kes ve Gerçek Süreleri Ölç
        actual_durations = None
        segment_files: List[str] = []
        merge_concat = None

        has_cuts = (
            keep_segments
            and len(keep_segments) > 0
            and not (len(keep_segments) == 1 and keep_segments[0][0] == 0.0 and abs(keep_segments[0][1] - total_duration) < 0.1)
        )

        smart_punch_in = bool(settings.get("smartPunchIn", False))
        playback_speed = float(settings.get("playbackSpeed") or settings.get("speed") or 1.0)

        if has_cuts:
            logger.info(f"🚀 Frame-Accurate Kesim başlıyor: {len(keep_segments)} korunan segment")
            concat_txt_path = os.path.join(temp_dir, f"cuts_{os.path.basename(output_path)}.txt")
            self._create_concat_file(keep_segments, video_path, concat_txt_path)

            cut_res = self._cut_segments(
                concat_txt_path=concat_txt_path,
                temp_dir=temp_dir,
                smart_punch_in=smart_punch_in,
                playback_speed=playback_speed,
            )
            segment_files, actual_durations, merge_concat = cut_res

            if transitions and len(segment_files) >= 2:
                segment_files, actual_durations, merge_concat = self.apply_transitions_between_segments(
                    segment_files=segment_files,
                    actual_durations=actual_durations,
                    keep_segments=keep_segments,
                    transitions=transitions,
                    temp_dir=temp_dir,
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

        # Zengin stil / kutu / gradyan / 3D / yay içeren metin kaplamalarını PillowGraphicsEngine ile
        # kusursuz antialiased şeffaf PNG katmanlara dönüştürüp image overlay zincirine dahil et
        filtered_text_overlays = []
        for ov in (mapped_text_overlays or []):
            if self.should_render_text_via_pillow(ov):
                badge_png = os.path.join(temp_dir, f"badge_{ov.get('id', 'txt')}.png")
                box_style = ov.get("boxStyle") or ov.get("box_style") or "none"
                try:
                    PillowGraphicsEngine.render_text_badge(
                        text=str(ov.get("content", "")),
                        output_path=badge_png,
                        font_name=ov.get("font") or ov.get("fontFamily") or "Montserrat",
                        font_size=int(ov.get("fontSize", 48)),
                        text_color=ov.get("color", "#FFFFFF"),
                        stroke_color=ov.get("strokeColor") or "#000000",
                        stroke_width=int(float(ov.get("strokeWidth") if ov.get("strokeWidth") is not None else 2)),
                        box_style=str(box_style),
                        box_bg_color=ov.get("boxBgColor") or ov.get("backgroundColor") or "rgba(0,0,0,0.75)",
                        box_padding=int(ov.get("boxPadding", 16)),
                        border_radius=int(ov.get("borderRadius", 24)),
                        all_caps=bool(ov.get("allCaps", False)),
                        letter_spacing=int(float(ov.get("letterSpacing") or 0)),
                        fill_type=str(ov.get("fillType") or ov.get("fill_type") or "solid"),
                        gradient_start=ov.get("gradientStart") or ov.get("gradient_start"),
                        gradient_end=ov.get("gradientEnd") or ov.get("gradient_end"),
                        gradient_angle=float(ov.get("gradientAngle") if ov.get("gradientAngle") is not None else 45.0),
                        outer_stroke_width=int(float(ov.get("outerStrokeWidth") or ov.get("outer_stroke_width") or 0)),
                        outer_stroke_color=ov.get("outerStrokeColor") or ov.get("outer_stroke_color") or "#000000",
                        glow_enabled=bool(ov.get("glowEnabled") or ov.get("glow_enabled")),
                        glow_color=ov.get("glowColor") or ov.get("glow_color"),
                        glow_radius=int(float(ov.get("glowRadius") or ov.get("glow_radius") or 0)),
                        shadow=bool(ov.get("shadow", True)),
                        shadow_color=ov.get("shadowColor") or ov.get("shadow_color"),
                        shadow_blur=int(float(ov.get("shadowBlur") if ov.get("shadowBlur") is not None else 4)),
                        shadow_distance=float(ov.get("shadowDistance") if ov.get("shadowDistance") is not None else 4.0),
                        shadow_angle=float(ov.get("shadowAngle") if ov.get("shadowAngle") is not None else 90.0),
                        curve_bend=float(ov.get("curveBend") or ov.get("curve_bend") or 0.0),
                        rotate_x=float(ov.get("rotateX") or ov.get("rotate_x") or 0.0),
                        rotate_y=float(ov.get("rotateY") or ov.get("rotate_y") or 0.0),
                        skew_x=float(ov.get("skewX") or ov.get("skew_x") or 0.0),
                        skew_y=float(ov.get("skewY") or ov.get("skew_y") or 0.0),
                    )
                    badge_img_ov = dict(ov)
                    badge_img_ov["type"] = "image"
                    badge_img_ov["source"] = badge_png
                    badge_img_ov["scale"] = float(ov.get("scale", 1.0))
                    mapped_image_overlays.append(badge_img_ov)
                    logger.info(f"🎨 Metin rozeti PNG olarak görsel katmanına dönüştürüldü: {badge_png}")
                except Exception as ex:
                    logger.warning(f"Metin rozeti render edilemedi, standart ASS olarak devam ediliyor: {ex}")
                    filtered_text_overlays.append(ov)
            else:
                filtered_text_overlays.append(ov)
        mapped_text_overlays = filtered_text_overlays

        target_format = settings.get("targetFormat", "16:9")
        face_data = edl_json.get("repurposing", {}).get("faceTrackingData", [])
        subtitles_enabled = settings.get("subtitlesEnabled", True)
        color_grading = settings.get("colorGrading") or edl_json.get("colorGrading")

        final_transcript = mapped_transcript if subtitles_enabled else None
        if not subtitles_enabled:
            logger.info("🚫 Altyazılar kullanıcı ayarı nedeniyle devre dışı bırakıldı (subtitlesEnabled=False).")

        ass_path = None
        if mapped_text_overlays or final_transcript:
            candidate_ass = os.path.join(temp_dir, f"subtitles_{os.path.basename(output_path)}.ass")

            res_x, res_y = 1920, 1080
            if target_format in ("9:16", "portrait"):
                res_x, res_y = 1080, 1920
            elif target_format in ("1:1", "square"):
                res_x, res_y = 1080, 1080

            TextOverlay.generate_ass(
                overlays=mapped_text_overlays,
                transcript=final_transcript,
                output_path=candidate_ass,
                play_res_x=res_x,
                play_res_y=res_y,
                subtitle_style=settings.get("subtitleStyle")
            )
            if os.path.isfile(candidate_ass):
                ass_path = candidate_ass
                logger.info(f"✅ Altyazı ASS dosyası üretildi: {ass_path} ({res_x}x{res_y})")

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
                trimmed_duration=trimmed_duration,
                color_grading=color_grading,
            )
        else:
            logger.info("Kesim listesi yok veya tüm video korunuyor. Doğrudan kaynak video işleniyor.")
            self._execute_ffmpeg_direct(
                video_path=video_path,
                target_format=target_format,
                face_data=face_data,
                ass_path=ass_path,
                output_path=output_path,
                color_grading=color_grading,
            )

        logger.info(f"Base render tamamlandı: {output_path}")

        # 3. İkinci Geçiş (Görsel Overlay'leri, BGM, SFX veya Loudnorm Varsa)
        bgm_cfg = settings.get("backgroundMusic") or {}
        if not isinstance(bgm_cfg, dict):
            bgm_cfg = getattr(bgm_cfg, "__dict__", {})
        has_bgm = bool(bgm_cfg and bgm_cfg.get("url"))

        sfx_clips = edl_json.get("sfxClips") or settings.get("sfxClips") or []
        normalize_audio = bool(settings.get("normalizeAudio", False))

        if mapped_image_overlays or has_bgm or sfx_clips or normalize_audio:
            logger.info(
                f"🎨 İkinci pass yürütülüyor (Görseller: {len(mapped_image_overlays)}, BGM: {has_bgm}, "
                f"SFX: {len(sfx_clips)}, Loudnorm: {normalize_audio})..."
            )
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

                    if mapped_image_overlays:
                        v_stream = self.image_overlay.apply_image_overlays(
                            v_stream,
                            mapped_image_overlays,
                            temp_dir=temp_dir,
                            base_w=base_w,
                            base_h=base_h
                        )

                    audio_reencode = False
                    if has_bgm:
                        bgm_url = bgm_cfg.get("url", "")
                        bgm_local = self.image_overlay.resolve_image_path(bgm_url, temp_dir=temp_dir)
                        if bgm_local and os.path.isfile(bgm_local):
                            a_stream = AudioMixer.apply_bgm_with_ducking(
                                speech_audio_stream=a_stream,
                                bgm_file_path=bgm_local,
                                total_duration=trimmed_duration,
                                volume=float(bgm_cfg.get("volume", 0.25)),
                                auto_ducking=bool(bgm_cfg.get("autoDucking", True)),
                                ducking_amount=float(bgm_cfg.get("duckingAmount", 0.15)),
                                fade_in_sec=float(bgm_cfg.get("fadeIn", 1.0)),
                                fade_out_sec=float(bgm_cfg.get("fadeOut", 2.0))
                            )
                            audio_reencode = True

                    if sfx_clips:
                        a_stream = AudioMixer.mix_sfx_clips(
                            speech_audio_stream=a_stream,
                            sfx_clips=sfx_clips,
                            temp_dir=temp_dir,
                            resolver_fn=self.image_overlay.resolve_image_path,
                        )
                        audio_reencode = True

                    if normalize_audio:
                        a_stream = AudioMixer.apply_loudnorm(a_stream)
                        audio_reencode = True

                    acodec_val = "aac" if audio_reencode else "copy"
                    audio_kwargs = {"audio_bitrate": "192k"} if audio_reencode else {}

                    out_cmd_nvenc = ffmpeg.output(
                        v_stream, a_stream, output_path,
                        vcodec="h264_nvenc", preset="p4", video_bitrate="6M", maxrate="8M", bufsize="12M",
                        acodec=acodec_val, shortest=None, **audio_kwargs
                    ).overwrite_output().compile()

                    out_cmd_cpu = ffmpeg.output(
                        v_stream, a_stream, output_path,
                        vcodec="libx264", preset="veryfast", crf="22",
                        acodec=acodec_val, shortest=None, **audio_kwargs
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

    def _cut_segments(
        self,
        concat_txt_path: str,
        temp_dir: str,
        smart_punch_in: bool = False,
        playback_speed: float = 1.0,
        segment_speeds: Optional[Dict[int, float]] = None
    ) -> Tuple[List[str], List[float], str]:
        """
        Segmentleri keser ve sürelerini ölçer.
        Opsiyonel Smart Punch-In (%10 dinamik yakınlaştırma) ve hız çarpanı uygular.
        Geri dönüş: (segment_files, actual_durations, merge_concat_path)
        """
        segments = self._parse_concat_file(concat_txt_path)
        if not segments:
            raise RuntimeError("Concat dosyası boş veya okunamadı!")

        max_workers = 2
        logger.info(f"🎬 Frame-accurate paralel kesim başlıyor: {len(segments)} segment, {max_workers} thread (NVENC limiti koruması)")

        def _cut_single_segment(item: Tuple[int, Tuple[str, float, float]]) -> Optional[Tuple[int, str]]:
            idx, (video_path, start, end) = item
            seg_out = os.path.join(temp_dir, f"seg_{idx:04d}.mp4")
            duration = end - start

            base_args = ["ffmpeg", "-y", "-ss", str(start), "-i", video_path, "-t", str(duration)]

            seg_speed = float((segment_speeds or {}).get(idx, playback_speed) or 1.0)
            seg_speed = max(0.5, min(2.0, seg_speed))

            vf_parts: List[str] = []
            if smart_punch_in and idx % 2 == 1:
                # Tek indeksli segmentlerde %10 merkez punch-in zoom
                vf_parts.append("crop=iw/1.1:ih/1.1:(iw-ow)/2:(ih-oh)/2,scale=trunc(iw*1.1/2)*2:trunc(ih*1.1/2)*2")
            if abs(seg_speed - 1.0) > 0.01:
                vf_parts.append(f"setpts={1.0 / seg_speed:.4f}*PTS")

            vf_arg = ["-vf", ",".join(vf_parts)] if vf_parts else []

            # Zero-drift 8ms mikro-fade
            eff_dur = duration / seg_speed
            fade_dur = 0.008
            fade_out_st = max(0.0, eff_dur - fade_dur)
            af_parts = []
            if abs(seg_speed - 1.0) > 0.01:
                af_parts.append(f"atempo={seg_speed:.4f}")
            af_parts.append(f"afade=t=in:ss=0:d={fade_dur:.3f},afade=t=out:st={fade_out_st:.3f}:d={fade_dur:.3f}")
            afade_arg = ["-af", ",".join(af_parts)]

            nvenc_cmd = (
                base_args
                + vf_arg
                + ["-c:v", "h264_nvenc", "-preset", "p1", "-b:v", "8M", "-pix_fmt", "yuv420p"]
                + afade_arg
                + ["-c:a", "aac", "-b:a", "192k", "-fps_mode", "cfr", "-avoid_negative_ts", "make_zero", seg_out]
            )
            res = subprocess.run(nvenc_cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.isfile(seg_out) and os.path.getsize(seg_out) > 1000:
                return (idx, seg_out)

            cpu_cmd = (
                base_args
                + vf_arg
                + ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p"]
                + afade_arg
                + ["-c:a", "aac", "-b:a", "192k", "-fps_mode", "cfr", "-avoid_negative_ts", "make_zero", seg_out]
            )
            res_cpu = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=300)
            if res_cpu.returncode == 0 and os.path.isfile(seg_out) and os.path.getsize(seg_out) > 1000:
                return (idx, seg_out)

            if os.path.isfile(seg_out):
                try:
                    os.remove(seg_out)
                except Exception:
                    pass

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

    def _concat_segments(
        self,
        merge_concat: str,
        segment_files: List[str],
        target_format: str,
        face_data: Optional[List[Dict[str, Any]]],
        ass_path: Optional[str],
        output_path: str,
        trimmed_duration: float,
        color_grading: Optional[Dict[str, Any]] = None
    ):
        """Hazırlanan segmentleri FFmpeg concat demuxer ve filtreler ile birleştirir."""
        vf = []
        if target_format == "9:16":
            crop_cmd = self._get_crop_str(face_data, "9:16").lstrip(",")
            if crop_cmd:
                vf.append(crop_cmd)
        elif target_format == "1:1":
            crop_cmd = self._get_crop_str(face_data, "1:1").lstrip(",")
            if crop_cmd:
                vf.append(crop_cmd)

        vf.extend(self._get_color_grading_filters(color_grading))

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

    def _execute_ffmpeg_direct(
        self,
        video_path: str,
        target_format: str,
        face_data: List[Dict[str, Any]],
        ass_path: Optional[str],
        output_path: str,
        color_grading: Optional[Dict[str, Any]] = None
    ):
        """Kesim olmadan yalnızca format, renk düzenleme veya altyazı varsa çalışan doğrudan komut."""
        vf = []
        if target_format == "9:16":
            vf.append(self._get_crop_str(face_data, "9:16").lstrip(","))
        elif target_format == "1:1":
            vf.append(self._get_crop_str(face_data, "1:1").lstrip(","))

        vf.extend(self._get_color_grading_filters(color_grading))

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
                s = float(c.get("start", 0.0) if isinstance(c, dict) else getattr(c, "start", 0.0))
                e = float(c.get("end", 0.0) if isinstance(c, dict) else getattr(c, "end", 0.0))
                if e > s:
                    valid_cuts.append((s, e))
            except (ValueError, TypeError):
                continue

        cut_ranges = sorted(valid_cuts, key=lambda x: x[0])
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
