from typing import List, Dict, Any, Optional
from models.command_model import CommandType, ParsedCommand
from models.edl_model import (
    CutItem, EdlDocument, EdlSettings, OverlayItem,
    RepurposingData, SuggestionItem
)
from models.transcript_model import TranscriptResult
from utils.constants import VideoFormat
from utils.logger import get_logger

logger = get_logger(__name__)


class EdlBuilder:
    """Tüm analiz aşamalarının çıktılarını standart EDL (Edit Decision List) JSON dokümanına birleştiren motor."""

    def build(
        self,
        project_id: str,
        video_id: str,
        transcript: TranscriptResult,
        silence_cuts: List[CutItem],
        commands: List[ParsedCommand],
        face_data: List[Dict[str, Any]],
        repurposing_data: RepurposingData,
        suggestions: List[SuggestionItem],
        video_format: int = 0
    ) -> Dict[str, Any]:
        """Tüm analiz çıktılarını tek bir EDL JSON sözlüğüne derler."""
        logger.info(f"EDL dokümanı inşa ediliyor: ProjectId={project_id}, VideoId={video_id}")

        target_format_str = VideoFormat.TO_STRING.get(video_format, "16:9")
        cuts: List[CutItem] = list(silence_cuts)
        overlays: List[OverlayItem] = []

        # 1. Çoklu-modal komutları EDL'ye dönüştür
        for idx, cmd in enumerate(commands, start=1):
            # Komut verilme anını (el hareketi + konuşma süresi) videodan kesip at
            if cmd.start is not None and cmd.end is not None and (cmd.end - cmd.start) > 0.1:
                cuts.append(CutItem(
                    id=f"cut_cmd_moment_{idx}",
                    start=cmd.start,
                    end=cmd.end,
                    reason="command_moment_cut",
                    source="auto",
                    command=cmd.raw_text
                ))

            # Komut türüne göre aksiyon
            if cmd.command_type == CommandType.CUT:
                cuts.append(CutItem(
                    id=f"cut_user_gesture_{idx}",
                    start=cmd.timestamp,
                    end=cmd.timestamp + 5.0,  # Varsayılan kesim penceresi
                    reason="gesture_dislike",
                    source="auto",
                    command=cmd.raw_text
                ))
            elif cmd.command_type == CommandType.ADD_TEXT and cmd.payload:
                overlays.append(OverlayItem(
                    id=f"overlay_text_{idx}",
                    type="text",
                    content=cmd.payload,
                    timestamp=cmd.timestamp,
                    duration=5.0,
                    font="Montserrat-Bold",
                    fontSize=52,
                    color="#FFFFFF",
                    position=["center", "bottom"],
                    animation="pop-up"
                ))
            elif cmd.command_type == CommandType.ADD_IMAGE and cmd.payload:
                overlays.append(OverlayItem(
                    id=f"overlay_img_{idx}",
                    type="image",
                    content=cmd.payload,
                    timestamp=cmd.timestamp,
                    duration=4.0,
                    position=["center", "center"],
                    animation="slide-left"
                ))

        # Cuts listesini kronolojik sırala ve çakışanları düzelt
        sorted_cuts = self._merge_overlapping_cuts(cuts)

        # 2. Transkripti JSON-friendly yapıya çevir
        transcript_dict = {
            "fullText": transcript.full_text,
            "duration": transcript.duration,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "words": [{"word": w.word, "start": w.start, "end": w.end} for w in seg.words]
                }
                for seg in transcript.segments
            ]
        }

        # 3. Repurposing verisine yüz takibini ekle
        repurposing_data.faceTrackingData = face_data

        # 4. EDL dokümanını oluştur
        edl = EdlDocument(
            projectId=project_id,
            videoId=video_id,
            duration=transcript.duration,
            settings=EdlSettings(
                targetFormat=target_format_str,
                faceTrackingEnabled=(target_format_str in ("9:16", "1:1")),
                gestureCommandsEnabled=len(commands) > 0
            ),
            transcript=transcript_dict,
            cuts=sorted_cuts,
            overlays=overlays,
            suggestions=suggestions,
            repurposing=repurposing_data
        )

        logger.info(f"EDL dokümanı başarıyla inşa edildi: {len(sorted_cuts)} kesim, {len(overlays)} overlay, {len(suggestions)} öneri.")
        return edl.model_dump()

    @staticmethod
    def _merge_overlapping_cuts(cuts: List[CutItem]) -> List[CutItem]:
        """Zaman aralıkları çakışan kesimleri birleştirir."""
        if not cuts:
            return []

        sorted_cuts = sorted(cuts, key=lambda c: c.start)
        merged: List[CutItem] = [sorted_cuts[0]]

        for current in sorted_cuts[1:]:
            prev = merged[-1]
            if current.start <= prev.end:
                # Çakışma var: Birleştir
                prev.end = max(prev.end, current.end)
                prev.reason = f"{prev.reason}+{current.reason}"
            else:
                merged.append(current)

        return merged
