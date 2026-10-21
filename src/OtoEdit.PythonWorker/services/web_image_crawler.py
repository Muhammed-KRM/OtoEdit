"""
Aşama 3A: Çoklu Kaynak Web Görsel Toplayıcı (WebImageCrawler) ve
OpenCV Slayt/Metin Kirliliği & Çözünürlük Ön Filtresi.
"""

import hashlib
import html
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

try:
    import requests
except Exception:
    requests = None

from utils.logger import get_logger

logger = get_logger("WebImageCrawler")


class WebImageCrawler:
    """
    Konuyla ilgili görselleri Pexels, Bing Images, Wikimedia Commons ve Unsplash
    üzerinden arar; indirilen adayları OpenCV ile slayt/yazı kirliliği ve
    bulanıklık açısından denetler.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, work_dir: str, pexels_client: Any = None):
        self.work_dir = work_dir
        self.pexels = pexels_client
        self.used_links: Set[str] = set()
        os.makedirs(self.work_dir, exist_ok=True)

    def gather_verified_candidates(
        self,
        query_tr: str,
        query_en: str,
        fallback_en: str,
        max_candidates: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Çoklu kaynaklardan aday URL'leri toplar, indirir ve OpenCV ön filtresinden
        geçen en temiz `max_candidates` adayı döndürür.
        """
        raw_pool: List[Dict[str, Any]] = []

        # 1. Pexels Photo adayları (yüksek estetik ve sıfır filigran)
        if self.pexels and query_en:
            raw_pool.extend(
                self.pexels.search_photo_candidates(
                    query_en, per_page=4, used_links=self.used_links
                )
            )

        # 2. Bing Web Görsel Araması (Türkçe ve İngilizce somut sorgu)
        if len(raw_pool) < 3 and query_tr:
            raw_pool.extend(self._search_bing_images(query_tr, limit=3))
        if len(raw_pool) < 4 and query_en:
            raw_pool.extend(self._search_bing_images(query_en, limit=3))

        # 3. Wikimedia Commons (Ansiklopedik / Kurumsal / Tarihi görseller)
        if len(raw_pool) < 4 and query_en:
            raw_pool.extend(self._search_wikimedia_images(query_en, limit=3))

        # 4. Yedek sorgu
        if not raw_pool and fallback_en and self.pexels:
            raw_pool.extend(
                self.pexels.search_photo_candidates(
                    fallback_en, per_page=3, used_links=self.used_links
                )
            )

        verified_candidates: List[Dict[str, Any]] = []
        for item in raw_pool:
            url = str(item.get("url", ""))
            if not url or url in self.used_links:
                continue

            local_path = self._download_candidate(url)
            if not local_path:
                continue

            passed, metrics = self._passes_opencv_prefilter(local_path)
            if not passed:
                logger.info(f"[WebImageCrawler] OpenCV ön filtresi reddetti ({url}): {metrics}")
                continue

            item["local_path"] = local_path
            item["cv_metrics"] = metrics
            verified_candidates.append(item)
            if len(verified_candidates) >= max_candidates:
                break

        return verified_candidates

    def _search_bing_images(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Bing Images üzerinden yüksek çözünürlüklü doğrudan görsel URL'lerini çeker."""
        if not requests or not query:
            return []
        try:
            resp = requests.get(
                "https://www.bing.com/images/search",
                params={"q": query, "qft": "+filterui:imagesize-large+filterui:photo-photo", "FORM": "IRFLTR"},
                headers=self.HEADERS,
                timeout=6,
            )
            if resp.status_code != 200:
                return []
            matches = re.findall(r'm="(\{[^"]*murl[^"]*\})"', resp.text)
            results: List[Dict[str, Any]] = []
            blocked_domains = (
                "shutterstock", "istockphoto", "gettyimages", "alamy",
                "123rf", "dreamstime", "depositphotos", ".svg", ".gif",
            )
            for raw_m in matches:
                try:
                    meta = json.loads(html.unescape(raw_m))
                    murl = str(meta.get("murl", ""))
                    if not murl or any(bad in murl.lower() for bad in blocked_domains):
                        continue
                    results.append({
                        "url": murl,
                        "source": "bing_web",
                        "alt": meta.get("t", query),
                    })
                    if len(results) >= limit:
                        break
                except Exception:
                    continue
            return results
        except Exception as exc:
            logger.debug(f"[WebImageCrawler] Bing araması hatası ({query}): {exc}")
            return []

    def _search_wikimedia_images(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        if not requests or not query:
            return []
        try:
            resp = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": f"filetype:bitmap {query}",
                    "gsrnamespace": 6,
                    "gsrlimit": limit + 3,
                    "prop": "imageinfo",
                    "iiprop": "url|dimensions|mime",
                    "format": "json",
                },
                headers=self.HEADERS,
                timeout=6,
            )
            if resp.status_code != 200:
                return []
            pages = resp.json().get("query", {}).get("pages", {})
            results: List[Dict[str, Any]] = []
            for p in pages.values():
                ii = (p.get("imageinfo") or [{}])[0]
                mime = ii.get("mime", "")
                url = ii.get("url", "")
                w, h = int(ii.get("width", 0)), int(ii.get("height", 0))
                if mime not in ("image/jpeg", "image/png") or min(w, h) < 500:
                    continue
                results.append({
                    "url": url,
                    "source": "wikimedia",
                    "width": w,
                    "height": h,
                    "alt": p.get("title", ""),
                })
                if len(results) >= limit:
                    break
            return results
        except Exception:
            return []

    def _download_candidate(self, url: str) -> Optional[str]:
        if not requests:
            return None
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        local_path = os.path.join(self.work_dir, f"cand_{url_hash}{ext}")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 4096:
            return local_path
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=6, stream=True)
            if resp.status_code != 200:
                return None
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
            return local_path if os.path.exists(local_path) and os.path.getsize(local_path) > 4096 else None
        except Exception:
            return None

    def _passes_opencv_prefilter(self, image_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Aşama 3A Deterministik OpenCV Ön Filtresi:
        1. Çözünürlük >= 420p
        2. Laplacian Keskinlik >= 35.0 (Bulanık fotoğrafları eler)
        3. Morfolojik Metin/Slayt Yoğunluğu <= 0.18 (PowerPoint slaytlarını ve belge sayfalarını eler)
        """
        if cv2 is None:
            return True, {"w": 1280, "h": 720, "sharpness": 100.0, "text_density": 0.0}

        img = cv2.imread(image_path)
        if img is None:
            return False, {"reason": "unreadable"}

        h, w = img.shape[:2]
        if min(w, h) < 420:
            return False, {"reason": "low_res", "w": w, "h": h}

        aspect = w / float(h)
        if aspect > 3.2 or aspect < 0.35:
            return False, {"reason": "extreme_aspect", "aspect": round(aspect, 2)}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if sharpness < 35.0:
            return False, {"reason": "blurry", "sharpness": round(sharpness, 1)}

        # Morfolojik Yatay Gradyan ile Slayt / Belge Metin Yoğunluğu Tespiti
        grad_x = cv2.Sobel(gray, cv2.CV_8U, 1, 0, ksize=3)
        thresh = cv2.threshold(grad_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_like_area = 0.0
        for cnt in contours:
            _, _, cw, ch = cv2.boundingRect(cnt)
            if cw > ch * 2.2 and 8 < ch < h * 0.12 and cw > w * 0.06:
                text_like_area += cw * ch

        text_density = text_like_area / float(w * h)
        if text_density > 0.18:
            return False, {"reason": "slide_or_document_text_clutter", "text_density": round(text_density, 3)}

        return True, {"w": w, "h": h, "sharpness": round(sharpness, 1), "text_density": round(text_density, 3)}
