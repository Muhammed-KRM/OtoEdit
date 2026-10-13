"""
OtoEdit Yerel Faster-Whisper STT Motoru (Tam Çevrimdışı Yedek)
- faster-whisper kütüphanesini kullanarak GPU/CPU üzerinde yerel transkripsiyon yapar.
- word_timestamps=True ile kelime zamanlarını çıkarır.
- Harici internet bağlantısı veya kota gerektirmez.
"""

import os
from typing import List, Optional
from config import Config
from pipeline.stt.base import BaseSTTEngine, Word
from pipeline.stt.chunker import AudioChunk
from utils.logger import get_logger

logger = get_logger("STT.LocalWhisper")


class LocalWhisperEngine(BaseSTTEngine):
    """Yerel Faster-Whisper Motoru."""

    def __init__(self, model_name: str = None):
        super().__init__(name="local_whisper")
        self.model_name = model_name or Config.LOCAL_WHISPER_MODEL
        self._model = None

    def is_available(self) -> bool:
        return True

    def _get_model(self):
        if self._model is None:
            import torch
            from faster_whisper import WhisperModel

            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "int8_float16" if device == "cuda" else "int8"

            logger.info(f"💻 Yerel Whisper modeli yükleniyor: {self.model_name} (cihaz={device}, compute={compute_type})")
            self._model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
                cpu_threads=4
            )
        return self._model

    def transcribe_chunk(self, chunk: AudioChunk) -> List[Word]:
        if not chunk.audio_path or not os.path.exists(chunk.audio_path):
            return []

        model = self._get_model()
        logger.info(f"🎙️ Yerel Whisper çalıştırılıyor (Parça {chunk.index}: {chunk.start_sec:.1f}s -> {chunk.end_sec:.1f}s)")

        # vad_filter=False çünkü parçalama zaten VAD ile yapıldı
        segments, _ = model.transcribe(
            chunk.audio_path,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False
        )

        words: List[Word] = []
        for segment in segments:
            if not segment.words:
                continue
            for w in segment.words:
                w_text = w.word.strip()
                if not w_text:
                    continue
                words.append(Word(
                    word=w_text,
                    start=round(chunk.start_sec + w.start, 3),
                    end=round(chunk.start_sec + w.end, 3),
                    confidence=float(getattr(w, "probability", 1.0))
                ))

        logger.info(f"✅ Yerel Whisper tamamlandı (Parça {chunk.index}): {len(words)} kelime bulundu.")
        return words
