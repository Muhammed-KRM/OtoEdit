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
from typing import List, Optional, Callable, Any
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
        video_id: str = "",
        on_progress: Optional[Callable[[int, int, str], None]] = None
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
            total_chunks = len(chunks)

            for chunk in chunks:
                if not chunk.has_speech:
                    logger.info(f"🔇 Parça {chunk.index} sessiz, STT motoruna gönderilmedi.")
                    if on_progress:
                        on_progress(chunk.index, total_chunks, f"Parça {chunk.index}/{total_chunks} sessiz bölge, atlandı.")
                    continue

                if on_progress:
                    on_progress(chunk.index, total_chunks, f"Parça {chunk.index}/{total_chunks} transkribe ediliyor ({chunk.start_sec:.0f}s - {chunk.end_sec:.0f}s)...")

                try:
                    words, engine_name = self.chain.transcribe_chunk(chunk)
                    all_words.extend(words)
                    engine_stats[engine_name] = engine_stats.get(engine_name, 0) + len(words)
                    if on_progress:
                        on_progress(chunk.index, total_chunks, f"Parça {chunk.index}/{total_chunks} tamamlandı ({engine_name}, {len(words)} kelime).")
                except Exception as ex:
                    logger.warning(
                        f"⚠️ Parça {chunk.index} ({chunk.start_sec:.1f}s -> {chunk.end_sec:.1f}s) STT hatası: {ex}. "
                        f"Bu parça atlandı ancak önceden toplanan {len(all_words)} kelime korunuyor."
                    )

            logger.info(f"📊 STT Motor İstatistikleri: {engine_stats} (Toplam {len(all_words)} kelime)")

            # 4. Kayıp Kelime Dedektörü (Gap Filler)
            if on_progress:
                on_progress(total_chunks, total_chunks, "Kayıp kelimeler ve konuşma aralıkları taranıyor...")
            all_words = self.gap_filler.fill_gaps(
                media_path=audio_path,
                analysis=analysis,
                words=all_words,
                chain=self.chain
            )

            if not all_words:
                logger.warning("⚠️ Transkripsiyondan hiç kelime dönmedi, fallback üretiliyor.")
                return self._generate_fallback_transcript(audio_path)

            # 5. Adım 1: Kelime Temizliği ve Çift Yönlü VAD Kırpması
            all_words = self.clean_and_trim_words(all_words, analysis)

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
                all_words = self.clean_and_trim_words(all_words, analysis if 'analysis' in locals() else None)
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
    def clean_and_trim_words(words: List[Word], analysis: Optional[AudioAnalysis] = None) -> List[Word]:
        """
        Adım 1: Kelime Temizliği ve Çift Yönlü VAD Kırpması
        Whisper'ın uzun duraklamalarda kelimeleri aşırı uzatmasını (örn. 'ancak' 7sn)
        ve sessizlik halüsinasyonlarını engeller.
        """
        if not words:
            return []

        cleaned: List[Word] = []
        for w in words:
            w_text = w.word.strip()
            # Bilinen halüsinasyon filtreleri
            w_norm = w_text.lower().replace(".", "").replace(",", "")
            if w_norm in ("altyazı", "mısır", "diber"):
                continue

            s = float(w.start)
            e = float(w.end)
            dur = e - s

            if analysis is not None and dur > 1.0 and getattr(analysis, "speech_regions", None):
                # Bu kelime aralığı ile çakışan VAD konuşma bölgelerini bul
                ov_regions = [r for r in analysis.speech_regions if r.end > s and r.start < e]
                if ov_regions:
                    new_s = max(s, ov_regions[0].start)
                    new_e = min(e, ov_regions[-1].end)
                    if new_e > new_s and (new_e - new_s) >= 0.05:
                        s, e = new_s, new_e

            cleaned.append(Word(
                word=w_text,
                start=round(s, 3),
                end=round(e, 3),
                confidence=w.confidence
            ))

        cleaned.sort(key=lambda w: w.start)
        return cleaned

    @staticmethod
    def regenerate_segments_with_cuts(
        words: List[Any],
        cuts: Optional[List[Any]] = None,
        max_words: int = 6,
        max_duration: float = 3.0
    ) -> List[TranscriptSegment]:
        """
        Adım 4.1: Altyazıların Kesim Sınırlarını Aşmayacak Şekilde Yeniden Üretilmesi
        Retake veya sessizlik ile kesilen kelimeleri segmentlerden çıkarır,
        ve kesim sınırlarında altyazı segmentlerini bölerek ekranda kesilmiş kelimenin
        görünmesini engeller.
        """
        if not words:
            return []

        all_cuts = cuts or []
        # Kesim içine düşmeyen kelimeleri koru
        preserved = []
        for w in words:
            ws = float(getattr(w, "start", 0.0) if hasattr(w, "start") else w.get("start", 0.0))
            we = float(getattr(w, "end", 0.0) if hasattr(w, "end") else w.get("end", 0.0))
            wt = str(getattr(w, "word", "") if hasattr(w, "word") else w.get("word", "")).strip()
            wc = float(getattr(w, "confidence", 1.0) if hasattr(w, "confidence") else w.get("confidence", 1.0))

            in_cut = any(c.start - 0.05 <= ws and we <= c.end + 0.05 for c in all_cuts)
            if not in_cut and wt:
                preserved.append(WordTimestamp(word=wt, start=round(ws, 2), end=round(we, 2), confidence=round(wc, 2)))

        segments: List[TranscriptSegment] = []
        cur_words: List[WordTimestamp] = []

        for idx, w in enumerate(preserved):
            if not cur_words:
                cur_words.append(w)
                continue

            prev_w = cur_words[-1]
            dur = w.end - cur_words[0].start
            is_term = prev_w.word.strip().endswith(('.', '!', '?', ':'))
            gap = w.start - prev_w.end

            # Eğer kelimeler arasında bir kesim varsa veya uzun duraklama varsa segmenti sonlandır
            has_cut_between = any(c.start >= prev_w.end - 0.05 and c.end <= w.start + 0.05 for c in all_cuts)

            if len(cur_words) >= max_words or dur >= max_duration or (is_term and len(cur_words) >= 3) or has_cut_between or gap >= 0.8:
                seg_text = " ".join(cw.word for cw in cur_words)
                segments.append(TranscriptSegment(
                    start=cur_words[0].start,
                    end=cur_words[-1].end,
                    text=seg_text,
                    words=list(cur_words)
                ))
                cur_words = [w]
            else:
                cur_words.append(w)

        if cur_words:
            seg_text = " ".join(cw.word for cw in cur_words)
            segments.append(TranscriptSegment(
                start=cur_words[0].start,
                end=cur_words[-1].end,
                text=seg_text,
                words=list(cur_words)
            ))

        return segments

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
