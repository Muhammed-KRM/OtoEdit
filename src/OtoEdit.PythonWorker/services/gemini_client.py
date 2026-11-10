import os
import json
import re
import time
import socket
from typing import List, Dict, Any, Optional
from config import Config
from utils.logger import get_logger

# Asılı kalan dış API soketlerinin iş parçacıklarını sonsuza kadar bloke etmesini önle
socket.setdefaulttimeout(90.0)

logger = get_logger(__name__)


import urllib.request
import urllib.error
import threading

class GeminiClient:
    """Google Gemini API ve Antigravity Proxy ile viral klip tespiti ve transkript zenginleştirme istemcisi."""

    _global_project_id: Optional[str] = None
    _proxy_lock = threading.Lock()
    _last_proxy_call_ts: float = 0.0

    def __init__(self):
        self.current_project_id: Optional[str] = None
        self.proxy_url = getattr(Config, "ANTIGRAVITY_PROXY_URL", "http://host.docker.internal:8045/v1").rstrip("/")
        self.proxy_key = getattr(Config, "ANTIGRAVITY_PROXY_KEY", "")
        self.proxy_model = getattr(Config, "ANTIGRAVITY_PROXY_MODEL", "gemini-3.8-flash-tiered")
        self.openrouter_api_key = getattr(Config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_base_url = getattr(Config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.openrouter_model = getattr(Config, "OPENROUTER_MODEL", "google/gemini-2.5-flash")
        self.active_provider = getattr(Config, "AI_ACTIVE_PROVIDER", "antigravity")

        self._redis = None
        self._redis_checked = False

        self.api_key = Config.GEMINI_API_KEY
        self.api_keys: List[str] = list(getattr(Config, "GEMINI_API_KEYS", []) or ([] if not self.api_key else [self.api_key]))
        self._key_idx = 0
        self.groq_api_key = getattr(Config, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        self.groq_api_keys: List[str] = list(getattr(Config, "GROQ_API_KEYS", []) or ([] if not self.groq_api_key else [self.groq_api_key]))
        self._groq_key_idx = 0
        self.groq_models = [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b",
            "llama-3.1-8b-instant",
        ]
        self.model = None
        self._genai = None
        self._proxy_dead = False
        self._proxy_fail_count = 0
        self._proxy_disabled_until = 0.0
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
                if "3.8" in model_name or "3.5" in model_name:
                    model_name = "gemini-2.5-flash"
                self.model_name = model_name
                self.model = self._genai.GenerativeModel(model_name)
                logger.info(f"Gemini API yedek istemcisi hazır ({len(self.api_keys)} anahtar, Model: {model_name})")
            except Exception as e:
                logger.warning(f"Gemini API başlatılamadı, diğer sağlayıcılar kullanılacak: {e}")

        if self.groq_api_key:
            logger.info("⚡ Groq Cloud LLM yedek istemcisi hazır (llama-3.3-70b-versatile, qwen/qwen3.8-27b, openai/gpt-oss-120b).")

    def _call_groq_llm(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        """Groq Cloud OpenAI-uyumlu uç noktasını anahtar ve model havuzu rotasyonuyla çağırır."""
        if not self.groq_api_keys or time.time() < getattr(self, "_groq_disabled_until", 0.0):
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        start_m_idx = getattr(self, "_groq_model_idx", 0)
        for offset in range(len(self.groq_models)):
            model_name = self.groq_models[(start_m_idx + offset) % len(self.groq_models)]
            active_key = self.groq_api_keys[self._groq_key_idx % len(self.groq_api_keys)]
            self._groq_key_idx += 1
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {active_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    self._groq_model_idx = (start_m_idx + offset + 1) % len(self.groq_models)
                    return content
            except Exception as ex:
                logger.warning(f"Groq LLM ({model_name}) çağrısı başarısız: {ex}")
                if "429" in str(ex):
                    time.sleep(2.5)
        return None

    def _get_redis(self):
        if getattr(self, "_redis_checked", False) and self._redis is not None:
            return self._redis
        self._redis_checked = True
        try:
            import redis
            r = redis.Redis(
                host=getattr(Config, "REDIS_HOST", "redis"),
                port=int(getattr(Config, "REDIS_PORT", 6379)),
                password=getattr(Config, "REDIS_PASSWORD", None) or None,
                db=int(getattr(Config, "REDIS_DB", 0)),
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            r.ping()
            self._redis = r
        except Exception:
            self._redis = None
        return self._redis

    def _get_active_provider_config(self) -> Dict[str, Any]:
        """Redis'ten veya Config'ten en güncel AI sağlayıcı ayarlarını alır."""
        provider = self.active_provider
        openrouter_key = self.openrouter_api_key
        openrouter_model = self.openrouter_model
        proxy_url = self.proxy_url
        proxy_key = self.proxy_key
        proxy_model = self.proxy_model

        r = self._get_redis()
        if r:
            try:
                raw = r.get("otoedit:settings:ai_provider")
                if raw:
                    data = json.loads(raw)
                    provider = data.get("ActiveProvider") or data.get("activeProvider") or provider
                    openrouter_key = data.get("OpenRouterApiKey") or data.get("openRouterApiKey") or openrouter_key
                    openrouter_model = data.get("OpenRouterModel") or data.get("openRouterModel") or openrouter_model
                    proxy_url = data.get("AntigravityProxyUrl") or data.get("antigravityProxyUrl") or proxy_url
                    proxy_key = data.get("AntigravityProxyKey") or data.get("antigravityProxyKey") or proxy_key
                    proxy_model = data.get("AntigravityProxyModel") or data.get("antigravityProxyModel") or proxy_model
            except Exception:
                pass

        # Docker içinde localhost:8045 veya 127.0.0.1:8045 gelirse host.docker.internal'a dönüştür
        if proxy_url and ("localhost" in proxy_url or "127.0.0.1" in proxy_url):
            proxy_url = proxy_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")

        return {
            "provider": (provider or "antigravity").lower(),
            "openrouter_key": openrouter_key,
            "openrouter_model": openrouter_model,
            "proxy_url": proxy_url.rstrip("/"),
            "proxy_key": proxy_key,
            "proxy_model": proxy_model or "gemini-3.8-flash-tiered",
        }

    def _call_openrouter_llm(self, prompt: str, json_mode: bool = False, model: str = None, api_key: str = None) -> Optional[str]:
        """OpenRouter API uç noktasını çağırır (22s sert zaman aşımı ile kilitlenmeye karşı korunmuştur)."""
        key = api_key or self.openrouter_api_key
        if not key or time.time() < max(getattr(self, "_openrouter_disabled_until", 0.0), getattr(GeminiClient, "_class_openrouter_disabled_until", 0.0)):
            return None
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            fut = pool.submit(self._do_call_openrouter, prompt, json_mode, model, key)
            return fut.result(timeout=22.0)
        except TimeoutError:
            logger.warning(f"OpenRouter LLM ({model or self.openrouter_model}) sert zaman aşımı (22s) aşıldı, güvenle atlanıyor.")
            return None
        except Exception as ex:
            logger.warning(f"OpenRouter LLM ({model or self.openrouter_model}) çağrısı başarısız: {ex}")
            return None
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _do_call_openrouter(self, prompt: str, json_mode: bool, model: Optional[str], key: str) -> Optional[str]:
        url = f"{self.openrouter_base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://otoedit.local",
            "X-Title": "OtoEdit",
            "User-Agent": "OtoEdit/2.0",
            "Connection": "close"
        }
        target_model = model or self.openrouter_model
        if target_model and ("gemini-3.8" in target_model or "gemini-2.0-flash" in target_model):
            target_model = "google/gemini-2.5-flash"
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        # Düşünce/Reasoning modellerinin (ling, r1, thinking) dakikalarca iç ses üretip takılmasını önle
        cur_model = (target_model or "").lower()
        if any(rm in cur_model for rm in ("ling", "r1", "reason", "thinking", "qwq")):
            payload["reasoning"] = {"max_tokens": 0}
        try:
            try:
                import requests
                resp = requests.post(url, headers=headers, json=payload, timeout=(5, 20))
                status_code = resp.status_code
                data = resp.json() if status_code == 200 else {}
                err_txt = resp.text[:150] if status_code != 200 else ""
            except ImportError:
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=20) as u_resp:
                    status_code = u_resp.status
                    data = json.loads(u_resp.read().decode("utf-8"))
                    err_txt = ""
            if status_code == 200:
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content") or ""
                # Eğer model içeriği boş bırakıp sadece reasoning ürettiyse kurtar
                if not content and msg.get("reasoning"):
                    reasoning_text = msg.get("reasoning", "").strip()
                    if json_mode and "{" in reasoning_text:
                        s_idx = reasoning_text.find("{")
                        e_idx = reasoning_text.rfind("}")
                        if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
                            content = reasoning_text[s_idx:e_idx + 1]
                    elif not json_mode:
                        content = reasoning_text[-600:].strip()
                if content:
                    return content
            else:
                logger.warning(f"OpenRouter LLM ({target_model}) HTTP {status_code}: {err_txt}")
                if status_code in (401, 402, 403):
                    self._openrouter_disabled_until = time.time() + 600.0
                    GeminiClient._class_openrouter_disabled_until = time.time() + 600.0
        except Exception as ex:
            logger.warning(f"OpenRouter LLM ({target_model}) çağrısı başarısız: {ex}")
            if "401" in str(ex) or "402" in str(ex):
                self._openrouter_disabled_until = time.time() + 600.0
                GeminiClient._class_openrouter_disabled_until = time.time() + 600.0
        return None

    def _call_direct_gemini(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Google Gemini API çağrısı (google.generativeai veya doğrudan REST)."""
        if self._gemini_dead or not self.api_keys or time.time() < max(getattr(self, "_gemini_disabled_until", 0.0), getattr(GeminiClient, "_class_gemini_disabled_until", 0.0)):
            return None
        delay = 1.0
        total_attempts = max(max_retries, min(len(self.api_keys), 3))
        for attempt in range(1, total_attempts + 1):
            try:
                key = self.api_keys[self._key_idx % len(self.api_keys)]
                self._key_idx += 1
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
                pdata = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=pdata, headers={"Content-Type": "application/json"}, method="POST")
                import ssl
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    rdata = json.loads(resp.read().decode("utf-8"))
                    cand = rdata.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if cand:
                        return cand
            except Exception as ex:
                logger.warning(f"Direct Gemini API denemesi #{attempt} başarısız: {ex}")
                if any(k in str(ex) for k in ("402", "429", "depleted", "RESOURCE_EXHAUSTED", "quota")):
                    logger.warning("Gemini API kredisi/kotası tükenmiş (429/402). Yedek sağlayıcıya geçiliyor.")
                    self._gemini_disabled_until = time.time() + 600.0
                    GeminiClient._class_gemini_disabled_until = time.time() + 600.0
                    break
                if attempt < total_attempts:
                    time.sleep(delay)
        return None

    def is_fallback_requested(self) -> bool:
        """Kullanıcının bu proje için kural tabanlı yedek motora geçiş talep edip etmediğini kontrol eder."""
        pid = self.current_project_id or getattr(GeminiClient, "_global_project_id", None)
        if not pid:
            return False
        r = self._get_redis()
        if not r:
            return False
        try:
            return bool(r.get(f"project:{pid}:force_fallback"))
        except Exception:
            return False

    def _call_antigravity_proxy(self, prompt: str, cfg: Optional[Dict[str, Any]] = None, timeout: float = 6.0) -> Optional[str]:
        """Antigravity CLI / Manager yerel API Proxy'sini sıralı kilit ve model yedeklemesi altında çağırır."""
        if time.time() < max(getattr(self, "_proxy_disabled_until", 0.0), getattr(GeminiClient, "_class_proxy_disabled_until", 0.0)):
            return None
        cfg = cfg or self._get_active_provider_config()
        p_url = cfg.get("proxy_url") or self.proxy_url
        p_key = cfg.get("proxy_key") or self.proxy_key

        if not p_url or not p_key:
            return None

        cand_model = getattr(GeminiClient, "_working_proxy_model", None) or "claude-sonnet-5-5-low"

        url = f"{p_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {p_key}",
            "Connection": "close",
        }
        with GeminiClient._proxy_lock:
            if time.time() < max(getattr(self, "_proxy_disabled_until", 0.0), getattr(GeminiClient, "_class_proxy_disabled_until", 0.0)):
                return None
            elapsed = time.time() - getattr(GeminiClient, "_last_proxy_call_ts", 0.0)
            if elapsed < 0.25:
                time.sleep(0.25 - elapsed)
            payload = {
                "model": cand_model,
                "messages": [{"role": "user", "content": prompt}],
            }
            try:
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=min(timeout, 6.0)) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                GeminiClient._last_proxy_call_ts = time.time()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    GeminiClient._working_proxy_model = cand_model
                    self._proxy_fail_count = 0
                    self._proxy_dead = False
                    return content
            except Exception as ex:
                GeminiClient._last_proxy_call_ts = time.time()
                logger.warning(f"Antigravity Proxy ({cand_model}) çağrı uyarısı: {ex}")
                self._proxy_disabled_until = time.time() + 180.0
                GeminiClient._class_proxy_disabled_until = time.time() + 180.0
        return None

    def _execute_with_retry(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Aktif sağlayıcıya göre LLM çağrısını gerçekleştirir (Antigravity Proxy / Groq / Gemini / OpenRouter)."""
        cfg = self._get_active_provider_config()
        active_provider = cfg["provider"]

        # Kullanıcı arayüzden kural motoruna geçiş istediyse doğrudan None dön
        if self.is_fallback_requested():
            logger.warning("⚡ Kullanıcı 'Yedek Kural Motoruna Geç' talep etti; LLM çağrısı atlanıyor.")
            return None

        # 1. Antigravity Proxy (hızlı çağrı + gecikirse anında yedek AI zincirine geçiş)
        if active_provider == "antigravity":
            res = self._call_antigravity_proxy(prompt, cfg=cfg, timeout=24.0)
            if res:
                return res
            if self.is_fallback_requested():
                return None

        # 2. Eğer Groq aktifse doğrudan Groq'a gönder (yüksek hız, güvenilir)
        if active_provider == "groq" and self.groq_api_key:
            res = self._call_groq_llm(prompt)
            if res:
                return res

        # 3. Eğer Gemini doğrudan aktifse
        if active_provider in ("gemini", "google") and self.api_keys:
            res = self._call_direct_gemini(prompt, max_retries=max_retries)
            if res:
                return res

        # 4. Eğer OpenRouter aktifse
        if active_provider == "openrouter":
            res = self._call_openrouter_llm(prompt, model=cfg["openrouter_model"], api_key=cfg["openrouter_key"])
            if res:
                return res

        # --- YEDEK YAPAY ZEKA ZİNCİRİ (AI FALLBACK CHAIN) ---
        # Birincil sağlayıcı zaman aşımına uğrarsa veya hız sınırına (429) takılırsa kural motoruna düşmek yerine diğer AI sağlayıcılarını dener
        if not self.is_fallback_requested():
            # Groq yedeği
            if self.groq_api_key and active_provider != "groq":
                groq_res = self._call_groq_llm(prompt)
                if groq_res:
                    return groq_res

            # Gemini doğrudan yedeği
            if self.api_keys and active_provider not in ("gemini", "google"):
                gemini_res = self._call_direct_gemini(prompt, max_retries=max_retries)
                if gemini_res:
                    return gemini_res

            # OpenRouter yedeği
            if cfg.get("openrouter_key") and active_provider != "openrouter":
                res = self._call_openrouter_llm(prompt, model=cfg["openrouter_model"], api_key=cfg["openrouter_key"])
                if res:
                    return res

        return None

    def is_available(self) -> bool:
        """Gemini API, Groq LLM, OpenRouter veya Antigravity Proxy aktif mi kontrol eder."""
        cfg = self._get_active_provider_config()
        has_proxy = bool(cfg.get("proxy_key") and cfg.get("proxy_url") and not getattr(self, "_proxy_dead", False))
        has_openrouter = bool(cfg.get("openrouter_key"))
        return bool(self.model or self.groq_api_key or has_openrouter or has_proxy)

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

            cfg = self._get_active_provider_config()
            active_provider = cfg["provider"]

            def _try_openrouter_vision() -> Optional[str]:
                or_key = cfg.get("openrouter_key") or self.openrouter_api_key
                if not or_key:
                    return None
                or_model = cfg.get("openrouter_model") or "google/gemini-2.5-flash"
                if "gemini-3.8" in or_model or "gemini-2.0-flash" in or_model:
                    or_model = "google/gemini-2.5-flash"
                url_or = f"{self.openrouter_base_url}/chat/completions"
                payload_or = {
                    "model": or_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_img}"}},
                            ],
                        }
                    ],
                    "temperature": 0.1,
                }
                headers_or = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {or_key}",
                    "HTTP-Referer": "https://otoedit.local",
                    "X-Title": "OtoEdit",
                    "Connection": "close",
                }
                try:
                    import requests
                    resp = requests.post(url_or, headers=headers_or, json=payload_or, timeout=(4, 12))
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content:
                            return content
                except Exception as ex:
                    logger.warning(f"OpenRouter Vision çağrısı başarısız: {ex}")
                return None

            if active_provider == "openrouter":
                or_res = _try_openrouter_vision()
                if or_res:
                    return or_res

            if (
                getattr(self, "use_proxy", False)
                and time.time() >= max(
                    getattr(self, "_vision_proxy_disabled_until", 0.0),
                    getattr(GeminiClient, "_class_vision_proxy_disabled_until", 0.0),
                    getattr(GeminiClient, "_class_proxy_disabled_until", 0.0),
                )
            ):
                p_url = cfg.get("proxy_url") or self.proxy_url
                p_key = cfg.get("proxy_key") or self.proxy_key
                url = f"{p_url}/chat/completions"
                v_model = "claude-sonnet-5-5-low"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {p_key}",
                    "Connection": "close",
                }
                payload = {
                    "model": v_model,
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
                try:
                    with GeminiClient._proxy_lock:
                        req = urllib.request.Request(
                            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                        )
                        with urllib.request.urlopen(req, timeout=8) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                    v_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if v_content:
                        return v_content
                except Exception as ex:
                    logger.warning(f"Vision Proxy ({v_model}) denemesi başarısız: {ex}")
                self._vision_proxy_disabled_until = time.time() + 180.0
                GeminiClient._class_vision_proxy_disabled_until = time.time() + 180.0

            if active_provider != "openrouter":
                or_res = _try_openrouter_vision()
                if or_res:
                    return or_res
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
            "2. Görsel simsiyah/boş bir kitap kapağı, kütüphane barkod etiketi veya filigranlı stok görsel mi? (is_blank_cover_or_barcode: true/false)\n"
            "   NOT: Eğer aranan kavram bir kitap, eser, Kur'an suresi/ayeti, el yazması, kanunname veya tarihsel belge ise; temiz hat/kaligrafi levhaları, mushaf/el yazması sayfaları ve orijinal kitap kapakları GEÇERLİDİR (is_blank_cover_or_barcode: false, matches_target_entity: true).\n"
            "   ÇOK ÖNEMLİ KİŞİ/PORTRE KURALI: Eğer aranan kavram bir kişi/düşünür/alim ise (örn. Nurettin Topçu, İmam Gazali, Bediüzzaman vb.), görselde o kişinin portresi/fotoğrafı/temsili çizimi OLMALIDIR! O kişinin adını taşıyan bir İLKOKUL, LİSE, OKUL BİNASI, ÖĞRENCİ GRUBU, BELEDİYE ETKİNLİĞİ veya BAŞKA BİR KİŞİ görseli KESİNLİKLE GEÇERSİZDİR (matches_target_entity: false, fatal_veto: true, weighted_score: 0)!\n"
            f"3. Görsel izleyiciye gerçekten aranan kişi/eser/kavramı ({concept_title}) doğru ve anlamlı biçimde temsil ediyor mu? (matches_target_entity: true/false)\n"
            "4. 0-100 arası uygunluk puanı (weighted_score). Eğer okul binası, öğrenci grubu, barkodlu kapak, boş cilt veya alakasız bir görsel ise fatal_veto: true ve weighted_score: 0 ver.\n"
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
    def extract_balanced_json(cls, text: str, prefer_array: bool = False) -> Optional[str]:
        """Metin içindeki <think>...</think> bloklarına ve [w12|1.4] gibi etiketlere takılmadan dengeli JSON dizisi veya nesnesi ayıklar."""
        if not text:
            return None
        # Reasoning modellerinin (<think>...</think>) düşünme blokları içindeki örnek JSON parçalarını atla
        cleaned_text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
        if "<think>" in cleaned_text.lower():
            think_end = cleaned_text.lower().rfind("</think>")
            if think_end != -1:
                cleaned_text = cleaned_text[think_end + 8 :].strip()
        if not cleaned_text:
            cleaned_text = text

        code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text, flags=re.IGNORECASE)
        search_targets = code_blocks + [cleaned_text]
        for target in search_targets:
            for start_pos, ch in enumerate(target):
                if ch not in ("[", "{"):
                    continue
                if prefer_array and ch != "[":
                    continue
                if ch == "[":
                    rest = target[start_pos + 1 :].lstrip()
                    if not rest or rest[0] not in ("{", "]", '"'):
                        continue
                elif ch == "{":
                    rest = target[start_pos + 1 :].lstrip()
                    if not rest or rest[0] not in ('"', "}"):
                        continue
                stack = []
                in_str = False
                esc = False
                for idx in range(start_pos, len(target)):
                    c = target[idx]
                    if esc:
                        esc = False
                        continue
                    if c == "\\" and in_str:
                        esc = True
                        continue
                    if c == '"':
                        in_str = not in_str
                        continue
                    if not in_str:
                        if c in ("[", "{"):
                            stack.append("]" if c == "[" else "}")
                        elif c in ("]", "}"):
                            if not stack or stack[-1] != c:
                                break
                            stack.pop()
                            if not stack:
                                cand = target[start_pos : idx + 1].strip()
                                fixed = re.sub(r",\s*([\]}])", r"\1", cand)
                                try:
                                    json.loads(fixed)
                                    return fixed
                                except json.JSONDecodeError:
                                    break
        return None

    @classmethod
    def _safe_parse_json(cls, text: str) -> Any:
        """Markdown ve format bozukluklarını temizleyerek güvenli JSON çözer."""
        balanced = cls.extract_balanced_json(text)
        if balanced:
            try:
                return json.loads(balanced)
            except json.JSONDecodeError:
                pass
        cleaned = cls._extract_json(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError as err:
                logger.error(f"JSON Çözme Hatası: {err}. Temizlenmiş Metin: {cleaned[:300]}")
                return None

    @classmethod
    def _extract_json(cls, text: str) -> str:
        """Markdown kod bloklarını veya metin içi JSON dizilerini ayıklar."""
        balanced = cls.extract_balanced_json(text)
        if balanced:
            return balanced

        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        first_bracket = min(
            (text.find("["), text.find("{")),
            key=lambda x: x if x != -1 else float("inf"),
        )
        if first_bracket != float("inf"):
            last_bracket = max(text.rfind("]"), text.rfind("}"))
            if last_bracket > first_bracket:
                return text[first_bracket : last_bracket + 1].strip()

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


extract_balanced_json = GeminiClient.extract_balanced_json

