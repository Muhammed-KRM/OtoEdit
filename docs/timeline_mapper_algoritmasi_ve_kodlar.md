# 🎬 OtoEdit — TimelineMapper Zaman Haritalama Algoritması ve Kod Mimarisi

> **Konum:** `src/OtoEdit.PythonWorker/render/timeline_mapper.py` (Gelecek Eklenti)  
> **Amaç:** Orijinal videodan kesilen boşluklar atıldıktan sonra (FFmpeg trim/concat), geriye kalan videodaki zaman çizgisine (timeline) **altyazıların, kelime-kelime karaoke sürelerinin ve görsel/metin overlay'lerinin** tam milisaniyesinde oturmasını sağlamak.

---

## 1. Temel Algoritma Mantığı (Nasıl Çalışır?)

Elimizde FFmpeg'e gönderdiğimiz, videonun **silinmeyen (korunan)** sahnelerinin bir listesi vardır. Buna `keep_segments` diyoruz.  
Örnek `keep_segments`: `[(0.0, 5.0), (10.0, 15.0)]`
* **Sahne 1:** 0'dan 5. saniyeye kadar. (5 sn sürdü, yeni videoda 0.0 - 5.0 arasına oturdu)
* **Sahne 2:** 10'dan 15. saniyeye kadar. (Önceki sahneler 5 saniye olduğu için, yeni videoda 5.0 - 10.0 arasına oturdu).

**Kural:** Orijinal videodaki herhangi bir $T$ anı, eğer korunan bir aralığın (`keep_segments[i]`) içindeyse; yeni zamanı = *Kendinden önceki sahnelerin toplam süresi + ($T$ - O anki sahnenin başlangıç süresi)* olarak hesaplanır. Eğer $T$ hiçbir korunan aralıkta değilse, kesilmiş (silinmiş) demektir ve çöpe atılır (`None` döner).

---

## 2. Adım Adım Kod Mimarisi ve Örnekler

### Adım 2.1: Tekil Zaman Noktasını Çeviren Çekirdek Fonksiyon

Bu fonksiyon, verilen tek bir saniye değerini alır ve yeni videodaki karşılığını hesaplar.

```python
from typing import List, Tuple, Optional, Dict, Any

class TimelineMapper:
    
    @staticmethod
    def remap_timestamp(t: float, keep_segments: List[Tuple[float, float]]) -> Optional[float]:
        """
        Orijinal videodaki 't' saniyesini, kesilmiş videodaki yeni saniyesine dönüştürür.
        Eğer 't' kesilen/silinen bir bölgedeyse None döner.
        """
        accumulated_duration = 0.0
        
        for (start, end) in keep_segments:
            # Eğer 't' bu korunan segmentin içindeyse
            if start <= t <= end:
                # Yeni zaman = Şu ana kadar biriken süre + segment içindeki konumu
                return accumulated_duration + (t - start)
            
            # Sonraki segmentin başlangıç kümülatifini hesapla
            accumulated_duration += (end - start)
            
        # Hiçbir segmente düşmediyse (kesilmiş bölgededir)
        return None
```

### Adım 2.2: Overlay'leri (Metin ve Görsel) Kaydırma

Overlay'ler `timestamp` (başlangıç) ve `duration` (süre) barındırır. Başlangıç noktası kesilen bir bölgeye düşerse objeyi listeden tamamen atarız. Başarılıysa, yeni zamanını yazar süresine dokunmayız.

```python
    @staticmethod
    def remap_overlays(overlays: List[Dict[str, Any]], keep_segments: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """
        Kullanıcının eklediği metin, logo ve görsellerin zamanlarını yeni videoya göre ayarlar.
        """
        remapped_overlays = []
        
        for ov in overlays:
            orig_t = float(ov.get("timestamp", 0.0))
            new_t = TimelineMapper.remap_timestamp(orig_t, keep_segments)
            
            if new_t is not None:
                # Objenin kopyasını oluştur ve timestamp'i güncelle
                new_ov = dict(ov)
                new_ov["timestamp"] = new_t
                remapped_overlays.append(new_ov)
                
        return remapped_overlays
```

### Adım 2.3: Whisper Transkriptini (Karaoke dahil) Kaydırma

Transkript içindeki hem cümlelerin (`start`, `end`) hem de her bir kelimenin (`words` dizisindeki `start`, `end`) saniyeleri yeniden hesaplanmalıdır.

```python
    @staticmethod
    def remap_transcript(transcript: Dict[str, Any], keep_segments: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Whisper'dan gelen altyazı cümlelerinin ve kelimelerinin zamanlarını kaydırır.
        Kesilen yerlere düşen kelimeleri veya tamamen silinen cümleleri temizler.
        """
        if not transcript or "segments" not in transcript:
            return transcript
            
        remapped_segments = []
        
        for segment in transcript["segments"]:
            orig_start = segment.get("start", 0.0)
            orig_end = segment.get("end", 0.0)
            
            new_start = TimelineMapper.remap_timestamp(orig_start, keep_segments)
            new_end = TimelineMapper.remap_timestamp(orig_end, keep_segments)
            
            # Eğer cümlenin başı veya sonu geçerliyse (tamamen silinmemişse)
            if new_start is not None and new_end is not None:
                new_seg = dict(segment)
                new_seg["start"] = new_start
                new_seg["end"] = new_end
                
                # Kelime (Karaoke) seviyesi haritalama
                if "words" in new_seg:
                    remapped_words = []
                    for word in new_seg["words"]:
                        w_new_start = TimelineMapper.remap_timestamp(word["start"], keep_segments)
                        w_new_end = TimelineMapper.remap_timestamp(word["end"], keep_segments)
                        
                        if w_new_start is not None and w_new_end is not None:
                            new_word = dict(word)
                            new_word["start"] = w_new_start
                            new_word["end"] = w_new_end
                            remapped_words.append(new_word)
                    new_seg["words"] = remapped_words
                    
                remapped_segments.append(new_seg)
                
        return {"segments": remapped_segments}
```

---

## 3. Doğrulama (Unit Test) Mimari Planı

Birim testler (`tests/test_timeline_mapper.py`), fonksiyonlarımızın her durumda çalıştığını ispatlayacaktır.

```python
import pytest
from render.timeline_mapper import TimelineMapper

def test_remap_timestamp_basic():
    # 0-5 sn korunuyor, 5-10 kesiliyor, 10-15 korunuyor
    keep_segments = [(0.0, 5.0), (10.0, 15.0)]
    
    # 1. Sahnenin İçi (Aynı kalmalı)
    assert TimelineMapper.remap_timestamp(2.0, keep_segments) == 2.0
    
    # 2. Sahnenin İçi (Kesilen boşluk çıkarılarak kaymalı: 12 -> 7)
    assert TimelineMapper.remap_timestamp(12.0, keep_segments) == 7.0
    
    # Kesilen Bölgenin İçi (None dönmeli)
    assert TimelineMapper.remap_timestamp(8.0, keep_segments) is None

def test_remap_overlays_filters_cut_content():
    keep_segments = [(0.0, 5.0), (10.0, 15.0)]
    overlays = [
        {"type": "text", "timestamp": 2.0, "text": "Başarılı Sahne 1"},
        {"type": "image", "timestamp": 8.0, "source": "logo.png"}, # Kesilen alan!
        {"type": "text", "timestamp": 12.0, "text": "Başarılı Sahne 2"}
    ]
    
    remapped = TimelineMapper.remap_overlays(overlays, keep_segments)
    
    # logo.png (8. saniye) otomatik silinmeli!
    assert len(remapped) == 2
    assert remapped[0]["timestamp"] == 2.0
    assert remapped[1]["timestamp"] == 7.0 # 12.0 olan timestamp 7.0'a kaydı
```

## 4. Uygulama Rotası
1. `src/OtoEdit.PythonWorker/render/timeline_mapper.py` oluşturulacak ve yukarıdaki kod eklenecek.
2. `src/OtoEdit.PythonWorker/tests/test_timeline_mapper.py` oluşturulacak.
3. `src/OtoEdit.PythonWorker/render/video_renderer.py` içerisindeki `render()` metodunda `TextOverlay.generate_ass()` çağrılmadan hemen önce `TimelineMapper` araya girecek.
