"""
OtoEdit STT Motor Zinciri (Failover Chain)
- Config.STT_ENGINE_ORDER sırasındaki motorları sırayla dener.
- Kota aşımı (429) veya bağlantı hatası durumunda bir sonraki motora otomatik geçer.
- Hangi parçanın hangi motordan çıktığını raporlar.
"""

from typing import List, Tuple, Dict
from config import Config
from pipeline.stt.base import BaseSTTEngine, Word
from pipeline.stt.chunker import AudioChunk
from pipeline.stt.gemini_transcribe import GeminiTranscribeEngine
from pipeline.stt.groq_engine import GroqEngine
from pipeline.stt.proxy_gemini import ProxyGeminiEngine
from pipeline.stt.local_whisper import LocalWhisperEngine
from utils.logger import get_logger

logger = get_logger("STT.EngineChain")


class STTEngineChain:
    """STT motorları arasında failover zinciri yönetir."""

    def __init__(self, engine_order: List[str] = None):
        self.engine_order = engine_order or Config.STT_ENGINE_ORDER
        self.engines: Dict[str, BaseSTTEngine] = {}
        self.exhausted_engines: set = set()
        self._init_engines()

    def _init_engines(self):
        # 1. Gemini Transcribe
        try:
            self.engines["gemini_transcribe"] = GeminiTranscribeEngine()
        except Exception as e:
            logger.warning(f"GeminiTranscribeEngine başlatılamadı: {e}")

        # 2. Groq
        try:
            self.engines["groq"] = GroqEngine()
        except Exception as e:
            logger.warning(f"GroqEngine başlatılamadı: {e}")

        # 3. Proxy Gemini
        try:
            self.engines["proxy_gemini"] = ProxyGeminiEngine()
        except Exception as e:
            logger.warning(f"ProxyGeminiEngine başlatılamadı: {e}")

        # 4. Local Whisper
        try:
            self.engines["local_whisper"] = LocalWhisperEngine()
        except Exception as e:
            logger.warning(f"LocalWhisperEngine başlatılamadı: {e}")

    def transcribe_chunk(self, chunk: AudioChunk) -> Tuple[List[Word], str]:
        """Parçayı zincirdeki ilk başarılı motora işletir."""
        if not chunk.has_speech:
            return [], "skipped_silence"

        errors = []

        for name in self.engine_order:
            if name in self.exhausted_engines:
                continue

            engine = self.engines.get(name)
            if not engine:
                continue

            if not engine.is_available():
                logger.debug(f"Motor '{name}' hazır değil (anahtar yok), atlanıyor.")
                continue

            try:
                words = engine.transcribe_chunk(chunk)
                return words, engine.name
            except Exception as ex:
                err_str = str(ex).lower()
                if "quota exceeded" in err_str or "rate limit" in err_str or "429" in err_str or "kota" in err_str:
                    logger.warning(f"🚫 Motor '{name}' kotası tükendi, bu iş için devre dışı bırakılıyor: {ex}")
                    self.exhausted_engines.add(name)
                logger.warning(f"⚠️ Motor '{name}' parça {chunk.index} için başarısız oldu: {ex}")
                errors.append(f"{name}: {str(ex)[:100]}")
                continue

        err_summary = " | ".join(errors)
        raise RuntimeError(f"❌ Zincirdeki tüm STT motorları parça {chunk.index} için başarısız oldu: {err_summary}")
