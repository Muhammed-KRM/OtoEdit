# OtoEdit: Kapsamlı Mimari ve Arayüz Çözüm Rehberi (Detaylı Uygulama Adımları)

Bu döküman, tespit edilen 8 kritik arayüz ve işlevsel sorunun sistem üzerinde **hangi dosyalarda, hangi satırlarda ve tam olarak hangi kod değişiklikleriyle** çözüleceğini anlatan, yazılım geliştirme sürecinde birebir referans alınacak kapsamlı bir kılavuzdur.

---

## 1. Kırmızı ve Sarı İşaretlerin Sağa Kayması (Timeline Slippage)

### Kök Neden
OtoEdit'te mevcut zaman çizelgesi (timeline), klipleri `<div class="flex">` etiketi içerisinde yan yana dizerek oluşturmaktadır. Video süresi uzadıkça ve kesim sayısı (100+) arttıkça; her klibin sınır çizgisi (border), iç boşluğu (padding) ve CSS motorunun piksel altı (subpixel) yuvarlama hataları birikir (Cumulative Layout Shift / Drift).
Üstteki zaman cetveli `position: absolute; left: 10%` gibi mutlak (absolute) değerlerle konumlanırken, aşağıdaki klipler `flex` ile göreceli dizildiğinden 10. dakikaya gelindiğinde klipler cetvelin 10-15 saniye ilerisine kaymış olur.

### Çözüm ve Kod Değişikliği
Klipler `flex` akışından çıkarılacak ve zaman cetveli gibi mutlak konumlamaya (Absolute Positioning) geçirilecektir.

**Değişecek Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` (Inline Template Kısmı)

**Eski Kod (Flexbox):**
```html
<!-- Klipleri Taşıyan Konteyner -->
<div class="flex h-full w-max min-w-full">
  <div *ngFor="let clip of clips()" [style.width.px]="getClipWidth(clip)" class="border-r border-white/20">
      <!-- Klip İçeriği -->
  </div>
</div>
```

**Yeni Kod (Mutlak Konumlandırma):**
```html
<!-- Klipleri Taşıyan Konteyner (Relative yapıyoruz) -->
<div class="relative h-full w-full">
  <div *ngFor="let clip of clips()" 
       class="absolute top-0 bottom-0 border-r border-white/20"
       [style.left.%]="(clip.start / totalDuration()) * 100"
       [style.width.%]="((clip.end - clip.start) / totalDuration()) * 100">
      
      <!-- Klip İçeriği (Kırmızı, Sarı, Mavi Bloklar) -->
      <div [ngClass]="getClipClass(clip)" class="w-full h-full relative group">
          <!-- İptal Et hover butonu vs. -->
      </div>
  </div>
</div>
```
Bu sayede her klip videonun toplam süresine oranla `%` cinsinden tam saniyesine matematiksel olarak çivilenmiş olacaktır.

---

## 2. Ses Dalga Formunun Sahte Olması ve Senkron Sorunu

### Kök Neden
Frontend'de `loadAudioWaveform` fonksiyonu, 500MB'lık koca videoyu tarayıcı üzerinden `fetch()` ile indirmeye çalışmaktadır. Tarayıcı RAM sınırına veya zaman aşımına takıldığında işlem `catch` bloğuna düşer ve yazılımcının koyduğu `Math.sin()` fonksiyonuyla rastgele bir dalga çizilir.

### Çözüm ve Kod Değişikliği
Ağır işi Python Worker yapacak. Videodan sesi `scipy` ile analiz edip (1 saniyede biter), 1000 noktalık hafif bir JSON dizisi çıkaracak ve bunu Angular'a gönderecek.

**Adım 1: Python Worker Tarafı**
**Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py`

```python
import scipy.io.wavfile as wavfile
import numpy as np

def _extract_audio_peaks(audio_path, num_peaks=1000):
    try:
        sample_rate, data = wavfile.read(audio_path)
        # Stereo ise mono'ya çevir
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        
        chunk_size = len(data) // num_peaks
        peaks = []
        for i in range(num_peaks):
            chunk = data[i * chunk_size : (i+1) * chunk_size]
            # RMS (Root Mean Square) genliğini hesapla
            peak = np.sqrt(np.mean(chunk**2))
            peaks.append(float(peak))
            
        # Normalize (0.0 - 1.0 arasına)
        max_val = max(peaks) if max(peaks) > 0 else 1
        return [p / max_val for p in peaks]
    except Exception as e:
        logger.error(f"Waveform çıkarılamadı: {e}")
        return []

# _on_message içinde:
audio_peaks = _extract_audio_peaks(clean_audio_path)

# edl_builder'a gönder:
edl_dict = self.edl_builder.build(..., audio_peaks=audio_peaks)
```

**Adım 2: Frontend Tarafı**
**Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts`

```typescript
// loadAudioWaveform fonksiyonunu tamamen değiştirin:
loadAudioWaveform() {
  const peaks = this.activeEdl()?.audioPeaks;
  if (peaks && peaks.length > 0) {
    this.drawRealWaveform(peaks);
  } else {
    // Sadece eski analizler (audioPeaks olmayanlar) için mock
    this.generateFallbackWaveform(); 
  }
}

drawRealWaveform(peaks: number[]) {
  // Canvas Context'i al ve gelen peaks dizisini çizgi olarak çiz
  const ctx = this.waveformCanvas.nativeElement.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  // ... çizim döngüsü (peaks dizisini dolaş)
}
```

---

## 3. Playhead (Zaman İğnesi) Scrubbing Eksikliği

### Kök Neden
Oynatma çubuğuna sadece `(click)="seekTo(...)"` bağlanmış. Fare basılı tutulduğunda videonun anlık olarak takip etmesi (Scrubbing) kodlanmamış. İğnenin kendisine de `pointer-events-none` verilmiş.

### Çözüm ve Kod Değişikliği
**Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts`

**TypeScript Kısmı:**
```typescript
isScrubbing = false;

@HostListener('window:mousemove', ['$event'])
onWindowMouseMove(event: MouseEvent) {
  if (!this.isScrubbing) return;
  
  const timelineRect = this.timelineContainer.nativeElement.getBoundingClientRect();
  const scrollLeft = this.timelineScrollArea.nativeElement.scrollLeft;
  
  // Farenin X pozisyonunu zamana çevir
  let x = event.clientX - timelineRect.left + scrollLeft;
  x = Math.max(0, Math.min(x, this.getTimelineWidthPixels()));
  
  const percentage = x / this.getTimelineWidthPixels();
  const targetTime = percentage * this.totalDuration();
  
  this.videoPlayer.nativeElement.currentTime = targetTime;
  this.currentTime.set(targetTime);
}

@HostListener('window:mouseup')
onWindowMouseUp() {
  if (this.isScrubbing) {
    this.isScrubbing = false;
  }
}

onPlayheadDragStart(event: MouseEvent) {
  this.isScrubbing = true;
  event.preventDefault(); // Metin seçimini engelle
}
```

**HTML Kısmı:**
```html
<!-- Playhead (İğne) div'i -->
<div class="absolute top-0 bottom-0 z-50 cursor-ew-resize pointer-events-auto"
     [style.left.%]="(currentTime() / totalDuration()) * 100"
     (mousedown)="onPlayheadDragStart($event)">
     <!-- İğne Çizgisi ve Tepe İkonu -->
</div>
```

---

## 4. Yatay Kaydırma (Timeline Pan) Sorunu

### Kök Neden
Farenin tekerleği varsayılan olarak dikey kaydırma yapar. Tarayıcıda dikey taşma (overflow-y) yoksa hiçbir şey olmaz. Kodda sadece `Shift` tuşuna basılırsa yatay kaydırma yapmaya izin verilmiş.

### Çözüm ve Kod Değişikliği
**Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts`

```typescript
onTimelineWheel(event: WheelEvent) {
  event.preventDefault(); // Varsayılan sayfa kaydırmasını durdur

  if (event.ctrlKey) {
    // CTRL + Tekerlek = ZOOM
    const zoomDelta = event.deltaY > 0 ? -0.1 : 0.1;
    this.timelineZoom.update(z => Math.max(1, Math.min(z + zoomDelta, 10)));
  } else {
    // Normal Tekerlek = YATAY KAYDIRMA (Shift gerektirmez)
    // deltaY'yi scrollLeft'e ekliyoruz
    const scrollContainer = this.timelineScrollArea.nativeElement;
    scrollContainer.scrollLeft += event.deltaY * 1.5; // Akıcı olması için 1.5 çarpanı
  }
}
```

---

## 5. İptal Et / Geri Yükle Yazısının Kutudan Taşması

### Kök Neden
Örneğin 0.5 saniyelik çok kısa bir jump-cut klibin genişliği ekranda 10 piksel oluyor. Ancak içine koyduğumuz "↩ Geri Yükle" hover butonunun minimum metin genişliği 70 piksel. CSS bu durumu tolere edemeyip yazıyı sola taşırıyor.

### Çözüm ve Kod Değişikliği
Hover elemanına `whitespace-nowrap` vereceğiz ve dışarı taşmasına izin vereceğiz, ancak konumlandırmasını kutunun ortasına sabitleyeceğiz (`left-1/2 -translate-x-1/2`).

**HTML Kısmı:**
```html
<div class="absolute inset-0 bg-rose-500/80 ... group">
   <!-- Tooltip Mantığında Ortalama -->
   <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 
               opacity-0 group-hover:opacity-100 transition-opacity 
               whitespace-nowrap px-2 py-0.5 bg-black/80 rounded z-50 text-[10px]">
       ↩ İptal Et
   </div>
</div>
```

---

## 6. Net Videonun Orijinal Süreyle Aynı Yazması

### Kök Neden
`visibleDuration` fonksiyonu, şu an görünür olan (filtrelerden geçen) kliplerin süresini topluyor. Kullanıcı AI Sessizlikleri (kırmızı kutular) butonunu açıp bunları görmek istediğinde, bu fonksiyon onları da toplayıp Net Süreyi orijinal süreyle (22:35) aynı çıkarıyor.

### Çözüm ve Kod Değişikliği
Net süre filtrelerden tamamen bağımsız çalışmalı, yani: **Toplam Süre - Kesilen Süreler**.

**Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts`

```typescript
// visibleDuration isimli sinyali şu şekilde değiştirin:
readonly visibleDuration = computed(() => {
   // Filtrelere bakmaksızın tüm klipleri getir
   const allClips = this.clips(); 
   let totalCut = 0;
   
   for (const c of allClips) {
       // Kırmızı (jumpcut) veya Sarı (retake) olanları topla
       if (c.source === 'auto' && (c.reason.includes('silence') || c.reason.includes('retake'))) {
           // Eğer kullanıcı o klibi iptal etmemişse (aktif bir kesimse)
           if (!c.isRestored) {
               totalCut += (c.end - c.start);
           }
       }
   }
   
   // Toplam süreden kesilenleri çıkar
   return Math.max(0, this.totalDuration() - totalCut);
});
```

---

## 7. Inspector Inputlarının Beyaz Olması

### Kök Neden
`tailwind.config.js` dosyasında `dark: { 950: '#060913' }` gibi bir renk kodu yok. `bg-dark-950` sınıfı derlenmiyor, inputlar tarayıcı varsayılanı beyaz arka plan alıyor. `text-white` verildiği için beyaz üstüne beyaz oluyor.

### Çözüm ve Kod Değişikliği
**Dosya:** `d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/tailwind.config.js`

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        dark: {
          50: '#f6f7fa',
          // ... diğerleri ...
          900: '#0f172a',
          950: '#060913', // EKSİK OLAN SATIR EKLENDİ
        },
        brand: {
          cyan: '#22d3ee',
          // ...
        }
      }
    }
  }
}
```

Ayrıca Inspector inputlarına şu sınıflar standart eklenecek:
`class="w-full bg-dark-950 border border-slate-700 rounded p-1.5 text-xs text-white focus:bg-dark-900 focus:border-brand-cyan"`

---

## 8. Çift Altyazı ve Altyazı Kanalı (Subtitle Track)

### Kök Neden
Video oynatıcısında `<track kind="subtitles">` HTML elementi kullanılmış. Tarayıcı kendi standart siyah kutulu altyazısını çıkarıyor. Ayrıca altyazılar sadece ekranda görünüyor, timeline'da bir katman olarak düzenlenemiyor.

### Çözüm ve Kod Değişikliği

**Adım 1: Native Track'i Kaldırın**
```html
<!-- ESKİ -->
<video>
  <track *ngIf="vttTrackUrl()" kind="subtitles" [src]="vttTrackUrl()">
</video>

<!-- YENİ (Track Yok, Karaoke Div ile devam ediyoruz) -->
<video #videoPlayer [src]="videoUrl()" ...></video>
```

**Adım 2: Altyazı Kanalı Çizimi (Timeline'a)**
Zaman çizelgesi katmanlarına özel bir `Subtitles` bölümü eklenecek.

```html
<!-- Katmanlar Arasında Altyazı Şeridi -->
<div class="h-10 w-full relative border-b border-slate-800 bg-dark-900/40">
   <div class="absolute left-0 top-0 bottom-0 w-[120px] bg-dark-950 border-r border-slate-700 flex items-center px-2 z-10 shadow-md">
       <span class="text-[10px] font-bold text-amber-400">💬 Altyazı</span>
   </div>
   
   <!-- Transkript Kelime Blokları -->
   <div class="absolute left-[120px] right-0 top-0 bottom-0 overflow-hidden">
       <div *ngFor="let seg of activeEdl()?.transcript?.segments"
            (click)="openSubtitleInspector(seg)"
            class="absolute top-1 bottom-1 bg-amber-500/20 border border-amber-500/50 rounded flex items-center px-1 text-[8px] text-amber-100 overflow-hidden cursor-pointer hover:bg-amber-500/40"
            [style.left.%]="(seg.start / totalDuration()) * 100"
            [style.width.%]="((seg.end - seg.start) / totalDuration()) * 100">
            {{ seg.text }}
       </div>
   </div>
</div>
```
Bu kod, konuşulan her cümleyi sarı bloklar halinde timeline'a dökecektir. Kullanıcı tıkladığında Inspector açılacak ve metindeki kelime hatalarını düzeltebilecektir.

---

**NOT:** Bu döküman, D:\OtoEdit\OtoEdit\docs klasörüne kalıcı teknik kılavuz olarak yazılmıştır. Geliştirici ekip, işlevsel sorunların çözümünü birebir bu dökümandaki kod yapılarıyla sağlayacaktır.
