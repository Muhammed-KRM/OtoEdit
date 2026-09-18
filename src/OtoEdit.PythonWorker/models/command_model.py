from enum import Enum
from dataclasses import dataclass
from typing import Optional


class CommandType(str, Enum):
    START_MARKER = "start_marker"  # 👍 "Başlat"
    CUT = "cut"                    # 👎 "Kes / Durdur"
    ADD_TEXT = "add_text"          # ✌️ "Buraya {metin} yazısını yaz"
    ADD_IMAGE = "add_image"        # 🖐️ "Buraya {nesne} resmi koy"
    REWIND_CUT = "rewind_cut"      # ✊ "{cümle}'ye kadar sil"


@dataclass
class ParsedCommand:
    command_type: CommandType
    timestamp: float
    start: Optional[float] = None
    end: Optional[float] = None
    payload: Optional[str] = None
    raw_text: Optional[str] = None
