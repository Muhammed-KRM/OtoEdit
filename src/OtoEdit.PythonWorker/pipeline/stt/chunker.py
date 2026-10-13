"""
OtoEdit Akıllı Ses Parçalayıcı (Chunker)
- Hedef parça uzunluğu STT_CHUNK_MAX_SEC (varsayılan 600 sn / 10 dk).
- Parça sınırları hedef noktanın ±60 sn içindeki en uzun VAD sessizliğinin ortasına konur.
- Tamamen sessiz parçalar STT'ye gönderilmez.
- 16 kHz mono 32 kbps MP3 formatında hızlıca dışa aktarılır (10 dk ≈ 2.4 MB).
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from config import Config
from pipeline.audio_analysis import AudioAnalysis
from utils.logger import get_logger

logger = get_logger("STT.Chunker")


@dataclass
class AudioChunk:
    index: int
    start_sec: float
    end_sec: float
    audio_path: str
    has_speech: bool = True

    @property
    def duration(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


class AudioChunker:
    """VAD sessizlik sınırlarına göre akıllı parçalama motoru."""

    def __init__(self, max_chunk_sec: float = None):
        self.max_chunk_sec = max_chunk_sec or float(Config.STT_CHUNK_MAX_SEC)

    def calculate_split_points(self, analysis: AudioAnalysis) -> List[float]:
        """Parçalama sınır saniyelerini belirler (0.0 hariç)."""
        duration = analysis.duration
        if duration <= self.max_chunk_sec:
            return [duration]

        split_points: List[float] = []
        current_pos = 0.0
        silences = analysis.get_silence_regions(min_silence_sec=0.2)

        while current_pos + self.max_chunk_sec < duration:
            target = current_pos + self.max_chunk_sec
            window_min = max(current_pos + 60.0, target - 60.0)
            window_max = min(duration - 30.0, target + 60.0)

            # Arama penceresine düşen sessizlikleri bul
            candidate_silences = []
            for s_start, s_end in silences:
                # Sessizlik pencereyle kesişiyor mu?
                if s_end > window_min and s_start < window_max:
                    cand_start = max(s_start, window_min)
                    cand_end = min(s_end, window_max)
                    cand_len = cand_end - cand_start
                    if cand_len > 0:
                        candidate_silences.append((cand_len, (s_start + s_end) / 2.0))

            if candidate_silences:
                # En uzun sessizliğin ortasını sınır olarak seç
                candidate_silences.sort(key=lambda x: x[0], reverse=True)
                split_at = candidate_silences[0][1]
            else:
                # Sessizlik yoksa hedef nokta civarındaki en düşük enerjili noktayı seç
                split_at = analysis.find_energy_minimum(target, search_window_sec=3.0)

            split_at = round(float(split_at), 3)
            # İlerleme garantisi
            if split_at <= current_pos + 30.0:
                split_at = round(target, 3)

            split_points.append(split_at)
            current_pos = split_at

        if not split_points or split_points[-1] < duration:
            split_points.append(round(duration, 3))

        return split_points

    def split(
        self,
        media_path: str,
        analysis: AudioAnalysis,
        output_dir: Path = None
    ) -> List[AudioChunk]:
        """Videoyu/sesi parçalara böler ve MP3 olarak dışa aktarır."""
        target_dir = output_dir or Config.TEMP_DIR
        os.makedirs(target_dir, exist_ok=True)

        split_points = self.calculate_split_points(analysis)
        chunks: List[AudioChunk] = []
        current_pos = 0.0

        stem = Path(media_path).stem

        for idx, split_end in enumerate(split_points, start=1):
            chunk_start = current_pos
            chunk_end = split_end
            current_pos = split_end

            # Bu parçada konuşma var mı kontrol et
            has_speech = any(
                r.end > chunk_start and r.start < chunk_end
                for r in analysis.speech_regions
            )

            chunk_file = str(target_dir / f"{stem}_chunk_{idx:02d}.mp3")

            if has_speech:
                # FFmpeg ile 16kHz mono 32kbps MP3 olarak kes
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(chunk_start),
                    "-to", str(chunk_end),
                    "-i", media_path,
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-ar", "16000",
                    "-ac", "1",
                    "-b:a", "32k",
                    chunk_file
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                file_size_kb = os.path.getsize(chunk_file) / 1024.0
                logger.info(
                    f"📦 Parça {idx} oluşturuldu: {chunk_start:.1f}s -> {chunk_end:.1f}s "
                    f"({chunk_end - chunk_start:.1f}s, {file_size_kb:.0f} KB)"
                )
            else:
                logger.info(
                    f"🔇 Parça {idx} tamamen sessiz, STT için atlanıyor: "
                    f"{chunk_start:.1f}s -> {chunk_end:.1f}s"
                )

            chunks.append(AudioChunk(
                index=idx,
                start_sec=chunk_start,
                end_sec=chunk_end,
                audio_path=chunk_file if has_speech else "",
                has_speech=has_speech
            ))

        return chunks

    @staticmethod
    def cleanup_chunks(chunks: List[AudioChunk]):
        """Oluşturulan geçici MP3 parçalarını temizler."""
        for c in chunks:
            if c.audio_path and os.path.exists(c.audio_path):
                try:
                    os.remove(c.audio_path)
                except Exception:
                    pass
