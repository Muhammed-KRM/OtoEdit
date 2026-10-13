"""
src/OtoEdit.PythonWorker/services/stock_media_fallback.py
Pexels API kota aşımı veya 401 yetki hatalarında devreye giren
Unsplash ve Wikimedia Commons açık stok medya istemcisi.
"""

from typing import Optional
from urllib.parse import quote_plus
try:
    import importlib
    requests = importlib.import_module("requests")
except Exception:
    requests = None
from utils.logger import get_logger

logger = get_logger("OtoEdit.StockMediaFallback")


class StockMediaFallback:
    """Pexels harici ücretsiz ve açık API'lerle stok görsel arama motoru."""

    USER_AGENT = "OtoEdit/2.0 (Video AI Editor; contact@otoedit.local)"

    @classmethod
    def search_unsplash(cls, query: str, orientation: str = "landscape") -> Optional[str]:
        """
        Unsplash Public NAPI üzerinden anahtar kelimeye uygun görsel URL'si arar.
        """
        if not requests:
            return None

        clean_query = query.strip()
        if not clean_query:
            return None

        # Unsplash yönelim parametresi: landscape, portrait, squarish
        un_orient = "landscape"
        if orientation in ("portrait", "dikey", "9:16"):
            un_orient = "portrait"
        elif orientation in ("squarish", "kare", "1:1"):
            un_orient = "squarish"

        url = f"https://unsplash.com/napi/search/photos?query={quote_plus(clean_query)}&per_page=1&orientation={un_orient}"
        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "application/json"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    img_url = results[0].get("urls", {}).get("regular") or results[0].get("urls", {}).get("full")
                    if img_url:
                        logger.info(f"Unsplash görsel bulundu: query='{clean_query}', url='{img_url}'")
                        return img_url
            else:
                logger.debug(f"Unsplash arama yanıt kodu: {resp.status_code}")
        except Exception as ex:
            logger.debug(f"Unsplash arama hatası ({clean_query}): {ex}")

        return None

    @classmethod
    def search_wikimedia(cls, query: str) -> Optional[str]:
        """
        Wikimedia Commons REST API üzerinden Creative Commons lisanslı görsel arar.
        """
        if not requests:
            return None

        clean_query = query.strip()
        if not clean_query:
            return None

        url = (
            "https://commons.wikimedia.org/w/api.php?"
            f"action=query&generator=search&gsrsearch={quote_plus(clean_query)}&gsrnamespace=6&gsrlimit=3"
            "&prop=imageinfo&iiprop=url&format=json"
        )
        headers = {
            "User-Agent": cls.USER_AGENT
        }

        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    image_info = page_info.get("imageinfo", [])
                    if image_info:
                        img_url = image_info[0].get("url")
                        if img_url and any(img_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                            logger.info(f"Wikimedia görsel bulundu: query='{clean_query}', url='{img_url}'")
                            return img_url
        except Exception as ex:
            logger.debug(f"Wikimedia arama hatası ({clean_query}): {ex}")

        return None

    @classmethod
    def resolve_stock_image(cls, query: str, orientation: str = "landscape") -> Optional[str]:
        """
        Sırayla Unsplash ve Wikimedia Commons fallback zincirini dener.
        """
        logger.info(f"🔄 Stok medya fallback zinciri devrede: query='{query}', orientation='{orientation}'")
        
        # 1. Unsplash Public Source
        url = cls.search_unsplash(query, orientation=orientation)
        if url:
            return url

        # 2. Wikimedia Commons
        url = cls.search_wikimedia(query)
        if url:
            return url

        logger.warning(f"Fallback stok medya bulunamadı: query='{query}'")
        return None
