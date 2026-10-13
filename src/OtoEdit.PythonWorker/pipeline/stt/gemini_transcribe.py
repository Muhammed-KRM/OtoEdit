"""
OtoEdit Gemini Transcribe Motoru
- Google'ın özel gemini-3.5-transcribe modelini doğrudan resmi REST API ile çağırır.
- Kelime zamanlarını VERBATIM modunda doğrudan API'den alır.
- DİL KODU GÖNDERİLMEZ (Bulgu 2: Dil kodu gönderildiğinde Arapça/yabancı ifadeler atlanıyordu).
- Anahtar rotasyonu ve 429 hız sınırlayıcısı ile tam entegredir.
"""

import base64
import json
import re
import time
import urllib.request
import urllib.error
from typing import List, Optional
from config import Config
from pipeline.stt.base import BaseSTTEngine, Word, parse_offset_sec
from pipeline.stt.chunker import AudioChunk
from pipeline.stt.rate_limiter import GeminiKeyRotator
from utils.logger import get_logger

logger = get_logger("STT.GeminiTranscribe")


class GeminiTranscribeEngine(BaseSTTEngine):
    """Google Gemini 3.5 Transcribe resmi motoru."""

    def __init__(self, api_keys: List[str] = None, rotator: GeminiKeyRotator = None):
        super().__init__(name="gemini_transcribe")
        keys = api_keys or Config.GEMINI_API_KEYS
        self.rotator = rotator or GeminiKeyRotator(
            api_keys=keys,
            max_rpm=Config.GEMINI_TRANSCRIBE_RPM,
            max_wait_sec=45.0
        )

    def is_available(self) -> bool:
        return bool(self.rotator.keys)

    def parse_response(self, data: dict, chunk_offset: float = 0.0) -> List[Word]:
        """Gemini API JSON yanıtından kelimeleri ve mutlak zamanları ayrıştırır."""
        words: List[Word] = []

        candidates = data.get("candidates", [])
        if not candidates:
            return words

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return words

        # 1. audioTranscription.words aranır
        raw_words = []
        for p in parts:
            at = p.get("audioTranscription", {})
            if "words" in at and isinstance(at["words"], list):
                raw_words = at["words"]
                break
            if "words" in p and isinstance(p["words"], list):
                raw_words = p["words"]
                break

        for item in raw_words:
            w_text = item.get("word", "").strip()
            if not w_text:
                continue

            s_sec = parse_offset_sec(item.get("startOffset", 0.0))
            e_sec = parse_offset_sec(item.get("endOffset", s_sec + 0.1))

            abs_start = round(chunk_offset + s_sec, 3)
            abs_end = round(chunk_offset + e_sec, 3)

            words.append(Word(
                word=w_text,
                start=abs_start,
                end=abs_end,
                confidence=1.0
            ))

        return words

    def transcribe_chunk(self, chunk: AudioChunk, max_retries: int = 3) -> List[Word]:
        if not chunk.audio_path:
            return []

        with open(chunk.audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        # 🚀 ÖNEMLİ: language_codes GÖNDERİLMEZ (Bismillah ve yabancı kökenli kelimelerin atlanmasını engeller)
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/mp3",
                                "data": audio_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "audio_transcription_config": {
                    "word_timestamp": True,
                    "mode": "VERBATIM"
                }
            }
        }

        last_error = None
        for attempt in range(1, max_retries + 1):
            # 1. Anahtar rotasyonundan uygun anahtar al (gerekiyorsa kotayı bekler)
            api_key = self.rotator.get_available_key(wait_if_needed=True)
            if not api_key:
                raise RuntimeError(f"Gemini kota sınırında ve uygun anahtar bulunamadı (Deneme {attempt}/{max_retries}).")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-transcribe:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            try:
                logger.info(f"🚀 GeminiTranscribe isteği gönderiliyor (Parça {chunk.index}: {chunk.start_sec:.1f}s -> {chunk.end_sec:.1f}s, Deneme {attempt}/{max_retries})")
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))

                words = self.parse_response(resp_data, chunk_offset=chunk.start_sec)
                logger.info(f"✅ GeminiTranscribe tamamlandı (Parça {chunk.index}): {len(words)} kelime bulundu.")
                return words

            except urllib.error.HTTPError as he:
                err_body = he.read().decode("utf-8", errors="ignore")
                logger.warning(f"⚠️ Gemini HTTP {he.code} hatası (Parça {chunk.index}, Deneme {attempt}/{max_retries}): {err_body[:200]}")

                if he.code == 429:
                    retry_sec = 25.0
                    match = re.search(r'retryDelay["\']?:\s*["\']?(\d+)s', err_body)
                    if match:
                        retry_sec = float(match.group(1)) + 1.0
                    self.rotator.report_429(api_key, retry_sec)

                    if attempt < max_retries:
                        logger.info(f"⏳ 429 Kota aşımı alındı. {retry_sec:.1f} sn sonra parça yeniden denenecek...")
                        time.sleep(min(retry_sec, 60.0))
                        last_error = he
                        continue

                last_error = he
                raise RuntimeError(f"Gemini API hatası ({he.code}): {err_body[:200]}") from he

            except Exception as ex:
                logger.error(f"❌ Gemini Transcribe bağlantı hatası (Parça {chunk.index}, Deneme {attempt}/{max_retries}): {ex}")
                last_error = ex
                if attempt < max_retries:
                    time.sleep(3.0)
                    continue
                raise

        raise RuntimeError(f"Gemini Transcribe {max_retries} deneme sonunda başarısız oldu: {last_error}")
