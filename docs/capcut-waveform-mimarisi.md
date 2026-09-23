# CapCut & Premiere Pro Tarzı Gelişmiş Ses Dalgası (Waveform) Mimarisi

Bu döküman, OtoEdit timeline'ındaki ses dalgası (waveform) gösteriminin endüstri standartlarına (CapCut ve Adobe Premiere Pro) uygun hale getirilmesi için gerekli olan mimari altyapıyı, görsel özellikleri ve teknik algoritmayı detaylandırmaktadır.

## 1. Görsel Hedefler ve Tasarım Felsefesi (CapCut Standardı)

Profesyonel video kurgu yazılımlarında (özellikle CapCut'ta) ses dalgası, sadece sesin varlığını göstermekle kalmaz, aynı zamanda kullanıcının **kesim yapacağı ritmi, konuşmanın patlama noktalarını ve sessizlikleri milisaniyesine kadar görsel olarak okumasını** sağlar. 

### 1.1 Asimetrik (Tek Yönlü) Çizim
- **Eski Durum:** Ses dalgası ekranın ortasından (y = height / 2) başlayıp hem yukarı hem aşağı doğru simetrik genişliyordu (Audacity tarzı).
- **Yeni Tasarım:** Alt zemin tamamen düz olacak (`y = height`). Ses tepe noktaları (peaks) sadece yukarı doğru (Y ekseninde eksi yöne doğru) yükselecek. Bu asimetrik yapı, timeline üzerinde daha temiz bir alt hat oluşturur ve CapCut'ın varsayılan görünümüyle aynıdır.

### 1.2 Yüksek Hassasiyet ve Yoğunluk (Density)
- **Eski Durum:** Tüm ses dosyası ortalama 600-800 nokta (peak) olarak örnekleniyordu. Bu da saniyede sadece 3-5 nokta demekti.
- **Yeni Tasarım:** Saniyede en az **50 ila 100 nokta (peak)** örneklenecek. Maksimum nokta sınırı 10.000'e çıkarılacak. Bu sayede bir kelimenin içindeki ses yükseliş-alçalışları bile ekranda tırtıklı ve keskin bir biçimde belirecektir.

### 1.3 Desibele (Şiddete) Duyarlı Dinamik Renk ve Parlama
- CapCut, kullanıcının "sesin patladığı" (clipping/distortion) noktaları görsel olarak anında fark etmesi için renk kodlaması kullanır.
- Ses dalgasına bir **Dikey Lineer Gradyan (Vertical Linear Gradient)** uygulanacaktır.
  - **%0 - %20 (En Yüksek Noktalar):** Kırmızı / Turuncu (Kritik yüksek ses veya patlamalar)
  - **%20 - %50 (Orta-Yüksek Noktalar):** Sarı (Yüksek ses)
  - **%50 - %100 (Normal Sesler):** Camgöbeği (Cyan) / Açık Mavi (Normal konuşma ve arka plan)
- Ayrıca SVG grafiğine `drop-shadow` filtresi (glow efekti) eklenerek yüksek piklerin ekranda "parlaması" sağlanacaktır.

---

## 2. Teknik Uygulama (Algoritma & Kod Mimarisi)

Mimarinin uygulanması için Angular (editor.component.ts) tarafında yapılması gereken teknik güncellemeler üç ana başlığa ayrılır:

### Adım 1: Ses Analiz Algoritmasının (AudioContext) İyileştirilmesi
`loadAudioWaveform` fonksiyonu içerisindeki çözünürlük parametreleri artırılmalıdır:
```typescript
// ESKİ:
// const totalPoints = Math.min(800, Math.max(160, Math.round(dur * 6)));

// YENİ (Yüksek Hassasiyet):
const totalPoints = Math.min(10000, Math.max(500, Math.round(dur * 50)));
```
RMS (Root Mean Square) ve Max genlik (Amplitude) hesaplamaları bu yeni blok büyüklüğüne (blockSize) göre çok daha mikro seviyede çalışacaktır. Olası RAM/Performans sorunlarını önlemek için, bu büyük veri seti UI'a renderlanırken SVG parçalanarak (per-clip) gösterilecektir.

### Adım 2: Asimetrik SVG Path Algoritması
`getWaveformPathForClip` fonksiyonu, ortadan başlayan ve hem üste hem alta giden (`L x yTop ... L x yBottom`) bir yapı yerine, sol alt köşeden başlayan, üst sınırları çizen ve sağ alt köşeden kapanan kapalı bir poligon çizecektir.
```typescript
let path = `M 0 ${height}`; // Sol alt köşeden başla
for (let i = 0; i < numPoints; i++) {
   const x = i * dx;
   const peakH = peaks[i] * height; // Tepe noktası yüksekliği
   const y = height - peakH; // Sadece yukarı doğru çık
   path += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
}
// Sağ alt köşeye in ve poligonu kapat
path += ` L ${width} ${height} Z`;
```

### Adım 3: SVG Gradient ve Filtre Tanımları
Her klibin içine eklenecek olan `<svg>` elementi, sese duyarlı dikey gradyanı içerecektir:
```html
<linearGradient [id]="'waveGrad_' + clip.id" x1="0%" y1="0%" x2="0%" y2="100%">
   <stop offset="0%" stop-color="#ef4444" stop-opacity="1" />   <!-- Kırmızı -->
   <stop offset="25%" stop-color="#f59e0b" stop-opacity="0.9" /> <!-- Sarı -->
   <stop offset="60%" stop-color="#06b6d4" stop-opacity="0.8" /> <!-- Cyan -->
   <stop offset="100%" stop-color="#0284c7" stop-opacity="0.7" /> <!-- Koyu Mavi -->
</linearGradient>

<path 
   [attr.d]="getWaveformPathForClip(clip)" 
   [attr.fill]="'url(#waveGrad_' + clip.id + ')'" 
   style="filter: drop-shadow(0px 0px 3px rgba(245, 158, 11, 0.5));"
/>
```

## 3. Beklenen Sonuç
Bu mimari uygulandığında:
1. Timeline çok daha detaylı ve profesyonel (tırtıklı ve net) bir dalga formuna kavuşacaktır.
2. Düşük sesli kısımlar mavi/yeşil tonlarda mütevazı bir yükseklikte kalırken, konuşmaların yüksek olduğu kısımlar sarı ve kırmızı tonlara uzanacak, ekranda adeta parlayacaktır.
3. Alt kısım tamamen düz olacağı için klibin alt sınırına tam oturacak, gözü yormayan modern bir tasarım elde edilecektir.
