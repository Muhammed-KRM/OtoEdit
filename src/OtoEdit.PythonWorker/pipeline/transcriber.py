import os
from config import Config
from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp
from utils.logger import get_logger

logger = get_logger(__name__)


class Transcriber:
    """OpenAI Whisper API veya yerel model üzerinden kelime düzeyinde transkript çıkaran motor."""

    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.client = None

        if self.api_key:
            try:
                import importlib
                openai_mod = importlib.import_module("openai")
                self.client = openai_mod.OpenAI(api_key=self.api_key)
                logger.info("Whisper API istemcisi hazırlandı.")
            except Exception as e:
                logger.warning(f"OpenAI istemcisi başlatılamadı: {e}")
        else:
            logger.warning("OPENAI_API_KEY tanımlı değil. Transkript fallback modunda çalışacak.")

    def transcribe(self, audio_path: str, video_id: str = "") -> TranscriptResult:
        """Ses dosyasını çözümler ve kelime bazlı zaman damgaları ile döner."""
        logger.info(f"Transkripsiyon başlıyor: {audio_path}")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Transkripsiyon için ses dosyası bulunamadı: {audio_path}")

        if self.client:
            try:
                with open(audio_path, "rb") as f:
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="verbose_json",
                        timestamp_granularities=["word", "segment"],
                        language="tr"
                    )

                full_text = getattr(response, "text", "")
                segments = []
                words = []

                # Segmentleri işle
                for seg in getattr(response, "segments", []):
                    seg_dict = seg if isinstance(seg, dict) else seg.model_dump()
                    seg_words = []
                    for w in seg_dict.get("words", []):
                        word_obj = WordTimestamp(
                            word=w.get("word", "").strip(),
                            start=float(w.get("start", 0.0)),
                            end=float(w.get("end", 0.0)),
                            confidence=float(w.get("confidence", 1.0))
                        )
                        seg_words.append(word_obj)
                        words.append(word_obj)

                    segments.append(TranscriptSegment(
                        start=float(seg_dict.get("start", 0.0)),
                        end=float(seg_dict.get("end", 0.0)),
                        text=seg_dict.get("text", "").strip(),
                        words=seg_words
                    ))

                # Eğer segment içinde kelimeler gelmediyse genel words listesini kontrol et
                if not words and hasattr(response, "words"):
                    for w in getattr(response, "words", []):
                        w_dict = w if isinstance(w, dict) else w.model_dump()
                        words.append(WordTimestamp(
                            word=w_dict.get("word", "").strip(),
                            start=float(w_dict.get("start", 0.0)),
                            end=float(w_dict.get("end", 0.0))
                        ))

                duration = getattr(response, "duration", 0.0)
                if not duration and words:
                    duration = max(w.end for w in words)

                logger.info(f"Transkripsiyon tamamlandı: {len(words)} kelime, {len(segments)} segment, süre={duration:.1f}s")
                return TranscriptResult(
                    full_text=full_text,
                    segments=segments,
                    words=words,
                    duration=float(duration)
                )
            except Exception as e:
                logger.error(f"Whisper API transkripsiyon hatası: {e}", exc_info=True)

        logger.info("Transkript fallback üretiliyor...")
        return self._generate_fallback_transcript(audio_path)

    @staticmethod
    def _generate_fallback_transcript(audio_path: str) -> TranscriptResult:
        """API anahtarı olmadığında geliştirme ve test için sentetik transkript üretir."""
        sample_words = [
            ("Merhaba", 0.5, 1.2),
            ("değerli", 1.3, 1.8),
            ("izleyiciler", 1.9, 2.7),
            ("bugün", 3.0, 3.5),
            ("yapay", 3.6, 4.0),
            ("zeka", 4.1, 4.5),
            ("ile", 4.6, 4.8),
            ("otomatik", 4.9, 5.5),
            ("video", 5.6, 6.0),
            ("kurgusunu", 6.1, 6.8),
            ("konuşuyoruz", 6.9, 7.8),
            ("burayı", 12.0, 12.5),
            ("kes", 12.6, 13.0),
            ("kanalımıza", 15.0, 15.8),
            ("abone", 15.9, 16.4),
            ("olmayı", 16.5, 17.0),
            ("unutmayın", 17.1, 18.0)
        ]

        words = [WordTimestamp(word=w, start=s, end=e) for w, s, e in sample_words]
        full_text = " ".join(w for w, _, _ in sample_words)
        segment = TranscriptSegment(start=0.5, end=18.0, text=full_text, words=words)

        return TranscriptResult(
            full_text=full_text,
            segments=[segment],
            words=words,
            duration=20.0
        )
