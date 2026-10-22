"""
timeline_mapper.py — OtoEdit Zaman Haritalama (Timeline Remapping) Motoru.

Kesilmiş video zaman çizgisine (keep_segments) göre altyazıları (transcript, karaoke words)
ve kaplamaları (text/image overlays) milisaniyesine kadar kaydırır ve kesilen aralıklardaki
içerikleri temizler.
"""
from typing import List, Tuple, Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class TimelineMapper:
    """Orijinal video zaman çizgisini kesilmiş nihai video zaman çizgisine dönüştürür."""

    @staticmethod
    def remap_timestamp(t: float, keep_segments: List[Tuple[float, float]], tolerance: float = 0.02, actual_durations: Optional[List[float]] = None) -> Optional[float]:
        """
        Orijinal videodaki 't' saniyesini kesilmiş videodaki yeni saniyesine dönüştürür.
        Eğer 't' kesilen/silinen bir bölgedeyse None döner.
        """
        if not keep_segments:
            return round(t, 3)

        accumulated_duration = 0.0

        for i, (start, end) in enumerate(keep_segments):
            expected_dur = end - start
            actual_dur = actual_durations[i] if actual_durations and i < len(actual_durations) else expected_dur
            
            # Segment sınırlarında küçük kaymalar için toleranslı kontrol
            if (start - tolerance) <= t <= (end + tolerance):
                clamped_t = max(start, min(end, t))
                # Segment içindeki offset, videonun kendisi esnemediği için sabittir
                offset = clamped_t - start
                return round(accumulated_duration + offset, 3)

            accumulated_duration += actual_dur

        return None

    @staticmethod
    def remap_range(start: float, end: float, keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> Optional[Tuple[float, float]]:
        """
        Bir zaman aralığını [start, end] kesilmiş videodaki yeni aralığına dönüştürür.
        Eğer aralık tamamen kesilmiş bir bölgedeyse None döner.
        Eğer aralık korunan segmentlerle kesişiyorsa, ilk görünür başlangıç noktasını ve
        toplam görünür süreyi (kesimler düşülmüş olarak) yeni zamana haritalar.
        """
        if not keep_segments:
            return (round(start, 3), round(end, 3))

        accumulated_duration = 0.0
        first_new_start: Optional[float] = None
        total_visible_dur = 0.0

        for i, (seg_start, seg_end) in enumerate(keep_segments):
            expected_dur = seg_end - seg_start
            actual_dur = actual_durations[i] if actual_durations and i < len(actual_durations) else expected_dur

            inter_start = max(start, seg_start)
            inter_end = min(end, seg_end)
            overlap = inter_end - inter_start

            if overlap > 0.01:
                if first_new_start is None:
                    first_new_start = accumulated_duration + (inter_start - seg_start)
                total_visible_dur += overlap

            accumulated_duration += actual_dur

        if first_new_start is None or total_visible_dur <= 0.01:
            return None

        return (round(first_new_start, 3), round(first_new_start + total_visible_dur, 3))

    @staticmethod
    def remap_timestamp_nearest(t: float, keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> float:
        """
        Orijinal videodaki 't' saniyesini kesilmiş videodaki en yakın sekans saniyesine dönüştürür
        (Frontend getVisTimeFromRawTime ile %100 birebir aynı davranış).
        """
        if not keep_segments:
            return round(max(0.0, t), 3)

        accumulated_duration = 0.0
        for i, (start, end) in enumerate(keep_segments):
            expected_dur = end - start
            actual_dur = actual_durations[i] if actual_durations and i < len(actual_durations) else expected_dur
            if t < start:
                return round(accumulated_duration, 3)
            if start <= t <= end:
                return round(accumulated_duration + (t - start), 3)
            accumulated_duration += actual_dur

        return round(accumulated_duration, 3)

    @staticmethod
    def remap_overlays(overlays: List[Dict[str, Any]], keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        Kullanıcının eklediği metin, logo, video ve görsel kaplamaların zamanlarını kesilmiş videoya göre ayarlar.
        Her zaman ham kaynak zamanını (`timestamp`) esas alarak `keep_segments` üzerinden sekans zamanına kaydırır;
        kesilen (silinen) bölgelerin içindeki katmanları temizler ve kısmen kesilenlerin süresini kırpar.
        """
        if not overlays:
            return []
        if not keep_segments:
            return list(overlays)

        remapped_overlays = []
        for ov in overlays:
            raw_ts_val = ov.get("timestamp")
            if raw_ts_val is None:
                seq_ts = ov.get("seqTimestamp") if ov.get("seqTimestamp") is not None else ov.get("seq_timestamp")
                if seq_ts is not None:
                    try:
                        new_t = round(max(0.0, float(seq_ts)), 3)
                        new_ov = dict(ov)
                        new_ov["timestamp"] = new_t
                        remapped_overlays.append(new_ov)
                    except (ValueError, TypeError):
                        pass
                continue

            try:
                orig_t = float(raw_ts_val)
                orig_dur = float(ov.get("duration", 3.0) or 3.0)
            except (ValueError, TypeError):
                continue

            mapped_range = TimelineMapper.remap_range(
                orig_t, orig_t + max(0.05, orig_dur), keep_segments, actual_durations=actual_durations
            )
            if mapped_range is None:
                # Tamamen kesilen/silinen bölgede kalan katmanı filtrele
                continue

            new_start, new_end = mapped_range
            new_ov = dict(ov)
            new_ov["timestamp"] = round(max(0.0, new_start), 3)
            new_ov["seqTimestamp"] = new_ov["timestamp"]
            if "duration" in new_ov:
                new_ov["duration"] = round(max(0.1, new_end - new_start), 3)
            remapped_overlays.append(new_ov)

        logger.info(f"TimelineMapper: {len(overlays)} overlay -> {len(remapped_overlays)} korunan overlay dönüştürüldü.")
        return remapped_overlays

    @staticmethod
    def remap_transcript(transcript: Optional[Dict[str, Any]], keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> Optional[Dict[str, Any]]:
        """
        Whisper transkriptindeki cümle ve kelime (karaoke) zamanlarını yeni videoya haritalar.
        Kesilen kısımlardaki kelimeleri ve silinen cümleleri temizler.
        """
        if not transcript or not isinstance(transcript, dict) or "segments" not in transcript:
            return transcript
        if not keep_segments:
            return transcript

        segments = transcript.get("segments", [])
        remapped_segments = []

        for segment in segments:
            try:
                orig_start = float(segment.get("start", 0.0))
                orig_end = float(segment.get("end", 0.0))
            except (ValueError, TypeError):
                continue

            words = segment.get("words", [])
            if words and isinstance(words, list):
                remapped_words = []
                for word in words:
                    try:
                        w_start = float(word.get("start", orig_start))
                        w_end = float(word.get("end", orig_end))
                    except (ValueError, TypeError):
                        continue

                    mapped_w = TimelineMapper.remap_range(w_start, w_end, keep_segments, actual_durations=actual_durations)
                    if mapped_w is not None:
                        new_w = dict(word)
                        new_w["start"] = mapped_w[0]
                        new_w["end"] = mapped_w[1]
                        remapped_words.append(new_w)

                if remapped_words:
                    new_seg = dict(segment)
                    new_seg["start"] = remapped_words[0]["start"]
                    new_seg["end"] = remapped_words[-1]["end"]
                    new_seg["words"] = remapped_words
                    remapped_segments.append(new_seg)
            else:
                mapped_range = TimelineMapper.remap_range(orig_start, orig_end, keep_segments, actual_durations=actual_durations)
                if mapped_range is not None:
                    new_seg = dict(segment)
                    new_seg["start"] = mapped_range[0]
                    new_seg["end"] = mapped_range[1]
                    remapped_segments.append(new_seg)

        logger.info(
            f"TimelineMapper: {len(segments)} transkript segmenti -> {len(remapped_segments)} korunan segmente dönüştürüldü."
        )
        result = dict(transcript)
        result["segments"] = remapped_segments
        return result
