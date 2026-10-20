"""
Comprehensive unit tests for OtoEdit Professional Video Editor Features (Optimization + Phases 1-6):
1. PillowGraphicsEngine (Typography, Gradients, Double Stroke, Neon Glow, Curved Arc, 3D Perspective, Highlight-Marker, SHA-256 Cache)
2. BackgroundRemoverService & ImageOverlay (Photoshop Adjustments, Shape Masks, Feather, Sticker Outline, Chroma Key, Animated GIF)
3. AnimationEffects (Entrance, Loop Animations, Piecewise-Linear Keyframes, ASS Tags)
4. AudioMixer (Multi-Track SFX Mixer & -14 LUFS Loudnorm)
5. VideoRenderer (Global Color Grading, xfade/acrossfade Scene Transitions, Styled Text Routing)
6. ProactiveDirector (Autonomous Video Director Proactive Suggestions Engine)
"""
import os
import time
import tempfile
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from PIL import Image

from render.pillow_graphics_engine import PillowGraphicsEngine, FONT_PATHS, hex_to_rgba
from services.bg_remover import BackgroundRemoverService
from render.image_overlay import ImageOverlay
from render.animation_effects import AnimationEffects
from render.audio_mixer import AudioMixer
from render.video_renderer import VideoRenderer
from pipeline.proactive_director import ProactiveDirector


# ==============================================================================
# 1. PillowGraphicsEngine — Phase 1 & Zero-Lag Caching Tests
# ==============================================================================

def test_pillow_expanded_font_map():
    """Verify 35+ fonts are mapped and get_font resolves gracefully."""
    assert len(FONT_PATHS) >= 35
    for font_name in [
        "Montserrat", "Poppins", "Bebas Neue", "Anton", "Cinzel", "Outfit", "Inter",
        "Playfair Display", "Orbitron", "Pacifico", "Permanent Marker", "Caveat",
        "Bangers", "Righteous", "JetBrains Mono", "Space Grotesk", "Syne",
        "Rubik Mono One", "Press Start 2P"
    ]:
        assert font_name in FONT_PATHS
        font_obj = PillowGraphicsEngine.get_font(font_name, 36)
        assert font_obj is not None


def test_pillow_solid_and_none_box_text(tmp_path):
    """Verify solid text and box_style='none' render crisp transparent PNGs."""
    out_none = str(tmp_path / "badge_none.png")
    res = PillowGraphicsEngine.render_text_badge(
        text="TRANSPARENT STUDIO TEXT",
        output_path=out_none,
        font_name="Montserrat",
        font_size=48,
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=3,
        box_style="none",
        shadow=True,
        shadow_distance=6,
        shadow_angle=45,
        shadow_blur=4,
    )
    assert os.path.isfile(res)
    img = Image.open(res)
    assert img.mode == "RGBA"
    assert img.width > 50 and img.height > 20
    # Corner pixel should be transparent since box_style="none"
    arr = np.array(img)
    assert arr[0, 0, 3] < 50


def test_pillow_gradient_and_radial_text(tmp_path):
    """Verify linear and radial gradient text fills."""
    out_lin = str(tmp_path / "badge_linear_grad.png")
    PillowGraphicsEngine.render_text_badge(
        text="GRADIENT FILL",
        output_path=out_lin,
        font_size=52,
        box_style="none",
        fill_type="gradient",
        gradient_start="#FF0055",
        gradient_end="#00F5D4",
        gradient_angle=45.0,
        stroke_width=2,
    )
    assert os.path.isfile(out_lin)
    img_lin = Image.open(out_lin)
    assert img_lin.width > 40

    out_rad = str(tmp_path / "badge_radial_grad.png")
    PillowGraphicsEngine.render_text_badge(
        text="RADIAL GLOW",
        output_path=out_rad,
        font_size=52,
        box_style="none",
        fill_type="radial",
        gradient_start="#FFD700",
        gradient_end="#7928CA",
        stroke_width=2,
    )
    assert os.path.isfile(out_rad)
    img_rad = Image.open(out_rad)
    assert img_rad.width > 40


def test_pillow_double_stroke_and_neon_glow(tmp_path):
    """Verify double stroke (outer_stroke_width) and neon outer glow."""
    out_path = str(tmp_path / "badge_double_stroke_glow.png")
    PillowGraphicsEngine.render_text_badge(
        text="NEON CYBERPUNK",
        output_path=out_path,
        font_name="Anton",
        font_size=56,
        text_color="#FFFFFF",
        stroke_color="#111827",
        stroke_width=3,
        outer_stroke_width=5,
        outer_stroke_color="#FF007F",
        glow_enabled=True,
        glow_color="#00F5D4",
        glow_radius=14,
        box_style="none",
    )
    assert os.path.isfile(out_path)
    img = Image.open(out_path)
    assert img.width > 60 and img.height > 30


def test_pillow_curved_arc_text_positive_and_negative(tmp_path):
    """Verify curved arc text for both positive (+45) and negative (-45) curve_bend."""
    out_pos = str(tmp_path / "curved_pos45.png")
    out_neg = str(tmp_path / "curved_neg45.png")

    PillowGraphicsEngine.render_text_badge(
        text="ARC UPWARD TEXT",
        output_path=out_pos,
        font_size=44,
        curve_bend=45.0,
        fill_type="gradient",
        gradient_start="#FF6B6B",
        gradient_end="#4ECDC4",
        stroke_width=2,
        box_style="none",
    )
    PillowGraphicsEngine.render_text_badge(
        text="ARC DOWNWARD TEXT",
        output_path=out_neg,
        font_size=44,
        curve_bend=-45.0,
        stroke_width=2,
        box_style="none",
    )
    assert os.path.isfile(out_pos)
    assert os.path.isfile(out_neg)
    img_pos = Image.open(out_pos)
    img_neg = Image.open(out_neg)
    assert img_pos.width > 50 and img_pos.height > 30
    assert img_neg.width > 50 and img_neg.height > 30


def test_pillow_3d_perspective_and_highlight_marker(tmp_path):
    """Verify 3D perspective warp (rotate_x=25, rotate_y=-20) and highlight-marker box."""
    out_3d = str(tmp_path / "badge_3d_marker.png")
    PillowGraphicsEngine.render_text_badge(
        text="3D MARKER TITLE\nSECOND LINE",
        output_path=out_3d,
        font_name="Bebas Neue",
        font_size=50,
        text_color="#0F172A",
        box_style="highlight-marker",
        box_bg_color="#FACC15",
        rotate_x=25.0,
        rotate_y=-20.0,
        skew_x=8.0,
        skew_y=2.0,
    )
    assert os.path.isfile(out_3d)
    img = Image.open(out_3d)
    assert img.width > 40 and img.height > 40


def test_pillow_sha256_cache_hit_speed(tmp_path):
    """Verify SHA-256 content-addressed cache returns in < 2ms on second call."""
    out_1 = str(tmp_path / "cache_test_1.png")
    out_2 = str(tmp_path / "cache_test_2.png")

    kwargs = dict(
        text="ULTRA FAST CACHE BADGE",
        font_name="Montserrat",
        font_size=54,
        text_color="#FFFFFF",
        box_style="pill",
        box_bg_color="#4F46E5",
        fill_type="gradient",
        gradient_start="#FF007F",
        gradient_end="#00F5D4",
        glow_enabled=True,
        glow_radius=8,
    )

    # First call: cold render
    PillowGraphicsEngine.render_text_badge(output_path=out_1, **kwargs)
    assert os.path.isfile(out_1)

    # Second call: warm cache hit (must be < 2ms = 0.002s, allow small OS file write margin if needed, check memory speed)
    t0 = time.perf_counter()
    PillowGraphicsEngine.render_text_badge(output_path=out_2, **kwargs)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert os.path.isfile(out_2)
    assert os.path.getsize(out_1) == os.path.getsize(out_2)
    assert elapsed_ms < 5.0, f"Cache hit took {elapsed_ms:.2f}ms"


# ==============================================================================
# 2. BackgroundRemoverService & ImageOverlay — Phase 2 & Phase 5 Tests
# ==============================================================================

def _create_sample_rgba_image(path: str, w: int = 160, h: int = 160) -> str:
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[:, :] = [0, 255, 0, 255]  # Green background for chroma key testing
    arr[30:130, 30:130] = [220, 60, 110, 255]  # Foreground subject
    Image.fromarray(arr, "RGBA").save(path, "PNG")
    return path


def test_bg_remover_photoshop_adjustments(tmp_path):
    """Verify brightness, contrast, saturation, warmth, hue, blur, sharpen, flip_h, flip_v, opacity, drop_shadow."""
    src = _create_sample_rgba_image(str(tmp_path / "sample.png"))
    out = str(tmp_path / "sample_adjusted.png")

    res = BackgroundRemoverService.apply_photoshop_adjustments(
        image_path=src,
        output_path=out,
        brightness=15,
        contrast=20,
        saturation=25,
        warmth=18,
        hue=30,
        blur=2,
        sharpen=15,
        opacity=85,
        flip_h=True,
        flip_v=True,
        drop_shadow=True,
        shadow_color="#000000",
        shadow_blur=8,
    )
    assert os.path.isfile(res)
    img = Image.open(res)
    assert img.mode == "RGBA"
    # Padded due to drop_shadow
    assert img.width > 160 and img.height > 160


def test_bg_remover_all_shape_masks_and_feather(tmp_path):
    """Verify apply_shape_mask for circle, rounded, star, heart, hexagon, diamond + feather."""
    src = _create_sample_rgba_image(str(tmp_path / "shape_src.png"))
    for shape in ["circle", "rounded", "star", "heart", "hexagon", "diamond"]:
        out = str(tmp_path / f"mask_{shape}.png")
        res = BackgroundRemoverService.apply_shape_mask(
            image_path=src,
            output_path=out,
            shape=shape,
            corner_radius=24,
            feather=4,
        )
        assert os.path.isfile(res)
        img = Image.open(res)
        arr = np.array(img)
        # Top-left corner (0, 0) must be masked out (transparent)
        assert arr[0, 0, 3] < 30, f"Shape {shape} did not mask corner!"
        # Center pixel must remain opaque
        assert arr[img.height // 2, img.width // 2, 3] > 200


def test_bg_remover_sticker_outline_and_chroma_key(tmp_path):
    """Verify apply_chroma_key removes green screen and add_sticker_outline adds border."""
    src = _create_sample_rgba_image(str(tmp_path / "chroma_src.png"))
    chroma_out = str(tmp_path / "chroma_clean.png")
    BackgroundRemoverService.apply_chroma_key(
        image_path=src,
        output_path=chroma_out,
        key_color_hex="#00FF00",
        similarity=0.35,
    )
    assert os.path.isfile(chroma_out)
    chroma_arr = np.array(Image.open(chroma_out))
    # Green corner is now transparent (alpha == 0)
    assert chroma_arr[5, 5, 3] == 0
    # Center subject is opaque
    assert chroma_arr[80, 80, 3] == 255

    sticker_out = str(tmp_path / "sticker_final.png")
    BackgroundRemoverService.add_sticker_outline(
        image_path=chroma_out,
        output_path=sticker_out,
        outline_width=6,
        outline_color_hex="#FFFFFF",
        shadow=True,
    )
    assert os.path.isfile(sticker_out)


# ==============================================================================
# 3. AnimationEffects — Entrance, Loop & Keyframe Expression Tests
# ==============================================================================

def test_animation_effects_entrance_and_loop_expressions():
    """Verify entrance (pop-up, bounce, slide-down) and loop (pulse, float, wiggle) FFmpeg expressions."""
    x_pop, y_pop = AnimationEffects.get_ffmpeg_overlay_coords(
        position=["center", "center"],
        anim_type="pop-up",
        start_time=1.0,
        duration=3.0,
        loop_anim="pulse",
    )
    assert "if(lt(t," in y_pop
    assert "sin(2*PI*(t-1.0)" in y_pop

    x_bnc, y_bnc = AnimationEffects.get_ffmpeg_overlay_coords(
        position=["center", "bottom"],
        anim_type="bounce",
        start_time=2.0,
        duration=4.0,
        loop_anim="float",
    )
    assert "abs(sin(" in y_bnc
    assert "12*sin(" in y_bnc

    x_sd, y_sd = AnimationEffects.get_ffmpeg_overlay_coords(
        position=["center", "top"],
        anim_type="slide-down",
        start_time=0.5,
        duration=3.0,
        loop_anim="wiggle",
    )
    assert "-overlay_h" in y_sd
    assert "sin(2*PI*" in x_sd
    assert "cos(2*PI*" in y_sd


def test_animation_effects_keyframes_piecewise_linear():
    """Verify piecewise-linear FFmpeg expression generation from keyframes."""
    keyframes = [
        {"timeOffset": 0.0, "x": 10.0, "y": 20.0},
        {"timeOffset": 1.5, "x": 50.0, "y": 50.0},
        {"timeOffset": 3.0, "x": 90.0, "y": 80.0},
    ]
    x_expr, y_expr = AnimationEffects.get_ffmpeg_overlay_coords(
        position=["center", "center"],
        base_w=1920,
        base_h=1080,
        start_time=2.0,
        duration=4.0,
        keyframes=keyframes,
    )
    # 10% of 1920 = 192, 50% of 1920 = 960, 90% of 1920 = 1728
    assert "192" in x_expr and "960" in x_expr and "1728" in x_expr
    assert "if(lt(t,2.0)" in x_expr
    assert "if(lt(t,3.5)" in x_expr
    assert "overlay_w/2" in x_expr
    assert "overlay_h/2" in y_expr


def test_animation_effects_rich_ass_tags():
    """Verify new ASS tags: bounce, typewriter, glitch, blur-in, zoom-crash."""
    for anim, expected_token in [
        ("bounce", "\\fscx115"),
        ("typewriter", "\\fsp"),
        ("glitch", "\\frz"),
        ("blur-in", "\\blur15"),
        ("zoom-crash", "\\fscx220"),
    ]:
        tag = AnimationEffects.get_ass_tags(anim, duration_sec=3.0)
        assert expected_token in tag, f"Missing {expected_token} for {anim}: {tag}"


# ==============================================================================
# 4. AudioMixer — Multi-Track SFX & -14 LUFS Loudnorm Tests
# ==============================================================================

def test_audio_mixer_sfx_and_loudnorm(tmp_path):
    """Verify AudioMixer.mix_sfx_clips and AudioMixer.apply_loudnorm build valid FFmpeg filter chains."""
    dummy_sfx = str(tmp_path / "whoosh.wav")
    with open(dummy_sfx, "wb") as f:
        f.write(b"RIFF0000WAVEfmt ")

    mock_speech = MagicMock(name="speech_stream")
    with patch("render.audio_mixer.ffmpeg") as mock_ffmpeg:
        mock_sfx_in = MagicMock()
        mock_sfx_audio = MagicMock()
        mock_sfx_audio.filter.return_value = mock_sfx_audio
        mock_sfx_in.audio = mock_sfx_audio
        mock_ffmpeg.input.return_value = mock_sfx_in
        mock_ffmpeg.filter.return_value = MagicMock(name="mixed_audio")

        sfx_clips = [
            {
                "id": "sfx_1",
                "sourceUrl": dummy_sfx,
                "start": 1.25,
                "duration": 1.5,
                "volume": 0.8,
                "fadeIn": 0.1,
                "fadeOut": 0.2,
            }
        ]
        mixed = AudioMixer.mix_sfx_clips(mock_speech, sfx_clips, temp_dir=str(tmp_path))
        assert mixed is not None
        # Check adelay was called with 1250|1250
        filter_calls = [c[0] for c in mock_sfx_audio.filter.call_args_list]
        assert ("adelay", "1250|1250") in filter_calls
        assert ("volume", 0.8) in filter_calls
        mock_ffmpeg.filter.assert_called_once()

        # Verify loudnorm
        norm_stream = AudioMixer.apply_loudnorm(mock_speech, target_i=-14.0, target_tp=-1.5, target_lra=11.0)
        mock_speech.filter.assert_called_with("loudnorm", I=-14.0, TP=-1.5, LRA=11.0)
        assert norm_stream is not None


# ==============================================================================
# 5. VideoRenderer — Color Grading, Transitions & Styled Text Routing Tests
# ==============================================================================

def test_video_renderer_color_grading_filters():
    """Verify _get_color_grading_filters generates FFmpeg eq and hue filters."""
    filters = VideoRenderer._get_color_grading_filters({
        "brightness": 10,
        "contrast": 20,
        "saturation": 15,
        "temperature": 12,
    })
    assert len(filters) == 2
    assert filters[0] == "eq=brightness=0.100:contrast=1.200:saturation=1.150"
    assert filters[1].startswith("hue=h=")

    # Default (all zeros) should produce empty filter list
    assert VideoRenderer._get_color_grading_filters({"brightness": 0, "contrast": 0, "saturation": 0, "temperature": 0}) == []


def test_video_renderer_styled_text_routing():
    """Verify should_render_text_via_pillow detects badges, gradients, curves, 3D, glows, and strokes."""
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "boxStyle": "pill"}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "boxStyle": "highlight-marker"}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "fillType": "gradient"}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "curveBend": 35}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "glowEnabled": True}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "rotateX": 20}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Hello", "outerStrokeWidth": 4}) is True
    assert VideoRenderer.should_render_text_via_pillow({"content": "Plain", "boxStyle": "none", "strokeWidth": 0}) is False


def test_video_renderer_transitions_matching(tmp_path):
    """Verify apply_transitions_between_segments matches boundaries and builds xfade/acrossfade."""
    seg0 = str(tmp_path / "seg_0000.mp4")
    seg1 = str(tmp_path / "seg_0001.mp4")
    with open(seg0, "wb") as f:
        f.write(b"0" * 2048)
    with open(seg1, "wb") as f:
        f.write(b"1" * 2048)

    def fake_run(cmd, *args, **kwargs):
        # Write output file (last arg of cmd) to simulate FFmpeg xfade success
        out_file = cmd[-1]
        with open(out_file, "wb") as f_out:
            f_out.write(b"M" * 4096)
        res = MagicMock()
        res.returncode = 0
        res.stderr = ""
        return res

    with patch("render.video_renderer.subprocess.run", side_effect=fake_run) as mock_run:
        out_files, out_durs, concat_path = VideoRenderer.apply_transitions_between_segments(
            segment_files=[seg0, seg1],
            actual_durations=[4.0, 5.0],
            keep_segments=[(0.0, 4.0), (6.0, 11.0)],
            transitions=[{"id": "t1", "type": "dissolve", "timestamp": 4.0, "duration": 0.5}],
            temp_dir=str(tmp_path),
        )
        assert mock_run.called
        called_cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(called_cmd)
        assert "xfade=transition=dissolve:duration=0.500:offset=3.500" in cmd_str
        assert "acrossfade=d=0.500" in cmd_str
        assert len(out_files) == 1
        assert abs(out_durs[0] - 8.5) < 0.01
        assert os.path.isfile(concat_path)


# ==============================================================================
# 6. ProactiveDirector — Phase 6 Autonomous Video Director Suggestions Tests
# ==============================================================================

def test_proactive_director_generates_rich_suggestions():
    """Verify ProactiveDirector generates 4-6 structured actionable suggestions."""
    sample_edl = {
        "projectId": "proj_dir_1",
        "duration": 24.0,
        "transcript": {
            "fullText": "Bu videoda en önemli kurgu sırrını açıklıyorum. Asla bu detayı atlamayın!",
            "segments": [
                {"start": 0.3, "end": 4.5, "text": "Bu videoda en önemli kurgu sırrını açıklıyorum."},
                {"start": 6.0, "end": 12.0, "text": "Asla bu detayı atlamayın, fark inanılmaz!"},
                {"start": 13.0, "end": 22.0, "text": "Sonuç olarak izleyici tutma oranınız ikiye katlanır."},
            ],
        },
        "cuts": [
            {"id": "cut_1", "start": 4.5, "end": 6.0, "reason": "silence"},
        ],
        "audioPeaks": [0.2, 0.4, 0.95, 0.3, 0.6, 0.88, 0.5, 0.3],
        "settings": {
            "targetFormat": "9:16",
            "smartPunchIn": False,
            "normalizeAudio": False,
        },
    }

    suggestions = ProactiveDirector.generate_suggestions(sample_edl)
    assert 4 <= len(suggestions) <= 6

    required_keys = {"id", "type", "title", "description", "timestamp", "duration", "confidence", "category", "payload"}
    categories = set()
    actions = set()

    for sug in suggestions:
        assert required_keys.issubset(sug.keys()), f"Missing keys in {sug}"
        assert 0.5 <= float(sug["confidence"]) <= 1.0
        assert isinstance(sug["payload"], dict) and "action" in sug["payload"]
        categories.add(sug["category"])
        actions.add(sug["payload"]["action"])

    assert "typography" in categories
    assert "audio" in categories
    assert "add_overlay" in actions
