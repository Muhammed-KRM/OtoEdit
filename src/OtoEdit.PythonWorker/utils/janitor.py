import os
import shutil
import time
from pathlib import Path
from utils.logger import get_logger
from config import Config

logger = get_logger("Janitor")


def cleanup_files(*paths):
    """Verilen dosya ve dizinleri güvenli bir şekilde siler."""
    for p in paths:
        if not p:
            continue
        try:
            path_obj = Path(p)
            if path_obj.is_file() or path_obj.is_symlink():
                size = path_obj.stat().st_size
                path_obj.unlink(missing_ok=True)
                logger.info(f"🧹 Geçici dosya temizlendi: {path_obj.name} ({size / (1024*1024):.2f} MB)")
            elif path_obj.is_dir():
                shutil.rmtree(path_obj, ignore_errors=True)
                logger.info(f"🧹 Geçici dizin temizlendi: {path_obj.name}")
        except Exception as e:
            logger.warning(f"⚠️ Dosya temizlenirken hata oluştu ({p}): {e}")


def run_janitor(temp_dir: Path = None, max_age_hours: float = 2.0):
    """
    Temp dizininde kalan yetim render klasörlerini ve eski geçici dosyaları temizler.
    Aktif kullanımda olan dosyalar korunur.
    """
    target_dir = temp_dir or Config.TEMP_DIR
    if not target_dir.exists():
        return

    now = time.time()
    max_age_seconds = max_age_hours * 3600
    freed_bytes = 0
    deleted_count = 0

    logger.info(f"🧹 Janitor başlatıldı: {target_dir} (Maksimum yaş: {max_age_hours} saat)")

    try:
        for entry in os.scandir(target_dir):
            try:
                # render_ ile başlayan klasörler veya geçici medya dosyaları
                is_render_dir = entry.is_dir() and entry.name.startswith("render_")
                is_temp_file = entry.is_file() and (
                    entry.name.endswith((".mp4", ".mp3", ".wav", ".png", ".ass", ".json"))
                    and not entry.name.startswith(".")
                )

                if is_render_dir or is_temp_file:
                    mtime = entry.stat().st_mtime
                    age = now - mtime
                    # 2 saatten eski veya render klasörüyse temizle
                    if age > max_age_seconds or is_render_dir:
                        path_to_delete = Path(entry.path)
                        if entry.is_dir():
                            dir_size = sum(f.stat().st_size for f in path_to_delete.rglob("*") if f.is_file())
                            shutil.rmtree(path_to_delete, ignore_errors=True)
                            freed_bytes += dir_size
                        else:
                            file_size = entry.stat().st_size
                            path_to_delete.unlink(missing_ok=True)
                            freed_bytes += file_size

                        deleted_count += 1
            except Exception as item_err:
                logger.debug(f"Öğe temizlenemedi ({entry.name}): {item_err}")

        if deleted_count > 0:
            logger.info(f"✨ Janitor tamamlandı: {deleted_count} öğe silindi, {freed_bytes / (1024**3):.2f} GB alan kazanıldı.")
        else:
            logger.info("✨ Janitor tamamlandı: Temizlenecek eski dosya bulunamadı.")
    except Exception as e:
        logger.error(f"❌ Janitor çalışırken hata: {e}", exc_info=True)
