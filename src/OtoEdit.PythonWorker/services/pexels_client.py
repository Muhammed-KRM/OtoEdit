from pathlib import Path
from typing import Optional
try:
    import importlib
    requests = importlib.import_module("requests")
except Exception:
    requests = None
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class PexelsClient:
    """Pexels API üzerinden telifsiz stok görsel arama ve indirme istemcisi."""

    BASE_URL = "https://api.pexels.com/v1/search"

    def __init__(self):
        self.api_key = Config.PEXELS_API_KEY

    def search_photo(self, query: str, orientation: str = "landscape") -> Optional[str]:
        """Arama sorgusuna göre ilk yüksek kaliteli fotoğrafın URL'sini döner."""
        if not self.api_key:
            logger.warning("PEXELS_API_KEY tanımlı değil, görsel aranamıyor.")
            return None

        headers = {
            "Authorization": self.api_key
        }
        params = {
            "query": query,
            "per_page": 1,
            "orientation": orientation
        }

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                if photos:
                    photo_url = photos[0].get("src", {}).get("large") or photos[0].get("src", {}).get("original")
                    logger.info(f"Pexels görsel bulundu: query='{query}', url='{photo_url}'")
                    return photo_url
            else:
                logger.warning(f"Pexels API yanıt kodu {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Pexels API istek hatası ({query}): {e}")

        return None

    def download_image(self, image_url: str, output_path: Optional[str] = None) -> Optional[str]:
        """Verilen görsel URL'sini yerel diske kaydeder."""
        Config.ensure_directories()
        if not output_path:
            filename = Path(image_url.split("?")[0]).name or "broll_image.jpg"
            output_path = str(Config.TEMP_DIR / filename)

        try:
            response = requests.get(image_url, timeout=20)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Görsel indirildi: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Görsel indirme hatası ({image_url}): {e}")

        return None
