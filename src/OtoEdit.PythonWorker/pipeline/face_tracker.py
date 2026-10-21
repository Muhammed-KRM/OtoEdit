from typing import List, Dict, Any
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class FaceTracker:
    """9:16, 1:1 ve 16:9 kadraj analizleri için konuşmacının yüzünü takip edip yumuşatılmış koordinat üreten motor."""

    def __init__(self, deadzone: float = 0.04, ema_alpha: float = 0.15):
        self.deadzone = deadzone      # Ani mikro titremeleri yok sayan ölü bölge eşiği
        self.ema_alpha = ema_alpha    # Yumuşatma katsayısı (küçük değer daha pürüzsüz)

    def track(self, video_path: str, sample_interval_sec: float = 0.4) -> List[Dict[str, Any]]:
        """Video boyunca konuşmacının yüzünü tespit eder ve yumuşatılmış X/Y merkez koordinatlarını döner."""
        tracking_data: List[Dict[str, Any]] = []
        logger.info(f"Yüz takibi (Face Tracking) başlıyor: {video_path} (Örnekleme aralığı: {sample_interval_sec}sn)")

        try:
            import importlib
            cv2 = importlib.import_module("cv2")
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                logger.error(f"Video açılamadı: {video_path}")
                return tracking_data

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            step_frames = max(1, int(fps * sample_interval_sec))
            frame_idx = 0
            previous_x = 0.5

            # MediaPipe legacy solutions API varsa kullan, yoksa (MediaPipe 0.10.21+) OpenCV Haar Cascade kullan
            mp_face_solution = None
            try:
                mp = importlib.import_module("mediapipe")
                if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
                    mp_face_solution = mp.solutions.face_detection
            except Exception:
                mp_face_solution = None

            haar_cascade = None
            if mp_face_solution is None:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                haar_cascade = cv2.CascadeClassifier(cascade_path)

            face_ctx = (
                mp_face_solution.FaceDetection(model_selection=1, min_detection_confidence=0.6)
                if mp_face_solution is not None
                else None
            )

            try:
                while cap.isOpened():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    h_img, w_img = frame.shape[:2]
                    timestamp = round(frame_idx / fps, 2)

                    current_face_x = 0.5
                    current_face_y = 0.30
                    current_face_w = 0.18
                    current_face_h = 0.24

                    if face_ctx is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        results = face_ctx.process(rgb)
                        if results and getattr(results, "detections", None):
                            best_detection = results.detections[0]
                            bbox = best_detection.location_data.relative_bounding_box
                            current_face_w = max(0.05, min(0.8, float(bbox.width)))
                            current_face_h = max(0.05, min(0.8, float(bbox.height)))
                            current_face_x = float(bbox.xmin) + (current_face_w / 2.0)
                            current_face_y = float(bbox.ymin) + (current_face_h / 2.0)
                    elif haar_cascade is not None and not haar_cascade.empty():
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        faces = haar_cascade.detectMultiScale(
                            gray, scaleFactor=1.15, minNeighbors=5, minSize=(48, 48)
                        )
                        if len(faces) > 0:
                            # En büyük yüzü seç
                            fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
                            current_face_w = max(0.05, min(0.8, float(fw) / max(1.0, float(w_img))))
                            current_face_h = max(0.05, min(0.8, float(fh) / max(1.0, float(h_img))))
                            current_face_x = (float(fx) + float(fw) / 2.0) / max(1.0, float(w_img))
                            current_face_y = (float(fy) + float(fh) / 2.0) / max(1.0, float(h_img))

                    # Deadzone & EMA Filtresi
                    delta = abs(current_face_x - previous_x)
                    if delta > self.deadzone:
                        smoothed_x = (current_face_x * self.ema_alpha) + (previous_x * (1.0 - self.ema_alpha))
                    else:
                        smoothed_x = previous_x

                    previous_x = smoothed_x

                    tracking_data.append({
                        "timestamp": timestamp,
                        "time": timestamp,
                        "raw_x": round(current_face_x, 4),
                        "raw_y": round(current_face_y, 4),
                        "center_x": round(smoothed_x, 4),
                        "center_y": round(current_face_y, 4),
                        "width": round(current_face_w, 4),
                        "height": round(current_face_h, 4),
                        "smoothed_crop_x": round(smoothed_x, 4)
                    })

                    frame_idx += step_frames
            finally:
                if face_ctx is not None and hasattr(face_ctx, "close"):
                    face_ctx.close()
                cap.release()

            logger.info(f"Yüz takibi tamamlandı: {len(tracking_data)} koordinat noktası hesaplandı.")
        except Exception as e:
            logger.warning(f"Yüz takibi uyarısı ({video_path}): {e}")

        return tracking_data
