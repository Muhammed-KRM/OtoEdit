"""
OtoEdit Transcriber Orkestratörü
- Tek kaynak AudioAnalysis nesnesinden beslenir.
- AudioChunker ile VAD sessizlik sınırlarından parçalama yapar.
- STTEngineChain ile sırasıyla Gemini 3.5 Transcribe -> Groq -> Antigravity Proxy -> Yerel Whisper zincirini çalıştırır.
- GapFiller ile atlanan konuşma bölgelerini tespit edip kurtarır ("hiçbir kelime atlanmamalı").
- Çıktıyı altyazı segmentlerine bölerek EDL ve Karaoke motoruna uyumlu TranscriptResult olarak döner.
"""

import os
import time
from typing import List, Optional
from config import Config
from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp
from pipeline.audio_analysis import AudioAnalysis, AudioAnalyzer
from pipeline.stt.base import Word
from pipeline.stt.chunker import AudioChunker
from pipeline.stt.engine_chain import STTEngineChain
from pipeline.stt.gap_filler import GapFiller
from utils.logger import get_logger

logger = get_logger("Transcriber")


class Transcriber:
    """Yüksek hızlı ve çok katmanlı akıllı transkripsiyon orkestratörü."""

    def __init__(self, engine_chain: Optional[STTEngineChain] = None):
        self.chain = engine_chain or STTEngineChain()
        self.chunker = AudioChunker(max_chunk_sec=Config.STT_CHUNK_MAX_SEC)
        self.gap_filler = GapFiller(min_gap_sec=0.40)

    def transcribe(
        self,
        audio_path: str,
        analysis: Optional[AudioAnalysis] = None,
        video_id: str = ""
    ) -> TranscriptResult:
        """
        Ses dosyasını çözümler:
        1. VAD & RMS analizi (verilmemişse yapar)
        2. Akıllı VAD parçalama
        3. STT Motor Zinciri (Gemini Transcribe -> Groq -> Proxy -> Local)
        4. GapFiller (atlanan kelimeleri geri kazanma)
        5. Altyazı mikro-segmentasyonu
        """
        logger.info(f"🎙️ Transkripsiyon orkestrasyonu başlıyor: {os.path.basename(audio_path)} (VideoId={video_id})")
        t0 = time.time()

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Transkripsiyon için ses dosyası bulunamadı: {audio_path}")

        # 1. Ses Analizi
        if analysis is None:
            analyzer = AudioAnalyzer()
            analysis = analyzer.analyze(audio_path)

        if analysis.duration <= 0.1:
            return self._generate_fallback_transcript(audio_path)

        chunks = []
        try:
            # 2. Akıllı Parçalama (Sessizlik sınırlarından)
            chunks = self.chunker.split(audio_path, analysis)
            logger.info(f"📦 Toplam {len(chunks)} parça oluşturuldu (Süre={analysis.duration:.1f}s).")

            # 3. Her parçayı STT zincirine gönder
            all_words: List[Word] = []
            engine_stats = {}

            for chunk in chunks:
                if not chunk.has_speech:
                    logger.info(f"🔇 Parça {chunk.index} sessiz, STT motoruna gönderilmedi.")
                    continue

                try:
                    words, engine_name = self.chain.transcribe_chunk(chunk)
                    all_words.extend(words)
                    engine_stats[engine_name] = engine_stats.get(engine_name, 0) + len(words)
                except Exception as ex:
                    logger.warning(
                        f"⚠️ Parça {chunk.index} ({chunk.start_sec:.1f}s -> {chunk.end_sec:.1f}s) STT hatası: {ex}. "
                        f"Bu parça atlandı ancak önceden toplanan {len(all_words)} kelime korunuyor."
                    )

            logger.info(f"📊 STT Motor İstatistikleri: {engine_stats} (Toplam {len(all_words)} kelime)")

            # 4. Kayıp Kelime Dedektörü (Gap Filler)
            all_words = self.gap_filler.fill_gaps(
                media_path=audio_path,
                analysis=analysis,
                words=all_words,
                chain=self.chain
            )

            if not all_words:
                logger.warning("⚠️ Transkripsiyondan hiç kelime dönmedi, fallback üretiliyor.")
                return self._generate_fallback_transcript(audio_path)

            # 5. Kelimeleri sırala
            all_words.sort(key=lambda w: w.start)

            # 6. Altyazı segmentlerine böl (Karaoke & EDL uyumlu)
            segments = self._words_to_segments(all_words, max_words=6, max_duration=3.0)

            # WordTimestamp nesnelerine çevir
            word_timestamps = [
                WordTimestamp(
                    word=w.word,
                    start=round(w.start, 2),
                    end=round(w.end, 2),
                    confidence=round(w.confidence, 2)
                )
                for w in all_words
            ]

            full_text = " ".join(w.word for w in all_words)
            total_duration = analysis.duration
            elapsed = time.time() - t0

            logger.info(
                f"🎉 Transkripsiyon tamamlandı: {len(all_words)} kelime, {len(segments)} segment, "
                f"Süre={total_duration:.1f}s, İşlem süresi={elapsed:.1f}s"
            )

            return TranscriptResult(
                full_text=full_text,
                segments=segments,
                words=word_timestamps,
                duration=float(total_duration)
            )

        except Exception as e:
            logger.error(f"❌ Transkripsiyon orkestrasyonu sırasında hata: {e}", exc_info=True)
            if 'all_words' in locals() and all_words:
                logger.info(f"⚠️ Hata oluştu ancak önceden toplanan {len(all_words)} kelime ile kurtarma yapılıyor.")
                all_words.sort(key=lambda w: w.start)
                segments = self._words_to_segments(all_words, max_words=6, max_duration=3.0)
                word_timestamps = [
                    WordTimestamp(word=w.word, start=round(w.start, 2), end=round(w.end, 2), confidence=round(w.confidence, 2))
                    for w in all_words
                ]
                return TranscriptResult(
                    full_text=" ".join(w.word for w in all_words),
                    segments=segments,
                    words=word_timestamps,
                    duration=float(analysis.duration if 'analysis' in locals() and analysis else 1.0)
                )
            return self._generate_fallback_transcript(audio_path)
        finally:
            # Geçici parçaları temizle
            if chunks:
                self.chunker.cleanup_chunks(chunks)

    @staticmethod
    def _words_to_segments(words: List[Word], max_words: int = 6, max_duration: float = 3.0) -> List[TranscriptSegment]:
        """Kelimeleri altyazı için estetik mikro-segmentlere böler."""
        segments: List[TranscriptSegment] = []
        current_chunk_words: List[WordTimestamp] = []

        for w in words:
            wt = WordTimestamp(
                word=w.word,
                start=round(w.start, 2),
                end=round(w.end, 2),
                confidence=round(w.confidence, 2)
            )
            current_chunk_words.append(wt)

            duration = current_chunk_words[-1].end - current_chunk_words[0].start
            is_terminal = w.word.strip().endswith(('.', '!', '?', ':'))

            if len(current_chunk_words) >= max_words or duration >= max_duration or (is_terminal and len(current_chunk_words) >= 3):
                chunk_text = " ".join(cw.word for cw in current_chunk_words)
                segments.append(TranscriptSegment(
                    start=current_chunk_words[0].start,
                    end=current_chunk_words[-1].end,
                    text=chunk_text,
                    words=list(current_chunk_words)
                ))
                current_chunk_words = []

        if current_chunk_words:
            chunk_text = " ".join(cw.word for cw in current_chunk_words)
            segments.append(TranscriptSegment(
                start=current_chunk_words[0].start,
                end=current_chunk_words[-1].end,
                text=chunk_text,
                words=list(current_chunk_words)
            ))

        return segments

    @staticmethod
    def _generate_fallback_transcript(audio_path: str) -> TranscriptResult:
        """API veya motorlar çalışmadığında güvenlik transkripti üretir."""
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
