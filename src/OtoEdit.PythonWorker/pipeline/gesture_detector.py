import math
from typing import List, Optional
from config import Config
from models.gesture_model import GestureResult, GestureType
from utils.logger import get_logger

logger = get_logger(__name__)


class GestureDetector:
    """MediaPipe Hands kullanarak video karelerindeki el hareketlerini (jestleri) sınıflandıran motor."""

    def __init__(self, frame_skip: int = 0, min_confidence: float = 0.0):
        self.frame_skip = frame_skip or Config.GESTURE_FRAME_SKIP
        self.min_confidence = min_confidence or Config.GESTURE_CONFIDENCE

    def detect_gestures(self, video_path: str) -> List[GestureResult]:
        """Videodaki el hareketlerini tespit eder ve zaman damgalı sonuçlar döner."""
        results = []
        logger.info(f"El hareketi (Gesture) algılama başlıyor: {video_path} (frame_skip={self.frame_skip})")

        try:
            import cv2
            import mediapipe as mp

            mp_hands = mp.solutions.hands
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                logger.error(f"Video dosyası açılamadı: {video_path}")
                return results

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_idx = 0

            with mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=self.min_confidence
            ) as hands:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_idx % self.frame_skip != 0:
                        frame_idx += 1
                        continue

                    timestamp = round(frame_idx / fps, 2)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    detection = hands.process(rgb)

                    if detection.multi_hand_landmarks:
                        for hand_landmarks in detection.multi_hand_landmarks:
                            gesture = self.classify_landmarks(hand_landmarks.landmark)
                            if gesture:
                                results.append(GestureResult(
                                    gesture_type=gesture,
                                    timestamp=timestamp,
                                    confidence=0.85
                                ))
                    frame_idx += 1

            cap.release()
            logger.info(f"El hareketi algılama tamamlandı: {len(results)} jest tespit edildi.")
        except Exception as e:
            logger.error(f"GestureDetector hatası ({video_path}): {e}", exc_info=True)

        return results

    def classify_landmarks(self, landmarks) -> Optional[GestureType]:
        """21 el landmark koordinatını inceleyerek jest türünü belirler."""
        try:
            wrist = landmarks[0]
            thumb_tip = landmarks[4]
            index_mcp = landmarks[5]
            index_tip = landmarks[8]
            middle_tip = landmarks[12]
            ring_tip = landmarks[16]
            pinky_tip = landmarks[20]

            # Diğer parmaklar kapalı mı? (Uçlar bilek-eklem mesafesine göre yakın)
            ref_dist = self._distance(index_mcp, wrist)
            fingers_closed = all(
                self._distance(tip, wrist) < ref_dist * 1.25
                for tip in [index_tip, middle_tip, ring_tip, pinky_tip]
            )

            # Thumbs Up (👍): Başparmak işaret parmağı kökünün yukarısında ve diğer parmaklar kapalı
            if thumb_tip.y < index_mcp.y and fingers_closed:
                return GestureType.THUMBS_UP

            # Thumbs Down (👎): Başparmak aşağıda ve diğer parmaklar kapalı
            if thumb_tip.y > index_mcp.y and fingers_closed:
                return GestureType.THUMBS_DOWN

            # Yumruk (✊): Tüm parmaklar bileğe/avuç içine çok yakın
            all_closed = (
                self._distance(thumb_tip, wrist) < ref_dist * 0.9 and
                fingers_closed
            )
            if all_closed:
                return GestureType.FIST

            # Avuç Açık (🖐️): Tüm parmak uçları açık ve birbirinden uzak
            all_open = all(
                self._distance(tip, wrist) > ref_dist * 1.4
                for tip in [thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip]
            )
            if all_open:
                return GestureType.OPEN_PALM

            # Zafer / T İşareti (✌️): İşaret ve orta parmak açık, yüzük ve serçe kapalı
            index_open = self._distance(index_tip, wrist) > ref_dist * 1.3
            middle_open = self._distance(middle_tip, wrist) > ref_dist * 1.3
            ring_closed = self._distance(ring_tip, wrist) < ref_dist * 1.2
            pinky_closed = self._distance(pinky_tip, wrist) < ref_dist * 1.2

            if index_open and middle_open and ring_closed and pinky_closed:
                return GestureType.PEACE_OR_T

        except Exception as e:
            logger.debug(f"Landmark sınıflandırma hatası: {e}")

        return None

    @staticmethod
    def _distance(p1, p2) -> float:
        """İki 3D landmark noktası arasındaki öklid mesafesini hesaplar."""
        return math.sqrt(
            (getattr(p1, 'x', 0) - getattr(p2, 'x', 0)) ** 2 +
            (getattr(p1, 'y', 0) - getattr(p2, 'y', 0)) ** 2 +
            (getattr(p1, 'z', 0) - getattr(p2, 'z', 0)) ** 2
        )
