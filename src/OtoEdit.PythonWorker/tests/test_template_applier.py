import pytest
from render.template_applier import TemplateApplier


def test_enrich_edl_with_template():
    edl_json = {
        "projectId": "test-project-123",
        "duration": 60.0,
        "overlays": [],
        "template": {
            "logo": "s3://otoedit/templates/kursu_tv_logo.png",
            "logoPosition": ["right", "top"],
            "speakerName": "Prof. Dr. Hasan Herken",
            "speakerTitle": "Psikiyatri Uzmanı"
        }
    }

    enriched = TemplateApplier.enrich_edl_with_template(edl_json)
    overlays = enriched.get("overlays", [])

    # Hem logo hem alt bant eklenmiş olmalı
    ids = [ov["id"] for ov in overlays]
    assert "tpl_logo" in ids
    assert "tpl_speaker_name" in ids

    # Logo detayları
    logo_ov = next(ov for ov in overlays if ov["id"] == "tpl_logo")
    assert logo_ov["type"] == "image"
    assert logo_ov["source"] == "s3://otoedit/templates/kursu_tv_logo.png"

    # Konuşmacı alt bant detayları
    speaker_ov = next(ov for ov in overlays if ov["id"] == "tpl_speaker_name")
    assert speaker_ov["type"] == "text"
    assert "Hasan Herken" in speaker_ov["content"]
    assert "Psikiyatri" in speaker_ov["content"]


def test_enrich_edl_idempotent():
    edl_json = {
        "projectId": "test-project-123",
        "overlays": [
            {"id": "tpl_logo", "type": "image", "source": "already_exists.png"}
        ],
        "template": {
            "logo": "s3://otoedit/templates/new_logo.png"
        }
    }

    enriched = TemplateApplier.enrich_edl_with_template(edl_json)
    overlays = enriched.get("overlays", [])
    assert len([ov for ov in overlays if ov["id"] == "tpl_logo"]) == 1
    assert overlays[0]["source"] == "already_exists.png"
