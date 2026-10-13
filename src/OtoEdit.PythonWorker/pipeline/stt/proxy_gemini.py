"""
OtoEdit Antigravity Proxy STT Motoru (Yedek)
- Yerel Antigravity Manager proxy (http://host.docker.internal:8045/v1) üzerinden
  gemini-3.8-flash modelini çağırır.
- Kelimeleri metin üzerinden ayrıştırıp konuşma aralığına orantılı dağıtır.
"""

import base64
import json
import urllib.request
import urllib.error
from typing import List
from config import Config
from pipeline.stt.base import BaseSTTEngine, Word
from pipeline.stt.chunker import AudioChunk
from utils.logger import get_logger

logger = get_logger("STT.ProxyGemini")


class ProxyGeminiEngine(BaseSTTEngine):
    """Antigravity Proxy Gemini Motoru."""

    def __init__(self, proxy_url: str = None, api_key: str = None, model: str = None):
        super().__init__(name="proxy_gemini")
        self.proxy_url = (proxy_url or Config.ANTIGRAVITY_PROXY_URL).rstrip("/")
        self.api_key = api_key or Config.ANTIGRAVITY_PROXY_KEY
        self.model = model or Config.ANTIGRAVITY_PROXY_MODEL

    def is_available(self) -> bool:
        return bool(self.proxy_url and self.api_key)

    def transcribe_chunk(self, chunk: AudioChunk) -> List[Word]:
        if not chunk.audio_path:
            return []

        url = f"{self.proxy_url}/chat/completions"
        with open(chunk.audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Lütfen bu sesteki tüm konuşmaları kelimesi kelimesine (verbatim) eksiksiz transkribe et. Başka hiçbir açıklama yazma, sadece konuşulan metni yaz."
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": "mp3"
                            }
                        }
                    ]
                }
            ]
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            logger.info(f"🌐 Antigravity Proxy STT isteği: Parça {chunk.index} ({self.model})")
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            raw_tokens = content.split()
            if not raw_tokens:
                return []

            # Kelimeleri parça süresi boyunca orantılı dağıt (Adım 3b)
            step = chunk.duration / max(1, len(raw_tokens))
            words: List[Word] = []
            for idx, tok in enumerate(raw_tokens):
                w_start = chunk.start_sec + (idx * step)
                w_end = min(chunk.end_sec, w_start + step * 0.9)
                words.append(Word(
                    word=tok,
                    start=round(w_start, 3),
                    end=round(w_end, 3),
                    confidence=0.85
                ))

            logger.info(f"✅ Antigravity Proxy STT tamamlandı: {len(words)} kelime.")
            return words

        except Exception as ex:
            logger.warning(f"⚠️ Antigravity Proxy çağrısı başarısız oldu: {ex}")
            raise
