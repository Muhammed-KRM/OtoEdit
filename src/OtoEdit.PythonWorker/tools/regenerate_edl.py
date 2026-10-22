"""
Mevcut bir projenin EDL'ini, worker'ın normal analiz akışıyla BİREBİR aynı yoldan yeniden üretir:
  projenin KENDİ transkripti -> LlmDirector -> Pydantic OverlayItem normalizasyonu -> Senkron Denetimi

Kullanım (worker container içinde):
    python -m tools.regenerate_edl <girdi_edl.json> <cikti_edl.json>

Güvenlik kuralları:
  - Transkript yalnızca EDL'in kendi 'transcript' alanından okunur (başka projenin verisi kullanılamaz).
  - Kullanıcının elle eklediği katmanlar (id'si 'ad_' ile başlamayan overlay/sfx/geçişler) aynen korunur.
  - Senkron denetiminde eşleşmeyen yazı oranı %10'u aşarsa çıktı YAZILMAZ ve çıkış kodu 2 döner.
"""

import json
import sys
from typing import Any, Dict, List

from models.edl_model import OverlayItem
from pipeline.holistic_analyzer import ENGINE_VERSION, audit_overlay_sync
from pipeline.llm_director import LlmDirector
from utils.logger import get_logger

logger = get_logger("RegenerateEdl")

MAX_MISMATCH_RATIO = 0.10


def _is_auto(item: Dict[str, Any]) -> bool:
    return str(item.get("id") or "").startswith("ad_")


def _dump(model: Any) -> Dict[str, Any]:
    fn = getattr(model, "model_dump", None) or getattr(model, "dict")
    return fn()


def regenerate(edl: Dict[str, Any]) -> Dict[str, Any]:
    transcript = edl.get("transcript") or {}
    segments: List[Dict[str, Any]] = transcript.get("segments", []) if isinstance(transcript, dict) else list(transcript)
    if not segments:
        raise RuntimeError("EDL içinde transkript segmenti yok; yeniden üretim yapılamaz.")

    duration = float(edl.get("duration") or transcript.get("duration") or segments[-1].get("end") or 0.0)
    cuts = edl.get("cuts") or []
    face_data = ((edl.get("repurposing") or {}).get("faceTrackingData")) or []
    subtitles_enabled = bool((edl.get("settings") or {}).get("subtitlesEnabled", True))

    manual_overlays = [o for o in (edl.get("overlays") or []) if not _is_auto(o)]
    manual_sfx = [s for s in (edl.get("sfxClips") or []) if not _is_auto(s)]
    manual_transitions = [t for t in (edl.get("transitions") or []) if not _is_auto(t)]

    logger.info(
        f"Yeniden üretim: Motor={ENGINE_VERSION} | segment={len(segments)} | süre={duration:.2f}s | "
        f"kesim={len(cuts)} | korunan manuel overlay={len(manual_overlays)}"
    )

    director = LlmDirector(enable_web_crawl=True)
    composed = director.compose_intelligent_plan(
        segments=segments,
        cuts=cuts,
        video_duration=duration,
        face_positions=face_data,
        existing_overlays=[],
        existing_sfx=[],
        existing_transitions=[],
        subtitles_enabled=subtitles_enabled,
        video_path=None,
    )

    # Worker'daki EdlBuilder ile aynı normalizasyon (varsayılan backgroundColor vb. alanlar)
    auto_overlays = [_dump(OverlayItem(**o)) if isinstance(o, dict) else _dump(o) for o in composed.get("overlays", [])]

    report = audit_overlay_sync(auto_overlays, segments)
    checked = max(1, report["checked"])
    ratio = len(report["mismatches"]) / checked
    logger.info(f"Senkron denetimi: {report['checked']} yazı, {len(report['mismatches'])} eşleşmeyen (%{ratio * 100:.1f})")
    if ratio > MAX_MISMATCH_RATIO:
        raise SystemExit(
            f"SENKRON DENETİMİ BAŞARISIZ: eşleşmeyen oran %{ratio * 100:.1f} > %{MAX_MISMATCH_RATIO * 100:.0f}. "
            f"Örnekler: {report['mismatches'][:8]}"
        )

    new_edl = dict(edl)
    new_edl["overlays"] = auto_overlays + manual_overlays
    new_edl["sfxClips"] = [dict(s) for s in composed.get("sfxClips", [])] + manual_sfx
    new_edl["transitions"] = [dict(t) for t in composed.get("transitions", [])] + manual_transitions
    new_edl["_regen"] = {
        "engine": ENGINE_VERSION,
        "syncChecked": report["checked"],
        "syncMismatches": report["mismatches"],
    }
    return new_edl


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "r", encoding="utf-8") as f:
        edl = json.load(f)
    try:
        new_edl = regenerate(edl)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(new_edl, f, ensure_ascii=False)
    print(json.dumps({
        "ok": True,
        "overlays": len(new_edl["overlays"]),
        "sfx": len(new_edl["sfxClips"]),
        "transitions": len(new_edl["transitions"]),
        **new_edl["_regen"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
