"""
Aşama 3B: VLMAssetVerifier (Gemini Vision 5-Kriterli Öz-Eleştiri Rubriği).
Bulunan görsellerin konuşulan konuyla ve ThemeProfile ile uyumunu 0-100 arasında
tartar; filigranlı/alakasız görselleri reddeder ve uygun görselin sunum stilini seçer.
"""

import base64
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from services.web_image_crawler import WebImageCrawler
from utils.logger import get_logger

try:
    import cv2
except Exception:
    cv2 = None

logger = get_logger("VLMAssetVerifier")


class VLMAssetVerifier:
    """
    Aday görselleri değerlendirir; OpenCV barkod/boş kapak anomali filtresinden ve
    Multimodal VLM denetiminden geçirir. En yüksek puanlı aday >= 75 ise onaylar,
    değilse Zarif Geri Çekilme (Graceful Degradation -> görsel koymama) tetikler.
    """

    ACCEPTANCE_THRESHOLD = 75.0

    def __init__(self, gemini_client: Any = None, enable_vlm: bool = True):
        self.gemini = gemini_client
        self.enable_vlm = enable_vlm

    def select_best_candidate(
        self,
        candidates: List[Dict[str, Any]],
        spoken_context_tr: str,
        concept_title_tr: str,
        theme_display_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Onaylanan adayı ve stil bilgilerini döndürür.
        Barkodlu kütüphane kapağı, simsiyah boş cilt veya alakasız görselleri kesin olarak eler.
        """
        if not candidates:
            return None

        # Aşama 1: Her aday için yerel dosya üzerinde Barkod / Boş Kapak ve Metadata Uygunluk Kontrolü
        clean_candidates: List[Dict[str, Any]] = []
        for cand in candidates:
            local_path = str(cand.get("local_path") or "")
            url_lower = str(cand.get("url") or "").lower()
            # PDF/DjVu 1. sayfası (dış cilt/barkod) asla kabul edilmez
            if re.search(r"/page1-\d+px-.*\.(pdf|djvu)\.jpg", url_lower, re.IGNORECASE):
                logger.info(f"[VLMAssetVerifier] PDF/DjVu 1. sayfa (dış kapak) veto edildi: {url_lower}")
                continue
            if local_path and os.path.exists(local_path) and cv2 is not None:
                img = cv2.imread(local_path)
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    has_anom, anom_reason = WebImageCrawler._detect_barcode_or_blank_cover_anomaly(
                        img, gray, is_work_or_manuscript=bool(cand.get("is_work", False))
                    )
                    if has_anom:
                        logger.info(f"[VLMAssetVerifier] Barkod/Boş kapak anomalisi veto edildi ({local_path}): {anom_reason}")
                        continue
            clean_candidates.append(cand)

        if not clean_candidates:
            return None

        # Aşama 2: Gemini VLM üzerinden değerlendirme (etkinse)
        if self.enable_vlm and self.gemini and getattr(self.gemini, "is_available", lambda: False)():
            scored = self._evaluate_with_gemini_vision(
                clean_candidates, spoken_context_tr, concept_title_tr, theme_display_name
            )
            if scored:
                return scored

        # Aşama 3: Deterministik Puanlayıcı (Wikipedia Portre/Kavram + Pexels + Wikimedia + OpenCV metrikleri)
        best_cand: Optional[Dict[str, Any]] = None
        best_score = 0.0
        for cand in clean_candidates:
            metrics = cand.get("cv_metrics", {})
            src = str(cand.get("source", ""))
            is_lead = bool(cand.get("is_lead_summary", False))
            is_work = bool(cand.get("is_work", False))
            if src in ("wikipedia_portrait", "wikipedia_concept"):
                base_score = 96.0 if is_lead else 88.0
            elif src == "pexels_photo":
                base_score = 84.0
            elif src in ("wikimedia", "bing_web"):
                base_score = 82.0
            else:
                base_score = 76.0
            text_pen_mult = 10.0 if (is_lead or is_work) else 60.0
            base_score -= float(metrics.get("text_density", 0.0)) * text_pen_mult
            sharpness = float(metrics.get("sharpness", 80.0))
            if sharpness < 25.0:
                base_score -= 20.0
            if base_score >= self.ACCEPTANCE_THRESHOLD and base_score > best_score:
                best_score = base_score
                best_cand = dict(cand)

        if best_cand:
            best_cand["vlm_score"] = round(best_score, 1)
            best_cand["styling"] = self._default_card_styling()
        return best_cand

    def _evaluate_with_gemini_vision(
        self,
        candidates: List[Dict[str, Any]],
        spoken_context_tr: str,
        concept_title_tr: str,
        theme_display_name: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            best_cand: Optional[Dict[str, Any]] = None
            best_score = -1.0
            best_eval: Dict[str, Any] = {}

            for cand in candidates[:3]:
                local_path = cand.get("local_path")
                if not local_path or not os.path.exists(local_path):
                    continue
                if hasattr(self.gemini, "verify_image_with_vision"):
                    ev = self.gemini.verify_image_with_vision(
                        image_path=local_path,
                        concept_title=concept_title_tr,
                        spoken_context=spoken_context_tr,
                        theme_display_name=theme_display_name,
                    )
                else:
                    ev = None
                if not isinstance(ev, dict):
                    continue
                if (
                    ev.get("fatal_veto")
                    or ev.get("is_blank_cover_or_barcode")
                    or ev.get("matches_target_entity") is False
                ):
                    logger.info(
                        f"[VLMAssetVerifier] VLM görseli reddetti ({concept_title_tr}): {ev.get('literal_description')}"
                    )
                    continue
                sc = float(ev.get("weighted_score", 0.0))
                if sc >= self.ACCEPTANCE_THRESHOLD and sc > best_score:
                    best_score = sc
                    best_cand = dict(cand)
                    best_eval = ev

            if best_cand:
                best_cand["vlm_score"] = round(best_score, 1)
                best_cand["styling"] = {
                    "mask_shape": best_eval.get("mask_shape", "rounded"),
                    "border_radius_px": 18,
                    "drop_shadow": True,
                    "shadow_blur_px": 18,
                    "remove_bg": bool(best_eval.get("remove_bg", False)),
                    "entry_animation": "pop-up",
                    "exit_animation": "fade",
                }
                return best_cand
            return None
        except Exception as exc:
            logger.warning(f"[VLMAssetVerifier] Gemini Vision değerlendirmesi atlandı: {exc}")
            return None

    def _default_card_styling(self) -> Dict[str, Any]:
        return {
            "mask_shape": "rounded",
            "border_radius_px": 18,
            "drop_shadow": True,
            "shadow_blur_px": 18,
            "remove_bg": False,
            "entry_animation": "pop-up",
            "exit_animation": "fade",
        }
