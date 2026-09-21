"""
OtoEdit Dinamik Altyazı Üretici (Dynamic ASS / Word-Level Subtitles)
Whisper kelime zaman damgalarını kullanarak sosyal medya tarzı karaoke vurgulu
veya dinamik renk geçişli ASS altyazı dosyası üretir.
"""
from pathlib import Path
from typing import List, Optional
from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp
from utils.logger import get_logger

logger = get_logger(__name__)


class DynamicSubtitleGenerator:
    """ASS (Advanced SubStation Alpha) formatında profesyonel dinamik altyazı üreten motor."""

    def __init__(
        self,
        font_name: str = "Montserrat ExtraBold",
        font_size: int = 24,
        primary_color: str = "&H00FFFFFF",      # Beyaz metin
        highlight_color: str = "&H0000FFFF",    # Canlı Sarı/Cyan aktif kelime
        outline_color: str = "&H00000000",      # Siyah kontur
        outline_width: int = 3,
        alignment: int = 2                       # Alt orta
    ):
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.highlight_color = highlight_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.alignment = alignment

    def generate_ass_file(
        self,
        transcript: TranscriptResult,
        output_path: str,
        video_width: int = 1920,
        video_height: int = 1080
    ) -> str:
        """
        Transkriptteki kelime zamanlamalarını baz alarak ASS dosyasını diske kaydeder.
        """
        logger.info(f"Dinamik ASS altyazı dosyası üretiliyor: {output_path}")

        # Font boyutunu ve alt kenar boşluğunu çözünürlüğe göre ölçekle
        scaled_font_size = max(18, int(self.font_size * (video_height / 1080.0)))
        margin_v = int(video_height * 0.12)  # Ekranın altından %12 yukarıda (güvenli alan)

        header = f"""[Script Info]
Title: OtoEdit Dynamic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font_name},{scaled_font_size},{self.primary_color},&H000000FF,{self.outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{self.outline_width},1,{self.alignment},30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # Her segmentteki kelimeleri 3 ila 5 kelimelik okunabilir bloklar halinde grupla
        for seg in transcript.segments:
            words = seg.words
            if not words:
                # Segmentte kelime ayrışımı yoksa tüm segmenti tek blok olarak bas
                if seg.text.strip():
                    start_str = self._format_ass_time(seg.start)
                    end_str = self._format_ass_time(seg.end)
                    events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{seg.text.strip()}")
                continue

            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue

                # Cümlenin o anki aktif kelimesini renklendirerek dinamik diyalog satırları oluştur
                for active_idx, target_word in enumerate(chunk):
                    w_start = self._format_ass_time(target_word.start)
                    w_end = self._format_ass_time(target_word.end)

                    line_parts = []
                    for idx, w in enumerate(chunk):
                        if idx == active_idx:
                            # Vurgulanan aktif kelime (renkli ve hafif büyütülmüş)
                            line_parts.append(f"{{\\c{self.highlight_color}\\fscx110\\fscy110}}{w.word}{{\\r}}")
                        else:
                            line_parts.append(w.word)

                    dialogue_text = " ".join(line_parts)
                    events.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{dialogue_text}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(events))

        logger.info(f"ASS altyazı dosyası başarıyla üretildi ({len(events)} satır): {output_path}")
        return output_path

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Saniyeyi ASS zaman formatına çevirir (H:MM:SS.cs)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int(round((seconds - int(seconds)) * 100))
        if centisecs >= 100:
            centisecs = 99
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
