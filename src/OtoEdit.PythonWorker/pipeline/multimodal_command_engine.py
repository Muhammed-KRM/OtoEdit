from typing import List, Tuple
from models.command_model import CommandType, ParsedCommand
from models.gesture_model import GestureResult, GestureType
from models.transcript_model import TranscriptResult
from pipeline.gesture_detector import GestureDetector
from pipeline.voice_command_parser import VoiceCommandParser
from utils.constants import GESTURE_VOICE_SYNC_TOLERANCE_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)


class MultimodalCommandEngine:
    """El hareketi (MediaPipe) ve sesli komutu (Whisper) eşzamanlı (±2s) doğrulayan çoklu-modal motor."""

    # Jest ve Sesli Komut Eşleşme Matrisi (Bölüm 1.6)
    GESTURE_COMMAND_MAP = {
        GestureType.THUMBS_UP: CommandType.START_MARKER,
        GestureType.THUMBS_DOWN: CommandType.CUT,
        GestureType.PEACE_OR_T: CommandType.ADD_TEXT,
        GestureType.OPEN_PALM: CommandType.ADD_IMAGE,
        GestureType.FIST: CommandType.REWIND_CUT
    }

    def __init__(self, tolerance_seconds: float = GESTURE_VOICE_SYNC_TOLERANCE_SECONDS):
        self.tolerance_seconds = tolerance_seconds
        self.gesture_detector = GestureDetector()
        self.voice_parser = VoiceCommandParser()

    def detect(self, video_path: str, transcript: TranscriptResult) -> List[ParsedCommand]:
        """Video ve transkripti analiz edip sadece eşzamanlı onaylanan komutları döner."""
        logger.info(f"Çoklu-modal komut algılama başlatılıyor: {video_path}")

        # 1. Sesli komut adaylarını transkriptten çıkar (Önce metin kontrolü - Çok Hızlı)
        voice_commands = self.voice_parser.parse_transcript(transcript)
        if not voice_commands:
            logger.info("⚡ [SmartWindowing] Transkriptte hiçbir sesli komut adayı bulunamadı. 1 Saatlik videoyu taramaya gerek yok (Tasarruf: %100).")
            return []

        # 2. Akıllı Pencereleme: Yalnızca sesli komutların etrafındaki ±tolerans saniyelerini tara
        target_windows = []
        for vc in voice_commands:
            ts = vc.timestamp or 0.0
            start_win = max(0.0, ts - self.tolerance_seconds - 0.5)
            end_win = ts + self.tolerance_seconds + 0.5
            target_windows.append((start_win, end_win))

        logger.info(f"🎯 [SmartWindowing] {len(voice_commands)} sesli komut adayı için {len(target_windows)} zaman aralığı MediaPipe ile taranıyor...")

        # 3. Yalnızca hedef zaman aralıklarında el hareketlerini tespit et
        gestures = self.gesture_detector.detect_gestures(video_path, target_windows=target_windows)

        # 4. İkisini eşzamanlılık (synchronicity) filtresinden geçir
        confirmed_commands = []

        for g in gestures:
            expected_cmd_type = self.GESTURE_COMMAND_MAP.get(g.gesture_type)
            if not expected_cmd_type:
                continue

            # ±2 saniye tolerans aralığındaki eşleşen ses komutunu ara
            matched_voice = None
            for vc in voice_commands:
                if vc.command_type == expected_cmd_type:
                    time_diff = abs(g.timestamp - vc.timestamp)
                    if time_diff <= self.tolerance_seconds:
                        matched_voice = vc
                        break

            if matched_voice:
                # Eşzamanlı komut doğrulandı!
                start_time = min(g.timestamp, matched_voice.start or g.timestamp)
                end_time = max(g.timestamp, matched_voice.end or g.timestamp)

                confirmed = ParsedCommand(
                    command_type=matched_voice.command_type,
                    timestamp=g.timestamp,
                    start=round(start_time, 2),
                    end=round(end_time, 2),
                    payload=matched_voice.payload,
                    raw_text=matched_voice.raw_text
                )
                confirmed_commands.append(confirmed)
                logger.info(f"✅ ÇOKLU-MODAL KOMUT ONAYLANDI: {confirmed.command_type.value} @ {confirmed.timestamp}s (Payload='{confirmed.payload}')")
            else:
                logger.debug(f"Yalnız el hareketi atlandı (ses eşleşmedi): {g.gesture_type.value} @ {g.timestamp}s")

        logger.info(f"Çoklu-modal komut analizi tamamlandı: {len(confirmed_commands)} komut uygulandı.")
        return confirmed_commands
