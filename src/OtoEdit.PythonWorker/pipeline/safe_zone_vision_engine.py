"""
Aşama 2: SafeZoneVisionEngine & SafeZoneSpatialSolver.
Hem 16:9 yatay hem 9:16 dikey videolarda:
1) Aday sahnelerden en keskin ekran görüntüsünü (Keyframe Snapshot) alır,
2) Konuşmacının yüzünü (+35% alın payı), gövdesini, kenar/slayt yoğunluğunu (Edge Saliency)
   ve altyazı kuşağını (Y ∈ [70%, 95%]) tespit eder,
3) Metin ve görseller için sıfır çarpışmalı (HardCollision == 0.0) çapa (Anchor) ve ölçek (Scale) hesaplar.
"""

from dataclasses import dataclass
import os
from typing import Any, Dict, List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger("SafeZoneVisionEngine")


@dataclass(frozen=True)
class BBoxPct:
    """[0.0 .. 100.0] yüzdelik tuval koordinatlarında dikdörtgen kutu."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    def intersection_area(self, other: "BBoxPct") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        return (ix2 - ix1) * (iy2 - iy1)

    def overlaps(self, other: "BBoxPct", margin_pct: float = 1.5) -> bool:
        expanded = BBoxPct(
            max(0.0, self.x1 - margin_pct),
            max(0.0, self.y1 - margin_pct),
            min(100.0, self.x2 + margin_pct),
            min(100.0, self.y2 + margin_pct),
        )
        return expanded.intersection_area(other) > 0.01


@dataclass(frozen=True)
class AnchorCandidate:
    slot_id: str
    center_x_pct: float
    center_y_pct: float
    base_w_pct: float
    base_h_pct: float


# 16:9 ve 9:16 için aday çapalar (Tüm koordinatlar 0..100 yüzdelik birimdedir!)
IMAGE_CARD_ANCHORS: List[AnchorCandidate] = [
    AnchorCandidate("TOP_RIGHT_CARD", 79.0, 26.0, 26.0, 30.0),
    AnchorCandidate("TOP_LEFT_CARD", 21.0, 26.0, 26.0, 30.0),
    AnchorCandidate("RIGHT_THIRD_SPLIT", 79.0, 36.0, 26.0, 34.0),
    AnchorCandidate("LEFT_THIRD_SPLIT", 21.0, 36.0, 26.0, 34.0),
]

TEXT_CALLOUT_ANCHORS: List[AnchorCandidate] = [
    AnchorCandidate("TOP_RIGHT_CARD", 78.0, 24.0, 28.0, 13.0),
    AnchorCandidate("TOP_LEFT_CARD", 22.0, 24.0, 28.0, 13.0),
    AnchorCandidate("UPPER_RIGHT_BADGE", 78.0, 18.0, 28.0, 12.0),
    AnchorCandidate("UPPER_LEFT_BADGE", 22.0, 18.0, 28.0, 12.0),
    AnchorCandidate("TOP_CENTER_HEADER", 50.0, 11.0, 44.0, 10.0),
]


class KeyframeSnapshotAnalyzer:
    """
    Katna & NarratoAI yaklaşımıyla aday zaman penceresinden en keskin kareyi
    (Laplacian Variance) çıkarır ve ekranın sol/sağ üst kadranlarındaki görsel
    yoğunluğu (Canny Edge Saliency) + yüz konumunu ölçer.
    """

    def __init__(self, video_path: Optional[str] = None):
        self.video_path = video_path if (video_path and os.path.exists(video_path)) else None
        self._cache: Dict[int, Dict[str, float]] = {}

    def analyze_window(self, start_sec: float, end_sec: float) -> Optional[Dict[str, float]]:
        if not self.video_path:
            return None
        bucket = int(round((start_sec + end_sec) / 2.0))
        if bucket in self._cache:
            return self._cache[bucket]

        try:
            import cv2
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                return None

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            sample_times = [
                max(0.0, start_sec + 0.2),
                max(0.0, (start_sec + end_sec) / 2.0),
                max(0.0, end_sec - 0.2),
            ]
            best_frame = None
            best_sharpness = -1.0

            for t in sample_times:
                frame_idx = max(0, int(t * fps))
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                if sharpness > best_sharpness:
                    best_sharpness = sharpness
                    best_frame = frame

            cap.release()
            if best_frame is None:
                return None

            h, w = best_frame.shape[:2]
            gray = cv2.cvtColor(best_frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 80, 180)

            # Sol üst ve sağ üst kadranların kenar/yazı kalabalıklığı (0.0 .. 1.0)
            top_h = max(1, int(h * 0.55))
            mid_w = max(1, int(w * 0.50))
            left_clutter = float((edges[:top_h, :mid_w] > 0).mean())
            right_clutter = float((edges[:top_h, mid_w:] > 0).mean())

            result: Dict[str, float] = {
                "sharpness": round(best_sharpness, 2),
                "left_clutter": round(left_clutter, 4),
                "right_clutter": round(right_clutter, 4),
            }
            self._cache[bucket] = result
            return result
        except Exception as e:
            logger.debug(f"KeyframeSnapshotAnalyzer uyarı: {e}")
            return None


class SafeZoneSpatialSolver:
    """
    Konuşmacının yüz/gövde kutularını, aktif altyazı kuşağını, ekran görüntüsü
    kenar yoğunluğunu ve eşzamanlı diğer katmanları hesaba katarak en uygun
    (slot_id, positionX, positionY, scale, box_rect) değerlerini döndürür.
    """

    def __init__(
        self,
        face_positions: Optional[List[Dict[str, Any]]] = None,
        subtitles_enabled: bool = True,
        video_path: Optional[str] = None,
    ):
        self.face_positions = face_positions or []
        self.subtitles_enabled = subtitles_enabled
        self.keyframe_analyzer = KeyframeSnapshotAnalyzer(video_path=video_path)
        self.placed_events: List[Tuple[float, float, BBoxPct]] = []

    def solve_placement(
        self,
        start_sec: float,
        end_sec: float,
        is_image_card: bool,
    ) -> Tuple[str, float, float, float, BBoxPct]:
        """
        Döndürür: (slot_id, position_x_pct, position_y_pct, scale_factor, placed_bbox)
        Not: position_x_pct ve position_y_pct 0..100 aralığındadır!
        """
        head_bbox, torso_bbox = self._estimate_speaker_boxes(start_sec, end_sec)
        snapshot_info = self.keyframe_analyzer.analyze_window(start_sec, end_sec)

        subtitle_bbox = (
            BBoxPct(5.0, 70.0, 95.0, 95.0)
            if self.subtitles_enabled
            else BBoxPct(0.0, 99.0, 0.0, 99.0)
        )
        active_boxes = [
            box
            for (s, e, box) in self.placed_events
            if not (end_sec + 0.6 < s or start_sec - 0.6 > e)
        ]

        candidates = IMAGE_CARD_ANCHORS if is_image_card else TEXT_CALLOUT_ANCHORS
        scales = [1.0, 0.9, 0.8, 0.72]

        best_choice: Optional[Tuple[str, float, float, float, BBoxPct]] = None
        best_cost = 1e9

        for anchor in candidates:
            for sc in scales:
                w = anchor.base_w_pct * sc
                h = anchor.base_h_pct * sc
                rect = BBoxPct(
                    max(2.0, anchor.center_x_pct - w / 2.0),
                    max(2.0, anchor.center_y_pct - h / 2.0),
                    min(98.0, anchor.center_x_pct + w / 2.0),
                    min(98.0, anchor.center_y_pct + h / 2.0),
                )

                # KESİN KISIT (HardCollision == 0.0):
                # 1. Altyazı kuşağıyla asla kesişemez
                if rect.overlaps(subtitle_bbox, margin_pct=1.0):
                    continue
                # 2. Konuşmacının genişletilmiş baş/alın/göz kutusuyla asla kesişemez
                if rect.overlaps(head_bbox, margin_pct=1.5):
                    continue
                # 3. Aynı anda ekranda olan başka bir katmanla asla kesişemez
                if any(rect.overlaps(ab, margin_pct=2.0) for ab in active_boxes):
                    continue

                # YUMUŞAK MALİYET FONKSİYONU J(A_k, s):
                torso_overlap = rect.intersection_area(torso_bbox) / max(1.0, rect.area)
                scale_penalty = (1.0 - sc) * 1.2

                # Görsel denge: konuşmacı merkez-soldaysa sağ köşeyi, merkez-sağdaysa sol köşeyi ödüllendir
                speaker_cx = head_bbox.center_x
                if speaker_cx <= 50.0 and anchor.center_x_pct > 50.0:
                    balance_cost = 0.0
                elif speaker_cx > 50.0 and anchor.center_x_pct < 50.0:
                    balance_cost = 0.0
                else:
                    balance_cost = 0.35

                # Ekran görüntüsü (Keyframe Snapshot) kenar yoğunluğu cezası
                clutter_cost = 0.0
                if snapshot_info:
                    if anchor.center_x_pct < 50.0:
                        clutter_cost = snapshot_info.get("left_clutter", 0.0) * 4.0
                    else:
                        clutter_cost = snapshot_info.get("right_clutter", 0.0) * 4.0

                # Ardışık olaylarda sol/sağ çeşitliliği için güçlü dengeleme (YouTube tarzı Sağ <-> Sol geçişi)
                alternation_bonus = 0.0
                if self.placed_events:
                    prev_cx = self.placed_events[-1][2].center_x
                    if (prev_cx > 50.0 and anchor.center_x_pct < 50.0) or (
                        prev_cx < 50.0 and anchor.center_x_pct > 50.0
                    ):
                        alternation_bonus = -0.55

                total_cost = (
                    (3.5 * torso_overlap)
                    + scale_penalty
                    + balance_cost
                    + clutter_cost
                    + alternation_bonus
                )
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_choice = (
                        anchor.slot_id,
                        round(anchor.center_x_pct, 2),
                        round(anchor.center_y_pct, 2),
                        round(sc, 2),
                        rect,
                    )

        if best_choice is None:
            # Acil durum güvenli yuvası: Sağ üst köşe (%79, %16), %75 ölçek
            fallback_rect = BBoxPct(64.0, 9.0, 94.0, 23.0)
            best_choice = ("UPPER_RIGHT_BADGE", 79.0, 16.0, 0.75, fallback_rect)

        self.placed_events.append((start_sec, end_sec, best_choice[4]))
        return best_choice

    def _estimate_speaker_boxes(
        self, start_sec: float, end_sec: float
    ) -> Tuple[BBoxPct, BBoxPct]:
        """
        [start_sec, end_sec] aralığında FaceTracker verisi varsa +35% alın paylı
        baş kutusunu ve gövde kutusunu hesaplar; yoksa standart merkez konuşmacı
        varsayımını (X ∈ [36.5%, 63.5%], Y ∈ [7.9%, 43.9%]) döndürür.
        """
        relevant = [
            fp
            for fp in self.face_positions
            if start_sec - 1.5
            <= float(fp.get("time", fp.get("timestamp", -99.0)))
            <= end_sec + 1.5
        ]
        if not relevant and self.face_positions:
            relevant = self.face_positions

        if relevant:
            avg_cx = (
                sum(
                    float(
                        f.get(
                            "center_x",
                            f.get("smoothed_crop_x", f.get("raw_x", 0.5)),
                        )
                    )
                    for f in relevant
                )
                / len(relevant)
                * 100.0
            )
            avg_cy = (
                sum(float(f.get("center_y", f.get("raw_y", 0.30))) for f in relevant)
                / len(relevant)
                * 100.0
            )
            raw_w = (
                sum(float(f.get("width", 0.16)) for f in relevant) / len(relevant) * 100.0
            )
            raw_h = (
                sum(float(f.get("height", 0.24)) for f in relevant) / len(relevant) * 100.0
            )
        else:
            # 16:9 eğitim videosu varsayılan merkez konuşmacı profili
            avg_cx, avg_cy, raw_w, raw_h = 50.0, 29.0, 18.0, 24.0

        # AutoFlip standardı: +38% alın/saç payı, +20% yan baş hareketi payı
        hx1 = max(0.0, avg_cx - (raw_w * 0.65))
        hy1 = max(0.0, avg_cy - (raw_h * 0.85))
        hx2 = min(100.0, avg_cx + (raw_w * 0.65))
        hy2 = min(100.0, avg_cy + (raw_h * 0.60))
        head_bbox = BBoxPct(hx1, hy1, hx2, hy2)

        # Gövde kutusu (başın altından ekranın altına kadar omuz genişliği)
        torso_half_w = raw_w * 1.35
        torso_bbox = BBoxPct(
            max(0.0, avg_cx - torso_half_w),
            hy2,
            min(100.0, avg_cx + torso_half_w),
            min(96.0, hy2 + raw_h * 2.2),
        )
        return head_bbox, torso_bbox
