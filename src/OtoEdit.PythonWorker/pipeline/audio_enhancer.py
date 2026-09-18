import os
import subprocess
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


class AudioEnhancer:
    """Videodan sesi ayıklayıp gürültü ve yankı filtreleme uygulayarak optimize eden motor."""

    def enhance(self, video_path: str) -> str:
        """Video dosyasından sesi çıkarır, gürültüyü temizler ve 32kbps MP3 olarak döner."""
        video_p = Path(video_path)
        output_mp3 = str(video_p.with_name(f"{video_p.stem}_clean.mp3"))
        raw_wav = str(video_p.with_name(f"{video_p.stem}_raw.wav"))

        logger.info(f"Ses iyileştirme başlıyor: {video_path}")

        try:
            # 1. FFmpeg ile 16kHz mono ham WAV çıkar
            subprocess.run([
                "ffmpeg", "-i", video_path,
                "-ac", "1", "-ar", "16000",
                "-vn", raw_wav, "-y"
            ], check=True, capture_output=True)

            # 2. noisereduce ve pydub ile AI tabanlı gürültü temizleme
            try:
                import numpy as np
                import noisereduce as nr
                from pydub import AudioSegment

                audio = AudioSegment.from_wav(raw_wav)
                samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
                rate = audio.frame_rate

                cleaned = nr.reduce_noise(y=samples, sr=rate, prop_decrease=0.8)

                cleaned_segment = AudioSegment(
                    cleaned.astype(np.int16).tobytes(),
                    frame_rate=rate, sample_width=2, channels=1
                )
                cleaned_segment.export(output_mp3, format="mp3", bitrate="32k")
                logger.info(f"AI gürültü temizleme tamamlandı: {output_mp3}")
            except Exception as ex:
                logger.warning(f"noisereduce çalıştırılamadı, FFmpeg filtresi ile sıkıştırma uygulanıyor: {ex}")
                # Fallback: FFmpeg doğrudan afftdn ile temizler ve mp3'e çevirir
                subprocess.run([
                    "ffmpeg", "-i", raw_wav,
                    "-af", "afftdn=nf=-25",
                    "-b:a", "32k",
                    output_mp3, "-y"
                ], check=True, capture_output=True)

            return output_mp3
        except Exception as e:
            logger.error(f"Ses iyileştirme hatası ({video_path}): {e}", exc_info=True)
            # Hata durumunda en kötü ihtimal ham videoyu veya sesi dön
            if os.path.exists(output_mp3):
                return output_mp3
            return video_path
        finally:
            # Geçici ham WAV dosyasını temizle
            if os.path.exists(raw_wav):
                try:
                    os.remove(raw_wav)
                except Exception:
                    pass
