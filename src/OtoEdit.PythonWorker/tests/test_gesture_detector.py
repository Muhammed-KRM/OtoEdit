from collections import namedtuple
from models.gesture_model import GestureType
from pipeline.gesture_detector import GestureDetector

Point = namedtuple('Point', ['x', 'y', 'z'])


def create_landmarks(thumb_y=0.2, index_mcp_y=0.5, fingers_y=0.6, open_distance=False):
    """Testler için 21 sentetik el eklem noktası üretir."""
    # 0: wrist, 4: thumb_tip, 5: index_mcp, 8: index_tip, 12: middle_tip, 16: ring_tip, 20: pinky_tip
    wrist = Point(0.5, 0.9, 0.0)
    index_mcp = Point(0.5, index_mcp_y, 0.0)
    thumb_tip = Point(0.4, thumb_y, 0.0)

    if open_distance:
        # Parmaklar tamamen açık (bilekten uzak)
        index_tip = Point(0.2, 0.1, 0.0)
        middle_tip = Point(0.4, 0.05, 0.0)
        ring_tip = Point(0.6, 0.08, 0.0)
        pinky_tip = Point(0.8, 0.15, 0.0)
    else:
        # Parmaklar kapalı (avuç içine/bileğe yakın)
        index_tip = Point(0.5, fingers_y, 0.0)
        middle_tip = Point(0.5, fingers_y, 0.0)
        ring_tip = Point(0.5, fingers_y, 0.0)
        pinky_tip = Point(0.5, fingers_y, 0.0)

    lm = [Point(0.5, 0.5, 0.0)] * 21
    lm[0] = wrist
    lm[4] = thumb_tip
    lm[5] = index_mcp
    lm[8] = index_tip
    lm[12] = middle_tip
    lm[16] = ring_tip
    lm[20] = pinky_tip
    return lm


def test_classify_thumbs_up():
    detector = GestureDetector()
    # thumb_y (0.2) < index_mcp_y (0.5) ve parmaklar kapalı -> THUMBS_UP
    lm = create_landmarks(thumb_y=0.2, index_mcp_y=0.5, fingers_y=0.7, open_distance=False)
    result = detector.classify_landmarks(lm)
    assert result == GestureType.THUMBS_UP


def test_classify_thumbs_down():
    detector = GestureDetector()
    # thumb_y (0.8) > index_mcp_y (0.5) ve parmaklar kapalı -> THUMBS_DOWN
    lm = create_landmarks(thumb_y=0.8, index_mcp_y=0.5, fingers_y=0.7, open_distance=False)
    result = detector.classify_landmarks(lm)
    assert result == GestureType.THUMBS_DOWN


def test_classify_open_palm():
    detector = GestureDetector()
    lm = create_landmarks(open_distance=True)
    result = detector.classify_landmarks(lm)
    assert result == GestureType.OPEN_PALM
