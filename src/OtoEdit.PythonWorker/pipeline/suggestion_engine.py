from typing import List
from models.edl_model import SuggestionItem
from models.transcript_model import TranscriptResult
from services.gemini_client import GeminiClient
from services.pexels_client import PexelsClient
from utils.logger import get_logger

logger = get_logger(__name__)


class SuggestionEngine:
    """Transkriptten akıllı B-Roll ve vurgu metin önerileri üretip Pexels ile zenginleştiren motor."""

    def __init__(self):
        self.gemini_client = GeminiClient()
        self.pexels_client = PexelsClient()

    def generate_suggestions(self, transcript: TranscriptResult) -> List[SuggestionItem]:
        """Transkripti analiz edip zenginleştirilmiş onay bekleyen öneri listesi döner."""
        logger.info(f"Akıllı öneri motoru çalışıyor (süre={transcript.duration:.1f}s)")
        suggestions = []

        raw_suggestions = self.gemini_client.generate_content_suggestions(transcript.full_text, transcript.duration)

        for item in raw_suggestions:
            try:
                sug_type = item.get("type", "image_broll")
                content = item.get("content", "")
                source_url = None

                # Eğer görsel önerisi ise Pexels üzerinden gerçek stok fotoğraf ara
                if sug_type == "image_broll" and content:
                    source_url = self.pexels_client.search_photo(content)

                suggestions.append(SuggestionItem(
                    id=item.get("id", f"sug_{len(suggestions)+1}"),
                    type=sug_type,
                    title=item.get("title", "İçerik Önerisi"),
                    content=content,
                    sourceUrl=source_url,
                    timestamp=float(item.get("timestamp", 0.0)),
                    duration=float(item.get("duration", 4.0)),
                    reason=item.get("reason", "İlgili görsel/metin"),
                    status="pending"  # Kullanıcı onayı bekleyen varsayılan durum
                ))
            except Exception as e:
                logger.warning(f"Öneri öğesi dönüştürülemedi: {e}")

        logger.info(f"Akıllı öneri motoru tamamlandı: {len(suggestions)} öneri oluşturuldu.")
        return suggestions
