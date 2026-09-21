"""
OtoEdit Akıllı B-Roll ve Görsel Zenginleştirme Motoru
Transkripti analiz eder, semantik anahtar kelimelerle Pexels'ten stok görseller bulur
ve doğrudan EDL OverlayItem katmanına şık animasyonlarla yerleştirir.
"""
from typing import List, Dict, Any, Optional
import json
from models.edl_model import OverlayItem
from models.transcript_model import TranscriptResult
from services.gemini_client import GeminiClient
from services.pexels_client import PexelsClient
from utils.logger import get_logger

logger = get_logger(__name__)


class AutoBrollEngine:
    """Videodaki konuşmalara göre otomatik görsel zenginleştirme yapan motor."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.pexels = PexelsClient()

    def generate_broll_overlays(
        self,
        transcript: TranscriptResult,
        video_format_str: str = "16:9",
        max_visuals: int = 6
    ) -> List[OverlayItem]:
        """
        Transkriptten en kritik görsel anları çıkarır ve Pexels'ten bulunan
        fotoğrafları OverlayItem listesi olarak döndürür.
        """
        if not transcript.full_text or transcript.duration < 5.0:
            logger.info("Transkript yetersiz olduğu için otomatik B-Roll atlandı.")
            return []

        logger.info(f"🎬 Otomatik B-Roll motoru çalışıyor (Format={video_format_str}, Süre={transcript.duration:.1f}s)...")
        overlays: List[OverlayItem] = []

        # 1. Gemini ile transkriptteki kilit görsel anları ve İngilizce arama terimlerini çıkar
        raw_prompts = self._extract_visual_moments_with_gemini(transcript)

        orientation = "portrait" if video_format_str == "9:16" else "landscape"
        used_timestamps: List[float] = []

        for idx, item in enumerate(raw_prompts[:max_visuals], start=1):
            timestamp = float(item.get("timestamp", 0.0))
            search_query = item.get("search_query", "").strip()
            concept_tr = item.get("concept", "Görsel")
            duration = float(item.get("duration", 3.5))

            # Zaman çakışması önleme (iki görsel arasında en az 4.0 saniye olmalı)
            if any(abs(timestamp - ut) < 4.0 for ut in used_timestamps):
                continue

            if not search_query:
                continue

            # 2. Pexels API ile gerçek görsel ara
            photo_url = self.pexels.search_photo(query=search_query, orientation=orientation)
            if not photo_url:
                # Yedek arama: ilk kelimeyi al
                fallback_query = search_query.split()[0] if " " in search_query else "technology"
                photo_url = self.pexels.search_photo(query=fallback_query, orientation=orientation)

            if not photo_url:
                logger.warning(f"Pexels görsel bulunamadı: '{search_query}'")
                continue

            # 3. Format ve konuma göre overlay ayarları
            if video_format_str == "9:16":
                pos = ["center", "top"]
                pos_x = 0.5
                pos_y = 0.25
                scale = 0.50
            elif video_format_str == "1:1":
                pos = ["right", "top"]
                pos_x = 0.70
                pos_y = 0.30
                scale = 0.40
            else:
                pos = ["right", "top"]
                pos_x = 0.75
                pos_y = 0.25
                scale = 0.35

            overlay = OverlayItem(
                id=f"overlay_auto_broll_{idx}",
                type="image",
                content=f"{concept_tr} ({search_query})",
                source=photo_url,
                timestamp=round(timestamp, 2),
                duration=round(duration, 2),
                animation="pop-up",
                position=pos,
                positionX=pos_x,
                positionY=pos_y,
                scale=scale,
                track_id=2
            )
            overlays.append(overlay)
            used_timestamps.append(timestamp)
            logger.info(f"  + B-Roll eklendi: [{timestamp:.1f}s - {timestamp+duration:.1f}s] Query='{search_query}', URL={photo_url[:45]}...")

        logger.info(f"Oto B-Roll motoru tamamlandı: Toplam {len(overlays)} görsel overlay oluşturuldu.")
        return overlays

    def _extract_visual_moments_with_gemini(self, transcript: TranscriptResult) -> List[Dict[str, Any]]:
        """Gemini'ye transkripti göndererek B-Roll için en uygun zamanları ve İngilizce Pexels terimlerini ister."""
        prompt = f"""
Sen profesyonel bir video yönetmenisin (Video Director & Content Producer).
Aşağıda bir videonun tam konuşma transkripti ve toplam süresi verilmiştir.
Görevin: Videoyu görsel olarak zenginleştirmek için konuşmacının bahsettiği en kritik 3 ila 5 anı tespit etmek.
Her an için konuşulan kavramı anlatan İNGİLİZCE bir stok fotoğraf arama terimi (Pexels query) belirle.

KURALLAR:
1. Zaman damgası (timestamp) mutlaka transkriptteki gerçek bir saniyeye denk gelmelidir (0.0 ile {transcript.duration:.1f} arasında).
2. 'search_query' alanı Pexels API'de yüksek kaliteli fotoğraf bulabilecek 1-3 kelimelik net İngilizce terim olmalıdır (Örn: 'artificial intelligence code', 'business growth graph', 'smartphone user').
3. ÇIKTI YALNIZCA GEÇERLİ BİR JSON DİZİSİ (JSON ARRAY) OLMALIDIR. Markdown (```json) bloğu dışında hiçbir açıklama veya metin yazma.

Örnek Çıktı Formatı:
[
  {{"timestamp": 4.5, "duration": 3.5, "concept": "Yapay Zeka Mimarisi", "search_query": "neural network technology"}},
  {{"timestamp": 14.2, "duration": 4.0, "concept": "Verimlilik Artışı", "search_query": "productivity office dashboard"}}
]

TRANSKRİPT:
{transcript.full_text[:3500]}
"""
        try:
            raw_response = self.gemini.generate_text(prompt)
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except Exception as ex:
            logger.error(f"Gemini B-Roll anları çıkarılırken hata: {ex}")

        # Fallback: Ekrana belirli aralıklarla transkriptten basit terimler atama
        return [
            {"timestamp": 2.0, "duration": 3.5, "concept": "Konu Girişi", "search_query": "technology workspace"},
            {"timestamp": min(max(4.0, transcript.duration - 5.0), 15.0), "duration": 4.0, "concept": "Önemli Nokta", "search_query": "digital innovation"}
        ]
