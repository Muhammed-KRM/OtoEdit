import json
import re
from typing import List, Dict, Any
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Google Gemini API ile viral klip tespiti ve transkript zenginleştirme istemcisi."""

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = None

        if self.api_key:
            try:
                import importlib
                genai = importlib.import_module("google.generativeai")
                genai.configure(api_key=self.api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Gemini API istemcisi başarıyla yapılandırıldı. Model: {model_name}")
            except Exception as e:
                logger.warning(f"Gemini API başlatılamadı, fallback modu kullanılacak: {e}")
        else:
            logger.warning("GEMINI_API_KEY tanımlı değil. Fallback motoru aktif.")

    def find_viral_clips(self, transcript_text: str, duration: float) -> List[Dict[str, Any]]:
        """Transkriptten en viral 30sn (Reels) ve 90sn (Shorts) bölümleri çıkarır."""
        if not self.model or not transcript_text.strip():
            return self._fallback_viral_clips(duration)

        prompt = f"""
        Aşağıdaki video transkriptini analiz et ve sosyal medya için en dikkat çekici kısımları seç.
        Videonun toplam süresi: {duration:.1f} saniye.

        İstenen Çıktılar:
        1. Reels / TikTok için en vurucu ardışık yaklaşık 30 saniyelik bir bölüm (targetFormat: "9:16").
        2. YouTube Shorts için en bilgilendirici ardışık yaklaşık 60-90 saniyelik bir bölüm (targetFormat: "9:16").

        Yanıtını SADECE ve kesinlikle aşağıdaki JSON formatında ver:
        [
          {{
            "id": "clip_reels_1",
            "title": "Vurucu Başlık",
            "start": 12.0,
            "end": 42.0,
            "duration": 30.0,
            "targetFormat": "9:16",
            "viralityScore": 95,
            "reason": "Konuşmacının en duygusal ve merak uyandıran cümlesi burada."
          }},
          {{
            "id": "clip_shorts_1",
            "title": "Detaylı Açıklama",
            "start": 60.0,
            "end": 145.0,
            "duration": 85.0,
            "targetFormat": "9:16",
            "viralityScore": 88,
            "reason": "Kavramın ana tanımı ve pratik tavsiye burada veriliyor."
          }}
        ]

        Transkript:
        {transcript_text[:10000]}
        """

        try:
            response = self.model.generate_content(prompt)
            clean_json = self._extract_json(response.text)
            parsed = json.loads(clean_json)
            if isinstance(parsed, list):
                logger.info(f"Gemini {len(parsed)} viral klip tespit etti.")
                return parsed
        except Exception as e:
            logger.error(f"Gemini viral klip analiz hatası: {e}", exc_info=True)

        return self._fallback_viral_clips(duration)

    def generate_content_suggestions(self, transcript_text: str, duration: float) -> List[Dict[str, Any]]:
        """Transkriptten B-Roll görsel ve vurgu metin önerileri üretir."""
        if not self.model or not transcript_text.strip():
            return self._fallback_suggestions(duration)

        prompt = f"""
        Aşağıdaki video transkriptini incele. Video kurgusunu zenginleştirmek için:
        1. Somut kavramlar, nesneler veya metaforlar geçtiğinde ("image_broll" tipi - Pexels araması için İngilizce arama anahtar kelimesi ile)
        2. Kilit tavsiyeler, aforizmalar veya dikkat çekici cümleler için ("text_callout" tipi - Türkçe vurgu yazısı)
        öneriler üret.

        Yanıtını SADECE ve kesinlikle aşağıdaki JSON dizisi formatında ver:
        [
          {{
            "id": "sug_1",
            "type": "image_broll",
            "title": "Yapay Zeka Görseli",
            "content": "artificial intelligence neural network",
            "timestamp": 15.0,
            "duration": 4.0,
            "reason": "Konuşmacı yapay zekadan bahsediyor.",
            "status": "pending"
          }},
          {{
            "id": "sug_2",
            "type": "text_callout",
            "title": "Kilit Vurgu",
            "content": "Sabır başarının anahtarıdır!",
            "timestamp": 45.0,
            "duration": 5.0,
            "reason": "Konuşmadaki ana mesaj.",
            "status": "pending"
          }}
        ]

        Transkript:
        {transcript_text[:10000]}
        """

        try:
            response = self.model.generate_content(prompt)
            clean_json = self._extract_json(response.text)
            parsed = json.loads(clean_json)
            if isinstance(parsed, list):
                logger.info(f"Gemini {len(parsed)} akıllı öneri üretti.")
                return parsed
        except Exception as e:
            logger.error(f"Gemini öneri üretim hatası: {e}", exc_info=True)

        return self._fallback_suggestions(duration)

    @staticmethod
    def _extract_json(text: str) -> str:
        """Markdown kod bloklarını temizleyerek saf JSON çıkarır."""
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1).strip()
        return text.strip()

    @staticmethod
    def _fallback_viral_clips(duration: float) -> List[Dict[str, Any]]:
        """API olmadığında veya hata durumunda zaman temelli güvenli klip üretir."""
        clips = []
        if duration >= 30.0:
            clips.append({
                "id": "clip_reels_auto",
                "title": "Öne Çıkan An (Reels)",
                "start": 0.0,
                "end": min(30.0, duration),
                "duration": min(30.0, duration),
                "targetFormat": "9:16",
                "viralityScore": 85,
                "reason": "Videonun açılış bölümü."
            })
        if duration >= 90.0:
            clips.append({
                "id": "clip_shorts_auto",
                "title": "Genişletilmiş Bölüm (Shorts)",
                "start": 0.0,
                "end": min(90.0, duration),
                "duration": min(90.0, duration),
                "targetFormat": "9:16",
                "viralityScore": 80,
                "reason": "Videonun ilk 90 saniyesi."
            })
        return clips

    @staticmethod
    def _fallback_suggestions(duration: float) -> List[Dict[str, Any]]:
        return []
