"""
Aşama 3B: VLMAssetVerifier (Gemini Vision 5-Kriterli Öz-Eleştiri Rubriği).
Bulunan görsellerin konuşulan konuyla ve ThemeProfile ile uyumunu 0-100 arasında
tartar; filigranlı/alakasız görselleri reddeder ve uygun görselin sunum stilini seçer.
"""

import base64
import json
import os
import re
from typing import Any, Dict, List, Optional
from utils.logger import get_logger

logger = get_logger("VLMAssetVerifier")


class VLMAssetVerifier:
    """
    Aday görselleri değerlendirir; en yüksek puanlı aday >= 75 ise onaylar,
    değilse Zarif Geri Çekilme (Graceful Degradation -> KEY_TERM_CALLOUT) tetikler.
    """

    ACCEPTANCE_THRESHOLD = 75.0

    def __init__(self, gemini_client: Any = None, enable_vlm: bool = False):
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
        Onaylanan adayı ve VLM tarafından belirlenen stil bilgilerini döndürür.
        Hiçbir aday >= 75 alamazsa None döndürür (bu durumda KEY_TERM_CALLOUT'a düşülür).
        """
        if not candidates:
            return None

        # Gemini VLM üzerinden değerlendirme (etkinse)
        if self.enable_vlm and self.gemini and getattr(self.gemini, "is_available", lambda: False)():
            scored = self._evaluate_with_gemini_vision(
                candidates, spoken_context_tr, concept_title_tr, theme_display_name
            )
            if scored:
                return scored

        # Deterministik Puanlayıcı (Wikipedia Portre/Kavram + Pexels + Wikimedia + OpenCV metrikleri)
        best_cand: Optional[Dict[str, Any]] = None
        best_score = 0.0
        for cand in candidates:
            metrics = cand.get("cv_metrics", {})
            src = str(cand.get("source", ""))
            if src in ("wikipedia_portrait", "wikipedia_concept"):
                base_score = 92.0
            elif src == "pexels_photo":
                base_score = 84.0
            elif src == "wikimedia":
                base_score = 80.0
            else:
                # Doğrulanmamış genel web/Bing görseli VLM onayı olmadan 75 barajını geçemez!
                base_score = 68.0
            base_score -= float(metrics.get("text_density", 0.0)) * 80.0
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
            prompt = (
                f"Video Teması: {theme_display_name}\n"
                f"Anlatılan Kavram: {concept_title_tr}\n"
                f"Konuşmacının Cümlesi: {spoken_context_tr}\n\n"
                "Bu aday görseli şu 5 kritere göre 0-100 arasında puanla:\n"
                "- semantic_relevance (35%): Kavramla doğrudan alakalı mı?\n"
                "- tone_match (25%): Video temasına uygun ciddiyette mi?\n"
                "- visual_cleanliness (20%): Filigran (watermark), slayt yazısı veya logo YOKSA 100, varsa 0.\n"
                "- technical_quality (10%): Netlik ve ışık kalitesi.\n"
                "- composition_fit (10%): Köşede kart olarak gösterilmeye uygun mu?\n"
                "Eğer görselde filigran, yoğun metin veya yanlış anlam varsa 'fatal_veto': true yap.\n"
                "Sadece JSON döndür:\n"
                '{"weighted_score": 85, "fatal_veto": false, "mask_shape": "rounded", "remove_bg": false}'
            )

            best_cand: Optional[Dict[str, Any]] = None
            best_score = -1.0
            best_eval: Dict[str, Any] = {}

            for cand in candidates[:2]:
                local_path = cand.get("local_path")
                if not local_path or not os.path.exists(local_path):
                    continue
                raw = self.gemini.generate_vision(prompt, local_path, max_retries=1)
                if not raw:
                    continue
                cleaned = re.sub(r"```json|```", "", raw).strip()
                ev = json.loads(cleaned)
                if not isinstance(ev, dict) or ev.get("fatal_veto"):
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
                    "entry_animation": "fade",
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
            "entry_animation": "fade",
            "exit_animation": "fade",
        }
