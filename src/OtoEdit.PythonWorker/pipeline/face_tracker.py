from typing import List, Dict, Any
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceTracker:
    """9:16 ve 1:1 dikey format dönüşümleri için konuşmacının yüzünü takip edip yumuşatılmış crop koordinatı üreten motor."""

    def __init__(self, deadzone: float = 0.04, ema_alpha: float = 0.15):
        self.deadzone = deadzone      # Ani mikro titremeleri yok sayan ölü bölge eşiği
        self.ema_alpha = ema_alpha    # Yumuşatma katsayısı (küçük değer daha pürüzsüz)

    def track(self, video_path: str) -> List[Dict[str, Any]]:
        """Video boyunca konuşmacının yüzünü tespit eder ve yumuşatılmış X merkez koordinatlarını döner."""
        tracking_data = []
        logger.info(f"Yüz takibi (Face Tracking) başlıyor: {video_path}")

        try:
            import importlib
            cv2 = importlib.import_module("cv2")
            mp = importlib.import_module("mediapipe")

            mp_face = mp.solutions.face_detection
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                logger.error(f"Video açılamadı: {video_path}")
                return tracking_data

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_idx = 0
            previous_x = 0.5  # Başlangıçta ekranın tam ortası varsayılır

            with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.6) as face_detection:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Her 4 frame'de bir analiz et (performans optimizasyonu)
                    if frame_idx % 4 != 0:
                        frame_idx += 1
                        continue

                    timestamp = round(frame_idx / fps, 2)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = face_detection.process(rgb)

                    current_face_x = 0.5
                    current_face_y = 0.5

                    if results.detections:
                        # En yüksek güven skoruna sahip ilk yüzü al
                        best_detection = results.detections[0]
                        bbox = best_detection.location_data.relative_bounding_box
                        current_face_x = bbox.xmin + (bbox.width / 2.0)
                        current_face_y = bbox.ymin + (bbox.height / 2.0)

                    # Deadzone & EMA Filtresi
                    delta = abs(current_face_x - previous_x)
                    if delta > self.deadzone:
                        smoothed_x = (current_face_x * self.ema_alpha) + (previous_x * (1.0 - self.ema_alpha))
                    else:
                        smoothed_x = previous_x

                    previous_x = smoothed_x

                    tracking_data.append({
                        "timestamp": timestamp,
                        "raw_x": round(current_face_x, 4),
                        "raw_y": round(current_face_y, 4),
                        "smoothed_crop_x": round(smoothed_x, 4)
                    })

                    frame_idx += 1

            cap.release()
            logger.info(f"Yüz takibi tamamlandı: {len(tracking_data)} koordinat noktası hesaplandı.")
        except Exception as e:
            logger.error(f"Yüz takibi hatası ({video_path}): {e}", exc_info=True)

        return tracking_data
