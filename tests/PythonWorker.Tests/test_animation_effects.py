import pytest
from render.animation_effects import AnimationEffects


def test_animation_effects_ass_fade():
    tag = AnimationEffects.get_ass_tags("fade", duration_sec=5.0)
    assert "\\fad(" in tag
    assert tag.startswith("\\fad(")


def test_animation_effects_ass_popup():
    tag = AnimationEffects.get_ass_tags("pop-up", duration_sec=3.0)
    assert "\\fscx50" in tag
    assert "\\t(" in tag
    assert "\\fscx100" in tag


def test_animation_effects_ass_slide_left():
    tag = AnimationEffects.get_ass_tags("slide-left", duration_sec=4.0, pos_x=500, pos_y=800)
    assert "\\move(" in tag
    assert "500,800" in tag


def test_resolve_static_position():
    x, y = AnimationEffects.resolve_static_position(["center", "bottom"])
    assert x == "(main_w-overlay_w)/2"
    assert "main_h-overlay_h" in y

    x_top_right, y_top_right = AnimationEffects.resolve_static_position(["right", "top"])
    assert "main_w-overlay_w" in x_top_right
    assert y_top_right == "40"
