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

                # Uzun segmentleri kısa altyazı parçalarına böl
                segments = self._chunk_segments(segments, max_words=6, max_duration=3.0)

                logger.info(f"Transkripsiyon tamamlandı: {len(words)} kelime, {len(segments)} parçalanmış segment, süre={duration:.1f}s")
                return TranscriptResult(
                    full_text=full_text,
                    segments=segments,
                    words=words,
                    duration=float(duration)
                )
            except Exception as e:
                logger.error(f"Whisper API transkripsiyon hatası: {e}", exc_info=True)

        # 2. Yerel faster-whisper motorunu dene (API anahtarı yoksa veya hata verdiyse)
        try:
            import importlib
            fw_mod = importlib.import_module("faster_whisper")
            whisper_model_cls = getattr(fw_mod, "WhisperModel")
            logger.info("Yerel faster-whisper modeli ile transkripsiyon başlatılıyor (model='base', device='cpu', compute_type='int8')...")
            local_model = whisper_model_cls("base", device="cpu", compute_type="int8")
            segments_iter, info = local_model.transcribe(
                audio_path,
                language="tr",
                word_timestamps=True
            )

            segments = []
            words = []
            full_text_parts = []

            for seg in segments_iter:
                seg_words = []
                if seg.words:
                    for w in seg.words:
                        w_obj = WordTimestamp(
                            word=w.word.strip(),
                            start=float(round(w.start, 2)),
                            end=float(round(w.end, 2)),
                            confidence=float(round(w.probability, 2))
                        )
                        seg_words.append(w_obj)
                        words.append(w_obj)

                seg_text = seg.text.strip()
                if seg_text:
                    full_text_parts.append(seg_text)
                    segments.append(TranscriptSegment(
                        start=float(round(seg.start, 2)),
                        end=float(round(seg.end, 2)),
                        text=seg_text,
                        words=seg_words
                    ))

            full_text = " ".join(full_text_parts)
            duration = float(getattr(info, "duration", 0.0))
            if not duration and words:
                duration = max(w.end for w in words)

            # Uzun segmentleri kısa altyazı parçalarına böl
            segments = self._chunk_segments(segments, max_words=6, max_duration=3.0)

            logger.info(f"Yerel Whisper transkripsiyonu tamamlandı: {len(words)} kelime, {len(segments)} parçalanmış segment, süre={duration:.1f}s")
            return TranscriptResult(
                full_text=full_text,
                segments=segments,
                words=words,
                duration=duration
            )
        except Exception as local_ex:
            logger.warning(f"Yerel faster-whisper transkripsiyonu başarısız oldu: {local_ex}")

        logger.info("Transkript fallback üretiliyor...")
        return self._generate_fallback_transcript(audio_path)

    @staticmethod
    def _generate_fallback_transcript(audio_path: str) -> TranscriptResult:
        """API anahtarı ve yerel model olmadığında uyarı transkripti üretir."""
        logger.warning("TRANSKRIPT UYARISI: Model bulunamadı veya çalıştırılamadı.")
        
        warning_text = "[TRANSKRİPT ÇIKARILAMADI]"
        words = [WordTimestamp(word=warning_text, start=0.0, end=1.0)]
        segment = TranscriptSegment(start=0.0, end=1.0, text=warning_text, words=words)

        return TranscriptResult(
            full_text=warning_text,
            segments=[segment],
            words=words,
            duration=1.0
        )

    @staticmethod
    def _chunk_segments(segments: list, max_words: int = 6, max_duration: float = 3.0) -> list:
        """
        Uzun segmentleri (cümleleri) ekranda güzel durması için 
        daha kısa mikro-parçalara (chunk) böler.
        """
        chunked = []
        for seg in segments:
            if not getattr(seg, 'words', None):
                chunked.append(seg)
                continue
                
            current_chunk_words = []
            for w in seg.words:
                current_chunk_words.append(w)
                
                duration = current_chunk_words[-1].end - current_chunk_words[0].start
                is_terminal = w.word.strip().endswith(('.', '!', '?', ',', ':'))
                
                # Eğer sınır aşıldıysa veya noktalama varsa böl
                if len(current_chunk_words) >= max_words or duration >= max_duration or is_terminal:
                    chunk_text = " ".join(cw.word for cw in current_chunk_words)
                    chunked.append(TranscriptSegment(
                        start=round(current_chunk_words[0].start, 2),
                        end=round(current_chunk_words[-1].end, 2),
                        text=chunk_text,
                        words=list(current_chunk_words)
                    ))
                    current_chunk_words = []
            
            # Arta kalan kelimeleri son bir parça olarak ekle
            if current_chunk_words:
                chunk_text = " ".join(cw.word for cw in current_chunk_words)
                chunked.append(TranscriptSegment(
                    start=round(current_chunk_words[0].start, 2),
                    end=round(current_chunk_words[-1].end, 2),
                    text=chunk_text,
                    words=list(current_chunk_words)
                ))
        return chunked
