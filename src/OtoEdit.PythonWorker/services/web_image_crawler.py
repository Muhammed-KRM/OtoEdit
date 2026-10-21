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
        max_candidates: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Kişi / Alim / Filozof ve Eser tanıtımlarında (PERSON_INTRODUCTION / WORK_INTRODUCTION)
        Türkçe ve İngilizce Wikipedia özet görsellerini, madde içi görselleri (generator=images)
        ve Wikimedia Commons adaylarını toplar; OpenCV barkod/boş kapak filtresinden geçirir.
        """
        raw_pool: List[Dict[str, Any]] = []
        # 1. ÖNCE Türkçe ve İngilizce Wikipedia ana özet (Lead Infobox) görselleri
        if wiki_title_tr:
            raw_pool.extend(
                self._search_wikipedia_summary_image(
                    wiki_title_tr, lang="tr", source_tag="wikipedia_portrait"
                )
            )
        if wiki_title_en:
            raw_pool.extend(
                self._search_wikipedia_summary_image(
                    wiki_title_en, lang="en", source_tag="wikipedia_portrait"
                )
            )
        # 2. Ardından konu başlığı ile örtüşen madde içi görseller (generator=images)
        if wiki_title_tr:
            raw_pool.extend(
                self._search_wikipedia_article_images(
                    wiki_title_tr, lang="tr", source_tag="wikipedia_portrait", limit=4
                )
            )
        if wiki_title_en:
            raw_pool.extend(
                self._search_wikipedia_article_images(
                    wiki_title_en, lang="en", source_tag="wikipedia_portrait", limit=4
                )
            )
        if wiki_title_en or wiki_title_tr:
            q = wiki_title_en or wiki_title_tr
            raw_pool.extend(self._search_wikimedia_images(q, limit=4))

        verified: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()
        for item in raw_pool:
            url = str(item.get("url", ""))
            if not url or url in self.used_links or url in seen_urls:
                continue
            seen_urls.add(url)
            local_path = self._download_candidate(url)
            if not local_path:
                continue
            passed, metrics = self._passes_opencv_prefilter(local_path, is_portrait=True)
            if not passed:
                logger.info(f"[WebImageCrawler] Portre/Eser OpenCV filtresinden geçemedi ({url}): {metrics}")
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

            # Önce Wikimedia standart adım genişliği (960px) veya hazır thumbnail/orijinal URL'yi aday listesine ekle
            candidate_urls: List[str] = []
            if thumb_url and not thumb_url.lower().endswith((".svg", ".gif")):
                # KRİTİK KURAL: PDF veya DjVu taramalarının 1. sayfası (page1-...) çoğunlukla
                # kütüphane dış siyah cildi ve barkod etiketidir (Örn: Mecelle-yi_ahkâm-ı_adliyye_1869.pdf).
                # Bu durumda page1'i reddet ve iç unvan/hat sayfalarını (page3, page5, page7) aday yap!
                if re.search(r"/page1-\d+px-.*\.(pdf|djvu)\.jpg", thumb_url, re.IGNORECASE):
                    logger.info(f"[WebImageCrawler] PDF/DjVu 1. sayfa (dış cilt/barkod riski) atlandı, iç sayfalar deneniyor: {thumb_url}")
                    for inner_p in ("page3-", "page5-", "page7-"):
                        candidate_urls.append(re.sub(r"/page1-", f"/{inner_p}", thumb_url, flags=re.IGNORECASE))
                else:
                    url_960 = re.sub(r"/\d+px-", "/960px-", thumb_url)
                    if url_960 != thumb_url:
                        candidate_urls.append(url_960)
                    candidate_urls.append(thumb_url)
            if orig_url and orig_url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                if not re.search(r"\.(pdf|djvu)\b", orig_url, re.IGNORECASE) and orig_url not in candidate_urls:
                    candidate_urls.append(orig_url)

            out_items: List[Dict[str, Any]] = []
            for cu in candidate_urls:
                lower_u = cu.lower()
                if any(bad in lower_u for bad in ("map_", "flag_of", "coat_of_arms", "signature", "autograph", "locator", "commons-logo", "wikidata-logo")):
                    continue
                out_items.append({
                    "url": cu,
                    "source": source_tag,
                    "is_lead_summary": True,
                    "alt": str(data.get("title") or title),
                    "description": str(data.get("description") or ""),
                })
            return out_items
        except Exception as exc:
            logger.debug(f"[WebImageCrawler] Wikipedia summary hatası ({lang}:{title}): {exc}")
            return []

    def _search_wikipedia_article_images(
        self, title: str, lang: str = "tr", source_tag: str = "wikipedia_portrait", limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        MediaWiki `generator=images` + `prop=imageinfo` uç noktasını kullanarak madde içindeki
        diğer tüm anlamlı görselleri ve Commons extmetadata açıklamalarını çeker.
        """
        if not title or not title.strip():
            return []
        try:
            data = self._http_get_json(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": title.strip(),
                    "generator": "images",
                    "gimlimit": limit + 6,
                    "prop": "imageinfo",
                    "iiprop": "url|dimensions|mime|extmetadata",
                    "iiurlwidth": 640,
                    "format": "json",
                    "redirects": 1,
                },
                headers=self.WIKI_HEADERS,
                timeout=5,
            )
            if not isinstance(data, dict):
                return []
            pages = (data.get("query") or {}).get("pages") or {}
            out: List[Dict[str, Any]] = []
            bad_tokens = (
                "map", "flag", "coat_of_arms", "signature", "autograph", "locator",
                "commons-logo", "wikidata", "disambig", "icon", "symbol", "crystal_clear",
                "nuvola", "kit_body", "kit_left", "kit_right", "increase", "decrease",
                "mohammed_splits", "jonah_and_the_whale", "portal",
            )
            fold_map = str.maketrans("çğıöşüâîûÇĞİÖŞÜÂÎÛ", "cgiosuaiuCGIOSUAIU")
            subject_stems = [
                tok[:4]
                for tok in re.split(r"[\s_\-]+", title.translate(fold_map).lower())
                if len(tok) >= 4
            ]
            for p in pages.values():
                file_title = str(p.get("title") or "")
                lower_t = file_title.translate(fold_map).lower()
                if any(bt in lower_t for bt in bad_tokens):
                    continue
                ii = (p.get("imageinfo") or [{}])[0]
                extmeta = ii.get("extmetadata") or {}
                desc = str((extmeta.get("ImageDescription") or {}).get("value") or "")
                obj_name = str((extmeta.get("ObjectName") or {}).get("value") or file_title)
                clean_desc = re.sub(r"<[^>]+>", " ", desc).strip()
                combined_meta = f"{lower_t} {obj_name.translate(fold_map).lower()} {clean_desc.translate(fold_map).lower()}"
                if subject_stems and not any(st in combined_meta for st in subject_stems):
                    continue
                mime = str(ii.get("mime") or "").lower()
                thumb_url = str(ii.get("thumburl") or ii.get("url") or "")
                w, h = int(ii.get("thumbwidth") or ii.get("width") or 0), int(ii.get("thumbheight") or ii.get("height") or 0)
                if not thumb_url or min(w, h) < 180:
                    continue
                if "svg" in mime or "gif" in mime:
                    continue
                # Eğer PDF/DjVu ise page1 yerine page3 kullan
                if re.search(r"/page1-\d+px-.*\.(pdf|djvu)\.jpg", thumb_url, re.IGNORECASE):
                    thumb_url = re.sub(r"/page1-", "/page3-", thumb_url, flags=re.IGNORECASE)
                out.append({
                    "url": thumb_url,
                    "source": source_tag,
                    "width": w,
                    "height": h,
                    "alt": obj_name,
                    "description": clean_desc[:240],
                })
                if len(out) >= limit:
                    break
            return out
        except Exception as exc:
            logger.debug(f"[WebImageCrawler] Wikipedia article images hatası ({lang}:{title}): {exc}")
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
        min_dim = 180 if is_portrait else 420
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

        # 4. Kütüphane Barkod Etiketi ve Simsiyah/Boş Kitap Kapağı Anomali Kontrolü
        has_anomaly, anomaly_reason = self._detect_barcode_or_blank_cover_anomaly(img, gray)
        if has_anomaly:
            return False, {"reason": anomaly_reason, "w": w, "h": h, "sharpness": round(sharpness, 1)}

        return True, {"w": w, "h": h, "sharpness": round(sharpness, 1), "text_density": round(text_density, 3)}

    @staticmethod
    def _detect_barcode_or_blank_cover_anomaly(img_bgr: Any, gray: Any) -> Tuple[bool, str]:
        """
        Taranmış kütüphane kitap ciltlerini (simsiyah/boş kapak + beyaz kütüphane barkod etiketi)
        ve düşük entropili boş kapakları OpenCV ile tespit edip veto eder.
        """
        if cv2 is None or np is None:
            return False, "clean"
        h, w = gray.shape[:2]
        if h < 64 or w < 64:
            return True, "image_too_small"

        dark_ratio = float(np.mean(gray < 52))
        mid_tone_ratio = float(np.mean((gray >= 60) & (gray <= 190)))

        # Shannon entropisi
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).ravel()
        prob = hist / max(1.0, float(np.sum(hist)))
        prob = prob[prob > 0]
        entropy = float(-np.sum(prob * np.log2(prob)))

        # 1. Simsiyah / boş kapak kontrolü
        if dark_ratio > 0.60 and mid_tone_ratio < 0.24:
            return True, f"blank_dark_cover(dark={dark_ratio:.2f},mid={mid_tone_ratio:.2f})"
        if entropy < 3.6 and mid_tone_ratio < 0.20:
            return True, f"low_entropy_blank_cover(entropy={entropy:.2f})"

        # 2. Kütüphane barkod etiketi tespiti (Parlak beyaz dikdörtgen ROI içinde dikey Sobel Gx >> Gy)
        _, bright_mask = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
        closed = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_area = float(h * w)
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            patch_area_ratio = float(cw * ch) / img_area
            aspect = float(cw) / max(1.0, float(ch))
            if 0.006 <= patch_area_ratio <= 0.32 and 0.75 <= aspect <= 7.0:
                roi = gray[y : y + ch, x : x + cw]
                gx = np.abs(cv2.Sobel(roi, cv2.CV_32F, 1, 0, ksize=3))
                gy = np.abs(cv2.Sobel(roi, cv2.CV_32F, 0, 1, ksize=3))
                mean_gx = float(np.mean(gx))
                mean_gy = float(np.mean(gy))
                vert_dominance = mean_gx / (mean_gy + 1.0)
                if mean_gx > 25.0 and vert_dominance > 1.70 and dark_ratio > 0.32:
                    return True, f"library_barcode_sticker_detected(vert={vert_dominance:.2f},dark={dark_ratio:.2f})"

        return False, "clean"
