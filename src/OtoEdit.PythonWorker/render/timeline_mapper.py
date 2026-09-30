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
    def remap_timestamp(t: float, keep_segments: List[Tuple[float, float]], tolerance: float = 0.02) -> Optional[float]:
        """
        Orijinal videodaki 't' saniyesini kesilmiş videodaki yeni saniyesine dönüştürür.
        Eğer 't' kesilen/silinen bir bölgedeyse None döner.
        """
        if not keep_segments:
            return round(t, 3)

        accumulated_duration = 0.0

        for (start, end) in keep_segments:
            # Segment sınırlarında küçük kaymalar için toleranslı kontrol
            if (start - tolerance) <= t <= (end + tolerance):
                clamped_t = max(start, min(end, t))
                return round(accumulated_duration + (clamped_t - start), 3)

            accumulated_duration += (end - start)

        return None

    @staticmethod
    def remap_range(start: float, end: float, keep_segments: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """
        Bir zaman aralığını [start, end] kesilmiş videodaki yeni aralığına dönüştürür.
        Eğer aralık tamamen kesilmiş bir bölgedeyse None döner.
        Eğer aralık korunan bir segmentle kesişiyorsa, kesişen kısmı yeni zamana haritalar.
        """
        if not keep_segments:
            return (round(start, 3), round(end, 3))

        accumulated_duration = 0.0
        best_overlap = 0.0
        best_range: Optional[Tuple[float, float]] = None

        for (seg_start, seg_end) in keep_segments:
            inter_start = max(start, seg_start)
            inter_end = min(end, seg_end)
            overlap = inter_end - inter_start

            if overlap > best_overlap:
                best_overlap = overlap
                new_start = accumulated_duration + (inter_start - seg_start)
                new_end = accumulated_duration + (inter_end - seg_start)
                best_range = (round(new_start, 3), round(new_end, 3))

            accumulated_duration += (seg_end - seg_start)

        # Eğer overlap çok küçükse (örn. sıfır süre veya tek nokta) remap_timestamp ile bak
        if best_overlap <= 0.01:
            t_mapped = TimelineMapper.remap_timestamp(start, keep_segments)
            if t_mapped is not None and end >= start:
                dur = max(0.01, end - start)
                return (round(t_mapped, 3), round(t_mapped + dur, 3))
            return None

        return best_range

    @staticmethod
    def remap_overlays(overlays: List[Dict[str, Any]], keep_segments: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """
        Kullanıcının eklediği metin, logo ve görsel kaplamaların zamanlarını yeni videoya göre ayarlar.
        Kesilen bölgelerde kalan objeler otomatik olarak elenir.
        """
        if not overlays:
            return []
        if not keep_segments:
            return list(overlays)

        remapped_overlays = []
        for ov in overlays:
            try:
                orig_t = float(ov.get("timestamp", 0.0))
            except (ValueError, TypeError):
                continue

            new_t = TimelineMapper.remap_timestamp(orig_t, keep_segments)
            if new_t is not None:
                new_ov = dict(ov)
                new_ov["timestamp"] = new_t
                remapped_overlays.append(new_ov)
            else:
                logger.debug(f"Overlay kesilen bölgede kaldığı için elendi: {ov.get('content') or ov.get('source') or ov}")

        logger.info(f"TimelineMapper: {len(overlays)} overlay -> {len(remapped_overlays)} korunan overlay dönüştürüldü.")
        return remapped_overlays

    @staticmethod
    def remap_transcript(transcript: Optional[Dict[str, Any]], keep_segments: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
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

                    mapped_w = TimelineMapper.remap_range(w_start, w_end, keep_segments)
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
                mapped_range = TimelineMapper.remap_range(orig_start, orig_end, keep_segments)
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
