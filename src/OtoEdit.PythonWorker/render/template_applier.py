"""OtoEdit Template Applier - Video şablonlarını (logo, alt bant, konuşmacı adı, altyazı stili) uygular."""
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class TemplateApplier:
    """EDL JSON içindeki template ayarlarını okuyup overlay ve ASS elemanlarına dönüştürür."""

    @staticmethod
    def enrich_edl_with_template(edl_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Şablon alanında belirtilen logo, konuşmacı adı (Lower Third) ve stil ayarlarını
        mevcut EDL overlays listesine ekler.
        """
        template = edl_json.get("template")
        if not template or not isinstance(template, dict):
            return edl_json

        overlays: List[Dict[str, Any]] = edl_json.get("overlays", [])
        existing_ids = {ov.get("id") for ov in overlays}

        # 1. Logo Ekleme
        logo_source = template.get("logo")
        if logo_source and "tpl_logo" not in existing_ids:
            logo_pos = template.get("logoPosition", ["right", "top"])
            total_duration = float(edl_json.get("duration", 3600.0))
            overlays.append({
                "id": "tpl_logo",
                "type": "image",
                "source": logo_source,
                "timestamp": 0.5,
                "duration": total_duration,
                "animation": "fade",
                "position": logo_pos,
                "scale": 0.15
            })
            logger.info(f"Şablon logosu overlay listesine eklendi: {logo_source}")

        # 2. Konuşmacı Adı & Unvanı (Lower Third Alt Bant)
        speaker_name = template.get("speakerName")
        speaker_title = template.get("speakerTitle")

        if speaker_name and "tpl_speaker_name" not in existing_ids:
            display_text = speaker_name
            if speaker_title:
                display_text = f"{speaker_name}\n{speaker_title}"

            overlays.append({
                "id": "tpl_speaker_name",
                "type": "text",
                "content": display_text,
                "font": "Montserrat-Bold",
                "fontSize": 44,
                "color": "#FFFFFF",
                "backgroundColor": "#002B49CC",  # Kurumsal lacivert yarı-saydam alt bant
                "timestamp": 3.0,
                "duration": 6.0,
                "animation": "slide-left",
                "position": ["left", "bottom"]
            })
            logger.info(f"Şablon konuşmacı alt bandı eklendi: {speaker_name}")

        edl_json["overlays"] = overlays
        return edl_json
