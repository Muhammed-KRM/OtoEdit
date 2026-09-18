from typing import List
from models.edl_model import RepurposingData, ViralClipItem
from models.transcript_model import TranscriptResult
from services.gemini_client import GeminiClient
from utils.logger import get_logger

logger = get_logger(__name__)


class RepurposingEngine:
    """Yapay zeka ile videonun en viral 30sn (Reels) ve 90sn (Shorts) anlarını tespit eden motor."""

    def __init__(self):
        self.gemini_client = GeminiClient()

    def analyze(self, transcript: TranscriptResult) -> RepurposingData:
        """Transkripti inceleyip viral klip önerilerini döner."""
        logger.info(f"Repurposing analizi başlıyor (süre={transcript.duration:.1f}s)")

        raw_clips = self.gemini_client.find_viral_clips(transcript.full_text, transcript.duration)
        clip_items = []

        for clip in raw_clips:
            try:
                clip_items.append(ViralClipItem(
                    id=clip.get("id", f"clip_{len(clip_items)+1}"),
                    title=clip.get("title", "Viral Klip"),
                    start=float(clip.get("start", 0.0)),
                    end=float(clip.get("end", 0.0)),
                    duration=float(clip.get("duration", 30.0)),
                    targetFormat=clip.get("targetFormat", "9:16"),
                    viralityScore=int(clip.get("viralityScore", 80)),
                    reason=clip.get("reason", "Önemli an")
                ))
            except Exception as e:
                logger.warning(f"Klip verisi dönüştürülemedi: {e}")

        logger.info(f"Repurposing tamamlandı: {len(clip_items)} viral klip belirlendi.")
        return RepurposingData(clips=clip_items)
