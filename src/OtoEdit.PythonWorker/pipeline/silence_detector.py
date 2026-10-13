"""
OtoEdit Jump-Cut & Sessizlik Algılama Motoru (v2)
- Silero VAD konuşma bölgeleri referans alınır.
- 300ms'den kısa yetim konuşma adaları birleştirilerek mikro-klipler/çıtırtılar önlenir.
- Doğal nefes araları (JUMPCUT_MIN_SILENCE_MS) korunur.
- Konuşma başı/sonu için içe padding (JUMPCUT_PAD_MS) uygulanır.
- Kelime zamanları varsa GUARD_MS ile mutlak kelime koruması sağlanır.
- Tık/patlama seslerini önlemek için kenarlar RMS lokal minimumuna (Adım 6.5) oturtulur.
"""

from pathlib import Path
from typing import List, Tuple, Optional, Any
import numpy as np

from config import Config
from models.edl_model import CutItem
from pipeline.audio_analysis import AudioAnalysis, AudioAnalyzer, SpeechRegion
from utils.logger import get_logger

logger = get_logger("SilenceDetector")


class SilenceDetector:
    """Videodaki veya sesteki uzun sessizlikleri (jump-cut) tespit eden motor."""

    def __init__(
        self,
        min_silence_len: int = 0,
        silence_thresh: int = 0,
        padding_sec: float = 0.0,
        pad_lead_sec: float = 0.0,
        pad_trailing_sec: float = 0.0,
        engine: str = None
    ):
        self.engine = engine or Config.JUMPCUT_ENGINE
        self.min_silence_ms = min_silence_len or Config.JUMPCUT_MIN_SILENCE_MS

        default_lead = getattr(Config, "JUMPCUT_PAD_LEAD_MS", 350) / 1000.0
        default_trailing = getattr(Config, "JUMPCUT_PAD_TRAILING_MS", 200) / 1000.0

        if padding_sec > 0:
            self._pad_lead_sec = pad_lead_sec if pad_lead_sec > 0 else padding_sec
            self._pad_trailing_sec = pad_trailing_sec if pad_trailing_sec > 0 else padding_sec
        else:
            self._pad_lead_sec = pad_lead_sec if pad_lead_sec > 0 else default_lead
            self._pad_trailing_sec = pad_trailing_sec if pad_trailing_sec > 0 else default_trailing

        self.word_guard_sec = Config.JUMPCUT_WORD_GUARD_MS / 1000.0
        self.min_island_sec = Config.JUMPCUT_MIN_ISLAND_MS / 1000.0

        # Legacy pydub parametreleri
        self.legacy_silence_thresh = silence_thresh or Config.SILENCE_THRESH_DBFS
        self.legacy_min_silence_len = min_silence_len or Config.SILENCE_MIN_LEN_MS

    @property
    def pad_lead_sec(self) -> float:
        return self._pad_lead_sec

    @pad_lead_sec.setter
    def pad_lead_sec(self, val: float):
        self._pad_lead_sec = val

    @property
    def pad_trailing_sec(self) -> float:
        return self._pad_trailing_sec

    @pad_trailing_sec.setter
    def pad_trailing_sec(self, val: float):
        self._pad_trailing_sec = val

    @property
    def pad_sec(self) -> float:
        return self._pad_trailing_sec

    @pad_sec.setter
    def pad_sec(self, val: float):
        self._pad_trailing_sec = val
        self._pad_lead_sec = val

    def detect(
        self,
        audio_path: str,
        analysis: Optional[AudioAnalysis] = None,
        transcript_words: Optional[List[Any]] = None
    ) -> List[CutItem]:
        """Sessiz kesim bölgelerini döner (v2 veya legacy motoru ile)."""
        if self.engine == "legacy":
            return self._detect_legacy(audio_path)

        return self.detect_v2(audio_path, analysis=analysis, transcript_words=transcript_words)

    def detect_v2(
        self,
        audio_path: Optional[str] = None,
        analysis: Optional[AudioAnalysis] = None,
        transcript_words: Optional[List[Any]] = None
    ) -> List[CutItem]:
        """
        Jump-Cut v2 Algoritması:
        1. VAD konuşma bölgeleri arasındaki boşlukları aday sessizlik olarak al
        2. İki sessizlik arasındaki konuşma adası min_island_sec'den kısaysa (ve kelime içermiyorsa) sessizlikleri birleştir
        3. min_silence_ms'den kısa olanları ele (doğal nefes araları kalsın)
        4. İki ucundan asimetrik pad kadar içeri çek (konuşma başı pad_lead_sec, konuşma sonu pad_trailing_sec)
        5. Kelime koruması: [word.start - guard, word.end + guard] aralıklarıyla çakışan kısımları çıkar
        6. Kenar ince ayarı: RMS zarfının lokal minimumuna tek yönlü (sessizliğin içine doğru) oturt
        """
        if analysis is None:
            if not audio_path:
                raise ValueError("detect_v2 için ya audio_path ya da analysis nesnesi verilmelidir.")
            analyzer = AudioAnalyzer()
            analysis = analyzer.analyze(audio_path)

        logger.info(
            f"✂️ Jump-Cut v2 başlıyor: Süre={analysis.duration:.1f}s | "
            f"MinSessizlik={self.min_silence_ms}ms | PadLead={self.pad_lead_sec*1000:.0f}ms | "
            f"PadTrailing={self.pad_trailing_sec*1000:.0f}ms | Guard={self.word_guard_sec*1000:.0f}ms | "
            f"KelimeSayısı={len(transcript_words or [])}"
        )

        # 1. Korumalı kelime aralıklarını hazırla
        protected_intervals: List[Tuple[float, float]] = []
        if transcript_words:
            for w in transcript_words:
                w_start = getattr(w, "start", None)
                w_end = getattr(w, "end", None)
                if w_start is None and isinstance(w, dict):
                    w_start = w.get("start", 0.0)
                    w_end = w.get("end", 0.0)
                if w_start is not None and w_end is not None and w_end >= w_start:
                    g_start = max(0.0, float(w_start) - self.word_guard_sec)
                    g_end = min(analysis.duration, float(w_end) + self.word_guard_sec)
                    protected_intervals.append((g_start, g_end))

            protected_intervals = self._merge_intervals(protected_intervals)

        # 2. VAD boşluklarından ham sessizlikleri al
        raw_silences = analysis.get_silence_regions(min_silence_sec=0.0)

        # 3. Küçük Konuşma Adalarını Birleştirme (Micro-Island Merging)
        merged_silences: List[Tuple[float, float]] = []
        for s_curr, e_curr in raw_silences:
            if not merged_silences:
                merged_silences.append((s_curr, e_curr))
                continue

            s_prev, e_prev = merged_silences[-1]
            island_gap = s_curr - e_prev  # İki sessizlik arasındaki ses adacığının süresi

            # Aradaki adacıkta korunan bir kelime var mı?
            has_word = False
            for p_s, p_e in protected_intervals:
                if p_e > e_prev and p_s < s_curr:
                    has_word = True
                    break

            if island_gap < self.min_island_sec and not has_word:
                # Konuşma adacığı çok kısa (çıtırtı / nefes / parazit), birleştir
                merged_silences[-1] = (s_prev, e_curr)
            else:
                merged_silences.append((s_curr, e_curr))

        # 4. Minimum sessizlik süresi filtresi (doğal nefes araları elenir)
        min_silence_sec = self.min_silence_ms / 1000.0
        candidate_silences = [
            (s, e) for s, e in merged_silences
            if (e - s) >= min_silence_sec
        ]

        # 5. İki ucundan asimetrik pad kadar içeri çek (Video başlangıcı ve bitişinde sıfıra/sona tam yasla)
        # s_raw: Önceki konuşmanın bitişi -> pad_trailing kadar ileri çek (konuşma sonu nefes payı)
        # e_raw: Sonraki konuşmanın başlangıcı -> pad_lead kadar geri çek (konuşma başı atak/hece payı)
        padded_intervals: List[Tuple[float, float]] = []
        for s_raw, e_raw in candidate_silences:
            s_pad = s_raw if s_raw <= 0.05 else (s_raw + self.pad_trailing_sec)
            e_pad = e_raw if e_raw >= (analysis.duration - 0.05) else (e_raw - self.pad_lead_sec)
            # Güvenlik payı uygulandıktan sonra en az 100ms sessizlik kalmalı
            if (e_pad - s_pad) >= 0.10:
                padded_intervals.append((round(s_pad, 4), round(e_pad, 4)))

        # 6. Kelime Koruması (Word Guard): kesimlerden korumalı aralıkları çıkar
        if protected_intervals:
            padded_intervals = self._subtract_intervals(padded_intervals, protected_intervals)

        # 7. Kenar İnce Ayarı (RMS Lokal Enerji Minimumuna Tek Yönlü Kaydırma)
        refined_intervals: List[Tuple[float, float]] = []
        for s, e in padded_intervals:
            s_ref = 0.0 if s <= 0.08 else analysis.find_energy_minimum(s, search_window_sec=0.05, direction="forward_only")
            e_ref = analysis.duration if e >= (analysis.duration - 0.08) else analysis.find_energy_minimum(e, search_window_sec=0.05, direction="backward_only")
            if (e_ref - s_ref) >= 0.10:
                refined_intervals.append((round(s_ref, 3), round(e_ref, 3)))

        # CutItem listesine dönüştür
        cuts: List[CutItem] = []
        for idx, (c_start, c_end) in enumerate(refined_intervals, start=1):
            cuts.append(CutItem(
                id=f"cut_silence_{idx}",
                start=round(c_start, 2),
                end=round(c_end, 2),
                reason="silence",
                source="auto"
            ))

        logger.info(
            f"✅ Jump-Cut v2 tamamlandı: {len(cuts)} sessiz kesim bölgesi üretildi. "
            f"Toplam kesilen sessizlik: {sum(c.end - c.start for c in cuts):.1f}s"
        )
        return cuts

    def _merge_intervals(self, intervals: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Çakışan veya ardışık aralıkları birleştirir."""
        if not intervals:
            return []
        sorted_ints = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_ints[0]]
        for cur_s, cur_e in sorted_ints[1:]:
            prev_s, prev_e = merged[-1]
            if cur_s <= prev_e:
                merged[-1] = (prev_s, max(prev_e, cur_e))
            else:
                merged.append((cur_s, cur_e))
        return merged

    def _subtract_intervals(
        self,
        base_intervals: List[Tuple[float, float]],
        to_remove: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """base_intervals aralıklarından to_remove aralıklarını çıkarır."""
        if not to_remove:
            return base_intervals

        result: List[Tuple[float, float]] = []
        for b_start, b_end in base_intervals:
            current_pieces = [(b_start, b_end)]
            for r_start, r_end in to_remove:
                next_pieces = []
                for p_start, p_end in current_pieces:
                    # Çakışma yok
                    if r_end <= p_start or r_start >= p_end:
                        next_pieces.append((p_start, p_end))
                    else:
                        # Sol parça
                        if r_start > p_start and (r_start - p_start) >= 0.08:
                            next_pieces.append((p_start, r_start))
                        # Sağ parça
                        if r_end < p_end and (p_end - r_end) >= 0.08:
                            next_pieces.append((r_end, p_end))
                current_pieces = next_pieces
            result.extend(current_pieces)

        return result

    def _detect_legacy(self, audio_path: str) -> List[CutItem]:
        """Eski pydub tabanlı sessizlik tespiti."""
        logger.info(f"[Legacy] Sessizlik algılama başlıyor: {audio_path}")
        cuts = []
        try:
            import importlib
            pydub_mod = importlib.import_module("pydub")
            pydub_silence = importlib.import_module("pydub.silence")
            AudioSegment = pydub_mod.AudioSegment
            detect_silence = pydub_silence.detect_silence

            ext = Path(audio_path).suffix.lower()
            if ext == ".mp3":
                audio = AudioSegment.from_mp3(audio_path)
            elif ext in (".wav", ".wave"):
                audio = AudioSegment.from_wav(audio_path)
            else:
                audio = AudioSegment.from_file(audio_path)

            silent_ranges_ms = detect_silence(
                audio,
                min_silence_len=self.legacy_min_silence_len,
                silence_thresh=self.legacy_silence_thresh
            )

            merged_silences = []
            for current in silent_ranges_ms:
                if not merged_silences:
                    merged_silences.append(current)
                else:
                    prev = merged_silences[-1]
                    gap = current[0] - prev[1]
                    if gap < 50.0:
                        merged_silences[-1] = (prev[0], current[1])
                    else:
                        merged_silences.append(current)

            for idx, (start_ms, end_ms) in enumerate(merged_silences, start=1):
                start_sec = max(0.0, (start_ms / 1000.0) + self.pad_sec)
                end_sec = max(start_sec, (end_ms / 1000.0) - self.pad_sec)
                if end_sec - start_sec >= 0.2:
                    cuts.append(CutItem(
                        id=f"cut_silence_{idx}",
                        start=round(start_sec, 2),
                        end=round(end_sec, 2),
                        reason="silence",
                        source="auto"
                    ))
        except Exception as e:
            logger.error(f"[Legacy] Sessizlik algılama hatası: {e}", exc_info=True)

        return cuts
