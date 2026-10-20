"""
proactive_director.py — Otonom Video Yönetmeni (Proactive AI Director Engine [E1]).
EDL JSON içerisindeki transkripti, kesimleri (cuts), ses tepe noktalarını (audioPeaks / audioWaveform),
mevcut kaplamaları ve proje ayarlarını analiz ederek tek tıkla uygulanabilir
4 ila 6 zengin proaktif kurgu önerisi (Tipografi Hook, Sahne Geçişi, SFX Vurgusu,
Smart Punch-In Zoom, Sinematik Renk Düzenleme ve -14 LUFS Ses Mastering) üretir.
"""
import re
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ProactiveDirector:
    """EDL durumunu inceleyerek tek tıkla uygulanabilir yönetmen önerileri üreten motor."""

    @staticmethod
    def _extract_hook_phrase(text: str, max_words: int = 4) -> str:
        """İlk cümleden dikkat çekici kısa bir başlık (hook) çıkarır."""
        if not text:
            return "ÖNEMLİ DETAY!"
        cleaned = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ!?]", "", text).strip()
        words = [w for w in cleaned.split() if len(w) > 1]
        if not words:
            return "BUNU KAÇIRMA!"
        phrase = " ".join(words[:max_words]).upper()
        if not phrase.endswith(("!", "?")):
            phrase += "!"
        return phrase

    @staticmethod
    def _extract_climax_segment(segments: List[Dict[str, Any]], duration: float) -> Dict[str, Any]:
        """Transkript içerisindeki en vurgulu / anahtar cümleyi bulur."""
        if not segments:
            return {"start": round(duration * 0.4, 2), "end": round(duration * 0.4 + 3.5, 2), "text": "KRİTİK NOKTA"}

        emphasis_keywords = {
            "önemli", "dikkat", "asla", "mutlaka", "sır", "nasıl", "neden",
            "en", "büyük", "fark", "sonuç", "özetle", "harika", "inanılmaz",
            "important", "secret", "never", "always", "best", "key"
        }

        best_seg = segments[min(len(segments) - 1, max(0, len(segments) // 2))]
        best_score = -1.0

        for idx, seg in enumerate(segments):
            if idx == 0 and len(segments) > 1:
                continue  # İlk segment zaten açılış hook'u için kullanılıyor
            txt = str(seg.get("text") or "").strip()
            if not txt:
                continue
            words = txt.lower().split()
            kw_hits = sum(1 for w in words if any(k in w for k in emphasis_keywords))
            excl_bonus = 2.0 if ("!" in txt or "?" in txt) else 0.0
            score = kw_hits * 2.5 + excl_bonus + min(len(words), 12) * 0.2
            if score > best_score:
                best_score = score
                best_seg = seg

        return best_seg

    @classmethod
    def generate_suggestions(cls, edl_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        EDL verisini analiz ederek 4 ila 6 zengin, uygulanabilir proaktif kurgu önerisi döner.
        Her öneri: id, type, title, description, timestamp, duration, confidence, category, payload içerir.
        """
        if not edl_json or not isinstance(edl_json, dict):
            edl_json = {}

        duration = float(edl_json.get("duration") or 0.0)
        transcript = edl_json.get("transcript") or {}
        segments: List[Dict[str, Any]] = transcript.get("segments", []) if isinstance(transcript, dict) else []
        if duration <= 0.0 and segments:
            duration = float(segments[-1].get("end") or 15.0)
        if duration <= 0.0:
            duration = 15.0

        cuts = edl_json.get("cuts") or []
        overlays = edl_json.get("overlays") or []
        transitions = edl_json.get("transitions") or []
        audio_peaks = edl_json.get("audioPeaks") or edl_json.get("audioWaveform") or []
        settings = edl_json.get("settings") or {}
        if not isinstance(settings, dict):
            settings = getattr(settings, "__dict__", {})

        suggestions: List[Dict[str, Any]] = []

        # 1. Açılış Hook Başlığı (3D / Gradyan / Neon Pill Rozeti) - İlk 3 saniye izleyici tutma
        first_seg = segments[0] if segments else {"start": 0.2, "text": "Bunu Bilmelisin!"}
        hook_ts = round(max(0.0, min(1.5, float(first_seg.get("start") or 0.2))), 2)
        hook_text = cls._extract_hook_phrase(str(first_seg.get("text") or "BUNU KAÇIRMA!"), max_words=4)

        suggestions.append({
            "id": "proactive_hook_badge_1",
            "type": "hook_title",
            "title": "Viral Açılış Hook Rozeti Ekle",
            "description": f"İlk 3 saniyede izleyiciyi yakalamak için '{hook_text}' metnini gradyan ve neon ışıltılı başlık olarak ekler.",
            "reason": "İlk 3 saniye izleyici tutma oranını (retention) %38 artırır.",
            "timestamp": hook_ts,
            "duration": 3.2,
            "confidence": 0.96,
            "category": "typography",
            "status": "pending",
            "payload": {
                "action": "add_overlay",
                "overlay": {
                    "id": "ov_dir_hook_1",
                    "type": "text",
                    "content": hook_text,
                    "timestamp": hook_ts,
                    "duration": 3.2,
                    "font": "Montserrat",
                    "fontSize": 56,
                    "color": "#FFFFFF",
                    "fillType": "gradient",
                    "gradientStart": "#FF007F",
                    "gradientEnd": "#FFD700",
                    "gradientAngle": 45,
                    "boxStyle": "pill",
                    "boxBgColor": "rgba(15, 23, 42, 0.85)",
                    "strokeColor": "#000000",
                    "strokeWidth": 3,
                    "glowEnabled": True,
                    "glowColor": "#FF007F",
                    "glowRadius": 12,
                    "allCaps": True,
                    "animation": "pop-up",
                    "loopAnimation": "pulse",
                    "position": ["center", "top"],
                    "positionX": 50,
                    "positionY": 18,
                },
            },
        })

        # 2. Kesim Noktasına Yumuşak Sahne Geçişi (xfade Transition)
        if cuts and len(cuts) > 0:
            first_cut = cuts[0] if isinstance(cuts[0], dict) else getattr(cuts[0], "__dict__", {})
            cut_ts = round(float(first_cut.get("start") or (duration * 0.3)), 2)
        else:
            cut_ts = round(duration * 0.33, 2)

        if not transitions:
            suggestions.append({
                "id": "proactive_transition_2",
                "type": "transition_xfade",
                "title": "Kesim Noktasına Sinematik Geçiş (Dissolve) Ekle",
                "description": f"{cut_ts:.1f}. saniyedeki sert jump-cut geçişini yumuşatmak için 0.45s 'dissolve' (xfade) geçişi uygular.",
                "reason": "Sert kesim sıçramalarını sinematik geçişle yumuşatır.",
                "timestamp": cut_ts,
                "duration": 0.45,
                "confidence": 0.92,
                "category": "transition",
                "status": "pending",
                "payload": {
                    "action": "add_transition",
                    "transition": {
                        "id": "tr_dir_1",
                        "type": "dissolve",
                        "timestamp": cut_ts,
                        "segmentIndex": 0,
                        "duration": 0.45,
                    },
                },
            })

        # 3. Anahtar Vurgu Noktasına Fosforlu Kalem (Highlight-Marker) Metin Katmanı
        climax_seg = cls._extract_climax_segment(segments, duration)
        climax_ts = round(float(climax_seg.get("start") or (duration * 0.5)), 2)
        climax_phrase = cls._extract_hook_phrase(str(climax_seg.get("text") or "ÖNEMLİ NOKTA"), max_words=3)

        suggestions.append({
            "id": "proactive_callout_3",
            "type": "keyword_badge",
            "title": "Anahtar Vurguya Highlight-Marker Metin Ekle",
            "description": f"Konuşmanın vurgu noktasında ({climax_ts:.1f}s) '{climax_phrase}' ifadesini fosforlu marker şeridiyle öne çıkarır.",
            "reason": "Önemli anahtar kelimeleri görsel olarak pekiştirir.",
            "timestamp": climax_ts,
            "duration": 3.0,
            "confidence": 0.91,
            "category": "typography",
            "status": "pending",
            "payload": {
                "action": "add_overlay",
                "overlay": {
                    "id": "ov_dir_marker_2",
                    "type": "text",
                    "content": climax_phrase,
                    "timestamp": climax_ts,
                    "duration": 3.0,
                    "font": "Bebas Neue",
                    "fontSize": 52,
                    "color": "#0F172A",
                    "boxStyle": "highlight-marker",
                    "boxBgColor": "#FACC15",
                    "strokeWidth": 0,
                    "allCaps": True,
                    "animation": "bounce",
                    "position": ["center", "center"],
                    "positionX": 50,
                    "positionY": 72,
                },
            },
        })

        # 4. Ses Tepe Noktası / Geçiş Anı İçin SFX (Whoosh / Pop) Ses Efekti Önerisi
        sfx_ts = hook_ts
        if audio_peaks and isinstance(audio_peaks, list) and len(audio_peaks) > 4:
            # En yüksek ses enerjisi tepe noktasını bul
            numeric_peaks = [float(p) if isinstance(p, (int, float)) else 0.5 for p in audio_peaks]
            max_idx = int(max(range(len(numeric_peaks)), key=lambda i: numeric_peaks[i]))
            sfx_ts = round((max_idx / max(1, len(numeric_peaks))) * duration, 2)

        suggestions.append({
            "id": "proactive_sfx_4",
            "type": "sfx_accent",
            "title": "Vurgu Anına 'Whoosh Pop' Ses Efekti (SFX) Ekle",
            "description": f"{sfx_ts:.1f}. saniyedeki görsel giriş ve ses vurgusunu güçlendirmek için senkronize SFX ekler.",
            "reason": "Görsel geçişleri işitsel geri bildirimle destekleyerek dinamizmi artırır.",
            "timestamp": sfx_ts,
            "duration": 1.2,
            "confidence": 0.89,
            "category": "audio",
            "status": "pending",
            "payload": {
                "action": "add_sfx",
                "sfx": {
                    "id": "sfx_dir_whoosh_1",
                    "name": "Whoosh Pop Hit",
                    "category": "whoosh",
                    "timestamp": sfx_ts,
                    "start": sfx_ts,
                    "duration": 1.2,
                    "volume": 0.75,
                    "fadeIn": 0.05,
                    "fadeOut": 0.25,
                },
            },
        })

        # 5. Smart Punch-In Zoom & Sinematik Renk Düzenleme (Color Grading)
        if not settings.get("smartPunchIn") or not settings.get("colorGrading"):
            mid_ts = round(duration * 0.25, 2)
            suggestions.append({
                "id": "proactive_visual_grade_5",
                "type": "smart_punch_in",
                "title": "Smart Punch-In Zoom ve Sinematik Renk (Color Grading) Aktifleştir",
                "description": "Kesim aralarında %10 dinamik kamera yakınlaştırması (Punch-In) ve sıcak sinematik kontrast filtresi uygular.",
                "reason": "Sabit kamera açısının yarattığı monotonluğu kırar ve profesyonel renk tonu sağlar.",
                "timestamp": mid_ts,
                "duration": round(duration, 2),
                "confidence": 0.94,
                "category": "retention",
                "status": "pending",
                "payload": {
                    "action": "update_settings",
                    "settings": {
                        "smartPunchIn": True,
                        "colorGrading": {
                            "brightness": 4,
                            "contrast": 14,
                            "saturation": 16,
                            "temperature": 8,
                        },
                    },
                },
            })

        # 6. Yayın Standardı -14 LUFS Ses Normalizasyonu & Auto-Ducking
        if not settings.get("normalizeAudio"):
            suggestions.append({
                "id": "proactive_audio_master_6",
                "type": "audio_mastering",
                "title": "-14 LUFS Yayın Standardı Ses Normalizasyonu (Loudnorm) Uygula",
                "description": "YouTube, TikTok ve Reels standartlarına uygun -14 LUFS ses dengelemesi ve arka plan müziği Auto-Ducking ayarını açar.",
                "reason": "Klipler arası ses seviyesi dalgalanmalarını önler ve konuşma netliğini maksimize eder.",
                "timestamp": 0.0,
                "duration": round(duration, 2),
                "confidence": 0.95,
                "category": "audio",
                "status": "pending",
                "payload": {
                    "action": "update_settings",
                    "settings": {
                        "normalizeAudio": True,
                        "audioEnhancement": True,
                    },
                },
            })

        logger.info(f"🎬 ProactiveDirector: {len(suggestions)} otonom yönetmen önerisi üretildi.")
        return suggestions[:6]
