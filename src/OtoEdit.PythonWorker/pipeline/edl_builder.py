from typing import List, Dict, Any, Optional
from models.command_model import CommandType, ParsedCommand
from models.edl_model import (
    CutItem, EdlDocument, EdlSettings, OverlayItem,
    RepurposingData, SuggestionItem
)
from models.transcript_model import TranscriptResult
from pipeline.proactive_director import ProactiveDirector
from utils.constants import VideoFormat
from utils.logger import get_logger

logger = get_logger(__name__)


class _AttrDict(dict):
    """Hem sözlük (d['k']) hem nesne (d.k) erişimini ve doğrudan JSON serileştirmeyi destekleyen dict."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'dict' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _to_attr_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return _AttrDict({k: _to_attr_dict(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_attr_dict(v) for v in obj]
    return obj


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
        video_format: int = 0,
        extra_cuts: Optional[List[CutItem]] = None,
        extra_overlays: Optional[List[OverlayItem]] = None,
        audio_peaks: Optional[List[float]] = None,
        video_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """Tüm analiz çıktılarını tek bir EDL JSON sözlüğüne derler."""
        logger.info(f"EDL dokümanı inşa ediliyor: ProjectId={project_id}, VideoId={video_id}")

        target_format_str = VideoFormat.TO_STRING.get(video_format, "16:9")
        cuts: List[CutItem] = list(silence_cuts)
        if extra_cuts:
            cuts.extend(extra_cuts)

        overlays: List[OverlayItem] = []
        if extra_overlays:
            overlays.extend(extra_overlays)

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

        # Editör kesimleri id ile güncellediği/sildiği için id'ler benzersiz olmalı
        seen_ids = set()
        for i, c in enumerate(sorted_cuts):
            if not c.id or c.id in seen_ids:
                c.id = f"{c.id or 'cut'}_{i}"
            seen_ids.add(c.id)

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
        if repurposing_data is not None:
            repurposing_data.faceTrackingData = face_data

        # Gerçek video süresini güvenceye al (Transkript hatasında 1.0s çöküşünü önle)
        effective_duration = float(video_duration) if (video_duration is not None and float(video_duration) > 0.1) else (
            float(transcript.duration) if (transcript and float(getattr(transcript, "duration", 0.0)) > 1.0) else 0.0
        )

        # 4. Otonom Yönetmen (ProactiveDirector) önerilerini üret
        proactive_sugs = []
        try:
            proactive_sugs = ProactiveDirector.generate_suggestions({
                "duration": effective_duration,
                "transcript": transcript_dict,
                "cuts": sorted_cuts,
                "overlays": overlays,
                "audioPeaks": audio_peaks,
                "settings": {"targetFormat": target_format_str},
            })
        except Exception as pd_err:
            logger.warning(f"ProactiveDirector öneri üretimi uyarısı: {pd_err}")

        # 5. EDL dokümanını oluştur
        edl = EdlDocument(
            projectId=project_id,
            videoId=video_id,
            duration=effective_duration,
            settings=EdlSettings(
                targetFormat=target_format_str,
                faceTrackingEnabled=(target_format_str in ("9:16", "1:1")),
                gestureCommandsEnabled=len(commands) > 0
            ),
            transcript=transcript_dict,
            cuts=sorted_cuts,
            overlays=overlays,
            suggestions=suggestions,
            proactiveSuggestions=proactive_sugs,
            repurposing=repurposing_data,
            audioPeaks=audio_peaks
        )

        logger.info(f"EDL dokümanı başarıyla inşa edildi: {len(sorted_cuts)} kesim, {len(overlays)} overlay, {len(suggestions)} öneri. Süre={effective_duration:.2f}s")
        dump_fn = getattr(edl, "model_dump", getattr(edl, "dict", None))
        raw_dict = dump_fn() if dump_fn else edl.__dict__
        return _to_attr_dict(raw_dict)

    @staticmethod
    def _merge_overlapping_cuts(cuts: List[CutItem]) -> List[CutItem]:
        """
        Zaman aralıkları çakışan kesimleri birleştirir.
        ÖNEMLİ KURAL: Yalnızca aynı türe sahip kesimler (silence ile silence, smart_retake ile smart_retake)
        birleştirilir. Farklı türler asla tek bloğa kaynaştırılmaz:
        sessizlik (silence) kesimleri, retake / komut gibi öncelikli kesimlerin aralıklarından
        ÇIKARILIR (kırpılır veya bölünür). Böylece editörde bir retake geri alındığında
        yanındaki sessizlik kesimi kesik kalmaya devam eder ve retake bloğu sessizliği yutmaz.
        """
        if not cuts:
            return []

        def merge_same_reason(items: List[CutItem]) -> List[CutItem]:
            out: List[CutItem] = []
            for cur in sorted(items, key=lambda c: c.start):
                if out and cur.reason == out[-1].reason and cur.start <= out[-1].end:
                    prev = out[-1]
                    prev.end = max(prev.end, cur.end)
                    if cur.command and cur.command not in (prev.command or ""):
                        prev.command = f"{prev.command} | {cur.command}" if prev.command else cur.command
                else:
                    out.append(cur)
            return out

        silence = [c for c in cuts if (c.reason or "") == "silence"]
        priority = [c for c in cuts if (c.reason or "") != "silence"]

        # Öncelikli kesimleri kendi türleri içinde birleştir
        by_reason: Dict[str, List[CutItem]] = {}
        for c in priority:
            by_reason.setdefault(c.reason or "", []).append(c)
        merged_priority: List[CutItem] = []
        for items in by_reason.values():
            merged_priority.extend(merge_same_reason(items))

        blockers = sorted((c.start, c.end) for c in merged_priority)

        # Sessizlikleri öncelikli kesimlerden çıkar
        clipped_silence: List[CutItem] = []
        for s in merge_same_reason(silence):
            pieces = [(s.start, s.end)]
            for b_start, b_end in blockers:
                if b_end <= s.start or b_start >= s.end:
                    continue
                next_pieces = []
                for p_start, p_end in pieces:
                    if b_end <= p_start or b_start >= p_end:
                        next_pieces.append((p_start, p_end))
                        continue
                    if b_start - p_start >= 0.05:
                        next_pieces.append((p_start, b_start))
                    if p_end - b_end >= 0.05:
                        next_pieces.append((b_end, p_end))
                pieces = next_pieces
            for k, (p_start, p_end) in enumerate(pieces):
                clipped_silence.append(CutItem(
                    id=s.id if k == 0 else f"{s.id}_{k}",
                    start=round(p_start, 3),
                    end=round(p_end, 3),
                    reason=s.reason,
                    source=getattr(s, "source", "auto"),
                    command=getattr(s, "command", None)
                ))

        return sorted(merged_priority + clipped_silence, key=lambda c: c.start)
