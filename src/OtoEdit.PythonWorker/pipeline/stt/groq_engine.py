"""
OtoEdit Groq Whisper STT Motoru
- Groq Cloud API üzerinden ultra hızlı Whisper (whisper-large-v3-turbo) transkripsiyonu sağlar.
- Kelime zamanlarını doğrudan verbose_json word-level timestamps ile alır.
- Kota aşımında veya anahtar yoksa sonraki motora devredilir.
"""

import os
import json
import uuid
import urllib.request
import urllib.error
from typing import List
from config import Config
from pipeline.stt.base import BaseSTTEngine, Word
from pipeline.stt.chunker import AudioChunk
from utils.logger import get_logger

logger = get_logger("STT.Groq")


class GroqEngine(BaseSTTEngine):
    """Groq Cloud Whisper Motoru."""

    def __init__(self, api_key: str = None, model: str = "whisper-large-v3-turbo"):
        super().__init__(name="groq")
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def transcribe_chunk(self, chunk: AudioChunk) -> List[Word]:
        if not self.is_available():
            raise RuntimeError("Groq API anahtarı yapılandırılmamış.")
        if not chunk.audio_path or not os.path.exists(chunk.audio_path):
            return []

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"

        # Multipart form-data oluştur
        body = bytearray()

        def add_field(name: str, value: str):
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{value}\r\n".encode("utf-8"))

        add_field("model", self.model)
        add_field("response_format", "verbose_json")
        add_field("timestamp_granularities[]", "word")

        # Dosya alanı
        filename = os.path.basename(chunk.audio_path)
        with open(chunk.audio_path, "rb") as f:
            file_bytes = f.read()

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(b"Content-Type: audio/mpeg\r\n\r\n")
        body.extend(file_bytes)
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(
            url,
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "OtoEdit/1.0",
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            },
            method="POST"
        )

        try:
            logger.info(f"⚡ Groq Whisper isteği gönderiliyor (Parça {chunk.index}: {chunk.start_sec:.1f}s -> {chunk.end_sec:.1f}s)")
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            words: List[Word] = []
            for w in data.get("words", []):
                w_text = w.get("word", "").strip()
                if not w_text:
                    continue
                s_sec = float(w.get("start", 0.0))
                e_sec = float(w.get("end", s_sec + 0.1))

                words.append(Word(
                    word=w_text,
                    start=round(chunk.start_sec + s_sec, 3),
                    end=round(chunk.end_sec if e_sec > chunk.duration else chunk.start_sec + e_sec, 3),
                    confidence=1.0
                ))

            logger.info(f"✅ Groq Whisper tamamlandı (Parça {chunk.index}): {len(words)} kelime bulundu.")
            return words

        except urllib.error.HTTPError as he:
            err = he.read().decode("utf-8", errors="ignore")
            logger.warning(f"⚠️ Groq API HTTP {he.code} hatası: {err[:200]}")
            raise RuntimeError(f"Groq API hatası ({he.code}): {err[:200]}") from he
        except Exception as ex:
            logger.error(f"❌ Groq bağlantı hatası: {ex}")
            raise
