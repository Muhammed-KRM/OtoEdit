import os
import json
import re
import time
from typing import List, Dict, Any, Optional
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


import urllib.request
import urllib.error

class GeminiClient:
    """Google Gemini API ve Antigravity Proxy ile viral klip tespiti ve transkript zenginleştirme istemcisi."""

    def __init__(self):
        self.proxy_url = getattr(Config, "ANTIGRAVITY_PROXY_URL", "http://host.docker.internal:8045/v1").rstrip("/")
        self.proxy_key = getattr(Config, "ANTIGRAVITY_PROXY_KEY", "")
        self.proxy_model = getattr(Config, "ANTIGRAVITY_PROXY_MODEL", "gemini-3.8-flash-tiered")
        self.api_key = Config.GEMINI_API_KEY
        self.model = None

        if self.proxy_key and self.proxy_url:
            self.use_proxy = True
            logger.info(f"🌐 Antigravity Proxy istemcisi yapılandırıldı: {self.proxy_url} (Model: {self.proxy_model})")
        elif self.api_key:
            self.use_proxy = False
            try:
                import importlib
                genai = importlib.import_module("google.generativeai")
                genai.configure(api_key=self.api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Gemini API istemcisi başarıyla yapılandırıldı. Model: {model_name}")
            except Exception as e:
                logger.warning(f"Gemini API başlatılamadı, fallback modu kullanılacak: {e}")
        else:
            self.use_proxy = False
            logger.warning("Ne ANTIGRAVITY_PROXY_KEY ne de GEMINI_API_KEY tanımlı. Fallback motoru aktif.")

    def _execute_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Ağ veya Rate Limit durumlarında Exponential Backoff ile tekrar dener."""
        delay = 2.0
        if getattr(self, "use_proxy", False):
            url = f"{self.proxy_url}/chat/completions"
            payload = {
                "model": self.proxy_model,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.proxy_key}"
            }
            for attempt in range(1, max_retries + 1):
                try:
                    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content
                except Exception as ex:
                    logger.warning(f"Antigravity Proxy çağrı denemesi #{attempt} başarısız: {ex}")
                    if attempt < max_retries:
                        time.sleep(delay)
                        delay *= 2.0
                    else:
                        logger.error(f"Antigravity Proxy tüm denemeler ({max_retries}) tükendi: {ex}")
            return None

        if not self.model:
            return None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.model.generate_content(prompt)
                if response and hasattr(response, "text"):
                    return response.text
                return None
            except Exception as ex:
                logger.warning(f"Gemini API çağrı denemesi #{attempt} başarısız: {ex}")
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    logger.error(f"Gemini API tüm denemeler ({max_retries}) tükendi: {ex}")
        return None

    def is_available(self) -> bool:
        """Gemini API veya Antigravity Proxy aktif mi kontrol eder."""
        return bool(self.model or getattr(self, "use_proxy", False))

    def generate_text(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Genel metin/prompt üretimi için Gemini veya Antigravity Proxy'yi çağırır."""
        if not self.is_available():
            return None
        return self._execute_with_retry(prompt, max_retries=max_retries)

    def generate_vision(self, prompt: str, image_path: str, max_retries: int = 2) -> Optional[str]:
        """Bir görsel dosyası (veya ekran görüntüsü) ile birlikte multimodal VLM analizi yapar."""
        if not self.is_available() or not image_path or not os.path.exists(image_path):
            return None
        import base64
        try:
            with open(image_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(image_path)[1].lower()
            mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")

            if getattr(self, "use_proxy", False):
                url = f"{self.proxy_url}/chat/completions"
                payload = {
                    "model": self.proxy_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_img}"}},
                            ],
                        }
                    ],
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.proxy_key}",
                }
                for attempt in range(1, max_retries + 1):
                    try:
                        req = urllib.request.Request(
                            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                        )
                        with urllib.request.urlopen(req, timeout=45) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    except Exception as ex:
                        logger.warning(f"Vision Proxy denemesi #{attempt} başarısız: {ex}")
                        if attempt < max_retries:
                            time.sleep(1.5)
                return None

            if self.model:
                from PIL import Image
                with Image.open(image_path) as img:
                    response = self.model.generate_content([prompt, img])
                    if response and hasattr(response, "text"):
                        return response.text
        except Exception as e:
            logger.warning(f"generate_vision hatası: {e}")
        return None

    def find_viral_clips(self, transcript_text: str, duration: float) -> List[Dict[str, Any]]:
        """Transkriptten en viral 30sn (Reels) ve 90sn (Shorts) bölümleri çıkarır."""
        if not self.is_available() or not transcript_text.strip():
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
            raw_text = self._execute_with_retry(prompt)
            if raw_text:
                parsed = self._safe_parse_json(raw_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    logger.info(f"Gemini {len(parsed)} viral klip tespit etti.")
                    return parsed
        except Exception as e:
            logger.error(f"Gemini viral klip analiz hatası: {e}", exc_info=True)

        return self._fallback_viral_clips(duration)

    def generate_content_suggestions(self, transcript_text: str, duration: float) -> List[Dict[str, Any]]:
        """Transkriptten B-Roll görsel ve vurgu metin önerileri üretir."""
        if not self.is_available() or not transcript_text.strip():
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
            raw_text = self._execute_with_retry(prompt)
            if raw_text:
                parsed = self._safe_parse_json(raw_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    logger.info(f"Gemini {len(parsed)} akıllı öneri üretti.")
                    return parsed
        except Exception as e:
            logger.error(f"Gemini öneri üretim hatası: {e}", exc_info=True)

        return self._fallback_suggestions(duration)

    def audit_transcript_coherence(self, segments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transkripti anlamsal bütünlük, takılmalar (semantic retake),
        yarım kalan yetim cümle parçaları (orphaned fragments) ve
        montaj outtake'leri açısından denetler.
        Elenmesi önerilen segmentlerin listesini döndürür.
        """
        if not self.is_available() or not segments_data:
            return []

        compact_segments = [
            {
                "id": s.get("id"),
                "start": round(float(s.get("start", 0)), 2),
                "end": round(float(s.get("end", 0)), 2),
                "text": s.get("text", "").strip()
            }
            for s in segments_data
            if s.get("text", "").strip()
        ]

        if not compact_segments:
            return []

        prompt = f"""
Sen profesyonel bir video kurgu yönetmenisin. Aşağıda bir konuşmacının video kaydına ait transkript segmentleri yer almaktadır.
Görevin: Videonun nihai kurgusunda DİNLENME AKICILIĞINI BOZAN ve ATILMASI (kesilmesi) gereken segmentleri tespit etmektir.

Hangi durumları tespit edeceksin?
1. "semantic_retake": Konuşmacı bir cümleye başlamış fakat kekelemiş, takılmış veya vazgeçip aynı düşünceyi hemen sonraki cümlede (farklı kelimeler kullansa bile) yeniden söylemiş. İlk (başarısız/terk edilmiş) cümleyi ele.
2. "aborted_sentence": Cümleye başlanmış fakat bitirilmeden yarıda bırakılmış, havada kalmış (örn: "Biz burada aslında...", "Şimdi şey...").
3. "orphaned_fragment": Tek başına kalmış, hiçbir yere bağlanmayan bağlaç, takılma veya bozuk kelime kırıntısı.
4. "meta_speech": Konuşmacının montajcıya, kendine veya stüdyo ekibine söylediği sözler (örn: "Pardon baştan alıyorum", "Bunu montajda kesersiniz", "Slaytı göremedim").

KURALLAR:
- Başarılı, anlamlı ve tamamlanmış cümleleri KESİNLİKLE KESME. Şüphede kalırsan koru.
- Sadece açıkça elenmesi gereken hatalı veya yarım cümleleri listele.
- Yanıtını SADECE aşağıdaki JSON dizisi formatında ver:
[
  {{
    "id": 4,
    "reason": "semantic_retake",
    "description": "Cümle takılarak yarıda bırakılmış, sonraki cümlede düzeltilerek söylenmiş."
  }}
]

Transkript Segmentleri:
{json.dumps(compact_segments, ensure_ascii=False, indent=2)}
"""

        try:
            raw_text = self._execute_with_retry(prompt)
            if raw_text:
                parsed = self._safe_parse_json(raw_text)
                if isinstance(parsed, list):
                    logger.info(f"Gemini Kurgu Denetçisi {len(parsed)} elenecek segment tespit etti.")
                    return parsed
        except Exception as e:
            logger.error(f"Gemini kurgu denetim hatası: {e}", exc_info=True)

        return []


    @classmethod
    def _safe_parse_json(cls, text: str) -> Any:
        """Markdown ve format bozukluklarını temizleyerek güvenli JSON çözer."""
        cleaned = cls._extract_json(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Trailing comma veya ufak sözdizim hatalarını temizle
            fixed = re.sub(r',\s*([\]}])', r'\1', cleaned)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError as err:
                logger.error(f"JSON Çözme Hatası: {err}. Temizlenmiş Metin: {cleaned[:300]}")
                return None

    @staticmethod
    def _extract_json(text: str) -> str:
        """Markdown kod bloklarını veya metin içi JSON dizilerini ayıklar."""
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Doğrudan [ ... ] veya { ... } ara
        first_bracket = min(
            (text.find('['), text.find('{')),
            key=lambda x: x if x != -1 else float('inf')
        )
        if first_bracket != float('inf'):
            last_bracket = max(text.rfind(']'), text.rfind('}'))
            if last_bracket > first_bracket:
                return text[first_bracket:last_bracket + 1].strip()

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
