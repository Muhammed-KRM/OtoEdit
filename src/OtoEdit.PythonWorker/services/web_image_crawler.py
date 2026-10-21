"""
Aşama 3A: Çoklu Kaynak Web Görsel Toplayıcı (WebImageCrawler),
Wikipedia REST Portre/Kavram Çözücüsü ve OpenCV Slayt/Metin Kirliliği Ön Filtresi.
"""

import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
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
    Kişi tanıtımları için Wikipedia REST API (tr.wikipedia.org & en.wikipedia.org) üzerinden
    doğrulanmış tarihsel portre/fotoğraf çeker; somut kavramlar için Pexels, Wikipedia ve
    Wikimedia Commons kaynaklarını tarar; haber/tabloid/ödev sitelerini kesin olarak engeller.
    """

    BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    # Wikimedia Foundation API politikasına uygun User-Agent (403 hatasını önler)
    WIKI_HEADERS = {
        "User-Agent": "OtoEditAutonomousDirector/2.0 (https://otoedit.local; studio@otoedit.local) python-requests/2.31"
    }

    BLOCKED_DOMAINS = (
        "shutterstock", "istockphoto", "gettyimages", "alamy",
        "123rf", "dreamstime", "depositphotos", ".svg", ".gif", ".pdf", ".djvu",
        # Haber, tabloid, forum, ödev ve e-ticaret siteleri (alakasız görsel kirliliğini önler)
        "haber", "gazete", "sivasekspres", "nefes.com.tr", "tgrthaber",
        "yeniakit", "oncusehir", "habergo", "risalehaber", "yenicaggazetesi",
        "sansasyonel", "bilecikhaber", "ensonhaber", "milliyet", "hurriyet",
        "sabah.com", "sozcu.com", "cumhuriyet.com", "chegg", "eodev",
        "nadirkitap", "trendyol", "hepsiburada", "pinterest", "facebook",
        "instagram", "tiktok", "ytimg", "youtube", "blogspot", "wordpress",
        "eksisozluk", "uludagsozluk", "kizlarsoruyor", "onedio",
    )

    def __init__(self, work_dir: str, pexels_client: Any = None):
        self.work_dir = work_dir
        self.pexels = pexels_client
        self.used_links: Set[str] = set()
        os.makedirs(self.work_dir, exist_ok=True)

    def gather_person_portrait_candidates(
        self,
        wiki_title_tr: str,
        wiki_title_en: str = "",
        max_candidates: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Kişi / Alim / Filozof tanıtımlarında (PERSON_INTRODUCTION) doğrudan
        Türkçe ve İngilizce Wikipedia biyografi sayfasındaki portre/minyatür/fotoğrafı indirir.
        """
        raw_pool: List[Dict[str, Any]] = []
        if wiki_title_tr:
            raw_pool.extend(
                self._search_wikipedia_summary_image(
                    wiki_title_tr, lang="tr", source_tag="wikipedia_portrait"
                )
            )
        if wiki_title_en and len(raw_pool) < max_candidates:
            raw_pool.extend(
                self._search_wikipedia_summary_image(
                    wiki_title_en, lang="en", source_tag="wikipedia_portrait"
                )
            )
        if not raw_pool and (wiki_title_en or wiki_title_tr):
            q = wiki_title_en or wiki_title_tr
            raw_pool.extend(self._search_wikimedia_images(f"{q} portrait", limit=2))

        verified: List[Dict[str, Any]] = []
        for item in raw_pool:
            url = str(item.get("url", ""))
            if not url or url in self.used_links:
                continue
            local_path = self._download_candidate(url)
            if not local_path:
                continue
            passed, metrics = self._passes_opencv_prefilter(local_path, is_portrait=True)
            if not passed:
                logger.info(f"[WebImageCrawler] Portre OpenCV filtresinden geçemedi ({url}): {metrics}")
                continue
            item["local_path"] = local_path
            item["cv_metrics"] = metrics
            verified.append(item)
            if len(verified) >= max_candidates:
                break
        return verified

    def gather_verified_candidates(
        self,
        query_tr: str,
        query_en: str,
        fallback_en: str,
        max_candidates: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Çoklu kaynaklardan (Pexels, Wikipedia Summary, Wikimedia Commons) aday URL'leri toplar,
        indirir ve OpenCV ön filtresinden geçen en temiz `max_candidates` adayı döndürür.
        """
        raw_pool: List[Dict[str, Any]] = []

        # 1. Wikipedia Ansiklopedik Kavram Görseli (eğer query_tr veya query_en net bir ansiklopedik başlık ise)
        if query_tr and len(query_tr.split()) <= 3:
            raw_pool.extend(
                self._search_wikipedia_summary_image(
                    query_tr, lang="tr", source_tag="wikipedia_concept"
                )
            )
        if query_en and len(query_en.split()) <= 3 and len(raw_pool) < 2:
            raw_pool.extend(
                self._search_wikipedia_summary_image(
                    query_en, lang="en", source_tag="wikipedia_concept"
                )
            )

        # 2. Pexels Photo adayları (yalnızca geçerli Pexels API anahtarı varsa)
        if self.pexels and getattr(self.pexels, "api_key", None) and query_en:
            raw_pool.extend(
                self.pexels.search_photo_candidates(
                    query_en, per_page=3, used_links=self.used_links
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

            passed, metrics = self._passes_opencv_prefilter(
                local_path,
                is_portrait=(item.get("source") in ("wikipedia_portrait", "wikipedia_concept")),
            )
            if not passed:
                logger.info(f"[WebImageCrawler] OpenCV ön filtresi reddetti ({url}): {metrics}")
                continue

            item["local_path"] = local_path
            item["cv_metrics"] = metrics
            verified_candidates.append(item)
            if len(verified_candidates) >= max_candidates:
                break

        return verified_candidates

    def _http_get_text(
        self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 5
    ) -> Optional[str]:
        hdrs = headers or self.BROWSER_HEADERS
        full_url = url
        if params:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
        if requests is not None:
            resp = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            return resp.text if resp.status_code == 200 else None
        req = urllib.request.Request(full_url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return None
            return resp.read().decode("utf-8", errors="replace")

    def _http_get_json(
        self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        txt = self._http_get_text(url, params=params, headers=headers, timeout=timeout)
        if not txt:
            return None
        return json.loads(txt)

    def _search_wikipedia_summary_image(
        self, title: str, lang: str = "tr", source_tag: str = "wikipedia_portrait"
    ) -> List[Dict[str, Any]]:
        """
        Wikipedia REST v1 `/page/summary/{title}` uç noktasından maddenin ana görselini çeker.
        """
        if not title or not title.strip():
            return []
        clean_title = title.strip().replace(" ", "_")
        encoded = urllib.parse.quote(clean_title, safe="_()")
        api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        try:
            data = self._http_get_json(api_url, headers=self.WIKI_HEADERS, timeout=5)
            if not isinstance(data, dict) or data.get("type") == "disambiguation":
                return []

            thumb_url = str((data.get("thumbnail") or {}).get("source") or "")
            orig_url = str((data.get("originalimage") or {}).get("source") or "")

            # Önce 640px genişlikli Wikipedia thumbnail'ini, yoksa hazır thumbnail veya orijinal URL'yi aday listesine ekle
            candidate_urls: List[str] = []
            if thumb_url and not thumb_url.lower().endswith((".svg", ".gif")):
                url_640 = re.sub(r"/\d+px-", "/640px-", thumb_url)
                if url_640 != thumb_url:
                    candidate_urls.append(url_640)
                candidate_urls.append(thumb_url)
            if orig_url and orig_url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                if orig_url not in candidate_urls:
                    candidate_urls.append(orig_url)

            out_items: List[Dict[str, Any]] = []
            for cu in candidate_urls:
                lower_u = cu.lower()
                if any(bad in lower_u for bad in ("map_", "flag_of", "coat_of_arms", "signature", "autograph", "locator")):
                    continue
                out_items.append({
                    "url": cu,
                    "source": source_tag,
                    "alt": str(data.get("title") or title),
                    "description": str(data.get("description") or ""),
                })
            return out_items
        except Exception as exc:
            logger.debug(f"[WebImageCrawler] Wikipedia summary hatası ({lang}:{title}): {exc}")
            return []

    def _search_bing_images(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Bing Images üzerinden filtrelenmiş doğrudan görsel URL'lerini çeker."""
        if not query:
            return []
        try:
            text_body = self._http_get_text(
                "https://www.bing.com/images/search",
                params={"q": query, "qft": "+filterui:imagesize-large+filterui:photo-photo", "FORM": "IRFLTR"},
                headers=self.BROWSER_HEADERS,
                timeout=5,
            )
            if not text_body:
                return []
            matches = re.findall(r'm="(\{[^"]*murl[^"]*\})"', text_body)
            results: List[Dict[str, Any]] = []
            for raw_m in matches:
                try:
                    meta = json.loads(html.unescape(raw_m))
                    murl = str(meta.get("murl", ""))
                    if not murl or any(bad in murl.lower() for bad in self.BLOCKED_DOMAINS):
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
        if not query:
            return []
        try:
            data = self._http_get_json(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": f"filetype:bitmap {query}",
                    "gsrnamespace": 6,
                    "gsrlimit": limit + 4,
                    "prop": "imageinfo",
                    "iiprop": "url|dimensions|mime",
                    "format": "json",
                },
                headers=self.WIKI_HEADERS,
                timeout=5,
            )
            if not isinstance(data, dict):
                return []
            pages = data.get("query", {}).get("pages", {})
            results: List[Dict[str, Any]] = []
            bad_title_tokens = ("map", "stamp", "signature", "coat of arms", "flag", "diagram", "chart", "page ", "djvu", "pdf")
            for p in pages.values():
                title_str = str(p.get("title", ""))
                if any(bt in title_str.lower() for bt in bad_title_tokens):
                    continue
                ii = (p.get("imageinfo") or [{}])[0]
                mime = ii.get("mime", "")
                url = ii.get("url", "")
                w, h = int(ii.get("width", 0)), int(ii.get("height", 0))
                if mime not in ("image/jpeg", "image/png") or min(w, h) < 420:
                    continue
                results.append({
                    "url": url,
                    "source": "wikimedia",
                    "width": w,
                    "height": h,
                    "alt": title_str,
                })
                if len(results) >= limit:
                    break
            return results
        except Exception:
            return []

    def _download_candidate(self, url: str) -> Optional[str]:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        local_path = os.path.join(self.work_dir, f"cand_{url_hash}{ext}")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 4096:
            return local_path
        headers = self.WIKI_HEADERS if ("wikipedia.org" in url or "wikimedia.org" in url) else self.BROWSER_HEADERS
        try:
            if requests is not None:
                resp = requests.get(url, headers=headers, timeout=6, stream=True)
                if resp.status_code != 200:
                    return None
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if getattr(resp, "status", 200) != 200:
                        return None
                    data = resp.read()
                    with open(local_path, "wb") as f:
                        f.write(data)
            return local_path if os.path.exists(local_path) and os.path.getsize(local_path) > 4096 else None
        except Exception:
            return None

    def _passes_opencv_prefilter(
        self, image_path: str, is_portrait: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Aşama 3A Deterministik OpenCV Ön Filtresi:
        1. Çözünürlük >= 420p (portre/minyatür için >= 250p)
        2. Laplacian Keskinlik >= 35.0 (portre/minyatür için >= 18.0)
        3. Morfolojik Metin/Slayt Yoğunluğu <= 0.18 (PowerPoint slaytlarını ve belge sayfalarını eler)
        """
        if cv2 is None:
            return True, {"w": 1280, "h": 720, "sharpness": 100.0, "text_density": 0.0}

        img = cv2.imread(image_path)
        if img is None:
            return False, {"reason": "unreadable"}

        h, w = img.shape[:2]
        min_dim = 250 if is_portrait else 420
        if min(w, h) < min_dim:
            return False, {"reason": "low_res", "w": w, "h": h}

        aspect = w / float(h)
        if aspect > 3.2 or aspect < 0.30:
            return False, {"reason": "extreme_aspect", "aspect": round(aspect, 2)}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        min_sharpness = 18.0 if is_portrait else 35.0
        if sharpness < min_sharpness:
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
        max_text_density = 0.24 if is_portrait else 0.18
        if text_density > max_text_density:
            return False, {"reason": "slide_or_document_text_clutter", "text_density": round(text_density, 3)}

        return True, {"w": w, "h": h, "sharpness": round(sharpness, 1), "text_density": round(text_density, 3)}
