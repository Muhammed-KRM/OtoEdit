"""
Aşama 2: SafeZoneVisionEngine & SafeZoneSpatialSolver.
Hem 16:9 yatay hem 9:16 dikey videolarda:
1) Aday sahnelerden en keskin ekran görüntüsünü (Keyframe Snapshot) alır,
2) Konuşmacının yüzünü (+35% alın payı), gövdesini, kenar/slayt yoğunluğunu (Edge Saliency)
   ve altyazı kuşağını (Y ∈ [70%, 95%]) tespit eder,
3) Metin ve görseller için sıfır çarpışmalı (HardCollision == 0.0) çapa (Anchor) ve ölçek (Scale) hesaplar.
"""

from dataclasses import dataclass
import math
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


@dataclass(frozen=True)
class DynamicTypographySpec:
    font_size_1080p: int
    max_width_cqi: int
    position_x_pct: float
    position_y_pct: float
    scale_factor: float
    line_height: float
    estimated_lines: int
    anchor_slot: str
    placed_bbox: BBoxPct


class DynamicTypographySizer:
    """
    Metnin bağlam rolüne (stack_count: Tekil=1, İkili=2, Liste>=3),
    kelime sayısına / en uzun kelime harf sayısına ve konuşmacının yüz/gövde
    güvenli koridor genişliğine göre optimal fontSize (1080p) ve maxWidthCqi hesaplar.
    """

    @staticmethod
    def compute(
        text: str,
        stack_count: int = 1,
        stack_slot: Optional[int] = None,
        action_type: str = "SINGLE_TERM",
        corridor_width_pct: float = 33.5,
    ) -> Tuple[int, int, float, int]:
        """
        Döndürür: (font_size_1080p, max_width_cqi, line_height, estimated_lines)
        """
        clean = " ".join((text or "").strip().split())
        words = clean.split() if clean else ["METİN"]
        total_len = len(clean)
        max_word_len = max((len(w) for w in words), default=6)

        # 1. Bağlam Rolüne (stack_count & action_type) göre taban boyut ve sınırlar
        if action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION", "CONCEPT_IMAGE_CARD"):
            f_base, f_min, f_max = 56.0, 48, 58
            max_w_cqi = 32
        elif stack_count <= 1 and stack_slot is None:
            # Tekil Vurgu (SINGLE_TERM, DEFINITION_CALLOUT, ENUMERATION_CALLOUT)
            f_base, f_min, f_max = 62.0, 54, 62
            max_w_cqi = 32
        elif stack_count == 2:
            # İkili Kavram (PAIRED_TERMS: örn. TABİAT / FITRAT)
            f_base, f_min, f_max = 54.0, 48, 54
            max_w_cqi = 30
        else:
            # Kümülatif Sıralı Liste (PROGRESSIVE_LIST: stack_count >= 3)
            f_base, f_min, f_max = 46.0, 42, 46
            max_w_cqi = 30

        # Güvenli koridor genişliği cqi üst sınırını aşmasın
        effective_cqi = int(min(max_w_cqi, max(26, math.floor(corridor_width_pct))))

        # 2. Toplam karakter uzunluğu sönümlemesi (10 karaktere kadar 0 ceza)
        len_penalty = max(0.0, (total_len - 10) * 0.45)

        # 3. En uzun tekil kelimenin 1080p koridoruna taşmadan sığma sınırı
        avail_px_1080p = 1920.0 * (effective_cqi / 100.0) * 0.92
        word_cap_px = avail_px_1080p / (max(6, max_word_len) * 0.62)

        raw_size = min(f_base - len_penalty, word_cap_px)
        # Çok uzun tekil kelimelerde (13+ harf) yüz kutusuna taşmaması için alt sınırı 4px esnet
        effective_min = max(38, f_min - 4) if (max_word_len >= 13 or total_len >= 24) else f_min
        final_font_size = int(round(max(effective_min, min(f_max, raw_size))))

        # 4. Tahmini satır sayısı (1 veya 2 satır)
        chars_per_line_cap = max(10, int(avail_px_1080p / max(1.0, final_font_size * 0.60)))
        est_lines = 2 if (len(words) >= 2 and total_len > chars_per_line_cap) else 1
        line_height = 1.12 if est_lines > 1 else 1.15

        return final_font_size, effective_cqi, line_height, est_lines


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

        # Bölge A (face_bbox / head_bbox): +38% alın/saç payı, +20% yan baş hareketi payı
        # KESİN YASAK (Hard Veto = ∞, %0 çakışma izni)
        hx1 = max(0.0, avg_cx - (raw_w * 0.68))
        hy1 = max(0.0, avg_cy - (raw_h * 0.88))
        hx2 = min(100.0, avg_cx + (raw_w * 0.68))
        hy2 = min(52.0, avg_cy + (raw_h * 0.58))
        head_bbox = BBoxPct(hx1, hy1, hx2, hy2)

        # Bölge B (torso_bbox): Çene/boyun altından (Y >= 52%) ekranın altına kadar omuz/gövde
        # YUMUŞAK CEZA (Soft Cost): Zorunda kalmadıkça kapatılmaz (1-3 satır tamamen Y < 52% üst boşlukta kalır)
        torso_half_w = raw_w * 1.38
        torso_y1 = max(52.0, hy2)
        torso_bbox = BBoxPct(
            max(0.0, avg_cx - torso_half_w),
            torso_y1,
            min(100.0, avg_cx + torso_half_w),
            min(96.0, torso_y1 + raw_h * 2.0),
        )
        return head_bbox, torso_bbox

    def solve_dynamic_typography_and_placement(
        self,
        text: str,
        start_sec: float,
        end_sec: float,
        stack_count: int = 1,
        stack_slot: Optional[int] = None,
        action_type: str = "SINGLE_TERM",
    ) -> DynamicTypographySpec:
        """
        Konuşmacının yüz (Hard Veto) ve gövde (Soft Cost) bölgelerini dikkate alarak
        hem en uygun (positionX, positionY) koordinatlarını hem de bağlama uygun
        optimal (fontSize, maxWidthCqi) değerlerini hesaplar.
        """
        head_bbox, torso_bbox = self._estimate_speaker_boxes(start_sec, end_sec)
        left_corridor_w = max(24.0, (head_bbox.x1 - 1.5) - 2.0)
        right_corridor_w = max(24.0, 98.0 - (head_bbox.x2 + 1.5))

        if stack_slot is not None:
            slot = int(stack_slot)
            if slot < 4:
                corridor_w = left_corridor_w
                pos_x = round((2.0 + (head_bbox.x1 - 1.5)) / 2.0, 1)
                row = slot
                side_prefix = "LEFT_STACK"
            else:
                corridor_w = right_corridor_w
                pos_x = round(((head_bbox.x2 + 1.5) + 98.0) / 2.0, 1)
                row = (slot - 4) % 4
                side_prefix = "RIGHT_STACK"

            if stack_count == 2:
                # İkili kavram (örn. TABİAT / FITRAT): Y=20% ve Y=33% (gövdeye %0 temas!)
                pos_y = round(20.0 + row * 13.0, 1)
            else:
                # 3+ sıralı liste: Satır 1 (16%), Satır 2 (27%), Satır 3 (38%) omuz üstünde,
                # yalnızca Satır 4 (49%) omuz dış eğimine hafif yaklaşır
                pos_y = round(16.0 + row * 11.0, 1)

            font_sz, max_cqi, line_h, est_lines = DynamicTypographySizer.compute(
                text=text,
                stack_count=stack_count,
                stack_slot=slot,
                action_type=action_type,
                corridor_width_pct=corridor_w,
            )
            box_h = 8.5 if est_lines == 1 else 12.0
            rect = BBoxPct(
                max(2.0, pos_x - max_cqi / 2.0),
                max(2.0, pos_y - box_h / 2.0),
                min(98.0, pos_x + max_cqi / 2.0),
                min(98.0, pos_y + box_h / 2.0),
            )
            # Stack öğesini uzamsal çözücü hafızasına kaydet (tekil/görsel çakışmasını önler - PROB-4.3)
            self.placed_events.append((start_sec, end_sec, rect))
            return DynamicTypographySpec(
                font_size_1080p=font_sz,
                max_width_cqi=max_cqi,
                position_x_pct=pos_x,
                position_y_pct=pos_y,
                scale_factor=1.0,
                line_height=line_h,
                estimated_lines=est_lines,
                anchor_slot=f"{side_prefix}_{row + 1}",
                placed_bbox=rect,
            )

        # Tekil kavram veya Kişi/Eser tanıtımı
        active_boxes = [
            box
            for (s, e, box) in self.placed_events
            if not (end_sec + 0.4 < s or start_sec - 0.4 > e)
        ]
        if action_type in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION"):
            corridor_w = left_corridor_w
            pos_x = round((2.0 + (head_bbox.x1 - 1.5)) / 2.0, 1)
            pos_y = 24.0
            slot_id = "TOP_LEFT_CARD"
            sc = 1.0
            rect = BBoxPct(2.5, 16.0, max(30.0, head_bbox.x1 - 1.5), 32.0)
            if any(rect.overlaps(ab, margin_pct=1.5) for ab in active_boxes):
                pos_y = 38.0
                rect = BBoxPct(2.5, 30.0, max(30.0, head_bbox.x1 - 1.5), 46.0)
            self.placed_events.append((start_sec, end_sec, rect))
        else:
            slot_id, raw_x, raw_y, sc, rect = self.solve_placement(
                start_sec=start_sec,
                end_sec=end_sec,
                is_image_card=False,
            )
            is_left = raw_x < 50.0
            corridor_w = left_corridor_w if is_left else right_corridor_w
            pos_x = (
                round((2.0 + (head_bbox.x1 - 1.5)) / 2.0, 1)
                if is_left
                else round(((head_bbox.x2 + 1.5) + 98.0) / 2.0, 1)
            )
            # Y=22.0% tercih edilir ancak o konumda başka aktif kutu varsa çözücünün seçtiği raw_y korunur (PROB-4.3)
            cand_y = 22.0 if raw_y > 26.0 else raw_y
            cand_rect = BBoxPct(
                max(2.0, pos_x - corridor_w / 2.0),
                max(2.0, cand_y - 6.5),
                min(98.0, pos_x + corridor_w / 2.0),
                min(98.0, cand_y + 6.5),
            )
            if any(cand_rect.overlaps(ab, margin_pct=1.5) for ab in active_boxes):
                pos_y = raw_y
            else:
                pos_y = cand_y
                rect = cand_rect
            if self.placed_events:
                self.placed_events[-1] = (start_sec, end_sec, rect)

        font_sz, max_cqi, line_h, est_lines = DynamicTypographySizer.compute(
            text=text,
            stack_count=1,
            stack_slot=None,
            action_type=action_type,
            corridor_width_pct=corridor_w,
        )
        return DynamicTypographySpec(
            font_size_1080p=font_sz,
            max_width_cqi=max_cqi,
            position_x_pct=pos_x,
            position_y_pct=pos_y,
            scale_factor=sc,
            line_height=line_h,
            estimated_lines=est_lines,
            anchor_slot=slot_id,
            placed_bbox=rect,
        )

    def register_external_box(
        self,
        start_sec: float,
        end_sec: float,
        center_x: float,
        center_y: float,
        width_pct: float = 26.0,
        height_pct: float = 28.0,
    ) -> Tuple[float, float]:
        """
        Görsel kartı (`ad_img_`) gibi harici katmanları `placed_events` içine kaydeder ve
        varsa aktif katmanlarla çakışmayan (center_x, center_y) koordinatını döndürür (PROB-4.3).
        """
        active_boxes = [
            box
            for (s, e, box) in self.placed_events
            if not (end_sec + 0.4 < s or start_sec - 0.4 > e)
        ]
        for cand_y in (center_y, 26.0, 38.0, 18.0):
            rect = BBoxPct(
                max(2.0, center_x - width_pct / 2.0),
                max(2.0, cand_y - height_pct / 2.0),
                min(98.0, center_x + width_pct / 2.0),
                min(98.0, cand_y + height_pct / 2.0),
            )
            if not any(rect.overlaps(ab, margin_pct=1.5) for ab in active_boxes):
                self.placed_events.append((start_sec, end_sec, rect))
                return round(center_x, 1), round(cand_y, 1)
        fallback_rect = BBoxPct(
            max(2.0, center_x - width_pct / 2.0),
            max(2.0, center_y - height_pct / 2.0),
            min(98.0, center_x + width_pct / 2.0),
            min(98.0, center_y + height_pct / 2.0),
        )
        self.placed_events.append((start_sec, end_sec, fallback_rect))
        return round(center_x, 1), round(center_y, 1)
