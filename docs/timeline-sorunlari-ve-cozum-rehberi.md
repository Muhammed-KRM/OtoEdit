# OtoEdit Timeline Sorunları — Kapsamlı Analiz ve Çözüm Rehberi

**Tarih:** 2026-09-23  
**Hedef Dosya:** `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts`  
**Toplam Tespit Edilen Sorun:** 7 adet kritik / önemli sorun  

---

## İçindekiler

1. [Genel Mimari Açıklama](#1-genel-mimari-açıklama)
2. [Sorunların Ortak Kök Nedeni](#2-sorunların-ortak-kök-nedeni)
3. [Sorun #1 — Sıkıştırma Klipleri Sadece Gizliyor, Gerçekten Sıkıştırmıyor](#3-sorun-1--sıkıştırma-klipleri-sadece-gizliyor-gerçekten-sıkıştırmıyor)
4. [Sorun #2 — Ses Dalga Formu (Waveform) Sıkıştırma ile Bozuluyor](#4-sorun-2--ses-dalga-formu-waveform-sıkıştırma-ile-bozuluyor)
5. [Sorun #3 — rippleRetake Toggle'ı Koordinat Fonksiyonlarına Dahil Değil](#5-sorun-3--rippleretake-toggleı-koordinat-fonksiyonlarına-dahil-değil)
6. [Sorun #4 — visibleDuration Hesaplaması Eksik ve Yanlış](#6-sorun-4--visibleduration-hesaplaması-eksik-ve-yanlış)
7. [Sorun #5 — Timeline Yatay Kaydırma (Scroll) Çalışmıyor](#7-sorun-5--timeline-yatay-kaydırma-scroll-çalışmıyor)
8. [Sorun #6 — Altyazı Segmentleri Sıkıştırma ile Hizalanmıyor](#8-sorun-6--altyazı-segmentleri-sıkıştırma-ile-hizalanmıyor)
9. [Sorun #7 — Playhead Sürükleme (Scrubbing) Ripple Modunu Dikkate Almıyor](#9-sorun-7--playhead-sürükleme-scrubbing-ripple-modunu-dikkate-almıyor)
10. [Uygulama Sırası ve Öncelikler](#10-uygulama-sırası-ve-öncelikler)
11. [Doğrulama ve Test Senaryoları](#11-doğrulama-ve-test-senaryoları)

---

## 1. Genel Mimari Açıklama

### Timeline Bileşeninin Yapısı

OtoEdit'in editör sayfası (`editor.component.ts`) yaklaşık 3361 satırlık tek bir Angular standalone component'dir. Bu component içinde inline template ve stil tanımları bulunur. Timeline bölümü sayfanın alt %44'lük kısmını kaplar ve şu yapıdadır:

```
┌─────────────────────────────────────────────────────────┐
│  Timeline Üst Araç Çubuğu (Toolbar)                     │
│  [Böl] [Sil] [Geri] [İleri] [Birleştir] [Retake Geri Al]│
│  [AI Sıkışık] [Retake Sıkışık] [Manuel Sıkışık]         │
│  [Zoom -][====][Zoom +] [+Katman] [T Yazı] [🖼️ Görsel]  │
├────────┬────────────────────────────────────────────────┤
│ KANALLAR│  Zaman Cetveli (00:00, 00:05, 00:10...)       │
├────────┼────────────────────────────────────────────────┤
│ 💬Altyazı│ [seg1][seg2][seg3]...                        │
├────────┼────────────────────────────────────────────────┤
│ T3     │ [overlay pill]                                 │
├────────┼────────────────────────────────────────────────┤
│ T2     │ [overlay pill]                                 │
├────────┼────────────────────────────────────────────────┤
│ T1     │ [overlay pill]                                 │
├────────┼────────────────────────────────────────────────┤
│ V1 Ana │ ▓▓▓░░▓▓▓▓▓░░░▓▓▓▓▓▓▓▓░░▓▓▓▓▓                │
│ Video  │ (Klipler + Arka plan Waveform)                 │
│        │      │  ← Playhead (beyaz çizgi)               │
└────────┴────────────────────────────────────────────────┘
```

### Temel Veri Yapıları

Timeline'ın çalışması şu signal ve computed'lara dayanır:

- **`totalDuration`** (signal): Video'nun toplam süresi (saniye). Video metadata'sından gelir.
- **`clips`** (computed): EDL cuts verilerinden hesaplanan klip dizisi. Her klip `{ id, start, end, duration, isCut, cutObj }` yapısındadır.
- **`audioPeaks`** (signal): Web Audio API ile çözümlenen ses dalga formu peak değerleri dizisi (0-1 arası float değerler).
- **`rippleAi`** (signal\<boolean\>): AI kesimlerini sıkıştır/genişlet toggle'ı.
- **`rippleRetake`** (signal\<boolean\>): Retake kesimlerini sıkıştır/genişlet toggle'ı.
- **`rippleManual`** (signal\<boolean\>): Manuel kesimleri sıkıştır/genişlet toggle'ı.
- **`visibleDuration`** (computed): Sıkıştırma sonrası görünen toplam süre.
- **`timelineZoom`** (signal): Zoom seviyesi (1x - 6x arası).
- **`currentTime`** (signal): Mevcut oynatma zamanı (saniye).

### Kliplerin Oluşturulma Mantığı (Satır 1435-1470)

`clips` computed signal'i şöyle çalışır:
1. `totalDuration`, tüm `cuts` başlangıç/bitiş noktaları ve `splitMarkers` bir Set'te birleştirilir
2. Bu noktalar sıralanır
3. Ardışık nokta çiftleri arasında klip nesneleri oluşturulur
4. Her klibin ortası bir cut bölgesine denk geliyorsa `isCut: true` yapılır

**Örnek:** 0-100 saniyelik bir videoda 20-30s ve 50-55s arası kesilmişse:
```
Klipler: [0-20, 20-30(cut), 30-50, 50-55(cut), 55-100]
```

### Kliplerin Görünürlüğü (Satır 1500-1509)

`isVisible(clip)` fonksiyonu şu mantıkla çalışır:
- Kesilmemiş klip → her zaman görünür
- Manuel kesim klibi → `rippleManual()` true ise gizle (sıkıştır)
- Retake kesim klibi → `rippleRetake()` true ise gizle (sıkıştır)
- AI kesim klibi → `rippleAi()` true ise gizle (sıkıştır)

```typescript
// Mevcut kod (satır 1500-1509):
isVisible(clip: any): boolean {
    if (!clip.isCut) return true;        // Kesilmemiş → her zaman göster
    if (this.isManualClip(clip)) {
       return !this.rippleManual();       // Manuel ripple açıksa → gizle
    }
    if (this.isRetakeClip(clip)) {
       return !this.rippleRetake();       // Retake ripple açıksa → gizle
    }
    return !this.rippleAi();              // AI ripple açıksa → gizle
}
```

Bu fonksiyon kendi başına doğru çalışıyor. Sorun, diğer fonksiyonların bu fonksiyonla uyumsuz olmasıdır.

---

## 2. Sorunların Ortak Kök Nedeni

Tüm 7 sorunun altında yatan **tek temel tasarım hatası** şudur:

> Timeline üzerindeki tüm öğeler (klipler, altyazılar, overlay'ler, waveform) **orijinal video süresine (`totalDuration()`)** göre `absolute` pozisyonla konumlandırılıyor. Sıkıştırma butonları klipleri `isVisible()` ile gizliyor ama **pozisyonlarını değiştirmiyor**. Bu yüzden sıkıştırma aktifken:
> - Gizlenen kliplerin yerinde boşluklar kalıyor
> - Waveform arka planı orijinal dağılımıyla çizilmeye devam ediyor
> - Altyazı segmentleri eski pozisyonlarında duruyor
> - Playhead/seek hesaplamaları tutarsızlaşıyor

**Beklenen Davranış (CapCut tarzı ripple edit):**
Bir klip sıkıştırıldığında (gizlendiğinde), sonraki tüm klipler sola kaymalı ve boşluk kalmamalıdır. Waveform da buna uyum sağlamalıdır.

**Mevcut Davranış:**
Klip gizleniyor ama yerine boşluk kalıyor. Waveform bozuluyor. Playhead yanlış yeri gösteriyor.

Şimdi her sorunu tek tek, kodun içine girerek detaylıca inceleyelim.

---

## 3. Sorun #1 — Sıkıştırma Klipleri Sadece Gizliyor, Gerçekten Sıkıştırmıyor

### Belirtiler
- Kullanıcı "🤖 AI Sıkışık" butonuna bastığında kırmızı/sarı kliplik alanlar kayboluyor
- Ancak bu kliplerin yerinde boşluklar kalıyor
- Timeline'da boş alanlar oluşuyor, klipler birbirine yapışmıyor
- Beyaz zaman oku (playhead) ileri gidiyor ama timeline düzgün sıkışmıyor

### Sorunun Kaynağı: Satır 996-1011

Template'deki klip render kodu:

```html
<!-- Satır 994-1011 -->
<ng-container *ngFor="let clip of clips()">
  <div 
    *ngIf="isVisible(clip)"
    (click)="selectClip(clip.id, $event)"
    (dblclick)="toggleClip(clip, $event)"
    (contextmenu)="openClipContextMenu($event, clip)"
    class="absolute top-0 bottom-0 ..."
    [style.left.%]="(clip.start / totalDuration()) * 100"        <!-- SORUN BURADA -->
    [style.width.%]="((clip.end - clip.start) / totalDuration()) * 100"  <!-- SORUN BURADA -->
    ...>
  </div>
</ng-container>
```

**Problem:** `*ngIf="isVisible(clip)"` ile gizlenen kliplerden sonra kalan kliplerin `left` değerleri değişmiyor. Örneğin:

```
Orijinal timeline (sıkıştırma kapalı):
|--Klip1--|--AI Cut--|--Klip2--|--AI Cut--|--Klip3--|
0%       20%       30%       50%       55%       100%

Sıkıştırma aktif (mevcut durum - YANLIŞ):
|--Klip1--|          |--Klip2--|          |--Klip3--|
0%       20%       30%       50%       55%       100%
           ↑ boşluk            ↑ boşluk

Sıkıştırma aktif (olması gereken - DOĞRU):
|--Klip1--|--Klip2--|--Klip3--|
0%                           100%
(boşluk yok, klipler yan yana)
```

### Detaylı Çözüm

#### Adım 1: Helper Fonksiyon Ekle (~Satır 1290 civarı)

```typescript
// Herhangi bir ripple toggle açık mı?
isAnyRippleActive(): boolean {
  return this.rippleAi() || this.rippleManual() || this.rippleRetake();
}
```

Bu helper fonksiyon, ilerideki tüm ripple kontrollerinde tekrar eden `!this.rippleAi() && !this.rippleManual()` kalıbının yerine kullanılacak.

#### Adım 2: Klip Pozisyon Fonksiyonları Ekle (Yeni fonksiyonlar)

```typescript
/**
 * Bir klibin timeline üzerindeki yatay başlangıç pozisyonunu yüzde olarak hesaplar.
 * 
 * Sıkıştırma KAPALI iken: Orijinal zaman pozisyonuna göre hesaplar.
 *   Formül: (clip.start / totalDuration) * 100
 * 
 * Sıkıştırma AÇIK iken: Bu klipten önceki tüm görünür kliplerin toplam
 *   süresini hesaplayarak, kliplerin boşluk bırakmadan yan yana dizilmesini sağlar.
 *   Formül: (öncekiGörünürToplamSüre / görünürToplamSüre) * 100
 */
getClipLeft(clip: any): number {
  // Hiçbir ripple toggle aktif değilse, orijinal pozisyonu kullan
  if (!this.isAnyRippleActive()) {
    return (clip.start / this.totalDuration()) * 100;
  }
  
  // Sıkıştırma aktifse: Bu klipten önceki tüm GÖRÜNÜR kliplerin toplam süresini hesapla
  const allClips = this.clips();
  const visDur = this.visibleDuration();
  if (visDur <= 0) return 0;
  
  let accumulatedDuration = 0;
  for (const c of allClips) {
    // Bu klibe ulaştıysak, dur
    if (c.id === clip.id) break;
    
    // Sadece görünür kliplerin sürelerini topla
    if (this.isVisible(c)) {
      accumulatedDuration += c.duration;
    }
  }
  
  return (accumulatedDuration / visDur) * 100;
}

/**
 * Bir klibin timeline üzerindeki genişliğini yüzde olarak hesaplar.
 * 
 * Sıkıştırma KAPALI iken: Orijinal süreye göre hesaplar.
 * Sıkıştırma AÇIK iken: Görünür toplam süreye oranla hesaplar.
 *   Bu sayede görünür klipler tüm genişliği kaplar, boşluk kalmaz.
 */
getClipWidth(clip: any): number {
  if (!this.isAnyRippleActive()) {
    return ((clip.end - clip.start) / this.totalDuration()) * 100;
  }
  
  const visDur = this.visibleDuration();
  if (visDur <= 0) return 0;
  
  return (clip.duration / visDur) * 100;
}
```

#### Adım 3: Template'i Güncelle (Satır 1009-1010)

**Eski kod:**
```html
[style.left.%]="(clip.start / totalDuration()) * 100"
[style.width.%]="((clip.end - clip.start) / totalDuration()) * 100"
```

**Yeni kod:**
```html
[style.left.%]="getClipLeft(clip)"
[style.width.%]="getClipWidth(clip)"
```

#### Neden Bu Çözüm Çalışır?

Düşünelim: 100 saniyelik bir video, 20-30s ve 50-55s arası AI tarafından kesilmiş.

**Orijinal klipler:** `[0-20, 20-30(AI), 30-50, 50-55(AI), 55-100]`

AI sıkıştırma açık olduğunda:
- Görünür klipler: `[0-20(20s), 30-50(20s), 55-100(45s)]`
- `visibleDuration` = 20 + 20 + 45 = **85 saniye**

| Klip | `accumulatedDuration` öncesi | `getClipLeft()` | `getClipWidth()` |
|------|------------------------------|-----------------|-------------------|
| 0-20 | 0s                           | (0/85)*100 = 0% | (20/85)*100 = 23.5% |
| 30-50 | 20s                         | (20/85)*100 = 23.5% | (20/85)*100 = 23.5% |
| 55-100 | 40s                        | (40/85)*100 = 47.1% | (45/85)*100 = 52.9% |

Toplam: 0% + 23.5% + 23.5% + 23.5% + 52.9% ≈ 100% ✅

Klipler boşluk bırakmadan yan yana dizilir!

---

## 4. Sorun #2 — Ses Dalga Formu (Waveform) Sıkıştırma ile Bozuluyor

### Belirtiler
- Sıkıştırma aktifken ses dalga formu (mavi dalgalar) kliplerle hizalanmıyor
- Kesilen bölgelerin ses verileri hâlâ gösteriliyor
- Waveform arka planı ile klip pozisyonları uyuşmuyor

### Sorunun Kaynağı: Satır 979-992

Mevcut waveform render kodu:

```html
<!-- Satır 979-992 -->
<!-- Gerçek Ses Dalga Formu (Web Audio API Waveform SVG Arka Planı) -->
<div *ngIf="audioPeaks()?.length" class="absolute inset-0 flex items-center pointer-events-none z-0">
  <svg class="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1000 56">
    <defs>
      <linearGradient id="waveGradient" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85" />
        <stop offset="50%" stop-color="#06b6d4" stop-opacity="0.95" />
        <stop offset="100%" stop-color="#0284c7" stop-opacity="0.85" />
      </linearGradient>
    </defs>
    <path [attr.d]="getWaveformPath()" fill="url(#waveGradient)" />
    <line x1="0" y1="28" x2="1000" y2="28" stroke="#0ea5e9" stroke-opacity="0.3" stroke-width="1" />
  </svg>
</div>
```

Sorun: `getWaveformPath()` fonksiyonu (satır 1716-1743) **HER ZAMAN** tüm `audioPeaks` dizisini baştan sona kullanarak tek bir SVG path çizer. Sıkıştırma aktif olduğunda bile kesilen bölgelerin peak değerleri dahil edilir.

```typescript
// Mevcut getWaveformPath() (Satır 1716-1743):
getWaveformPath(): string {
    const peaks = this.audioPeaks();
    if (!peaks || peaks.length === 0) return '';
    
    const width = 1000;
    const height = 56;
    const midY = height / 2;
    const numPoints = peaks.length;
    const dx = width / (numPoints - 1);
    
    // Üst yarı çizimi
    let topPath = `M 0 ${midY}`;
    for (let i = 0; i < numPoints; i++) {
      const x = i * dx;
      const peakH = peaks[i] * (height / 2 - 3);
      const y = midY - peakH;
      topPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    // Alt yarı çizimi (ters sıra)
    let bottomPath = '';
    for (let i = numPoints - 1; i >= 0; i--) {
      const x = i * dx;
      const peakH = peaks[i] * (height / 2 - 3);
      const y = midY + peakH;
      bottomPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    return `${topPath} ${bottomPath} Z`;
}
```

Burada `peaks` dizisinin indeksleri doğrudan zaman çizgisinin x koordinatına eşleniyor. Peak #0 = videonun başı, peak #son = videonun sonu. Sıkıştırma aktifken kesilen bölgelerdeki peak'ler de çiziliyor.

### Detaylı Çözüm

Waveform'u sıkıştırma moduna uyumlu hale getirmek için iki yaklaşım var:

#### Yaklaşım A: Filtrelenmiş Peak Dizisi ile Tek Path (Daha Basit)

`getWaveformPath()` fonksiyonunu, sıkıştırma aktifken **sadece görünür kliplere ait peak değerlerini** kullanacak şekilde güncellemek:

```typescript
/**
 * Ses dalga formunun SVG path'ini oluşturur.
 * 
 * Sıkıştırma KAPALI: Tüm peak değerlerini kullanır.
 * Sıkıştırma AÇIK: Sadece görünür kliplere denk gelen peak
 *   değerlerini kullanır. Kesilen bölgelerin peak'leri atlanır.
 *   Bu sayede waveform, sıkıştırılmış kliplerle hizalanır.
 */
getWaveformPath(): string {
    const allPeaks = this.audioPeaks();
    if (!allPeaks || allPeaks.length === 0) return '';
    
    const width = 1000;
    const height = 56;
    const midY = height / 2;
    
    // Sıkıştırma aktif değilse orijinal peak'leri kullan
    let peaks: number[];
    if (!this.isAnyRippleActive()) {
      peaks = allPeaks;
    } else {
      // Sıkıştırma aktifse: Sadece görünür kliplere ait peak'leri topla
      peaks = this.getFilteredPeaks(allPeaks);
    }
    
    if (peaks.length === 0) return '';
    
    const numPoints = peaks.length;
    const dx = width / Math.max(1, numPoints - 1);
    
    // Üst yarı çizimi
    let topPath = `M 0 ${midY}`;
    for (let i = 0; i < numPoints; i++) {
      const x = i * dx;
      const peakH = peaks[i] * (height / 2 - 3);
      const y = midY - peakH;
      topPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    // Alt yarı çizimi (ayna - ters sıra)
    let bottomPath = '';
    for (let i = numPoints - 1; i >= 0; i--) {
      const x = i * dx;
      const peakH = peaks[i] * (height / 2 - 3);
      const y = midY + peakH;
      bottomPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    return `${topPath} ${bottomPath} Z`;
}

/**
 * Sadece görünür kliplere ait ses peak değerlerini döndürür.
 * Kesilen kliplerin peak'leri atlanır.
 * 
 * Mantık:
 * 1. Her peak indeksini zaman değerine çevir
 * 2. Bu zamanın hangi klibe ait olduğunu bul
 * 3. Eğer klip görünürse peak'i dahil et
 * 4. Görünmüyorsa atla
 */
private getFilteredPeaks(allPeaks: number[]): number[] {
    const totalDur = Math.max(1, this.totalDuration());
    const allClips = this.clips();
    const filtered: number[] = [];
    
    for (let i = 0; i < allPeaks.length; i++) {
      // Bu peak hangi zamana karşılık geliyor?
      const time = (i / allPeaks.length) * totalDur;
      
      // Bu zamandaki klibi bul
      const clip = allClips.find(c => time >= c.start && time <= c.end);
      
      // Klip yoksa veya görünürse peak'i ekle
      if (!clip || this.isVisible(clip)) {
        filtered.push(allPeaks[i]);
      }
      // Klip gizliyse (sıkıştırılmışsa) → peak'i atla
    }
    
    return filtered;
}
```

#### Yaklaşım B: Her Klip İçin Ayrı Waveform Segmenti (Daha Performanslı, Daha Doğru)

Bu yaklaşımda tek büyük bir SVG yerine, her görünür klip için kendi waveform parçası çizilir. Bu sayede kliplerin konumu ile waveform her zaman mükemmel hizalanır.

Template değişikliği:

```html
<!-- ESKI: Tek bir global waveform -->
<!--
<div *ngIf="audioPeaks()?.length" class="absolute inset-0 ...">
  <svg ...>
    <path [attr.d]="getWaveformPath()" ... />
  </svg>
</div>
-->

<!-- YENİ: Her görünür klip için ayrı waveform segmenti -->
<ng-container *ngFor="let clip of clips()">
  <div *ngIf="isVisible(clip) && audioPeaks()?.length"
       class="absolute top-0 bottom-0 pointer-events-none z-0"
       [style.left.%]="getClipLeft(clip)"
       [style.width.%]="getClipWidth(clip)">
    <svg class="w-full h-full" preserveAspectRatio="none" viewBox="0 0 200 56">
      <defs>
        <linearGradient [attr.id]="'waveGrad_' + clip.id" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85" />
          <stop offset="50%" stop-color="#06b6d4" stop-opacity="0.95" />
          <stop offset="100%" stop-color="#0284c7" stop-opacity="0.85" />
        </linearGradient>
      </defs>
      <path [attr.d]="getWaveformPathForClip(clip)" [attr.fill]="'url(#waveGrad_' + clip.id + ')'" />
      <line x1="0" y1="28" x2="200" y2="28" stroke="#0ea5e9" stroke-opacity="0.3" stroke-width="0.5" />
    </svg>
  </div>
</ng-container>
```

Yeni fonksiyon:

```typescript
/**
 * Belirli bir klibe ait waveform SVG path'ini oluşturur.
 * 
 * Klibin orijinal zamanlarına denk gelen peak değerlerini alır
 * ve 200 birimlik bir viewBox içinde çizer.
 */
getWaveformPathForClip(clip: any): string {
    const allPeaks = this.audioPeaks();
    if (!allPeaks || allPeaks.length === 0) return '';
    
    const totalDur = Math.max(1, this.totalDuration());
    
    // Bu klibin zamanlarına denk gelen peak indekslerini hesapla
    const startIdx = Math.floor((clip.start / totalDur) * allPeaks.length);
    const endIdx = Math.ceil((clip.end / totalDur) * allPeaks.length);
    const clipPeaks = allPeaks.slice(startIdx, Math.min(endIdx, allPeaks.length));
    
    if (clipPeaks.length === 0) return '';
    
    const width = 200;  // viewBox genişliği
    const height = 56;
    const midY = height / 2;
    const numPoints = clipPeaks.length;
    const dx = width / Math.max(1, numPoints - 1);
    
    // Üst yarı
    let topPath = `M 0 ${midY}`;
    for (let i = 0; i < numPoints; i++) {
      const x = i * dx;
      const peakH = clipPeaks[i] * (height / 2 - 3);
      const y = midY - peakH;
      topPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    // Alt yarı (ayna)
    let bottomPath = '';
    for (let i = numPoints - 1; i >= 0; i--) {
      const x = i * dx;
      const peakH = clipPeaks[i] * (height / 2 - 3);
      const y = midY + peakH;
      bottomPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    return `${topPath} ${bottomPath} Z`;
}
```

#### Hangi Yaklaşımı Seçmeli?

| Kriter | Yaklaşım A (Filtrelenmiş) | Yaklaşım B (Per-Klip) |
|--------|---------------------------|------------------------|
| Uygulama zorluğu | Kolay | Orta |
| Doğruluk | İyi | Mükemmel |
| Performans | Tek SVG, hızlı | Çok SVG, biraz yavaş |
| Kliplerle hizalanma | Yaklaşık | Piksel-mükemmel |

**Öneri:** Yaklaşım B'yi kullanın. Per-klip waveform, sıkıştırma modundan bağımsız olarak her zaman doğru çalışır. Performans farkı ihmal edilebilir çünkü tipik bir videoda 20-50 arası klip olur.

---

## 5. Sorun #3 — `rippleRetake` Toggle'ı Koordinat Fonksiyonlarına Dahil Değil

### Belirtiler
- Retake sıkıştırma butonu açıldığında retake klipleri gizleniyor
- Ama playhead yanlış yerde duruyor
- Timeline'a tıklayınca (seek) yanlış zamana atlıyor
- Overlay katmanları yanlış pozisyonlarda gösteriliyor

### Sorunun Kaynağı: 8+ Yerdeki Kontrol Hatası

Kodda `isVisible()` fonksiyonu 3 toggle'ı da kontrol ediyor: `rippleAi`, `rippleManual`, `rippleRetake`. Ama **diğer tüm koordinat hesaplama fonksiyonları** sadece `rippleAi` ve `rippleManual` kontrol ediyor — `rippleRetake` unutulmuş.

İşte sorunlu satırlar ve her birinin ne yaptığının açıklaması:

#### 1) `getRawTimeFromVisTime()` — Satır 2183-2197

Bu fonksiyon, sıkıştırılmış (visible) zamandan orijinal (raw) zamana dönüşüm yapar. Örneğin sıkıştırılmış timeline'da 30. saniye orijinalde kaçıncı saniyeye denk geliyor?

```typescript
// HATALI (satır 2184):
getRawTimeFromVisTime(visTime: number): number {
    if (!this.rippleAi() && !this.rippleManual()) {   // ← rippleRetake YOK!
       return Math.max(0, Math.min(this.totalDuration(), visTime));
    }
    // ... ripple hesaplaması
}
```

#### 2) `getVisTimeFromRawTime()` — Satır 2199-2216

Bu fonksiyon, orijinal zamandan sıkıştırılmış zamana dönüşüm yapar. Playhead pozisyonu bu fonksiyonla hesaplanır.

```typescript
// HATALI (satır 2200):
getVisTimeFromRawTime(rawTime: number): number {
    if (!this.rippleAi() && !this.rippleManual()) {   // ← rippleRetake YOK!
       return Math.max(0, Math.min(this.totalDuration(), rawTime));
    }
    // ... ripple hesaplaması
}
```

#### 3) `getTimeAtClientX()` — Satır 2218-2231

Mouse tıklama pozisyonunu zamana çevirir. `seekTimeline()` bu fonksiyonu kullanır.

```typescript
// HATALI (satır 2225):
getTimeAtClientX(clientX: number): number {
    // ...
    if (!this.rippleAi() && !this.rippleManual()) {   // ← rippleRetake YOK!
       return percentage * this.totalDuration();
    }
    // ...
}
```

#### 4) `getPlayheadPosition()` — Satır 2233-2241

Playhead çizgisinin yatay pozisyonunu yüzde olarak hesaplar.

```typescript
// HATALI (satır 2235):
getPlayheadPosition(): number {
    const t = this.currentTime();
    if (!this.rippleAi() && !this.rippleManual()) {   // ← rippleRetake YOK!
       return (t / this.totalDuration()) * 100;
    }
    // ...
}
```

#### 5) `getOverlayStyle()` — Satır 2557-2576

Overlay katmanlarının timeline üzerindeki pozisyon ve genişliğini hesaplar.

```typescript
// HATALI (satır 2559):
getOverlayStyle(ov: any): any {
    const totalDur = Math.max(1, this.totalDuration());
    if (!this.rippleAi() && !this.rippleManual()) {   // ← rippleRetake YOK!
       return {
          left: `${(ov.timestamp / totalDur) * 100}%`,
          width: `${Math.max(1.0, (ov.duration / totalDur) * 100)}%`
       };
    }
    // ...
}
```

#### 6) Overlay Drag Handler — Satır 3232

Overlay sürüklenirken konumunu hesaplar.

```typescript
// HATALI (satır 3232):
if (!this.rippleAi() && !this.rippleManual()) {   // ← rippleRetake YOK!
    // ... orijinal koordinat hesaplaması
}
```

### Detaylı Çözüm

#### Adım 1: Helper Fonksiyon (Zaten Sorun #1'de ekledik)

```typescript
isAnyRippleActive(): boolean {
  return this.rippleAi() || this.rippleManual() || this.rippleRetake();
}
```

#### Adım 2: Tüm Kontrolleri Güncelle

Aşağıdaki tablodaki **her satırda** `!this.rippleAi() && !this.rippleManual()` ifadesini `!this.isAnyRippleActive()` ile değiştir:

| Satır No | Fonksiyon | Eski Kontrol | Yeni Kontrol |
|----------|-----------|-------------|-------------|
| 2184 | `getRawTimeFromVisTime()` | `!this.rippleAi() && !this.rippleManual()` | `!this.isAnyRippleActive()` |
| 2200 | `getVisTimeFromRawTime()` | `!this.rippleAi() && !this.rippleManual()` | `!this.isAnyRippleActive()` |
| 2225 | `getTimeAtClientX()` | `!this.rippleAi() && !this.rippleManual()` | `!this.isAnyRippleActive()` |
| 2235 | `getPlayheadPosition()` | `!this.rippleAi() && !this.rippleManual()` | `!this.isAnyRippleActive()` |
| 2559 | `getOverlayStyle()` | `!this.rippleAi() && !this.rippleManual()` | `!this.isAnyRippleActive()` |
| 3232 | Overlay drag handler | `!this.rippleAi() && !this.rippleManual()` | `!this.isAnyRippleActive()` |

Bu değişiklik toplamda **6 satırdaki koşul ifadesini** güncellemek demektir. Mantık aynı kalır — sadece kontrol genişletilir.

#### Örnek Güncelleme (getRawTimeFromVisTime):

**Eski:**
```typescript
getRawTimeFromVisTime(visTime: number): number {
    if (!this.rippleAi() && !this.rippleManual()) {
       return Math.max(0, Math.min(this.totalDuration(), visTime));
    }
    let accumulated = 0;
    for (const c of this.clips()) {
       if (this.isVisible(c)) {
          if (accumulated + c.duration >= visTime) {
             return c.start + (visTime - accumulated);
          }
          accumulated += c.duration;
       }
    }
    return this.totalDuration();
}
```

**Yeni:**
```typescript
getRawTimeFromVisTime(visTime: number): number {
    // HERHANGİ bir ripple aktif değilse orijinal zamanı döndür
    if (!this.isAnyRippleActive()) {
       return Math.max(0, Math.min(this.totalDuration(), visTime));
    }
    let accumulated = 0;
    for (const c of this.clips()) {
       if (this.isVisible(c)) {
          if (accumulated + c.duration >= visTime) {
             return c.start + (visTime - accumulated);
          }
          accumulated += c.duration;
       }
    }
    return this.totalDuration();
}
```

---

## 6. Sorun #4 — `visibleDuration` Hesaplaması Eksik ve Yanlış

### Belirtiler
- Sıkıştırma sonrası playhead yanlış yerde duruyor
- Overlay genişlikleri yanlış hesaplanıyor
- Altyazı pozisyonları kayıyor
- Timeline sonundaki klipler taşıyor veya eksik kalıyor

### Sorunun Kaynağı: Satır 1531-1540

Mevcut `visibleDuration` computed signal'i:

```typescript
readonly visibleDuration = computed(() => {
   const allClips = this.clips(); 
   let totalCut = 0;
   for (const c of allClips) {
       // BUG: Hangi ripple toggle açık olursa olsun, bu sabit kurallara göre çıkarıyor
       if (c.isCut && (
         this.isRetakeClip(c) ||                           // Her zaman retake'leri çıkarıyor
         c.cutObj?.reason?.includes('silence') ||           // Her zaman sessizlikleri çıkarıyor
         c.cutObj?.reason?.includes('manuel')               // Her zaman manuelleri çıkarıyor
       )) {
           totalCut += c.duration;
       }
   }
   return Math.max(0, this.totalDuration() - totalCut);
});
```

**Problemler:**

1. **Toggle durumlarını kontrol etmiyor:** `rippleAi()` kapalıyken bile sessizlik kesimlerinin süresini çıkarıyor.
2. **String eşleştirmesi güvenilmez:** `reason?.includes('silence')` AI kesimlerinin tamamını kapsamayabilir. Farklı reason formatları (ör. "Silence detected", "quiet_section") yakalanmaz.
3. **`isVisible()` fonksiyonu ile tutarsız:** `isVisible()` toggle durumlarına bakıyor ama `visibleDuration` bakmıyor. Bu, iki hesaplama arasında çelişki yaratır.

### Detaylı Çözüm

En doğru yaklaşım: `isVisible()` fonksiyonunu **doğrudan kullanarak** sadece görünür kliplerin sürelerini toplamak:

```typescript
/**
 * Sıkıştırma sonrası timeline'da görünen toplam süreyi hesaplar.
 * 
 * MANTIK: Tüm klipleri dolaş. İsVisible() true dönenlerinin 
 * sürelerini topla. Bu, toggle durumlarıyla birebir tutarlıdır.
 * 
 * NOT: isVisible() zaten şu kontrolleri yapıyor:
 *   - Kesilmemiş klip → her zaman görünür
 *   - Manuel kesim klibi → rippleManual true ise gizle
 *   - Retake kesim klibi → rippleRetake true ise gizle  
 *   - AI kesim klibi → rippleAi true ise gizle
 * 
 * Dolayısıyla visibleDuration otomatik olarak tüm toggle 
 * kombinasyonlarını doğru yansıtır.
 */
readonly visibleDuration = computed(() => {
    const allClips = this.clips();
    let totalVisible = 0;
    for (const c of allClips) {
        if (this.isVisible(c)) {
            totalVisible += c.duration;
        }
    }
    // Sıfır bölme hatasını önle
    return Math.max(0.1, totalVisible);
});
```

**Neden bu çözüm daha iyi?**

1. **Tek doğruluk kaynağı:** `isVisible()` fonksiyonu hem template'de (kliplerin gösterilip gösterilmeyeceği) hem de `visibleDuration`'da (toplam süre) aynı mantığı kullanır. Toggle'lar değiştiğinde her ikisi de otomatik olarak güncellenir.

2. **String eşleştirmesine bağımlı değil:** `reason?.includes('silence')` gibi kırılgan string kontrolleri yerine `isVisible()`'ın type-safe kontrollerini kullanır.

3. **Gelecekte yeni kesim tipleri eklendiğinde:** Sadece `isVisible()` fonksiyonunu güncellemek yeterli olur, `visibleDuration` otomatik olarak doğru hesaplar.

### Edge Case'ler

- **Tüm toggle'lar kapalı:** `isVisible()` tüm kliplere `true` döner → `visibleDuration` = `totalDuration()` ✅
- **Tüm toggle'lar açık:** Sadece kesilmemiş klipler görünür → doğru süre ✅
- **Hiç kesim yoksa:** Tüm klipler görünür → `visibleDuration` = `totalDuration()` ✅
- **Tüm klipler kesilmişse:** `visibleDuration` = 0.1 (minimum değer, sıfır bölme koruması) ✅

---

## 7. Sorun #5 — Timeline Yatay Kaydırma (Scroll) Çalışmıyor

### Belirtiler
- Mouse tekerleği ile timeline sağa-sola kaydırılamıyor
- Shift + Tekerlek çalışsa da kullanıcılar bunu bilmiyor
- Altta görünür bir scrollbar veya sol/sağ butonları yok
- Zoom yapıldıktan sonra timeline'ın sağ kısmına erişilemiyor

### Sorunun Kaynağı: Satır 1941-1955

Mevcut `onTimelineWheel()` fonksiyonu:

```typescript
// Satır 1940-1955:
onTimelineWheel(event: WheelEvent): void {
    if (event.ctrlKey || event.metaKey) {
      // Ctrl + Tekerlek = Zoom
      event.preventDefault();
      if (event.deltaY < 0) {
        this.zoomIn();
      } else {
        this.zoomOut();
      }
    } else if (event.shiftKey) {
      // Shift + Tekerlek = Yatay scroll
      const container = this.timelineScrollContainerRef?.nativeElement;
      if (container) {
        container.scrollLeft += event.deltaY;
      }
    }
    // SORUN: else bloğu yok!
    // Normal tekerlek (Ctrl/Shift yok) → HİÇBİR ŞEY YAPILMIYOR
}
```

Normal tekerlek kaydırmasında hiçbir işlem yapılmıyor. Ayrıca timeline container'ı `overflow-x-auto` sınıfına sahip ama zoom=1 iken içerik tam genişlikte olduğu için native scroll çalışmıyor.

### Detaylı Çözüm

#### Adım 1: Normal Tekerlek ile Yatay Scroll Ekle

```typescript
/**
 * Timeline üzerinde mouse tekerleği olaylarını yönetir.
 * 
 * 3 Mod:
 * 1. Ctrl/Cmd + Tekerlek → Zoom in/out
 * 2. Shift + Tekerlek → Yatay scroll (mevcut)
 * 3. Normal Tekerlek → Yatay scroll (YENİ!)
 * 
 * Normal tekerlek ile yatay scroll çok önemlidir çünkü
 * kullanıcıların büyük çoğunluğu Shift kısayolunu bilmez.
 */
onTimelineWheel(event: WheelEvent): void {
    if (event.ctrlKey || event.metaKey) {
      // Mod 1: Ctrl/Cmd + Tekerlek → Zoom
      event.preventDefault();
      if (event.deltaY < 0) {
        this.zoomIn();
      } else {
        this.zoomOut();
      }
    } else {
      // Mod 2 & 3: Normal veya Shift + Tekerlek → Yatay Scroll
      // Normal tekerlekte deltaY'i yatay scroll olarak kullan
      // Shift + tekerlekte de aynı şekilde çalışır
      event.preventDefault();
      const container = this.timelineScrollContainerRef?.nativeElement;
      if (container) {
        // deltaY'yi yatay scroll'a çevir. 
        // Çarpan ile hassasiyet ayarlanabilir.
        const scrollAmount = event.shiftKey ? event.deltaY : event.deltaY * 1.5;
        container.scrollLeft += scrollAmount;
      }
    }
}
```

#### Adım 2: Manuel Sol/Sağ Kaydırma Butonları Ekle

Timeline section'ının kapanış tag'inden hemen önce (satır 1047 civarı, `</section>` öncesinde) bir alt toolbar ekle:

```html
<!-- Timeline Alt Kaydırma Çubuğu -->
<div class="h-7 px-4 bg-dark-900/95 border-t border-slate-800 flex items-center justify-between shrink-0 select-none">
  <!-- Sol: Bilgi -->
  <div class="flex items-center gap-2 text-[10px] text-slate-500">
    <span class="font-mono">{{ formatTime(currentTime()) }}</span>
    <span>/</span>
    <span class="font-mono">{{ formatTime(isAnyRippleActive() ? visibleDuration() : totalDuration()) }}</span>
  </div>
  
  <!-- Orta: Kaydırma Butonları -->
  <div class="flex items-center gap-1">
    <button 
      (click)="scrollTimelineLeft()" 
      class="px-2 py-0.5 rounded bg-dark-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700 text-[10px] font-bold transition-colors cursor-pointer"
      title="Sola Kaydır">
      ◀ Sol
    </button>
    <button 
      (click)="scrollTimelineToPlayhead()" 
      class="px-2 py-0.5 rounded bg-dark-800 text-brand-cyan hover:text-white hover:bg-slate-700 border border-slate-700 text-[10px] font-bold transition-colors cursor-pointer"
      title="İmlece Git">
      ⊙ İmleç
    </button>
    <button 
      (click)="scrollTimelineRight()" 
      class="px-2 py-0.5 rounded bg-dark-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700 text-[10px] font-bold transition-colors cursor-pointer"
      title="Sağa Kaydır">
      Sağ ▶
    </button>
  </div>
  
  <!-- Sağ: Kısayol İpucu -->
  <div class="text-[9px] text-slate-600">
    Tekerlek: Sola/Sağa kaydır • Ctrl+Tekerlek: Yakınlaş/Uzaklaş
  </div>
</div>
```

#### Adım 3: Scroll Fonksiyonları Ekle

```typescript
/**
 * Timeline'ı 200px sola kaydırır.
 * Smooth scroll kullanarak akıcı bir kaydırma sağlar.
 */
scrollTimelineLeft(): void {
    const container = this.timelineScrollContainerRef?.nativeElement;
    if (container) {
      container.scrollBy({ left: -200, behavior: 'smooth' });
    }
}

/**
 * Timeline'ı 200px sağa kaydırır.
 */
scrollTimelineRight(): void {
    const container = this.timelineScrollContainerRef?.nativeElement;
    if (container) {
      container.scrollBy({ left: 200, behavior: 'smooth' });
    }
}

/**
 * Timeline'ı playhead'in bulunduğu konuma kaydırır.
 * Playhead ekranın ortasında olacak şekilde konumlanır.
 */
scrollTimelineToPlayhead(): void {
    const container = this.timelineScrollContainerRef?.nativeElement;
    if (!container) return;
    
    const playheadPercent = this.getPlayheadPosition() / 100;
    const targetScrollLeft = (playheadPercent * container.scrollWidth) - (container.clientWidth / 2);
    
    container.scrollTo({
      left: Math.max(0, targetScrollLeft),
      behavior: 'smooth'
    });
}

/**
 * Saniye cinsinden zamanı MM:SS formatına çevirir.
 * Alt toolbar'daki zaman göstergesi için kullanılır.
 */
formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
```

#### Adım 4: Timeline Section Yapısını Güncelle (Opsiyonel Düzenleme)

Mevcut timeline section yapısı (satır 752):
```html
<section class="h-[44%] min-h-[220px] shrink-0 flex flex-col bg-dark-950 select-none">
```

Bu section'ın içindeki alan dağılımı:
1. Toolbar: `h-10` (40px sabit)
2. Timeline gövdesi: `flex-1` (kalan alan)
3. **YENİ:** Alt kaydırma çubuğu: `h-7` (28px sabit)

Section'ın `flex flex-col` yapısı sayesinde bu 3 parça doğal olarak dikey dizilir.

---

## 8. Sorun #6 — Altyazı Segmentleri Sıkıştırma ile Hizalanmıyor

### Belirtiler
- Sıkıştırma aktifken altyazı blokları klipler ile uyuşmuyor
- Altyazılar birbiri üstüne biniyor
- Kesilen bölgelerdeki altyazılar hâlâ gösteriliyor

### Sorunun Kaynağı: Satır 917-925

Altyazı segmentlerinin template kodu:

```html
<!-- Satır 917-925 -->
<div class="absolute left-[120px] right-0 top-0 bottom-0 overflow-hidden">
  <div *ngFor="let seg of activeEdl()?.transcript?.segments"
       class="absolute top-1 bottom-1 ..."
       [style.left.%]="(seg.start / totalDuration()) * 100"
       [style.width.%]="((seg.end - seg.start) / totalDuration()) * 100"
       [title]="seg.text">
       <span class="truncate font-semibold">{{ seg.text }}</span>
  </div>
</div>
```

**Problem 1:** `left` ve `width` her zaman `totalDuration()`'a göre hesaplanıyor. Sıkıştırma aktifken klipler `visibleDuration()`'a göre konumlanırken altyazılar hâlâ `totalDuration()`'a göre konumlanıyor.

**Problem 2:** Kesilen bölgelere denk gelen altyazı segmentleri hâlâ gösteriliyor. Sıkıştırma ile gizlenen bir klibin üzerindeki altyazı da gizlenmeli.

### Detaylı Çözüm

#### Adım 1: Altyazı Pozisyon Fonksiyonları Ekle

```typescript
/**
 * Bir altyazı segmentinin timeline üzerindeki yatay pozisyonunu hesaplar.
 * 
 * Sıkıştırma KAPALI: Orijinal zamana göre pozisyon.
 * Sıkıştırma AÇIK: Sıkıştırılmış zamana göre pozisyon.
 *   getVisTimeFromRawTime() ile orijinal zamanı sıkıştırılmış zamana çevirir.
 */
getSubtitleLeft(seg: any): number {
    if (!this.isAnyRippleActive()) {
      return (seg.start / this.totalDuration()) * 100;
    }
    const visDur = this.visibleDuration();
    if (visDur <= 0) return 0;
    return (this.getVisTimeFromRawTime(seg.start) / visDur) * 100;
}

/**
 * Bir altyazı segmentinin timeline üzerindeki genişliğini hesaplar.
 * 
 * Sıkıştırma KAPALI: Orijinal süreye göre genişlik.
 * Sıkıştırma AÇIK: Sıkıştırılmış süreye göre genişlik.
 *   Başlangıç ve bitiş zamanlarını sıkıştırılmış zamana çevirip
 *   farkını hesaplar.
 */
getSubtitleWidth(seg: any): number {
    if (!this.isAnyRippleActive()) {
      return ((seg.end - seg.start) / this.totalDuration()) * 100;
    }
    const visDur = this.visibleDuration();
    if (visDur <= 0) return 0;
    
    const startVis = this.getVisTimeFromRawTime(seg.start);
    const endVis = this.getVisTimeFromRawTime(seg.end);
    
    // Segment tamamen kesilen bir bölgedeyse genişlik 0 olabilir
    const width = ((endVis - startVis) / visDur) * 100;
    return Math.max(0, width);
}
```

#### Adım 2: Görünür Altyazı Filtreleme Fonksiyonu Ekle

```typescript
/**
 * Sıkıştırma modunda sadece GÖRÜNÜR kliplere denk gelen altyazı segmentlerini döndürür.
 * 
 * MANTIK:
 * - Her segmentin orta noktasını hesapla
 * - Bu orta noktanın hangi klibe ait olduğunu bul
 * - Klip görünürse segmenti dahil et
 * - Klip gizliyse (sıkıştırılmışsa) segmenti çıkar
 * 
 * Sıkıştırma kapalıysa tüm segmentleri döndürür.
 */
getVisibleSubtitleSegments(): any[] {
    const segments = this.activeEdl()?.transcript?.segments || [];
    
    // Sıkıştırma aktif değilse tüm segmentleri göster
    if (!this.isAnyRippleActive()) {
      return segments;
    }
    
    const allClips = this.clips();
    
    return segments.filter(seg => {
      // Segmentin orta noktası
      const midTime = (seg.start + seg.end) / 2;
      
      // Bu zamanda hangi klip var?
      const clip = allClips.find(c => midTime >= c.start && midTime <= c.end);
      
      // Klip bulunamadıysa (çok nadiren olur) göster
      if (!clip) return true;
      
      // Klip görünürse segmenti göster
      return this.isVisible(clip);
    });
}
```

#### Adım 3: Template'i Güncelle (Satır 918-921)

**Eski:**
```html
<div *ngFor="let seg of activeEdl()?.transcript?.segments"
     class="absolute top-1 bottom-1 ..."
     [style.left.%]="(seg.start / totalDuration()) * 100"
     [style.width.%]="((seg.end - seg.start) / totalDuration()) * 100"
     [title]="seg.text">
```

**Yeni:**
```html
<div *ngFor="let seg of getVisibleSubtitleSegments()"
     class="absolute top-1 bottom-1 ..."
     [style.left.%]="getSubtitleLeft(seg)"
     [style.width.%]="getSubtitleWidth(seg)"
     [title]="seg.text">
```

### Neden Bu Çözüm Çalışır?

Düşünelim: Bir video'da 3 altyazı segmenti var:
- Seg1: "Merhaba" (5s-8s) → Klip 0-20s içinde (görünür)
- Seg2: "Bu bir test" (22s-25s) → Klip 20-30s içinde (AI cut, sıkıştırılmış)
- Seg3: "Devam edelim" (35s-40s) → Klip 30-50s içinde (görünür)

**Sıkıştırma kapalı:**
```
|--Seg1---|          |--Seg2--|     |---Seg3----|
5s       8s        22s     25s    35s         40s
```

**Sıkıştırma açık (AI):**
- `getVisibleSubtitleSegments()` → [Seg1, Seg3] (Seg2 filtrelenir)
- Seg1: `getSubtitleLeft()` → `getVisTimeFromRawTime(5) / visibleDuration * 100`
- Seg3: `getSubtitleLeft()` → `getVisTimeFromRawTime(35) / visibleDuration * 100`
- Klipler sıkıştığı için pozisyonlar da sıkışır ve hizalanır ✅

---

## 9. Sorun #7 — Playhead Sürükleme (Scrubbing) Ripple Modunu Dikkate Almıyor

### Belirtiler
- Playhead sürüklenirken (scrubbing) sıkıştırma modunda yanlış zamana atlıyor
- Özellikle kesilen bölgelerin yerine atlarken fark ediliyor
- Playhead'in görsel pozisyonu ile gerçek seek zamanı uyuşmuyor

### Sorunun Kaynağı: Satır 1183-1202

Mevcut playhead scrubbing kodu:

```typescript
// Satır 1183-1202:
@HostListener('window:mousemove', ['$event'])
onWindowMouseMove(event: MouseEvent) {
    if (!this.isScrubbing || !this.timelineScrollContainerRef) return;
    
    const container = this.timelineScrollContainerRef.nativeElement;
    const rect = container.getBoundingClientRect();
    const scrollLeft = container.scrollLeft;
    
    let x = event.clientX - rect.left + scrollLeft;
    const totalW = container.scrollWidth;
    x = Math.max(0, Math.min(x, totalW));
    
    const percentage = x / totalW;
    const targetTime = percentage * this.totalDuration();    // ← SORUN BURADA
    
    if (this.videoRef && this.videoRef.nativeElement) {
      this.videoRef.nativeElement.currentTime = targetTime;
    }
    this.currentTime.set(targetTime);
}
```

**Problem:** `percentage * this.totalDuration()` her zaman orijinal video süresine göre hesaplar. Sıkıştırma aktifken klipler `visibleDuration()`'a göre konumlanmış olduğundan, mouse'un x koordinatı yanlış zamana eşlenir.

**Örnek:** 100 saniyelik video, 40-60s arası kesilmiş, sıkıştırma açık.
- `visibleDuration` = 80s
- Timeline'ın %50'sine tıklıyoruz
- **Mevcut hesaplama:** `0.5 * 100 = 50s` (kesilen bölgenin ortasına atlıyor!) ❌
- **Doğru hesaplama:** `getRawTimeFromVisTime(0.5 * 80) = getRawTimeFromVisTime(40) = 60s` ✅

### Detaylı Çözüm

```typescript
@HostListener('window:mousemove', ['$event'])
onWindowMouseMove(event: MouseEvent) {
    if (!this.isScrubbing || !this.timelineScrollContainerRef) return;
    
    const container = this.timelineScrollContainerRef.nativeElement;
    const rect = container.getBoundingClientRect();
    const scrollLeft = container.scrollLeft;
    
    let x = event.clientX - rect.left + scrollLeft;
    const totalW = container.scrollWidth;
    x = Math.max(0, Math.min(x, totalW));
    
    const percentage = x / totalW;
    
    // =====================================================
    // DÜZELTME: Ripple modunda visibleDuration kullan
    // =====================================================
    let targetTime: number;
    
    if (this.isAnyRippleActive()) {
      // Sıkıştırma modunda: 
      // 1. Yüzdeyi sıkıştırılmış süreye çevir
      // 2. Sıkıştırılmış zamanı orijinal zamana çevir
      const visTime = percentage * this.visibleDuration();
      targetTime = this.getRawTimeFromVisTime(visTime);
    } else {
      // Normal mod: Doğrudan orijinal süreye çevir
      targetTime = percentage * this.totalDuration();
    }
    
    if (this.videoRef && this.videoRef.nativeElement) {
      this.videoRef.nativeElement.currentTime = targetTime;
    }
    this.currentTime.set(targetTime);
}
```

**Neden iki ayrı hesaplama gerekiyor?**

Sıkıştırma aktifken timeline üzerindeki yüzdelik konum farklı bir zamanı temsil eder:

```
Normal mod (sıkıştırma kapalı):
0%        25%       50%       75%       100%
|---------|---------|---------|---------|
0s       25s       50s       75s      100s

Sıkıştırma modu (40-60s kesilmiş):
0%        25%       50%       75%       100%
|---------|---------|---------|---------|
0s       20s       40s→60s   80s      100s
                    ↑ 40s'lik sıkıştırılmış pozisyon
                      orijinal 60s'ye eşleniyor
```

`getRawTimeFromVisTime()` fonksiyonu bu dönüşümü doğru yapar: Sıkıştırılmış 40s'ye denk gelen orijinal zamanı bulur (kesilen 40-60s bölgesini atlayarak 60s'ye ulaşır).

---

## 10. Uygulama Sırası ve Öncelikler

### Bağımlılık Grafiği

Sorunlar arasında bağımlılıklar vardır. Şu sırayla uygulamak gerekir:

```
ADIM 1: isAnyRippleActive() helper fonksiyon ekle
    ↓
ADIM 2: visibleDuration hesaplamasını düzelt (Sorun #4)
    ↓
ADIM 3: rippleRetake kontrollerini ekle (Sorun #3)
    ↓
ADIM 4: Klip pozisyonlarını ripple-aware yap (Sorun #1)
    ↓
ADIM 5: Waveform'u ripple-aware yap (Sorun #2)
    ↓
ADIM 6: Altyazı pozisyonlarını ripple-aware yap (Sorun #6)
    ↓
ADIM 7: Playhead scrubbing düzelt (Sorun #7)
    ↓
ADIM 8: Timeline scroll düzelt ve butonları ekle (Sorun #5)
```

### Neden Bu Sıra?

1. **`isAnyRippleActive()`** tüm diğer düzeltmelerde kullanılır → ilk yapılmalı.
2. **`visibleDuration`** diğer hesaplamaların dayandığı temel metriktir → ikinci yapılmalı.
3. **`rippleRetake` kontrolü** eklenmeden klip pozisyonları düzeltilse bile retake kesimleri hâlâ sorunlu olur.
4. **Klip pozisyonları** düzeltildikten sonra waveform ve altyazılar daha anlamlı test edilebilir.
5. **Scroll** diğerlerinden bağımsızdır ama en sonda test etmek daha mantıklı.

### Değişiklik Özet Tablosu

| Adım | Sorun | Değişiklik Tipi | Tahmini Satır |
|------|-------|-----------------|---------------|
| 1 | Ortak | Yeni fonksiyon ekle | +5 satır |
| 2 | #4 | `visibleDuration` computed güncelle | ~10 satır değişiklik |
| 3 | #3 | 6 satırdaki koşulu güncelle | 6 satır değişiklik |
| 4 | #1 | 2 yeni fonksiyon + template güncelle | +35 satır, 2 satır değişiklik |
| 5 | #2 | Waveform fonksiyonları güncelle + template | +50 satır, ~15 satır değişiklik |
| 6 | #6 | 3 yeni fonksiyon + template güncelle | +40 satır, 3 satır değişiklik |
| 7 | #7 | Scrubbing fonksiyonu güncelle | ~15 satır değişiklik |
| 8 | #5 | Scroll fonksiyonları + template + butonlar | +60 satır |

**Toplam:** ~215 satır yeni kod, ~50 satır değişiklik.

---

## 11. Doğrulama ve Test Senaryoları

Her adımdan sonra çalıştırılması gereken test senaryoları:

### Test Grubu A: Sıkıştırma (Sorun #1, #3, #4)

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| A1 | AI sıkıştırma butonunu aç | Kırmızı (AI) klipler kaybolur, kalan klipler yan yana dizilir, boşluk kalmaz |
| A2 | Retake sıkıştırma butonunu aç | Sarı (Retake) klipler kaybolur, boşluk kalmaz |
| A3 | Manuel sıkıştırma butonunu aç | Mor (Manuel) klipler kaybolur, boşluk kalmaz |
| A4 | Hepsini birlikte aç | Sadece yeşil (korunan) klipler kalır, yan yana dizilir |
| A5 | Hepsini kapat | Tüm klipler orijinal pozisyonlarında görünür |
| A6 | AI aç → kapat → tekrar aç | Her seferinde tutarlı sonuç |

### Test Grubu B: Ses Dalga Formu (Sorun #2)

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| B1 | Sıkıştırma kapalı + waveform | Waveform tüm kliplerin arkasında, hizalı |
| B2 | AI sıkıştırma açık + waveform | Waveform sadece görünür kliplerin arka planında, kesilen bölgelerin dalga verileri gösterilmez |
| B3 | Zoom ile waveform | Zoom değiştiğinde waveform ölçeği de değişir |
| B4 | Tüm sıkıştırmalar açık + waveform | Waveform sadece kalan kliplerin altında |

### Test Grubu C: Playhead ve Seek (Sorun #3, #7)

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| C1 | Sıkıştırma açık + timeline'a tıkla | Video doğru zamana atlar, kesilen bölgelere atlamaz |
| C2 | Sıkıştırma açık + playhead sürükle | Playhead sorunsuz hareket eder, kesilen bölgeleri atlar |
| C3 | Retake sıkıştırma açık + seek | Doğru zamana atlar |
| C4 | Video oynat + sıkıştırma açık | Playhead görünür klipler arasında düzgün ilerler |

### Test Grubu D: Altyazılar (Sorun #6)

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| D1 | Sıkıştırma kapalı + altyazılar | Altyazılar doğru pozisyonlarda |
| D2 | AI sıkıştırma açık + altyazılar | Altyazılar kliplerle hizalı, birbiri üstüne binmiyor |
| D3 | Kesilen bölgedeki altyazı | Görünmüyor |
| D4 | Sıkıştırma aç/kapat | Altyazılar doğru şekilde güncellenir |

### Test Grubu E: Timeline Scroll (Sorun #5)

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| E1 | Normal tekerlek | Timeline sağa/sola kayar |
| E2 | Shift + tekerlek | Timeline sağa/sola kayar |
| E3 | Ctrl + tekerlek | Zoom in/out |
| E4 | Sol butonuna bas | Timeline 200px sola kayar |
| E5 | Sağ butonuna bas | Timeline 200px sağa kayar |
| E6 | İmleç butonuna bas | Timeline playhead pozisyonuna kaydırılır |
| E7 | Zoom = 3x + scroll | Zoom'lanmış timeline'da scroll çalışır |

### Test Grubu F: Overlay Katmanları (Sorun #3)

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| F1 | Sıkıştırma açık + overlay pozisyonu | Overlay klipler ile hizalı |
| F2 | Retake sıkıştırma açık + overlay | Overlay doğru pozisyonda |
| F3 | Overlay sürükle (sıkıştırma açık) | Sorunsuz sürüklenebilir, doğru pozisyona bırakılır |

---

## Ek: Tüm Değişikliklerin Diff Formatında Özeti

Aşağıda tüm değişikliklerin hangi satırlarda yapılacağını gösteren bir harita verilmiştir:

```
editor.component.ts Değişiklik Haritası:
=========================================

Satır ~918-921:  Altyazı template → getSubtitleLeft/getSubtitleWidth (Sorun #6)
Satır ~979-992:  Waveform template → per-clip veya filtered waveform (Sorun #2)
Satır ~1009-1010: Klip left/width → getClipLeft/getClipWidth (Sorun #1)
Satır ~1047:     Timeline section kapanışı → Scroll butonları ekleme (Sorun #5)
Satır ~1183-1202: onWindowMouseMove → ripple-aware scrubbing (Sorun #7)
Satır ~1290:     isAnyRippleActive() helper ekleme (Tüm sorunlar)
Satır ~1531-1540: visibleDuration → isVisible tabanlı hesaplama (Sorun #4)
Satır ~1716-1743: getWaveformPath → filtered peaks (Sorun #2)
Satır ~1941-1955: onTimelineWheel → normal scroll ekleme (Sorun #5)
Satır ~2184:     getRawTimeFromVisTime → isAnyRippleActive (Sorun #3)
Satır ~2200:     getVisTimeFromRawTime → isAnyRippleActive (Sorun #3)
Satır ~2225:     getTimeAtClientX → isAnyRippleActive (Sorun #3)
Satır ~2235:     getPlayheadPosition → isAnyRippleActive (Sorun #3)
Satır ~2559:     getOverlayStyle → isAnyRippleActive (Sorun #3)
Satır ~3232:     Overlay drag → isAnyRippleActive (Sorun #3)

Yeni eklenen fonksiyonlar:
  + isAnyRippleActive()
  + getClipLeft(clip)
  + getClipWidth(clip)
  + getFilteredPeaks(allPeaks)       [Yaklaşım A kullanılırsa]
  + getWaveformPathForClip(clip)     [Yaklaşım B kullanılırsa]
  + getSubtitleLeft(seg)
  + getSubtitleWidth(seg)
  + getVisibleSubtitleSegments()
  + scrollTimelineLeft()
  + scrollTimelineRight()
  + scrollTimelineToPlayhead()
  + formatTime(seconds)
```

---

**Son Not:** Bu döküman, OtoEdit editor.component.ts dosyasının 2026-09-23 tarihli mevcut durumu baz alınarak hazırlanmıştır. Dosyada yapılacak değişiklikler sonrasında satır numaraları kayabilir. Her değişiklik sonrası doğrulama testlerini çalıştırmak kritik önem taşır.
