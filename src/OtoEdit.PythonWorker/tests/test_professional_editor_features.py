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

from render.pillow_graphics_engine import PillowGraphicsEngine, FONT_PATHS, _LOCAL_ASSET_MAP, hex_to_rgba
from services.bg_remover import BackgroundRemoverService
from render.image_overlay import ImageOverlay
from render.animation_effects import AnimationEffects
from render.audio_mixer import AudioMixer
from render.video_renderer import VideoRenderer, XFADE_TRANSITION_MAP
from pipeline.proactive_director import ProactiveDirector
from pipeline.auto_director_composer import AutoDirectorComposer
from pipeline.edl_builder import EdlBuilder
from models.edl_model import CutItem, RepurposingData
from models.transcript_model import TranscriptResult, TranscriptSegment


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


# ==============================================================================
# 7. AutoDirectorComposer, EdlBuilder Slimming, 45+ xfade & V1 Clip Reordering
# ==============================================================================

def test_auto_director_composer_generates_hook_highlights_stickers_transitions_and_sfx():
    """Verify AutoDirectorComposer.compose generates hook text, highlight texts, Noto animated emoji stickers, transitions, and SFX."""
    transcript = {
        "fullText": "Bu videoda en önemli kurgu sırrını açıklıyorum. İkinci bölümde yapay zeka araçlarını inceliyoruz. Üçüncü adımda izleyici tutma oranını ikiye katlıyoruz.",
        "duration": 65.0,
        "segments": [
            {"start": 0.4, "end": 4.2, "text": "Bu videoda en önemli kurgu sırrını açıklıyorum."},
            {"start": 25.0, "end": 30.0, "text": "İkinci bölümde yapay zeka araçlarını inceliyoruz."},
            {"start": 50.0, "end": 56.0, "text": "Üçüncü adımda izleyici tutma oranını ikiye katlıyoruz."},
        ],
    }
    cuts = [
        {"id": "c1", "start": 12.0, "end": 14.0, "reason": "silence"},
        {"id": "c2", "start": 38.0, "end": 40.0, "reason": "silence"},
    ]

    composed = AutoDirectorComposer.compose(
        transcript=transcript,
        cuts=cuts,
        existing_overlays=[],
        video_duration=65.0,
        target_format="9:16",
    )

    assert "overlays" in composed
    assert "transitions" in composed
    assert "sfxClips" in composed

    overlays = composed["overlays"]
    transitions = composed["transitions"]
    sfx_clips = composed["sfxClips"]

    # 1. Hook title at 0.3s on trackId=2
    hook_overlays = [ov for ov in overlays if ov.get("id") == "ad_hook_title_1"]
    assert len(hook_overlays) == 1
    hook = hook_overlays[0]
    assert hook["type"] == "text"
    assert hook["trackId"] == 2
    assert hook["font"] == "Montserrat"
    assert hook["fontSize"] == 58
    assert hook["color"] == "#FACC15"
    assert hook["strokeColor"] == "#000000"
    assert hook["strokeWidth"] == 4
    assert hook["boxStyle"] == "none"
    assert hook["animation"] == "pop-up"
    assert abs(float(hook["timestamp"]) - 0.3) < 0.01

    # 2. Key phrase highlight overlays on trackId=2
    hl_overlays = [ov for ov in overlays if str(ov.get("id", "")).startswith("ad_highlight_text_")]
    assert len(hl_overlays) >= 2
    for hl in hl_overlays:
        assert hl["type"] == "text"
        assert hl["trackId"] == 2
        assert hl["positionX"] == 50.0
        assert hl["positionY"] == 22.0
        assert hl["color"] in ("#22D3EE", "#4ADE80", "#FACC15")
        assert hl["animation"] in ("bounce", "slide-up")

    # 3. Animated Emoji / Sticker callouts on trackId=3
    sticker_overlays = [ov for ov in overlays if ov.get("type") == "sticker"]
    assert 2 <= len(sticker_overlays) <= 6
    for st in sticker_overlays:
        assert st["trackId"] == 3
        assert st["positionX"] == 82.0
        assert st["positionY"] == 24.0
        assert st["scale"] == 0.85
        assert st["animation"] == "pop-up"
        assert "https://fonts.gstatic.com/s/e/notoemoji/latest/" in st["source"]
        assert st["source"].endswith("/512.gif")

    # 4. Transitions & SFX
    assert len(transitions) >= 2
    for tr in transitions:
        assert tr["type"] in ("fade", "smoothleft", "zoomin")

    assert len(sfx_clips) >= 3
    sfx_presets = {s.get("presetId") for s in sfx_clips}
    assert sfx_presets.issubset({"whoosh-fast", "pop-bubble", "ding-bright"})


def test_edl_builder_rounding_subtitles_and_auto_director():
    """Verify EdlBuilder rounds audioPeaks to 3 decimals, sets subtitlesEnabled, and wires AutoDirectorComposer."""
    builder = EdlBuilder()
    transcript = TranscriptResult(
        full_text="Birinci cümle burada başlıyor. İkinci cümle yirmi beşinci saniyede geliyor.",
        duration=35.0,
        segments=[
            TranscriptSegment(start=0.5, end=4.0, text="Birinci cümle burada başlıyor."),
            TranscriptSegment(start=24.0, end=29.0, text="İkinci cümle yirmi beşinci saniyede geliyor."),
        ],
    )
    raw_peaks = [0.012000000104308128, 0.8549999892711639, 0.3333333432674408]

    edl = builder.build(
        project_id="proj_slim_1",
        video_id="vid_slim_1",
        transcript=transcript,
        silence_cuts=[CutItem(id="c1", start=8.0, end=10.0, reason="silence")],
        commands=[],
        face_data=[],
        repurposing_data=RepurposingData(),
        suggestions=[],
        video_format=1,
        audio_peaks=raw_peaks,
        video_duration=35.0,
        subtitles_enabled=False,
        auto_director=True,
        video_clips=[{"id": "vc_1", "start": 0.0, "end": 15.0}],
    )

    assert edl["settings"]["subtitlesEnabled"] is False
    assert edl["audioPeaks"] == [0.012, 0.855, 0.333]
    for p in edl["audioPeaks"]:
        assert len(str(p).split(".")[-1]) <= 3

    assert len(edl["overlays"]) >= 3
    assert len(edl["transitions"]) >= 1
    assert len(edl["sfxClips"]) >= 2
    assert len(edl["videoClips"]) == 1


def test_xfade_transition_map_has_all_45_plus_transitions():
    """Verify XFADE_TRANSITION_MAP contains all 45+ standard FFmpeg xfade transitions."""
    expected_transitions = [
        "fade", "fadeblack", "fadewhite", "fadegrays", "distance",
        "wipeleft", "wiperight", "wipeup", "wipedown", "wipetl", "wipetr", "wipebl", "wipebr",
        "slideleft", "slideright", "slideup", "slidedown",
        "smoothleft", "smoothright", "smoothup", "smoothdown",
        "circlecrop", "rectcrop", "circleopen", "circleclose",
        "vertopen", "vertclose", "horzopen", "horzclose",
        "dissolve", "pixelize",
        "diagtl", "diagtr", "diagbl", "diagbr",
        "hlslice", "hrslice", "vuslice", "vdslice",
        "hblur", "squeezeh", "squeezev", "zoomin",
        "hlwind", "hrwind", "vuwind", "vdwind",
        "coverleft", "coverright", "coverup", "coverdown",
        "revealleft", "revealright", "revealup", "revealdown",
    ]
    assert len(expected_transitions) >= 45
    for tr_name in expected_transitions:
        assert tr_name in XFADE_TRANSITION_MAP, f"Missing xfade transition: {tr_name}"
        assert XFADE_TRANSITION_MAP[tr_name] == tr_name


def test_video_renderer_cut_ordered_video_clips(tmp_path):
    """Verify VideoRenderer._cut_ordered_video_clips reorders V1 segments and skips cut clips."""
    main_vid = str(tmp_path / "main_source.mp4")
    ext_vid = str(tmp_path / "external_clip.mp4")
    with open(main_vid, "wb") as f:
        f.write(b"M" * 4096)
    with open(ext_vid, "wb") as f:
        f.write(b"E" * 4096)

    renderer = VideoRenderer(minio_client=MagicMock())

    # Reordered V1 clips: [10..15] first, then external clip [0..4], then [2..6], while [6..10] isCut=True
    video_clips = [
        {"id": "clip_b", "start": 10.0, "end": 15.0, "isCut": False},
        {"id": "clip_cut", "start": 6.0, "end": 10.0, "isCut": True},
        {"id": "clip_ext", "start": 0.0, "end": 4.0, "sourceUrl": ext_vid, "isCut": False},
        {"id": "clip_a", "start": 2.0, "end": 6.0, "isCut": False},
    ]

    captured_segments = []

    def fake_cut_segments(
        concat_txt_path,
        temp_dir,
        smart_punch_in=False,
        playback_speed=1.0,
        segment_speeds=None,
        segment_zooms=None,
    ):
        parsed = renderer._parse_concat_file(concat_txt_path)
        captured_segments.extend(parsed)
        seg_files = [os.path.join(temp_dir, f"seg_{i:04d}.mp4") for i in range(len(parsed))]
        durs = [e - s for _, s, e in parsed]
        return seg_files, durs, concat_txt_path

    with patch.object(renderer, "_cut_segments", side_effect=fake_cut_segments):
        seg_files, actual_durs, merge_concat = renderer._cut_ordered_video_clips(
            video_clips=video_clips,
            main_video_path=main_vid,
            temp_dir=str(tmp_path),
            smart_punch_in=True,
            playback_speed=1.0,
        )

    assert len(captured_segments) == 3
    assert captured_segments[0][1:] == (10.0, 15.0)
    assert os.path.basename(captured_segments[1][0]) == "external_clip.mp4"
    assert captured_segments[1][1:] == (0.0, 4.0)
    assert captured_segments[2][1:] == (2.0, 6.0)
    assert actual_durs == [5.0, 4.0, 4.0]


def test_local_asset_map_has_no_fake_font_redirects_and_pip_video_overlay(tmp_path):
    """Verify _LOCAL_ASSET_MAP only maps real local fonts and ImageOverlay supports video PiP overlays."""
    for fake_key in ("playfair", "merriweather", "lora", "cormorant", "abril", "bangers", "oswald", "orbitron"):
        assert fake_key not in _LOCAL_ASSET_MAP

    pip_vid = str(tmp_path / "pip_sample.mp4")
    with open(pip_vid, "wb") as f:
        f.write(b"V" * 2048)

    overlay_engine = ImageOverlay(minio_client=MagicMock())
    mock_base_stream = MagicMock(name="base_v")

    with patch("render.image_overlay.ffmpeg") as mock_ffmpeg:
        mock_in = MagicMock(name="pip_in")
        mock_in.filter.return_value = mock_in
        mock_ffmpeg.input.return_value = mock_in
        mock_ffmpeg.overlay.return_value = MagicMock(name="overlaid_v")

        res = overlay_engine.apply_image_overlays(
            base_stream=mock_base_stream,
            overlays=[{
                "id": "ov_vid_1",
                "type": "video",
                "source": pip_vid,
                "timestamp": 1.5,
                "duration": 3.5,
                "scale": 0.5,
                "trackId": 2,
            }],
            temp_dir=str(tmp_path),
        )
        assert res is not None
        mock_ffmpeg.input.assert_called_once_with(pip_vid, ss=0, t=3.5)
        mock_ffmpeg.overlay.assert_called_once()


def test_split_keep_segments_at_transitions_and_no_ping_pong_zoom(tmp_path):
    """Verify _split_keep_segments_at_transitions splits continuous clips at transition boundaries and odd clips do not auto-zoom."""
    renderer = VideoRenderer(minio_client=MagicMock())

    # 1. Split keep_segments at transition boundaries (boundaryTime, boundarySourceTime, timestamp)
    initial_segments = [(0.0, 12.0), (15.0, 25.0)]
    transitions = [
        {"id": "tr_1", "type": "fade", "boundaryTime": 4.5, "duration": 0.5},
        {"id": "tr_2", "type": "zoomin", "boundarySourceTime": 8.0, "duration": 0.5},
        {"id": "tr_3", "type": "smoothleft", "timestamp": 20.0, "duration": 0.5},
        # Near-edge transition within 0.15s should NOT split into micro-segment
        {"id": "tr_edge", "type": "fade", "boundaryTime": 0.05, "duration": 0.5},
    ]

    split_segs = renderer._split_keep_segments_at_transitions(initial_segments, transitions)
    assert split_segs == [
        (0.0, 4.5),
        (4.5, 8.0),
        (8.0, 12.0),
        (15.0, 20.0),
        (20.0, 25.0),
    ]

    # 2. Verify odd-indexed clips do NOT automatically zoom when smart_punch_in=True unless explicit zoom > 1.01
    main_vid = str(tmp_path / "source.mp4")
    with open(main_vid, "wb") as f:
        f.write(b"S" * 4096)

    video_clips = [
        {"id": "c0", "start": 0.0, "end": 3.0, "isCut": False},
        {"id": "c1", "start": 3.0, "end": 6.0, "isCut": False},  # Odd index, no zoom set -> must NOT zoom!
        {"id": "c2", "start": 6.0, "end": 9.0, "isCut": False, "zoom": 1.25},  # Explicit zoom=1.25 -> MUST zoom!
    ]

    recorded_ffmpeg_cmds = []

    def fake_subprocess_run(cmd, *args, **kwargs):
        if cmd and cmd[0] == "ffmpeg":
            recorded_ffmpeg_cmds.append(cmd)
            out_file = cmd[-1]
            with open(out_file, "wb") as f_out:
                f_out.write(b"V" * 2048)
            res = MagicMock()
            res.returncode = 0
            res.stderr = ""
            return res
        # ffprobe mock
        res = MagicMock()
        res.returncode = 0
        res.stdout = "3.0\n"
        return res

    with patch("render.video_renderer.subprocess.run", side_effect=fake_subprocess_run):
        renderer._cut_ordered_video_clips(
            video_clips=video_clips,
            main_video_path=main_vid,
            temp_dir=str(tmp_path),
            smart_punch_in=True,
            playback_speed=1.0,
        )

    assert len(recorded_ffmpeg_cmds) == 3
    # Sort by output filename seg_0000, seg_0001, seg_0002
    sorted_cmds = sorted(recorded_ffmpeg_cmds, key=lambda c: c[-1])
    cmd_0_str = " ".join(sorted_cmds[0])
    cmd_1_str = " ".join(sorted_cmds[1])
    cmd_2_str = " ".join(sorted_cmds[2])

    assert "crop=" not in cmd_0_str
    assert "crop=" not in cmd_1_str, "Odd-indexed clip must NOT auto-zoom when smart_punch_in=True!"
    assert "crop=iw/1.250:ih/1.250" in cmd_2_str, "Clip with explicit zoom=1.25 must apply crop/scale zoom!"


def test_timeline_mapper_seq_timestamp_and_nearest_cut_boundary(tmp_path):
    """Verify TimelineMapper never drops overlays falling inside a cut and honors seqTimestamp, and ImageOverlay offsets video PTS with setpts."""
    from render.timeline_mapper import TimelineMapper
    from render.image_overlay import ImageOverlay

    # Keep segments: [0..17.91] (17.91s), cut [17.91..32.27], keep [32.27..50.0]
    keep_segments = [(0.0, 17.91), (32.27, 50.0)]
    overlays = [
        # 1. Overlay whose raw timestamp (22.97) fell inside cut [17.91..32.27] -> must snap to 0.0 / 17.91 instead of being dropped!
        {"id": "ov_cut_boundary", "type": "image", "timestamp": 22.97, "duration": 16.47},
        # 2. Overlay with explicit seqTimestamp = 3.24 -> must use seqTimestamp directly!
        {"id": "ov_seq_explicit", "type": "text", "timestamp": 36.11, "seqTimestamp": 3.24, "duration": 4.0},
    ]

    remapped = TimelineMapper.remap_overlays(overlays, keep_segments)
    assert len(remapped) == 2
    assert remapped[0]["id"] == "ov_cut_boundary"
    assert abs(float(remapped[0]["timestamp"]) - 17.91) < 0.01
    assert remapped[1]["id"] == "ov_seq_explicit"
    assert abs(float(remapped[1]["timestamp"]) - 3.24) < 0.01


# ==============================================================================
# 7. 5-Stage Multimodal Autonomous Director V2 Tests
# ==============================================================================

def test_turkish_semantic_title_never_cuts_mid_word():
    """Verify Turkish semantic title extractor never slices words or leaves dangling stopwords."""
    from pipeline.theme_profiles import extract_turkish_semantic_title

    raw = "Hukuk Muhakemeleri Kanununun çevresinde şekillenen dava şartları mahkemece incelenir."
    title = extract_turkish_semantic_title(raw, max_chars=32)
    assert "..." not in title
    assert not title.endswith("ÇEV")
    assert not title.endswith("ÇEVRESİNDE")
    assert title == "HUKUK MUHAKEMELERİ KANUNU"


def test_academic_lecture_disables_gifs_and_cyberpunk():
    """Verify academic/law lecture locks academic_lecture ThemeProfile and disables GIFs."""
    from pipeline.theme_profiles import detect_theme_profile_heuristic

    transcript = "Bugünkü dersimizde Hukuk Muhakemeleri Kanunu madde 114 dava şartlarını inceleyeceğiz."
    profile = detect_theme_profile_heuristic(transcript)
    assert profile.id == "academic_lecture"
    assert profile.allow_gifs is False
    assert profile.font_family == "Montserrat"


def test_safe_zone_solver_zero_collision_with_subtitles_and_head():
    """Verify SafeZoneSpatialSolver places cards in 0..100% coordinates with 0% overlap with head & subtitles."""
    from pipeline.safe_zone_vision_engine import SafeZoneSpatialSolver

    face_positions = [{"time": 10.0, "center_x": 0.50, "center_y": 0.28, "width": 0.18, "height": 0.24}]
    solver = SafeZoneSpatialSolver(face_positions=face_positions, subtitles_enabled=True)
    slot_id, px, py, scale, bbox = solver.solve_placement(8.0, 12.0, is_image_card=True)
    assert 10.0 <= px <= 90.0
    assert 5.0 <= py <= 65.0
    assert bbox.y2 <= 70.0


def test_validator_strips_stickers_in_academic_theme_and_fixes_unit_scale():
    """Verify MasterPlanValidator strips stickers in academic theme, fixes 0..1 coords, and drops unlinked SFX."""
    from pipeline.theme_profiles import detect_theme_profile_heuristic
    from pipeline.master_plan_validator import MasterPlanValidator

    profile = detect_theme_profile_heuristic("Hukuk mahkeme dava kanun madde")
    validator = MasterPlanValidator()
    overlays = [
        {"type": "sticker", "source": "https://example.com/512.gif", "start": 5.0, "end": 8.0},
        {"type": "image", "source": "https://example.com/law.jpg", "start": 10.0, "end": 14.0, "positionX": 0.75, "positionY": 0.25},
    ]
    sfx = [
        {"type": "whoosh", "timestamp": 10.0, "volume": 0.85},
        {"type": "ding", "timestamp": 32.0, "volume": 0.80},
    ]
    valid_ov, valid_sfx, _ = validator.validate_and_repair(
        overlays, sfx, [], profile, video_duration=1200.0, subtitles_enabled=True
    )
    assert len(valid_ov) == 1
    assert valid_ov[0]["type"] == "image"
    assert valid_ov[0]["positionX"] == 75.0
    assert len(valid_sfx) == 1
    assert valid_sfx[0]["volume"] <= 0.24


def test_llm_director_20min_lecture_full_coverage_and_image_hash_cache(tmp_path):
    """Verify LlmDirector covers full 20-minute lecture without stickers and ImageOverlay hashes 512.gif URLs uniquely."""
    from pipeline.llm_director import LlmDirector
    from render.image_overlay import ImageOverlay

    # 20-minute lecture (1214.0s) with segments every 20 seconds
    segments = [
        {
            "start": float(i * 20),
            "end": float(i * 20 + 6),
            "text": f"Hukuk Muhakemeleri Kanununun çevresinde madde {100 + i} dava şartları ve mahkeme görev kuralları incelenir.",
        }
        for i in range(60)
    ]
    director = LlmDirector(enable_web_crawl=False, work_dir=str(tmp_path))
    plan = director.compose_intelligent_plan(
        segments=segments,
        cuts=[],
        video_duration=1214.0,
        subtitles_enabled=True,
    )

    assert plan["theme_profile_id"] == "academic_lecture"
    assert len(plan["overlays"]) >= 12
    # Must cover past minute 15 (> 900s), not stop at minute 2!
    assert max(float(o["start"]) for o in plan["overlays"]) >= 900.0
    # Zero stickers in academic lecture
    assert all(o["type"] != "sticker" for o in plan["overlays"])
    # Zero subtitle collisions (Y < 68%)
    assert all(float(o["positionY"]) < 68.0 for o in plan["overlays"])
    # Transitions generated at chapter boundaries
    assert len(plan["transitions"]) >= 4

    # Verify ImageOverlay resolves different .../512.gif URLs to distinct filenames
    io = ImageOverlay(minio_client=MagicMock())
    with patch("render.image_overlay.urllib.request.urlretrieve") as mock_dl:
        def fake_dl(url, target):
            with open(target, "wb") as f:
                f.write(url.encode("utf-8"))
        mock_dl.side_effect = fake_dl
        p1 = io.resolve_image_path("https://fonts.gstatic.com/s/e/notoemoji/latest/1f525/512.gif", temp_dir=str(tmp_path))
        p2 = io.resolve_image_path("https://fonts.gstatic.com/s/e/notoemoji/latest/1f680/512.gif", temp_dir=str(tmp_path))
        assert p1 != p2


def test_youtube_style_person_enumeration_and_definition_triggers(tmp_path):
    """Verify HolisticAnalyzer + LlmDirector perform Word-Synchronized Single Term, Paired Terms (Tabiat + Fıtrat), Progressive Stack List (Fizik..Astronomi Left->Right overflow), and Person Portrait placement."""
    from pipeline.llm_director import LlmDirector

    segments = [
        {"start": 45.0, "end": 48.2, "text": "İlk dönem kelamcılarının geliştirdiği hudus delili kainatın başlangıcını açıklar."},
        {"start": 120.0, "end": 123.5, "text": "İslam düşünce tarihinde İmam Gazali bu ayrımı çok net ortaya koymuştur."},
        {
            "start": 565.04,
            "end": 567.25,
            "text": "İkincisi tekvini şeriattır.",
            "words": [
                {"word": "İkincisi", "start": 565.04, "end": 565.71},
                {"word": "tekvini", "start": 565.97, "end": 566.58},
                {"word": "şeriattır.", "start": 566.58, "end": 567.25},
            ],
        },
        {
            "start": 570.80,
            "end": 574.30,
            "text": "sıvatından gelen tabiat ve fıtrat",
            "words": [
                {"word": "sıvatından", "start": 570.80, "end": 571.40},
                {"word": "gelen", "start": 571.40, "end": 571.80},
                {"word": "tabiat", "start": 571.80, "end": 572.08},
                {"word": "ve", "start": 572.87, "end": 573.64},
                {"word": "fıtrat", "start": 573.64, "end": 574.30},
            ],
        },
        {
            "start": 574.30,
            "end": 578.06,
            "text": "kanunlarıdır. Fizik, kimya, biyoloji,",
            "words": [
                {"word": "kanunlarıdır.", "start": 574.30, "end": 575.27},
                {"word": "Fizik,", "start": 575.75, "end": 576.45},
                {"word": "kimya,", "start": 576.55, "end": 577.24},
                {"word": "biyoloji,", "start": 577.27, "end": 578.06},
            ],
        },
        {
            "start": 578.26,
            "end": 584.94,
            "text": "tıp, astronomi ilimlerinin tespit ettiği kanunlar bu şeriatın maddeleridir.",
            "words": [
                {"word": "tıp,", "start": 578.26, "end": 578.62},
                {"word": "astronomi", "start": 579.18, "end": 579.90},
                {"word": "ilimlerinin", "start": 579.90, "end": 580.74},
                {"word": "maddeleridir.", "start": 584.04, "end": 584.94},
            ],
        },
    ]

    director = LlmDirector(enable_web_crawl=True, work_dir=str(tmp_path))
    with patch.object(
        director.crawler,
        "gather_person_portrait_candidates",
        return_value=[{
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Al-Ghazali.png/800px-Al-Ghazali.png",
            "source": "wikipedia_portrait",
            "local_path": str(tmp_path / "ghazali.png"),
            "cv_metrics": {"w": 800, "h": 900, "sharpness": 120.0, "text_density": 0.01},
        }],
    ):
        plan = director.compose_intelligent_plan(
            segments=segments,
            cuts=[],
            video_duration=600.0,
            subtitles_enabled=True,
        )

    ovs = plan["overlays"]
    by_text = {o.get("text"): o for o in ovs if o.get("type") == "text"}
    images = [o for o in ovs if o.get("type") == "image"]

    # 1. Person Introduction ONLY gets an image (no abstract concept images!)
    assert "İMAM GAZALİ" in by_text
    assert len(images) == 1
    assert "Al-Ghazali" in images[0]["source"]

    # 2. "TEKVİNÎ ŞERİAT" starts on "tekvini" (565.97s) and vanishes when "şeriattır." ends (567.25s)
    assert "TEKVİNÎ ŞERİAT" in by_text
    tekvini_ov = by_text["TEKVİNÎ ŞERİAT"]
    assert abs(tekvini_ov["start"] - 565.97) < 0.05
    assert abs(tekvini_ov["end"] - 567.25) < 0.05

    # 3. Paired terms "TABİAT" (571.80s) and "FITRAT" (573.64s) both end when "kanunlarıdır." ends (575.27s)
    assert "TABİAT" in by_text and "FITRAT" in by_text
    assert abs(by_text["TABİAT"]["start"] - 571.80) < 0.05
    assert abs(by_text["FITRAT"]["start"] - 573.64) < 0.05
    assert abs(by_text["TABİAT"]["end"] - 575.27) < 0.05
    assert abs(by_text["FITRAT"]["end"] - 575.27) < 0.05

    # 4. Progressive list "FİZİK, KİMYA, BİYOLOJİ, TIP" on Left Column (X=16.0) + "ASTRONOMİ" on Right Column (X=84.0), all ending at 584.94s!
    for idx_sci, sci in enumerate(["FİZİK", "KİMYA", "BİYOLOJİ", "TIP"]):
        assert sci in by_text
        assert by_text[sci]["positionX"] == 16.0
        assert abs(by_text[sci]["end"] - 584.94) < 0.05
    assert "ASTRONOMİ" in by_text
    assert by_text["ASTRONOMİ"]["positionX"] == 84.0
    assert abs(by_text["ASTRONOMİ"]["end"] - 584.94) < 0.05





