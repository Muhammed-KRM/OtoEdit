import os
import json
import re
import time
import socket
from typing import List, Dict, Any, Optional
from config import Config
from utils.logger import get_logger

# Asılı kalan dış API soketlerinin iş parçacıklarını sonsuza kadar bloke etmesini önle
socket.setdefaulttimeout(25.0)

logger = get_logger(__name__)


import urllib.request
import urllib.error

class GeminiClient:
    """Google Gemini API ve Antigravity Proxy ile viral klip tespiti ve transkript zenginleştirme istemcisi."""

    def __init__(self):
        self.proxy_url = getattr(Config, "ANTIGRAVITY_PROXY_URL", "http://host.docker.internal:8045/v1").rstrip("/")
        self.proxy_key = getattr(Config, "ANTIGRAVITY_PROXY_KEY", "")
        self.proxy_model = getattr(Config, "ANTIGRAVITY_PROXY_MODEL", "gemini-3.8-flash-tiered")
        self.openrouter_api_key = getattr(Config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "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")
        self.openrouter_base_url = getattr(Config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.openrouter_model = getattr(Config, "OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
        self.active_provider = getattr(Config, "AI_ACTIVE_PROVIDER", "antigravity")

        self._redis = None
        try:
            import redis
            self._redis = redis.Redis(
                host=getattr(Config, "REDIS_HOST", "redis"),
                port=int(getattr(Config, "REDIS_PORT", 6379)),
                password=getattr(Config, "REDIS_PASSWORD", None) or None,
                db=int(getattr(Config, "REDIS_DB", 0)),
                decode_responses=True,
                socket_timeout=1.5
            )
        except Exception:
            pass

        self.api_key = Config.GEMINI_API_KEY
        self.api_keys: List[str] = list(getattr(Config, "GEMINI_API_KEYS", []) or ([] if not self.api_key else [self.api_key]))
        self._key_idx = 0
        self.groq_api_key = getattr(Config, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        self.groq_api_keys: List[str] = list(getattr(Config, "GROQ_API_KEYS", []) or ([] if not self.groq_api_key else [self.groq_api_key]))
        self._groq_key_idx = 0
        self.groq_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        self.model = None
        self._genai = None
        self._proxy_dead = False
        self._gemini_dead = False

        self.use_proxy = bool(self.proxy_key and self.proxy_url)
        if self.use_proxy:
            logger.info(f"🌐 Antigravity Proxy istemcisi yapılandırıldı: {self.proxy_url} (Model: {self.proxy_model})")

        if self.api_keys:
            try:
                import importlib
                self._genai = importlib.import_module("google.generativeai")
                self._genai.configure(api_key=self.api_keys[0])
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                if "3.8" in model_name:
                    model_name = "gemini-2.5-flash"
                self.model_name = model_name
                self.model = self._genai.GenerativeModel(model_name)
                logger.info(f"Gemini API yedek istemcisi hazır ({len(self.api_keys)} anahtar, Model: {model_name})")
            except Exception as e:
                logger.warning(f"Gemini API başlatılamadı, diğer sağlayıcılar kullanılacak: {e}")

        if self.groq_api_key:
            logger.info("⚡ Groq Cloud LLM yedek istemcisi hazır (llama-3.3-70b-versatile).")

    def _call_groq_llm(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        """Groq Cloud OpenAI-uyumlu uç noktasını anahtar havuzu rotasyonuyla çağırır."""
        if not self.groq_api_keys:
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        for model_name in self.groq_models:
            active_key = self.groq_api_keys[self._groq_key_idx % len(self.groq_api_keys)]
            self._groq_key_idx += 1
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {active_key}",
                "User-Agent": "OtoEdit/2.0",
            }
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            try:
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    return content
            except Exception as ex:
                if "429" in str(ex):
                    time.sleep(1.2)
                logger.warning(f"Groq LLM ({model_name}) çağrısı başarısız: {ex}")
        return None

    def _get_active_provider_config(self) -> Dict[str, Any]:
        """Redis'ten veya Config'ten en güncel AI sağlayıcı ayarlarını alır."""
        provider = self.active_provider
        openrouter_key = self.openrouter_api_key
        openrouter_model = self.openrouter_model
        if self._redis:
            try:
                raw = self._redis.get("otoedit:settings:ai_provider")
                if raw:
                    data = json.loads(raw)
                    provider = data.get("ActiveProvider") or data.get("activeProvider") or provider
                    openrouter_key = data.get("OpenRouterApiKey") or data.get("openRouterApiKey") or openrouter_key
                    openrouter_model = data.get("OpenRouterModel") or data.get("openRouterModel") or openrouter_model
            except Exception:
                pass
        return {
            "provider": (provider or "antigravity").lower(),
            "openrouter_key": openrouter_key,
            "openrouter_model": openrouter_model
        }

    def _call_openrouter_llm(self, prompt: str, json_mode: bool = False, model: str = None, api_key: str = None) -> Optional[str]:
        """OpenRouter API uç noktasını çağırır."""
        key = api_key or self.openrouter_api_key
        if not key:
            return None
        url = f"{self.openrouter_base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://otoedit.local",
            "X-Title": "OtoEdit",
            "User-Agent": "OtoEdit/2.0",
            "Connection": "close"
        }
        payload: Dict[str, Any] = {
            "model": model or self.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            import requests
            resp = requests.post(url, headers=headers, json=payload, timeout=(5, 10))
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    return content
            else:
                logger.warning(f"OpenRouter LLM ({model or self.openrouter_model}) HTTP {resp.status_code}: {resp.text[:150]}")
        except Exception as ex:
            logger.warning(f"OpenRouter LLM ({model or self.openrouter_model}) çağrısı başarısız: {ex}")
        return None

    def _execute_with_retry(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Aktif sağlayıcıya (OpenRouter / Antigravity Proxy) göre LLM çağrısını gerçekleştirir."""
        cfg = self._get_active_provider_config()
        active_provider = cfg["provider"]

        # 1. Eğer OpenRouter aktifse öncelikle OpenRouter'a gönder
        if active_provider == "openrouter":
            res = self._call_openrouter_llm(prompt, model=cfg["openrouter_model"], api_key=cfg["openrouter_key"])
            if res:
                return res

        # 2. Antigravity Proxy (aktifse veya OpenRouter fallback olarak)
        if getattr(self, "use_proxy", False) and not self._proxy_dead:
            url = f"{self.proxy_url}/chat/completions"
            payload = {
                "model": self.proxy_model,
                "messages": [{"role": "user", "content": prompt}],
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.proxy_key}",
                "Connection": "close",
            }
            try:
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    return content
            except Exception as ex:
                logger.warning(f"Antigravity Proxy erişilemez ({ex}); devre kesici aktif, yedek sağlayıcıya geçiliyor.")
                self._proxy_dead = True

        # 2.1. Eğer Antigravity aktifken başarısız olduysa ve OpenRouter tanımlıysa OpenRouter dene
        if active_provider != "openrouter" and cfg["openrouter_key"]:
            res = self._call_openrouter_llm(prompt, model=cfg["openrouter_model"], api_key=cfg["openrouter_key"])
            if res:
                return res

        # 3. Hızlı Groq Cloud LLM Yedeği
        if self.groq_api_key:
            groq_res = self._call_groq_llm(prompt)
            if groq_res:
                return groq_res

        # 3. Gemini API Anahtar Havuzu Rotasyonu
        if self._gemini_dead or not self.model or not self._genai or not self.api_keys:
            return None

        delay = 1.5
        total_attempts = max(max_retries, min(len(self.api_keys), 4))
        for attempt in range(1, total_attempts + 1):
            try:
                key = self.api_keys[self._key_idx % len(self.api_keys)]
                self._key_idx += 1
                self._genai.configure(api_key=key)
                self.model = self._genai.GenerativeModel(getattr(self, "model_name", "gemini-2.5-flash"))
                response = self.model.generate_content(prompt)
                if response and hasattr(response, "text"):
                    return response.text
            except Exception as ex:
                logger.warning(f"Gemini API denemesi #{attempt} başarısız: {ex}")
                if "API_KEY_INVALID" in str(ex) and attempt >= len(self.api_keys):
                    self._gemini_dead = True
                    break
                if attempt < total_attempts:
                    time.sleep(delay)
        return None

    def is_available(self) -> bool:
        """Gemini API, Groq LLM, OpenRouter veya Antigravity Proxy aktif mi kontrol eder."""
        cfg = self._get_active_provider_config()
        has_openrouter = bool(cfg.get("openrouter_key"))
        return bool(self.model or self.groq_api_key or has_openrouter or (getattr(self, "use_proxy", False) and not self._proxy_dead))

    def generate_text(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Genel metin/prompt üretimi için aktif LLM sağlayıcısını çağırır."""
        if not self.is_available():
            return None
        return self._execute_with_retry(prompt, max_retries=max_retries)

    def generate_json(self, prompt: str, max_retries: int = 2) -> Any:
        """Yapılandırılmış JSON yanıtı üretir ve güvenli şekilde parse eder."""
        raw = self.generate_text(prompt, max_retries=max_retries)
        if not raw:
            return None
        return self._safe_parse_json(raw)

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

    def verify_image_with_vision(
        self,
        image_path: str,
        concept_title: str,
        spoken_context: str,
        theme_display_name: str = "Akademik Ders",
    ) -> Optional[Dict[str, Any]]:
        """
        İndirilen görseli Base64 olarak Multimodal VLM'e göndererek görselde tam olarak
        ne olduğunu, barkodlu/boş kapak olup olmadığını ve aranan kişi/eserle gerçekten
        ilgili olup olmadığını doğrular.
        """
        if not self.is_available() or not image_path or not os.path.exists(image_path):
            return None
        prompt = (
            f"Video Teması: {theme_display_name}\n"
            f"Aranan Kişi/Eser/Kavram: {concept_title}\n"
            f"Konuşmacının Cümlesi: {spoken_context}\n\n"
            "Bu görseli dikkatlice incele ve şu soruları yanıtla:\n"
            "1. Görselde tam olarak ne görünüyor? (literal_description)\n"
            "2. Görsel simsiyah/boş bir kitap kapağı, kütüphane barkod etiketi, okunaksız belge taraması veya filigranlı stok görsel mi? (is_blank_cover_or_barcode: true/false)\n"
            "3. Görsel izleyiciye gerçekten aranan kişi/eser/kavramı ({concept_title}) doğru ve anlamlı biçimde temsil ediyor mu? (matches_target_entity: true/false)\n"
            "4. 0-100 arası uygunluk puanı (weighted_score). Eğer barkodlu kapak, boş cilt veya alakasız bir görsel ise fatal_veto: true ve weighted_score: 0 ver.\n"
            "SADECE JSON döndür:\n"
            '{"literal_description": "...", "is_blank_cover_or_barcode": false, "matches_target_entity": true, "weighted_score": 88, "fatal_veto": false, "mask_shape": "rounded", "remove_bg": false}'
        )
        raw = self.generate_vision(prompt, image_path, max_retries=1)
        if not raw:
            return None
        parsed = self._safe_parse_json(raw)
        return parsed if isinstance(parsed, dict) else None

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
