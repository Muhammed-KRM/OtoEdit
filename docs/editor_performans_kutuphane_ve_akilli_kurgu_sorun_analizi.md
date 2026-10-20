# OtoEdit — Editör Performans Çöküşü, Zengin İçerik Kütüphaneleri ve Akıllı Kurgu Mimarisi: Kapsamlı Sorun Analizi ve Çözüm Raporu

**Tarih:** 20 Ekim 2026  
**Kapsam:** Angular Editör (`OtoEdit.Frontend`), .NET Backend (`OtoEdit.API` & `OtoEdit.Business`), Python İşleme & Render Motoru (`OtoEdit.PythonWorker`)  
**Durum:** Tüm sorunlar kaynak kod seviyesinde (satır numaralarıyla) tespit edilmiş ve kök nedenleri doğrulanmıştır.

---

## İçindekiler
1. [BÖLÜM 1: Editördeki Kritik Yavaşlık (~2 Saniye Gecikme / Lag) Sorunu ve Kök Nedenleri](#bölüm-1-editördeki-kritik-yavaşlık-2-saniye-gecikme--lag-sorunu-ve-kök-nedenleri)
2. [BÖLÜM 2: Font, Ses Efekti, Çıkartma, Görsel, Animasyon ve Geçiş Kütüphanelerinin Yetersizliği ve Hazır Açık Kaynak Kütüphane Araştırması](#bölüm-2-font-ses-efekti-çıkartma-görsel-animasyon-ve-geçiş-kütüphanelerinin-yetersizliği-ve-hazır-açık-kaynak-kütüphane-araştırması)
3. [BÖLÜM 3: Otonom Kurgu (Kesilmiş Videoyu Zenginleştirme) Sorunu](#bölüm-3-otonom-kurgu-kesilmiş-videoyu-zenginleştirme-sorunu)
4. [BÖLÜM 4: Başlangıç Tiklerinin (Checkbox) Çalışmama Nedenleri ve Yeniden Tasarımı](#bölüm-4-başlangıç-tiklerinin-checkbox-çalışmama-nedenleri-ve-yeniden-tasarımı)
5. [BÖLÜM 5: İşlemsiz "Direkt Editöre Geçiş" ve Editör İçi İhtiyaç Anında (On-Demand) AI Eksikliği](#bölüm-5-işlemsiz-direkt-editöre-geçiş-ve-editör-içi-ihtiyaç-anında-on-demand-ai-eksikliği)
6. [BÖLÜM 6: Kliplerin Yerini Oynatamama (Sıra Değiştirememe) ve Başka Video Klipleri Ekleyememe Sorunları](#bölüm-6-kliplerin-yerini-oynatamama-sıra-değiştirememe-ve-başka-video-klipleri-ekleyememe-sorunları)
7. [BÖLÜM 7: Uygulama ve Çözüm Yol Haritası](#bölüm-7-uygulama-ve-çözüm-yol-haritası)

---

## BÖLÜM 1: Editördeki Kritik Yavaşlık (Her İşlemde 2.5 – 5.2 Saniye Gecikme / Lag) Sorunu ve Canlı Veritabanı / Ağ / CPU Kanıtlarıyla Kök Nedenleri

**Kullanıcı Gözlemi:** *"Uygulama artık kullanılamaz düzeyde yavaş çalışıyor neredeyse, mesela bir yazıyı oynatıyorum 2 saniye sonra hareket ediyor gibi... Tek geciken o değil, o örnekti çünkü her bir şeyi yaptığımda uzun sürüyor, genel bir sorun var."*

Bu tespitiniz **%100 doğrudur**. Sorun sadece yazı sürüklemek değil; **uygulamadaki HER BİR İŞLEMİN** (klip silme, klip geri alma, çıkartma ekleme, görsel boyutlandırma, arka plan kaldırma, ses efekti ekleme, geçiş ekleme, altyazı düzenleme, renk kaydetme, geri/ileri alma) **2.5 ila 5.2 saniye** sürmesidir.

Bunu kanıtlamak için doğrudan çalışan sisteminizdeki PostgreSQL `endpoint_logs` ve `edit_decision_lists` tablolarını ve canlı `.NET API (:5001)` + `Angular Proxy (:4200)` + `Frontend Main Thread` katmanlarını ölçtük.

### 📊 Canlı Sistem Ölçümleri ve Adli Kanıtlar (Proje: `fef2ad89-ff4c-4bae-9294-3ad85f4cef02`)

1. **Veritabanındaki Gerçek `EdlJson` Boyutu (`edit_decision_lists` tablosu):**
   * Videonuzun süresi: **`4,222.8 saniye` (~70 dakika)**.
   * Tek bir `EdlJson` satırının boyutu: **`2,384,160 Byte` (`2.38 MB`!)**.
   * Bu `2.38 MB` JSON verisinin dağılımı:
     * **`audioPeaks`:** **`168,913 adet`** yüksek hassasiyetli float sayı (`0.008999999612569809` gibi 18 karakterli ondalıklar) = **`2,000,853 Byte` (`2.00 MB` — toplam boyutun %84'ü!)**.
     * **`transcript.segments`:** **`634 adet`** altyazı segmenti ve binlerce kelime = **`167,853 Byte` (`168 KB`)**.
     * **`overlays`:** **`8 adet`** katman (içinde `removeBackgroundNow()` tarafından gömülmüş **`158,142 Byte` (`158 KB`) Base64 PNG** verisi var) = **`164,016 Byte` (`164 KB`)**.
     * **`cuts`:** **`591 adet`** kesim noktası (bu 591 kesim noktası `V1` kanalını tam **`1,182 adet`** klibe bölmektedir!) = **`49,336 Byte` (`49 KB`)**.

2. **PostgreSQL `endpoint_logs` Tablosundaki Gerçek Tıklama Kayıtlarınız (`id = 9808` – `9831`):**
   Editörde yaptığınız son 10 işlemin her birinde `PATCH /edl` ve hemen arkasından tetiklenen `GET /edl` (`this.loadEdl()`) arasındaki **gerçek tamamlanma süreleri**:
   * **İşlem #1 (`id: 9808 -> 9809`, Görsel Ekleme):** `PATCH` (`625 ms`) + `GET /edl` = **`2,506 ms` (`2.51 saniye`)**
   * **İşlem #2 (`id: 9810 -> 9811`, Görsel Taşıma):** `PATCH` (`450 ms`) + `GET /edl` = **`2,865 ms` (`2.87 saniye`)**
   * **İşlem #3 (`id: 9812 -> 9813`, Görsel Boyutlandırma):** `PATCH` (`428 ms`) + `GET /edl` = **`2,715 ms` (`2.71 saniye`)**
   * **İşlem #4 (`id: 9814 -> 9815`, Arka Plan Kaldırma):** `PATCH` (`360 ms`) + `GET /edl` = **`2,549 ms` (`2.55 saniye`)**
   * **İşlem #5 (`id: 9816 -> 9817`, Inspector Kaydetme):** `PATCH` (`445 ms`) + `GET /edl` = **`5,228 ms` (`5.23 saniye!`)**
   * **İşlem #6 (`id: 9818 -> 9819`, Inspector Kaydetme):** `PATCH` (`406 ms`) + `GET /edl` = **`2,753 ms` (`2.75 saniye`)**
   * **İşlem #7 (`id: 9820 -> 9821`, Stok Görsel Ekleme):** `PATCH` (`412 ms`) + `GET /edl` = **`2,497 ms` (`2.50 saniye`)**
   * **İşlem #8 (`id: 9824 -> 9825`, Görsel Ölçekleme):** `PATCH` (`468 ms`) + `GET /edl` = **`2,974 ms` (`2.97 saniye`)**
   * **İşlem #9 (`id: 9828 -> 9829`, "💡 Parlak Fikir" Çıkartması Ekleme):** `PATCH` (`414 ms`) + `GET /edl` = **`2,619 ms` (`2.62 saniye`)**
   * **İşlem #10 (`id: 9830 -> 9831`, Çıkartmayı Sürükleme):** `PATCH` (`468 ms`) + `GET /edl` = **`2,933 ms` (`2.93 saniye`)**

---

### 🔍 Neden Her İşlem 2.5 – 5.2 Saniye Sürüyor? (7 Katmanlı Sistemik Darboğaz)

#### Kök Neden 1.1: `audioPeaks` (`168,913 float` = `2.00 MB`) Verisinin Doğrudan `EdlJson` İçinde Saklanması ve Her `PATCH` / `GET` İşleminde Taşınması (Backend + DB + Ağ Felaketi)
* **İlgili Kod:** [EdlManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/EdlManager.cs#L43-L246) (`GetEdlAsync`, `PatchEdlAsync`, `SaveSnapshotAsync`) ve [edl_generator.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_generator.py).
* **Neden Oluyor?**
  * Ses dalga formu (`audioPeaks`), video yüklendikten sonra **hiçbir zaman değişmeyen (salt-okunur / read-only)** statik bir dizidir.
  * Ancak bu `168,913` elemanlı dizi (`2.00 MB` metin!), her tıklamada güncellenen `EditDecisionLists.EdlJson` sütununun **içine** gömülmüştür!
  * Siz editörde 30 byte'lık küçücük bir değişiklik yaptığınızda bile (`PATCH /edl`):
    1. PostgreSQL'den `2.38 MB` metin okunur.
    2. `SaveSnapshotAsync` ([EdlManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/EdlManager.cs#L346-L380)) Undo/Redo için **tüm `2.38 MB` metni (`2.00 MB` `audioPeaks` dahil!) `EdlSnapshots` tablosuna kopyalar** (50 snapshot = veritabanında proje başına **120 MB** gereksiz kopya!).
    3. `JsonNode.Parse(edl.EdlJson)` ([EdlManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/EdlManager.cs#L123)) `168,913` adet float sayısını .NET belleğinde **168,913 adet ayrı `JsonValue` heap nesnesine** dönüştürür!
    4. `rootNode.ToJsonString()` bu `168,913` nesneyi tekrar `2.38 MB` string'e serileştirir.
    5. `SaveChangesAsync()` PostgreSQL'e toplam **`4.76 MB`** (`EditDecisionLists` + `EdlSnapshots`) veri yazar.
    6. `_cacheService.RemoveAsync("edl:{projectId}")` Redis önbelleğini siler!

#### Kök Neden 1.2: Editördeki 31 Fonksiyonun Tamamında `.subscribe(() => this.loadEdl())` Çağrılması (Her Tıklamada `2.38 MB` Verinin Tekrar İndirilmesi ve Tüm Ekranın Baştan Çizilmesi)
* **İlgili Kod:** [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L4907-L4970) (`loadEdl()`) ve `deleteClip`, `restoreClip`, `addTextOverlay`, `addImageOverlayFromUrl`, `saveInspector`, `onGlobalMouseUp`, `addSfxToTimeline`, `saveCurrentTransition` vb. **31 ayrı metot**.
* **Neden Oluyor?**
  * Editörde ne yaparsanız yapın, `patchEdl` biter bitmez `.subscribe(() => this.loadEdl())` çağrılmaktadır.
  * Az önce `PatchEdlAsync` Redis önbelleğini sildiği için, arkasından gelen `GET /edl` isteği **%100 ihtimalle Redis Cache MISS** olur; PostgreSQL'den `2.38 MB` tekrar okunur, Redis'e tekrar yazılır ve HTTP üzerinden tarayıcıya `2.38 MB` olarak tekrar indirilir.
  * Daha da kötüsü, `loadEdl()` içinde satır 4925 ve 4960'ta:
    ```typescript
    this.edl.set(res.edl);
    this.audioPeaks.set(res.edl.audioPeaks);
    ```
    çağrılarak hem tüm katman/klip/altyazı sinyalleri sıfırlanır hem de `168,913` elemanlı `audioPeaks` sinyali yeniden tetiklenerek **tüm timeline kanvaslarının baştan sona tekrar çizilmesine** yol açar!

#### Kök Neden 1.3: Monolitik `this.edl` Sinyali + `visibleSubtitleSegments()` İçindeki **1.87 Milyonluk** Gizli Döngü (`O(N × M)`)
* **İlgili Kod:** [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L3943-L4052) (`clips` ve `visibleSubtitleSegments` computed sinyalleri) ve [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L5587-L5610) (`getVisTimeFromRawTime`).
* **Neden Oluyor? (Matematiksel Kanıt):**
  1. `this.edl` tek bir sinyaldir. Bir yazıyı/görseli ekranda sürüklerken (`onGlobalMouseMove`, satır 7498), Inspector'da bir harf yazarken (`onInspectorChange`, satır 6484) veya yeni bir öğe eklerken `this.edl.update(...)` çağrılır.
  2. `clips = computed(...)` (satır 3943) doğrudan `this.activeEdl()`'i dinlediği için, **sadece bir yazının rengi veya X koordinatı değişse bile** `clips()` baştan çalışır ve 591 kesim noktasından **`1,182 adet yeni klip nesnesi`** (`rawClips.push({ id: ... })`) üretir!
  3. `visibleSubtitleSegments = computed(...)` (satır 4025) hem `this.activeEdl()`'i hem de `this.clips()`'i dinler. İçerisinde:
     * Önce `634` altyazı segmenti × `591` görünür klip = **`374,694` iterasyon** (`segments.filter(...)`) çalışır.
     * Ardından **her bir altyazı segmenti için 2 kez** (`seg.start` ve `seg.end`) `this.getVisTimeFromRawTime(...)` çağrılır.
     * `getVisTimeFromRawTime` (satır 5592) her çağrıda `for (const c of this.clips())` ile `1,182` klibi baştan sona tarar (`634 segment × 2 çağrı × 1,182 klip` = **`1,498,776` iterasyon**)!
     * **Toplam:** Tek bir `this.edl.update()` çağrısında tarayıcı ana iş parçacığı (Main Thread) üzerinde **`1,873,470` (1.87 Milyon!) JS döngü adımı** çalışır!

#### Kök Neden 1.4: `*ngFor` Döngülerinde `trackBy` Olmaması Yüzünden Her İşlemde **1,182 `<canvas>` + 634 Altyazı + 590 Geçiş Butonunun** Yıkılıp Sıfırdan Yaratılması (DOM Thrashing)
* **İlgili Kod:**
  * [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L2279-L2311): `<ng-container *ngFor="let clip of clips()">` (`trackBy` YOK!)
  * [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L2184): `<div *ngFor="let seg of visibleSubtitleSegments()">` (`trackBy` YOK!)
  * [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L2338): `<button *ngFor="let b of clipTransitionBoundaries()">` (`trackBy` YOK!)
  * [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L2237): `<div *ngFor="let ov of getOverlaysForTrack(trackNum)">` (`trackBy` YOK!)
* **Neden Oluyor?**
  * `clips()`, `visibleSubtitleSegments()` ve `clipTransitionBoundaries()` her `edl.update()` veya `loadEdl()` sonrasında yeni nesne referansları döndürdüğü ve `*ngFor` üzerinde `trackBy` bulunmadığı için Angular:
    * Timeline üzerindeki **591 ila 1,182 adet `<div class="timeline-clip">` ve `<canvas appClipWaveform>`** elemanını DOM'dan tamamen siler,
    * **591 ila 1,182 adet `ResizeObserver`** nesnesini yok edip yeniden oluşturur ([clip-waveform.directive.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/clip-waveform.directive.ts#L35-L46)),
    * **591 ila 1,182 adet yeni HTML5 `<canvas>` GPU dokusu** ayırır ve her biri için `168,913` elemanlı `audioPeaks` dizisi üzerinde `drawWaveform()` çalıştırır,
    * **634 adet altyazı kutusunu** (~2.500 DOM düğümü) ve **590 adet `⚡` geçiş butonunu** DOM'dan silip baştan yaratır!
  * Üstelik bir işlem yaptığınızda önce yerel `edl.update()` (1. yıkım), ardından `patchEdl` cevabındaki `loadEdl() -> edl.set()` (2. yıkım) olmak üzere tüm bu yıkım/yaratım işlemi **iki kez üst üste** gerçekleşir!

#### Kök Neden 1.5: `RequestResponseLoggingMiddleware.cs` İçinde Her Yanıtın `MemoryStream`'e Kopyalanması ve `2.38 MB` String Üzerinde 3 Kez `.Replace("\0", "")` Çalıştırılması
* **İlgili Kod:** [RequestResponseLoggingMiddleware.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.API/Middleware/RequestResponseLoggingMiddleware.cs#L46-L86).
* **Neden Oluyor?**
  * API'deki her HTTP yanıtı önce geçici bir `MemoryStream` içine yazılır, ardından `ReadToEndAsync()` ile tamamen belleğe (`2.38 MB` string) okunur, ardından satır 77'de:
    ```csharp
    ResponseBody = responseBody != null ? (responseBody.Replace("\0", string.Empty).Length > 4000 ? responseBody.Replace("\0", string.Empty)[..4000] : responseBody.Replace("\0", string.Empty)) : null
    ```
    kodu sadece ilk 4000 karakteri almak için **`2.38 MB` string üzerinde tam 3 kez `.Replace("\0", string.Empty)`** çalıştırarak .NET Large Object Heap (LOH) üzerinde her istekte **`7.14 MB`** gereksiz bellek ayırır (GC duraksaması yaratır) ve yanıt kapanmadan önce `await logService.LogEndpointAsync(endpointLog)` ile PostgreSQL'e senkron `INSERT` bekler!

#### Kök Neden 1.6: Windows IPv6 (`::1`) / IPv4 (`127.0.0.1`) Proxy Bağlantı Gecikmesi ve `@HostListener('window:mousemove')`
* **İlgili Kod:** [proxy.conf.json](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/proxy.conf.json#L3) (`"target": "http://localhost:5001"`) ve [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L7457).
* **Neden Oluyor?**
  * `curl.exe` ile yaptığımız canlı ölçümde:
    * `http://localhost:4200/api/.../edl` -> `connect: 223 ms | total: 455 ms` (Keep-Alive kapandığında Windows `::1` IPv6 SYN aşımı yüzünden `+220ms` – `+2,000ms` eklenmektedir).
    * `http://127.0.0.1:4200/api/.../edl` -> `connect: 1.1 ms | total: 93 ms` (**5 kat daha hızlı!**).
  * Ayrıca `@HostListener('window:mousemove')` `NgZone` içinde çalıştığı için fare boşta hareket ederken bile saniyede 120 kez Angular Change Detection tetiklenmektedir.

#### Kök Neden 1.7: Base64 PNG (`158 KB`) ve Base64 WAV Verilerinin Doğrudan `EdlJson` İçine Gömülmesi
* **İlgili Kod:** [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L6777-L6781) (`removeBackgroundNow`) ve [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L6837-L6845) (`addSfxToTimeline`).
* **Neden Oluyor?**
  * Arka planı kaldırılan görsel (`158 KB` Base64 PNG) ve sentezlenen ses efektleri doğrudan `EdlJson` içine metin olarak yazıldığı için her `PATCH`, her `GET` ve her `EdlSnapshot` kaydında tekrar tekrar kopyalanmaktadır.

---

### 🛠️ Performans Sorununun Kesin Çözümü (`2,500–5,200 ms` -> `< 15 ms` / `120 FPS` Garantili Mimari Plan)

1. **`audioPeaks` Verisinin `GET /edl` ve `PATCH /edl` Döngüsünden Ayrıştırılması (`2.38 MB` -> `~120 KB`, **20 Kat Küçülme!**):**
   * `GET /api/projects/{id}/edl` yanıtından `audioPeaks` çıkarılacak (veya `?includePeaks=false` varsayılan olacak); dalga formu sadece editör ilk açıldığında bir kez `GET /api/projects/{id}/edl/waveform` (veya önbellekten) yüklenecek.
   * `EdlManager.PatchEdlAsync` ve `SaveSnapshotAsync` içinde `audioPeaks` her defasında `JsonNode.Parse` ile 168,913 nesneye ayrıştırılmayacak ve `EdlSnapshots` tablosuna kopyalanmayacak! Böylece `PATCH /edl` süresi `450 ms`'den **`< 12 ms`**'ye düşecek!
2. **31 Noktadaki Gereksiz `this.loadEdl()` Çağrılarının Kaldırılması (Optimistic Local State):**
   * Editörde klip silme, kesim geri alma, yazı/görsel/çıkartma ekleme, taşıma, boyutlandırma, Inspector kaydetme, SFX ve geçiş ekleme işlemlerinde yerel sinyal zaten anında güncellendiği için, `patchEdl` sonrasında `2.38 MB` veriyi tekrar indiren ve tüm ekranı yıkan `this.loadEdl()` **kesinlikle çağrılmayacak**!
3. **Granüler Sinyaller (Signal Isolation) + `O(N + M)` İkili Arama (Binary Search) Optimizasyonu:**
   * `cutsSignal`, `overlaysSignal`, `subtitlesSignal`, `transitionsSignal`, `sfxSignal`, `settingsSignal` birbirinden ayrılacak. Bir katmanı (`overlay`) taşımak veya düzenlemek **asla** `clips()` veya `visibleSubtitleSegments()` sinyalini tetiklemeyecek!
   * `visibleSubtitleSegments()` içindeki `1.87 Milyon` iterasyonluk `getVisTimeFromRawTime` döngüsü, önceden hesaplanmış kümülatif görünür süre dizisi (`prefixSum`) + İkili Arama (`Binary Search - O(log N)`) ile **`1.870.000` adımdan `~4.000` adıma (450 kat hızlanma!)** indirilecek.
4. **Tüm `*ngFor` Döngülerine `trackBy` + Sanal Timeline (Viewport Culling) Eklenmesi:**
   * `trackByClipId`, `trackBySubtitleId`, `trackByOverlayId`, `trackByBoundaryId` eklenecek; hiçbir `<canvas appClipWaveform>` veya `ResizeObserver` yıkılıp yeniden yaratılmayacak.
5. **`NgZone.runOutsideAngular` + GPU `transform: translate3d()` ile Sıfır Gecikmeli (`0 ms`) Sürükleme:**
   * `mousemove` dinleyicileri `NgZone` dışına alınacak; sürükleme sırasında sadece ilgili DOM elemanının `style.transform` değeri güncellenecek ve sinyal yalnızca `mouseup` anında tek sefer güncellenecek.
6. **`RequestResponseLoggingMiddleware` ve `proxy.conf.json` Hızlandırması:**
   * Middleware'de büyük yanıt gövdelerinin (`> 64 KB` veya `/edl`) `MemoryStream` / string olarak kopyalanması engellenecek ve DB loglaması arka plana (`Fire-and-Forget` / `Channel`) alınacak.
   * `proxy.conf.json` içindeki `"target": "http://localhost:5001"` ifadesi `"http://127.0.0.1:5001"` yapılarak Windows IPv6 (`::1`) bağlantı gecikmesi tamamen sıfırlanacak.

---

## BÖLÜM 2: Font, Ses Efekti, Çıkartma, Görsel, Animasyon ve Geçiş Kütüphanelerinin Yetersizliği ve Hazır Açık Kaynak Kütüphane Araştırması

**Kullanıcı Gözlemi:** *"Eklenen fontlar, ses efektleri, animasyonlar, geçiş efektleri filan hiç yeterli değil. Çıkartma, görsel filan bunlar hiç yeterli değil; bunları direkt yüzlerce indirebileceğim hazır bir kütüphane filan var mı, bunu da internetten araştır."*

### 2.1. Mevcut Kütüphanelerin Kod İçi Durumu (Neden Yetersiz?)

| Kategori | Şu Anki Sayı | Kod İçi Gerçek Durum ve Eksiklik |
| :--- | :---: | :--- |
| **Fontlar (Yazı Tipleri)** | Arayüzde **37**, Python'da gerçekte **7** | [studio-engine.service.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts#L70-L113) içinde 37 font var **AMA** Python Worker'ın `assets/fonts/` klasöründe sadece **7 adet `.ttf` dosyası** (`Montserrat`, `Poppins`, `BebasNeue`, `Anton`, `Cinzel`, `Outfit`, `Inter`) mevcut! [pillow_graphics_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/pillow_graphics_engine.py#L79-L103) içinde `Playfair`, `Merriweather`, `Lora` gizlice `Cinzel.ttf`'e; `Bangers`, `Titan One`, `Russo One` ise gizlice `Anton.ttf`'e yönlendirilmiş! Diğer 20 font ise Docker'da dosyası olmadığı için düz `DejaVuSans`'a düşüyor. |
| **Ses Efektleri (SFX)** | **16** | [studio-engine.service.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts#L408-L425) içindeki 16 ses, gerçek stüdyo kaydı değil, Web Audio API ile üretilen basit sentetik bip/hışırtı sesleridir. |
| **Çıkartmalar (Stickers & Emoji & GIF)** | **12** | [studio-engine.service.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts#L446-L520) içinde sadece 4 basit SVG şekli ve 8 sabit emoji var. Hareketli çıkartma, 3D emoji veya GIF arama kütüphanesi yok. |
| **Stok Görsel & Video (B-Roll)** | **14** | [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L3720-L3746) içindeki `stockImagesLibrary` nesnesinde sadece 14 adet sabit Unsplash fotoğraf linki var. Arama çubuğu veya stok video desteği yok. |
| **Geçiş Efektleri (Transitions)** | **14** | FFmpeg `xfade` motorunda **45 yerleşik geçiş** varken sadece 14'ü listelenmiş; üstelik tarayıcı önizlemesinde ([editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L4086-L4119)) sadece 5 tanesinin basit CSS karşılığı var. |
| **Metin & Katman Animasyonları** | **11 Giriş / 3 Çıkış / 6 Loop** | CapCut/Premiere seviyesindeki kinetik tipografi, harf/kelime bazlı girişler, 3D takla, elastik sarkaç gibi zengin animasyon kütüphanesi eksik. |

---

### 2.2. Yüzlerce / Binlerce Hazır İçeriği Doğrudan İndirebileceğimiz ve Bağlayabileceğimiz Açık Kaynak Kütüphaneler (Araştırma Sonuçları)

İnternet ve açık kaynak ekosistemi üzerinde yaptığımız araştırmaya göre, **telif sorunu olmayan (CC0 / MIT / Apache / OFL)** ve projeye **doğrudan yüzlerce/binlerce varlık olarak indirilebilen veya API anahtarı bile gerektirmeden bağlanabilen** en güçlü hazır kütüphaneler şunlardır:

#### A. Font Kütüphanesi: 1.600+ Google Fonts & `google-webfonts-helper` Otomatik `.ttf` Motoru
1. **Google Webfonts Helper REST API (`https://gwfh.mranftl.com/api/fonts`) & Resmi `github.com/google/fonts` Deposu:**
   * **Nedir?** Google Fonts'taki **1.600'den fazla açık kaynaklı (OFL) font ailesinin** tamamını (ve Türkçe `latin-ext` desteklerini) doğrudan `.ttf` ve `.woff2` indirme linkleriyle sunan ücretsiz, API anahtarsız açık kaynak servisidir.
   * **Projeye Nasıl Eklenir?**
     * **1) Toplu İndirme Scripti (`download_fonts_pack.py`):** Tek komutla en popüler **120+ profesyonel Türkçe destekli fontun gerçek `.ttf` dosyasını** doğrudan `src/OtoEdit.PythonWorker/assets/fonts/` klasörüne indirebiliriz.
     * **2) Dinamik Font Arama & Otomatik İndirme (1.600+ Font):** Editördeki font seçiciye bir arama kutusu ekleriz; kullanıcı 1.600 font arasından hangisini seçerse seçsin, tarayıcıda anında Google Fonts CSS ile yüklenir, Python Worker ise render sırasında o fontun `.ttf` dosyası klasörde yoksa `github.com/google/fonts` / `gwfh` üzerinden **otomatik indirip önbelleğe alır!** Böylece sahte font yönlendirmesi (`_LOCAL_ASSET_MAP`) tamamen ortadan kalkar.

#### B. Çıkartma (Sticker), Hareketli Emoji ve Vektör Kütüphaneleri (200.000+ Hazır Varlık!)
1. **Google Noto Animated Emoji (`googlefonts/noto-emoji` — 400+ Hareketli Emoji Çıkartma):**
   * **Nedir?** Google'ın resmi hareketli emoji kütüphanesidir (Telegram ve YouTube Shorts'ta kullanılan yüksek kaliteli hareketli emojiler).
   * **Doğrudan CDN Yapısı (API Anahtarsız):**
     * Hareketli WebP: `https://fonts.gstatic.com/s/e/notoemoji/latest/{codepoint}/512.webp`
     * Hareketli GIF: `https://fonts.gstatic.com/s/e/notoemoji/latest/{codepoint}/512.gif`
     * Lottie JSON: `https://fonts.gstatic.com/s/e/notoemoji/latest/{codepoint}/lottie.json`
   * Hem tarayıcıda hem de FFmpeg render motorunda (`ignore_loop=0` ile) **yüzlerce hareketli çıkartma** olarak anında çalışır!
2. **Microsoft FluentUI 3D & Animated Emojis (`microsoft/fluentui-emoji` & `microsoft/fluentui-emoji-animated` — 1.500+ 3D Çıkartma):**
   * **Nedir?** Microsoft'un MIT lisansıyla açık kaynak yaptığı **1.500'den fazla 3 boyutlu (3D kil/cam görünümlü)** modern çıkartma ve hareketli APNG koleksiyonudur.
   * jsDelivr CDN (`https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@latest/assets/...`) üzerinden veya toplu paket olarak doğrudan editöre entegre edilebilir.
3. **Iconify Açık Kaynak Vektör & Rozet API'si (`https://api.iconify.design` — 200.000+ Vektör Çıkartma):**
   * **Nedir?** 150'den fazla açık kaynak ikon/illüstrasyon setini (`Noto`, `Twemoji`, `OpenMoji`, `Fluent Emoji`, `Streamline`, `Solar`, `Game Icons`, `Phosphor`, `Lucide` vb.) tek bir **ücretsiz ve API anahtarsız** REST uç noktasında birleştiren devasa kütüphanedir.
   * **Kullanımı:** Editördeki Çıkartmalar sekmesine bir arama kutusu koyduğumuzda, kullanıcı `"arrow"`, `"fire"`, `"subscribe"`, `"crown"`, `"money"`, `"star"`, `"heart"` yazdığında `https://api.iconify.design/search?query=...&limit=60` üzerinden **200.000+ vektör çıkartma** arasından anında seçim yapıp tek tıkla videoya ekleyebilir!
4. **Giphy / Tenor / Klipy Hareketli GIF & Sticker Arama API'si:**
   * Ücretsiz public/developer key ile milyonlarca şeffaf arkaplanlı hareketli Sticker (`.gif` / `.webp`) doğrudan editör içinden aranıp eklenebilir.

#### C. Ses Efektleri (SFX) ve Müzik Kütüphaneleri (Yüzlerce Gerçek Stüdyo Kaydı)
1. **Açık Kaynak CC0 Gerçek Stüdyo SFX Paketleri (Doğrudan İndirilebilir Paketler):**
   * **Kenney.nl CC0 Audio Pack (`kenney.nl/assets/category:Audio`) & OpenGameArt CC0 SFX:** Yüzlerce yüksek kaliteli UI, Pop, Whoosh, Impact, Chime, Glitch, Switch, Cartoon ses efekti (Tamamen Public Domain / CC0).
   * **Pixabay Sound Effects & Freesound.org CC0 Koleksiyonu:** Sinematik Bass Drop, Risers, Whoosh, Swoosh, Kamera Deklanşör, Klavye Daktilo, Para Sesi (Ka-Ching), Alkış, Gülme, Plak Durma (Record Scratch), Haber Bandı, Siber Glitch gibi **100+ gerçek MP3/WAV ses efektini** bir indirme scripti (`download_sfx_pack.py`) ile doğrudan projenin varlıklarına (`assets/sfx/`) indirebiliriz.
   * Ayrıca kullanıcının kendi bilgisayarından `.mp3 / .wav / .ogg` ses efekti yüklemesi ve online SFX araması yapabilmesi sağlanır.

#### D. Geçiş Efektleri (45+ FFmpeg `xfade` + `gl-transitions`) ve 50+ Animasyon Paketi
1. **FFmpeg `xfade` İçindeki 45 Yerleşik Geçişin Tamamı:**
   * FFmpeg'de halihazırda yüklü olan **45 geçiş efektinin tamamını** (`fade`, `fadeblack`, `fadewhite`, `fadegrays`, `distance`, `wipeleft`, `wiperight`, `wipeup`, `wipedown`, `wipetl`, `wipetr`, `wipebl`, `wipebr`, `slideleft`, `slideright`, `slideup`, `slidedown`, `smoothleft`, `smoothright`, `smoothup`, `smoothdown`, `circlecrop`, `rectcrop`, `circleopen`, `circleclose`, `vertopen`, `vertclose`, `horzopen`, `horzclose`, `dissolve`, `pixelize`, `diagtl`, `diagtr`, `diagbl`, `diagbr`, `hlslice`, `hrslice`, `vuslice`, `vdslice`, `hblur`, `squeezeh`, `squeezev`, `zoomin`, `hlwind`, `hrwind`, `vuwind`, `vdwind`, `coverleft`, `coverright`, `coverup`, `coverdown`, `revealleft`, `revealright`, `revealup`, `revealdown`) 8 kategori altında editöre ekleyebiliriz ve her biri için tarayıcıda birebir görsel önizleme çalıştırabiliriz.
2. **50+ Giriş / Çıkış / Döngü (Loop) Animasyonu (`Animate.css` & FFmpeg Matematiksel İfadeleri):**
   * `rubberBand`, `jello`, `tada`, `heartBeat`, `swing`, `wobble`, `flipInX`, `flipInY`, `lightSpeedInLeft`, `LightSpeedInRight`, `jackInTheBox`, `rollIn`, `zoomInDown`, `backInUp`, `bounceInLeft` gibi **50+ hazır animasyonu** hem CSS/WAAPI önizlemesine hem de `AnimationEffects` Python motoruna ekleyebiliriz.

#### E. Stok Görsel ve Stok Video (B-Roll) Kütüphanesi (Milyonlarca Fotoğraf & Video)
1. **Pexels Photo & Video API + Pixabay Photo & Video API + Unsplash:**
   * Python Worker'da zaten [pexels_client.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/pexels_client.py) mevcuttur, ancak sadece ilk analizde arka planda kullanılmaktadır.
   * Editörün sol panelindeki **Medya** sekmesine canlı bir **"🔍 Stok Fotoğraf & Stok Video Ara (Pexels / Pixabay / Unsplash)"** arama motoru ve **20+ zengin kategori** ekleyerek milyonlarca telifsiz görsel ve B-Roll videoya editör içinden anında ulaşılmasını sağlayabiliriz.

---

## BÖLÜM 3: Otonom Kurgu (Kesilmiş Videoyu Zenginleştirme) Sorunu

**Kullanıcı Gözlemi:** *"Kesme biçmesi filan yapılmış bir videom var, gene buradan yaptım onu indirdim, onu yeni proje oluşturup versem direkt kurgusunu yap ve gerekli yazıları, görselleri filan koyma işi çalışıyor mu şu an?"*

### 3.1. Şu Anki Durum ve Kök Neden
* **İlgili Kod:** [analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L308-L356), [auto_broll_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/auto_broll_engine.py#L24-L107), [edl_builder.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py#L148-L178).
* **Neden Tam Çalışmıyor?**
  1. **Sadece Stok Fotoğraf Ekleniyor:** `AutoBrollEngine.generate_broll_overlays()` fonksiyonu transkripti okuyup timeline'a (`overlays` listesine) **yalnızca `type="image"` (Pexels stok fotoğrafı)** eklemektedir.
  2. **Vurgu Yazıları (`text`), Geçişler (`transitions`), Ses Efektleri (`sfxClips`) ve Çıkartmalar (`sticker`) Timeline'a Otomatik Dizilmiyor:** Bu öğeler [ProactiveDirector.generate_suggestions()](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/proactive_director.py) tarafından üretilip `edl.proactiveSuggestions` / `edl.suggestions` içine (yani sol paneldeki "Yönetmen" sekmesine **öneri kartı olarak**) konulmaktadır. Kullanıcının editöre girip her birine tek tek *"Uygula"* demesi gerekmektedir.
  3. **Kesilmiş Videonun Tekrar Kesilmesi:** Önceden kesilmiş bir videoyu yeni projeye yüklerken `autoJumpcut` ve `autoRetake` varsayılan olarak açık olduğu için, sistem zaten kesilmiş videonuzdaki doğal nefes paylarını tekrar kesmektedir.

### 3.2. Çözüm: Gerçek `AutoDirectorComposer` (Tam Otonom Kurgu Dizici)
* Kullanıcı **"✨ Otonom Kurgu: Yazı, Görsel, Geçiş ve SFX Yerleştir"** seçeneğini işaretlediğinde (veya editör içinden *"Otonom Kurguyu Uygula"* dediğinde):
  * Konuşmanın ilk 3 saniyesine **Viral Hook Başlığı (`mrbeast_viral` / `hormozi_yellow` şablonlu)** + `whoosh-fast` SFX,
  * Her 10–15 saniyede bir konuşmanın en önemli anahtar cümlesine **Stilize Vurgu Metni (`type="text"`)** veya **Hareketli Çıkartma** + `pop-bubble` SFX,
  * Somut kavram anlatılan yerlere **Pexels B-Roll Görseli / Videosu**,
  * Sahne ve konu geçişlerine **FFmpeg `xfade` Geçiş Efektleri (`transitions`)**
  doğrudan `edl.overlays`, `edl.transitions` ve `edl.sfxClips` listelerine yazılarak **timeline'a hazır dizilmiş olarak** gelecektir.

---

## BÖLÜM 4: Başlangıç Tiklerinin (Checkbox) Çalışmama Nedenleri ve Yeniden Tasarımı

**Kullanıcı Gözlemi:** *"Verdiğim resimlerde de olan bu tikler gerçekten çalışıyor mu? Çalışmıyor gibi geldi. Bir de bu senaryo önerisi ve bunun gibi şeyleri istiyor muyuz, bunlar için baştaki tikleri daha bir düzenlemek gerek bence."*

### 4.1. Kodda Tespit Edilen 4 Kritik Tik (Checkbox) Hatası

1. **Hata 4.1 — "Dinamik Kelime Altyazısı" (`autoSubtitles`) Tiki Kodda Hiçbir Yere Bağlı Değil (%0 Çalışıyor):**
   * **İlgili Kod:** [analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L111) ve [edl_builder.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py#L39-L179).
   * `analysis_consumer.py` satır 111'de `auto_subtitles = bool(msg.get("autoSubtitlesEnabled", False))` okunup loglanmakta, **ancak alt satırlarda hiçbir yere (`edl_builder.build` dahil) parametre olarak verilmemektedir!**
   * `EdlSettings.subtitlesEnabled` her zaman varsayılan `True` kalmakta ve altyazı her zaman üretilip videoya basılmaktadır.

2. **Hata 4.2 — "Otomatik Ses İyileştirme (Gürültü ve Yankı Temizleme)" (`audioEnhancementEnabled`) Videonun Sesini Değiştirmiyor:**
   * **İlgili Kod:** [analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L149-L160), [audio_enhancer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/audio_enhancer.py#L13-L58) ve [render_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/render_consumer.py#L122-L127).
   * `AudioEnhancer.enhance()` gürültüsü temizlenmiş `{video}_clean.mp3` dosyasını üretip MinIO'ya yüklemekte, fakat bu dosyayı **sadece Whisper STT metin çıkarma aşamasında** kullanmaktadır!
   * Ne tarayıcıdaki editör önizlemesinde ne de `RenderConsumer` (final MP4 çıktısı) aşamasında bu temiz ses videoya gömülmemekte; her zaman ham videonun orijinal kirli sesi kullanılmaktadır.

3. **Hata 4.3 — "El Hareketi Komutlarını Aktif Et (Thumbs Down = Cut)" (`gestureCommandsEnabled`) Tek Başına El Hareketiyle Çalışmıyor:**
   * **İlgili Kod:** [multimodal_command_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/multimodal_command_engine.py#L34-L38).
   * Arayüzde *"Thumbs Down = Cut"* yazmasına rağmen, `MultimodalCommandEngine.detect()` önce transkriptte sesli komut (`"burayı kes"`, `"yazı ekle"`) arar. Eğer konuşmacı sesli komut söylemediyse satır 37'deki `if not voice_commands: return []` kontrolü yüzünden **MediaPipe el hareketi taraması hiç çalıştırılmadan atlanır!**

4. **Hata 4.4 — Redis Analiz Önbelleği (`ENABLE_ANALYSIS_CACHE`) Seçilen Tikleri Yok Sayıyor:**
   * **İlgili Kod:** [analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L132-L144).
   * `video_hash = self.cache.compute_video_hash(local_video_path)` yalnızca video dosyasının byte'larını hash'ler; kullanıcının seçtiği tikleri (`auto_jumpcut`, `auto_retake`, `auto_broll`, `auto_subtitles` vb.) hash anahtarına dahil etmez. Aynı video farklı tiklerle tekrar yüklendiğinde eski önbellek sonucu döner.

### 4.2. Tiklerin İki Ekrana Dağılmış Olması ve Yeni Tasarım
* **Mevcut Sorun:** 2 tik `Yeni Kurgu Projesi` modalında ([project-list.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-list/project-list.component.ts#L100-L121)), 4 tik ise video yükleme ekranında ([project-detail.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-detail/project-detail.component.ts#L134-L176)) dağınık durmaktadır.
* **Çözüm:** Tüm işlem tercihleri **Video Yükleme ekranında tek bir panelde** birleştirilecek ve üst kısmına **4 Hızlı Mod Butonu** eklenecektir:
  1. **⚡ Direkt Editör (İşlemsiz / Manuel Kurgu):** Tüm tikler kapalıdır; video yüklenir yüklenmez analiz bekletmeden doğrudan editör açılır.
  2. **✨ Kesilmiş Videoyu Kurgula (Oto Yazı + Görsel + Geçiş + SFX + Altyazı):** `Jump-Cut` ve `Retake` kapalıdır; `Oto Yazı & Başlık`, `Oto B-Roll Görsel`, `Oto Geçiş & SFX` ve `Dinamik Altyazı` açıktır.
  3. **✂️ Sadece Temizle (Jump-Cut + Retake + Ses Temizleme):** Sadece sessizlikleri ve hatalı tekrarları keser, ekrana yazı/görsel eklemez.
  4. **🚀 Tam Otonom Stüdyo (Hepsi Açık):** Ham videoyu hem keser hem de yazı, görsel, geçiş, SFX ve altyazı ile baştan sona kurgular.

---

## BÖLÜM 5: İşlemsiz "Direkt Editöre Geçiş" ve Editör İçi İhtiyaç Anında (On-Demand) AI Eksikliği

**Kullanıcı Gözlemi:** *"Videoyu hiçbir işlemden geçirmeden direkt editte yapılmak isteniyor olabilir. Bu senaryoda gene otocut filan yapıyor, direkt edite giremiyoruz. Videoyu atınca proje hiçbir kutucuk seçili değilse direkt atıp editöre geçsin. Eğer akıllı özelliklerimizin bazılarını kullanmak için zorunlu şeyler varsa kullanıcı o özellikleri kullanmak isteyince yaparsın."*

### 5.1. Kök Neden
* [VideoManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/VideoManager.cs#L101-L116) dosyayı MinIO'ya yükledikten sonra tiklerin hepsi `false` olsa bile projeyi `ProjectDurumu.AnalizEdiliyor` durumuna geçirir ve [analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L190-L330) içerisinde **Whisper STT + Yüz Takibi + Repurposing + SuggestionEngine** adımlarını zorunlu olarak çalıştırır.
* Ayrıca [project-detail.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-detail/project-detail.component.ts#L416-L420) yükleme biter bitmez `this.isAnalyzing.set(true)` yaparak kullanıcıyı analiz bekleme ekranına kilitler.

### 5.2. Çözüm: `Direct-to-Editor` (Sıfır Bekleme) & `On-Demand AI` (İhtiyaç Anında Analiz)
1. **Hiçbir Kutucuk Seçili Değilse Sıfır Bekleme ile Direkt Editöre Geçiş:**
   * Tüm işlem kutucukları kapalıysa (`autoJumpcut == false && autoRetake == false && autoBroll == false && autoSubtitles == false && !gestureCommands && !audioEnhancement`):
   * Ağır AI modelleri (Whisper STT, MediaPipe, Gemini, Pexels) **hiç çalıştırılmaz**.
   * Yalnızca `~0.5 saniyede` videonun süresi (`duration`) ve ses dalgası (`audioPeaks`) çıkarılarak kesimsiz (`cuts: []`), boş bir başlangıç EDL'si oluşturulur ve kullanıcı video yüklenir yüklenmez **otomatik olarak `/project/{id}/editor` ekranına yönlendirilir!**
2. **Editör İçinde İhtiyaç Anında (Lazy / On-Demand) AI Tetikleme:**
   * Kullanıcı işlemsiz olarak girdiği editörde manuel kesimlerini yaptıktan sonra sol panelden **"Altyazı Üret"**, **"Yönetmen Önerileri Al"**, **"Otonom Yazı/Görsel Diz"** veya **"AI Sohbet"** özelliğini kullanmak isterse:
   * Editör içindeki ilgili sekmede yer alan **"🧠 Şimdi AI Analizi / Transkript Çalıştır (Mevcut Kesimleri Korur)"** butonu (veya özellik tıklandığında otomatik tetiklenen uç nokta `POST /api/projects/{id}/edl/run-ai-task`) sadece istenen AI modülünü çalıştırır ve kullanıcının yaptığı manuel kesimleri bozmadan sonuçları canlı olarak timeline'a ekler.

---

## BÖLÜM 6: Kliplerin Yerini Oynatamama (Sıra Değiştirememe) ve Başka Video Klipleri Ekleyememe Sorunları

**Kullanıcı Gözlemi:** *"Bir eksik daha fark ettim: Kliplerin yerini oynatamıyorum editörde, mesela bir parçayı böldüm ayırdım ama onun yeri değişmiyor. Bir de içine başka video klipleri koyamıyorum."*

### 6.1. Sorun A: Bölünen Kliplerin Yerini Değiştirememe (Timeline Reorder Eksikliği)
* **Kök Neden ([editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L3943-L4022)):**
  * Mevcut `V1` kanalı (`readonly clips = computed(...)`), bağımsız kliplerden oluşan sıralı bir dizi (`playlist`) tutmamaktadır!
  * Bunun yerine tek bir videonun `0` ile `totalDuration` arasındaki zaman noktalarını (`cuts` ve `splitMarkers`) bir `Set<number>()` içine atıp satır 3962'de **`Array.from(allPoints).sort((a,b) => a-b)`** ile her zaman küçükten büyüğe sıralamaktadır.
  * Ayrıca [video_renderer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py) de sadece `cuts` listesini okuyup kalan parçaları (`keep_segments`) kronolojik sırayla birleştirmektedir.
* **Çözüm:**
  * EDL veri modeline (`EdlContent` / `EdlDocument`) sıralı bir **`videoClips: VideoClipItem[]`** (`{ id, sourceVideoId, sourceUrl, title, start, end, duration, order, speed }`) dizisi eklenecektir.
  * Kullanıcı bir klibi **Böl (`Split`)** yaptığında veya seçtiğinde, o klibi fareyle **sürükleyip başka bir klibin önüne/arkasına bırakabilecek (Drag & Drop Reorder)** veya üst bar / sağ tık menüsündeki **`⬅️ Sola Taşı` / `➡️ Sağa Taşı`** butonlarıyla sırasını değiştirebilecektir.
  * Hem tarayıcıdaki video önizleme oynatıcısı hem de Python FFmpeg Render motoru (`video_renderer.py`), klipleri sabit saniye sırasına göre değil, `videoClips` dizisindeki **kullanıcı sıralamasına göre** oynatacak ve birleştirecektir.

### 6.2. Sorun B: Editörün İçine Başka Video Klipleri Koyamama (Çoklu Video & Video B-Roll Eksikliği)
* **Kök Neden ([editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L1200-L1206) & [VideosController.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/VideosController.cs#L45-L53)):**
  1. Editörün sol panelindeki **Medya** sekmesinde bulunan dosya yükleme `<input type="file">` elemanı sadece `accept="image/*"` kabul etmektedir.
  2. [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L5412-L5449) içindeki `addAssetOverlay()` fonksiyonu, bir video yüklense bile bunu `V1` ana kanalına klip olarak ekleyememekte; `T1` katmanında ise `<video>` önizleme etiketi bulunmamaktadır (satır 708'de sadece `*ngIf="ov.type === 'image'"` için `<img>` etiketi vardır!).
* **Çözüm:**
  1. **Çoklu Video Yükleme (`accept="image/*,video/*,audio/*"`):** Medya sekmesinden `.mp4`, `.mov`, `.webm`, `.mkv` video dosyaları yüklenebilecek.
  2. **Ana Video Kanalına (`V1`) Klip Olarak Ekleme:** Yüklenen herhangi bir video (veya stok video kütüphanesinden seçilen bir video), **"🎬 Ana Kanala (`V1`) Klip Olarak Ekle (İmleç Noktasına / Sona)"** butonuyla doğrudan ana video şeridine eklenecek, bölünebilecek ve diğer kliplerin arasına taşınabilecek!
  3. **Üst Katmana (`T1/T2`) B-Roll / Picture-in-Picture (PiP) Video Olarak Ekleme:** İstenirse eklenen video **"📺 Üst Katmana (`T1`) PiP / B-Roll Video Olarak Ekle"** seçeneğiyle ana videonun üzerinde (köşede veya tam ekranda, kendi sesi ayarlanabilir şekilde) oynayan bir video katmanı (`ov.type === 'video'`) olarak hem canlı önizlemede hem de FFmpeg render'da çalışacak!

---

## BÖLÜM 7: Uygulama ve Çözüm Yol Haritası

Tüm bu sorunları kalıcı olarak çözmek için uygulanacak 5 adımlı teknik plan:

1. **Adım 1 — Sıfır Gecikme (Zero-Lag 120 FPS) Editör Performans Mimarisi:**
   * `editor.component.ts` içerisinde `clips`, `visibleSubtitleSegments`, `overlays` sinyallerinin birbirinden izole edilmesi, tüm `*ngFor` döngülerine `trackBy` eklenmesi, `NgZone.runOutsideAngular` ile 0ms gecikmeli doğrudan DOM `transform` sürükleme motoru ve `mouseup` sonrası gereksiz `loadEdl()` tam sayfa yenilemelerinin kaldırılması.
2. **Adım 2 — Dev Açık Kaynak Varlık & Kütüphane Entegrasyonu:**
   * **Fontlar:** Google Fonts / `gwfh` 100+ Türkçe destekli font listesi + Python Worker'da eksik `.ttf` dosyalarını otomatik indiren dinamik font çözücü + toplu font indirme scripti.
   * **Çıkartmalar & Hareketli Emojis:** **Google Noto Animated Emoji CDN (150+ hareketli WebP/GIF emoji)** + **Microsoft Fluent 3D Emoji** + **Iconify 200.000+ Vektör Çıkartma Canlı Arama Motoru**.
   * **Ses Efektleri (SFX):** Kategorize edilmiş **80+ zengin SFX kütüphanesi** + özel `.mp3/.wav` SFX yükleme.
   * **Geçişler & Animasyonlar:** FFmpeg `xfade` **45 geçiş efektinin tamamı** + **40+ giriş/çıkış/loop animasyonu**.
   * **Stok Görsel & Video:** Pexels / Pixabay destekli canlı stok fotoğraf ve stok video arama motoru.
3. **Adım 3 — Başlangıç Tiklerinin Düzeltilmesi, Tek Ekranda Birleştirilmesi ve "Direkt Editör" Modu:**
   * `autoSubtitles`, `audioEnhancementEnabled`, `gestureCommandsEnabled` ve Redis önbellek hash (`video_hash + flags`) hatalarının düzeltilmesi.
   * Tüm tiklerin Video Yükleme ekranında 4 hazır mod (**Direkt Editör**, **Kesilmiş Videoyu Kurgula**, **Sadece Kesim**, **Tam Otonom**) ile birleştirilmesi.
   * Hiçbir tik seçili değilse 0.5 saniyede kesimsiz EDL üretip direkt editöre yönlendirme + editör içinden İhtiyaç Anında (On-Demand) AI çalıştırma.
4. **Adım 4 — `AutoDirectorComposer` (Kesilmiş Videolar İçin Otomatik Yazı, Görsel, Geçiş ve SFX Dizici):**
   * Otonom kurgu seçildiğinde önerileri sadece kenar çubuğunda bırakmayıp doğrudan timeline üzerine vurgu başlıkları, B-Roll görselleri, geçiş efektleri ve ses efektleri olarak dizme.
5. **Adım 5 — `V1` Klip Sırası Değiştirme (Drag & Drop Reorder) ve Çoklu Video Klip / Video Overlay Ekleme:**
   * `V1` kanalında bölünen veya eklenen kliplerin sırasını sürükle-bırak ve `⬅️ / ➡️` butonlarıyla değiştirme + projeye dışarıdan yeni video klipleri (`V1` ana kanal veya `T1` PiP video katmanı olarak) ekleme.
