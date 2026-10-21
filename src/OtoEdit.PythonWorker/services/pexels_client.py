from pathlib import Path
from typing import Any, Dict, List, Optional, Set
try:
    import importlib
    requests = importlib.import_module("requests")
except Exception:
    requests = None
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class PexelsClient:
    """Pexels API üzerinden telifsiz stok görsel ve video B-Roll arama/indirme istemcisi."""

    BASE_URL = "https://api.pexels.com/v1/search"
    VIDEO_BASE_URL = "https://api.pexels.com/videos/search"

    def __init__(self):
        self.api_key = Config.PEXELS_API_KEY

    def search_photo_candidates(
        self,
        query: str,
        per_page: int = 6,
        orientation: str = "landscape",
        used_links: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """VLM doğrulayıcı için Pexels'ten tek fotoğraf yerine K adet benzersiz aday döndürür."""
        if not query:
            return []
        used = used_links or set()
        if not self.api_key or not requests:
            from services.stock_media_fallback import StockMediaFallback
            fallback_url = StockMediaFallback.resolve_stock_image(query, orientation=orientation)
            if fallback_url and fallback_url not in used:
                return [{
                    "url": fallback_url,
                    "source": "stock_fallback",
                    "width": 1280,
                    "height": 720,
                    "alt": query,
                }]
            return []
        try:
            resp = requests.get(
                self.BASE_URL,
                headers={"Authorization": self.api_key},
                params={"query": query, "per_page": per_page, "orientation": orientation},
                timeout=8,
            )
            if resp.status_code != 200:
                return []
            candidates: List[Dict[str, Any]] = []
            for p in resp.json().get("photos", []):
                url = p.get("src", {}).get("large2x") or p.get("src", {}).get("large")
                if not url or url in used:
                    continue
                candidates.append({
                    "url": url,
                    "source": "pexels_photo",
                    "width": int(p.get("width", 1280)),
                    "height": int(p.get("height", 720)),
                    "alt": p.get("alt", ""),
                })
            return candidates
        except Exception as exc:
            logger.warning(f"[PexelsClient] Fotoğraf aday araması başarısız ({query}): {exc}")
            return []

    def search_video_candidates(
        self,
        query: str,
        per_page: int = 5,
        orientation: str = "landscape",
        min_duration: int = 3,
        used_links: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Pexels Videos API (/videos/search) üzerinden HD B-Roll video adayları döndürür."""
        if not self.api_key or not query or not requests:
            return []
        used = used_links or set()
        try:
            resp = requests.get(
                self.VIDEO_BASE_URL,
                headers={"Authorization": self.api_key},
                params={"query": query, "per_page": per_page, "orientation": orientation},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            candidates: List[Dict[str, Any]] = []
            for v in resp.json().get("videos", []):
                dur = int(v.get("duration", 0))
                if dur < min_duration:
                    continue
                files = v.get("video_files", [])
                hd_files = [
                    f for f in files
                    if f.get("file_type") == "video/mp4"
                    and int(f.get("width", 0)) >= 1280
                ]
                if not hd_files:
                    hd_files = [f for f in files if f.get("file_type") == "video/mp4"]
                if not hd_files:
                    continue
                hd_files.sort(key=lambda f: int(f.get("width", 9999)) * int(f.get("height", 9999)))
                chosen = hd_files[0]
                link = chosen.get("link")
                if not link or link in used:
                    continue
                candidates.append({
                    "url": link,
                    "preview_image": v.get("image", ""),
                    "source": "pexels_video",
                    "width": int(chosen.get("width", 1920)),
                    "height": int(chosen.get("height", 1080)),
                    "duration": dur,
                })
            return candidates
        except Exception as exc:
            logger.warning(f"[PexelsClient] Video B-Roll araması başarısız ({query}): {exc}")
            return []

    def search_photo(self, query: str, orientation: str = "landscape") -> Optional[str]:
        """Arama sorgusuna göre ilk yüksek kaliteli fotoğrafın URL'sini döner (Fallback destekli)."""
        from services.stock_media_fallback import StockMediaFallback

        if not self.api_key:
            logger.info(f"PEXELS_API_KEY tanımlı değil, açık fallback zinciri kullanılıyor: query='{query}'")
            return StockMediaFallback.resolve_stock_image(query, orientation=orientation)

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
                logger.warning(f"Pexels API yanıt kodu {response.status_code} ({response.text[:120]}), fallback devreye giriyor...")
        except Exception as e:
            logger.error(f"Pexels API istek hatası ({query}): {e}, fallback devreye giriyor...")

        # Kota bittiğinde veya yetki hatasında Unsplash / Wikimedia fallback
        return StockMediaFallback.resolve_stock_image(query, orientation=orientation)

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
