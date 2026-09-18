from enum import Enum
from dataclasses import dataclass


class GestureType(str, Enum):
    THUMBS_UP = "thumbs_up"      # 👍 Başlat / Onayla
    THUMBS_DOWN = "thumbs_down"  # 👎 Kes / Durdur
    PEACE_OR_T = "peace_or_t"    # ✌️ Metin Yazısı Ekle
    OPEN_PALM = "open_palm"      # 🖐️ Görsel / Resim Ekle
    FIST = "fist"                # ✊ Geriye Sil / Sar


@dataclass
class GestureResult:
    gesture_type: GestureType
    timestamp: float
    confidence: float = 0.85
