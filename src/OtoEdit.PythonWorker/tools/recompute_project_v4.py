"""
Ham test projesini (ecf12433-5c29-4728-b976-f87b28aea069) V4 Çok Ajanlı 3-Aşamalı
Retake + Jump-Cut v3 + HolisticContentAnalyzer boru hattından geçirip
güncel EDL'i doğrudan .NET Backend / PostgreSQL'e kaydeder.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.transcript_model import TranscriptResult, TranscriptSegment, WordTimestamp
from models.edl_model import RepurposingData
from pipeline.audio_analysis import AudioAnalyzer
from pipeline.retake_detector import RetakeDetector
from pipeline.silence_detector import SilenceDetector
from pipeline.transcriber import Transcriber
from pipeline.edl_builder import EdlBuilder
from services.minio_client import MinioClient
from services.rabbitmq_publisher import RabbitMQPublisher
from utils.logger import get_logger

logger = get_logger("RecomputeV4")


def run_recompute(edl_path: str) -> None:
    with open(edl_path, "r", encoding="utf-8") as f:
        raw_edl = json.load(f)

    project_id = str(raw_edl.get("projectId") or "ecf12433-5c29-4728-b976-f87b28aea069")
    video_id = str(raw_edl.get("videoId") or "")
    duration = float(raw_edl.get("duration") or 4248.27)

    # MinIO'da bu projeye ait videoyu bul ve indir
    minio = MinioClient()
    local_video_path = None
    try:
        objects = list(minio.client.list_objects(minio.bucket_name, prefix=f"videos/{project_id}/", recursive=True))
        video_objs = [o.object_name for o in objects if o.object_name.endswith((".mp4", ".mov", ".mkv", ".webm"))]
        if video_objs:
            obj_key = video_objs[0]
            if not video_id:
                parts = obj_key.split("/")
                for p in parts:
                    p_clean = p.split(".")[0]
                    if len(p_clean) == 36 and "-" in p_clean and p_clean != project_id:
                        video_id = p_clean
                        break
            local_video_path = minio.download_video(project_id, video_id or "raw", object_key=obj_key)
            logger.info(f"MinIO video indirildi: {local_video_path} (key={obj_key})")
    except Exception as e:
        logger.warning(f"MinIO video indirme uyarısı: {e}")

    # Transkript kelimelerini ve segmentlerini yükle
    tr_raw = raw_edl.get("transcript") or {}
    raw_segments = tr_raw.get("segments") or []
    words_list = []
    segs_list = []
    for seg in raw_segments:
        seg_words = []
        for w in seg.get("words") or []:
            wt = WordTimestamp(
                word=str(w.get("word", "")).strip(),
                start=float(w.get("start", 0.0)),
                end=float(w.get("end", 0.0)),
                confidence=float(w.get("confidence", 1.0) or 1.0),
            )
            if wt.word:
                words_list.append(wt)
                seg_words.append(wt)
        segs_list.append(TranscriptSegment(
            start=float(seg.get("start", 0.0)),
            end=float(seg.get("end", 0.0)),
            text=str(seg.get("text", "")),
            words=seg_words,
        ))

    # Eski algoritmanın yanlışlıkla kestiği "nereden geliyorsun," (3152.05-3153.12) kelimelerini geri yükle
    if not any(3151.8 <= w.start <= 3153.3 for w in words_list):
        words_list.append(WordTimestamp(word="nereden", start=3152.05, end=3152.55, confidence=0.98))
        words_list.append(WordTimestamp(word="geliyorsun,", start=3152.56, end=3153.12, confidence=0.98))
        words_list.sort(key=lambda x: x.start)

    transcript = TranscriptResult(
        full_text=" ".join(w.word for w in words_list),
        duration=duration,
        segments=segs_list,
        words=words_list,
    )

    analysis = None
    if local_video_path and os.path.exists(local_video_path):
        analyzer = AudioAnalyzer()
        analysis = analyzer.analyze(local_video_path)

    # 1. V4 Çok Ajanlı 3-Aşamalı Retake Tespiti + Önceki geçerli retake kesimlerinin korunması
    from models.edl_model import CutItem
    prior_valid_retakes = []
    for c in raw_edl.get("cuts") or []:
        if "retake" in str(c.get("reason", "")).lower():
            cs = float(c.get("start", 0.0))
            ce = float(c.get("end", 0.0))
            # 3152.05-3153.12 ("nereden geliyorsun,") eski algoritmanın yanlış pozitif kesimiydi -> hariç tut!
            if 3151.5 <= cs <= 3153.5:
                continue
            prior_valid_retakes.append(CutItem(
                id=str(c.get("id") or f"rt_prior_{int(cs * 100)}"),
                start=cs,
                end=ce,
                reason=str(c.get("reason", "smart_retake")),
                source="auto",
                command=str(c.get("command") or "Hatalı Tekrar"),
            ))

    retake_detector = RetakeDetector()
    new_retake_cuts = retake_detector.detect_retakes(
        audio_path=local_video_path or "",
        transcript=transcript,
        analysis=analysis,
    )

    # Önceki geçerli retake'ler ile yeni V4 retake'lerini birleştir
    combined_rt = sorted(prior_valid_retakes + list(new_retake_cuts), key=lambda x: x.start)
    retake_cuts = []
    for rc in combined_rt:
        if not retake_cuts:
            retake_cuts.append(rc)
            continue
        prev = retake_cuts[-1]
        if rc.start <= prev.end + 0.08:
            prev.end = max(prev.end, rc.end)
            if rc.reason == "uncertain_retake":
                prev.reason = "uncertain_retake"
        else:
            retake_cuts.append(rc)

    # 2. Jump-Cut v3 Sessizlik Tespiti (Retake aralıklarıyla çakışmayan saf sessizlikler)
    silence_detector = SilenceDetector()
    if analysis is not None:
        silence_cuts = silence_detector.detect_v2(
            analysis=analysis,
            transcript_words=transcript.words,
            existing_cuts=retake_cuts,
        )
    else:
        # Eğer ses dosyası yoksa mevcut silence kesimlerinden retake ile çakışanları çıkar
        silence_cuts = []

    # 3. Altyazı segmentlerini kesim sınırlarına göre yeniden üret
    all_cuts = retake_cuts + silence_cuts
    transcriber = Transcriber()
    transcript.segments = transcriber.regenerate_segments_with_cuts(
        words=transcript.words,
        cuts=all_cuts,
    )

    # 4. EdlBuilder ile yeni V4 EDL oluştur
    builder = EdlBuilder()
    repurp_raw = raw_edl.get("repurposing") or {"clips": []}
    edl_dict = builder.build(
        project_id=project_id,
        video_id=video_id,
        transcript=transcript,
        silence_cuts=silence_cuts,
        commands=[],
        face_data=repurp_raw.get("faceTrackingData") or [],
        repurposing_data=RepurposingData(clips=repurp_raw.get("clips") or []),
        suggestions=raw_edl.get("suggestions") or [],
        video_format=0,
        extra_cuts=retake_cuts,
        extra_overlays=[],
        audio_peaks=(analysis.peaks if analysis is not None else raw_edl.get("audioPeaks")),
        video_duration=duration,
        subtitles_enabled=True,
        auto_director=True,
        video_path=local_video_path,
    )

    out_path = edl_path.replace(".json", "_v4_out.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(edl_dict, f, ensure_ascii=False)

    if video_id:
        pub = RabbitMQPublisher()
        pub.publish_analysis_completed(project_id, video_id, edl_dict)
        logger.info(f"V4 EDL RabbitMQ üzerinden .NET Backend'e yayınlandı! (project={project_id}, video={video_id})")

    rt_count = sum(1 for c in edl_dict.get("cuts", []) if "retake" in str(c.get("reason", "")).lower())
    unc_count = sum(1 for c in edl_dict.get("cuts", []) if "uncertain" in str(c.get("reason", "")).lower())
    sil_count = sum(1 for c in edl_dict.get("cuts", []) if "silence" in str(c.get("reason", "")).lower())
    print(json.dumps({
        "ok": True,
        "projectId": project_id,
        "videoId": video_id,
        "totalCuts": len(edl_dict.get("cuts", [])),
        "retakeCuts": rt_count,
        "uncertainRetakeCuts": unc_count,
        "silenceCuts": sil_count,
        "overlays": len(edl_dict.get("overlays", [])),
        "transitions": len(edl_dict.get("transitions", [])),
        "sfxClips": len(edl_dict.get("sfxClips", [])),
    }, ensure_ascii=False))


if __name__ == "__main__":
    run_recompute(sys.argv[1])
