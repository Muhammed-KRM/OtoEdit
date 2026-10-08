# 📋 OtoEdit — Temel Mimari Sorunlar, Süreç Analizi ve Endüstriyel E2E Debugging Planı

> **Tarih:** 8 Ekim 2026  
> **Konum:** `docs/mimari_sorunlar_ve_e2e_debugging_plani.md`  
> **Durum:** 🟡 Analiz ve Teşhis Dokümanı (Kod Değişikliği Öncesi Yol Haritası)  
> **Kapsam:** Font Kaybolması, Player Küçülünce Letterbox Kayması, Görsel Ölçekleme Sınırı, Sarı Parlama Senkronu  

---

## 📑 Giriş: Sektör Terminolojisi ve Endüstri Standartları

Video kurgu, medya işleme ve dağıtık render mimarilerinde (Descript, CapCut, Runway, Netflix Media Engineering vb.) kullanıcı arayüzündeki (UI) bir tıklamadan, render edilmiş nihai videodaki piksellere kadar tüm yaşam döngüsünü adım adım denetleyen bu sisteme sektörde şu isimler verilir:

1. **Distributed Tracing & Correlation Tracking (Dağıtık İzleme - W3C / OpenTelemetry):**  
   Kullanıcının UI üzerinde başlattığı her aksiyona tekil bir `TraceId` (örn: `trc_ov_cinzel_1082`) atanır. Bu kimlik; UI State → REST API → Veritabanı (EDL JSON) → RabbitMQ → Python Worker → FFmpeg komutuna kadar aynı kimlikle taşınır ve her aşamada loglanır.
2. **Media Pipeline Verification Harness (Medya Doğrulama Çatısı):**  
   Verinin geçtiği her fonksiyonda **Girdi (Input) → İşlem (Transform) → Çıktı (Output) → Kalıcı Durum (Persisted State)** dörtlüsünü bir **Veri Sözleşmesine (Data Contract / Invariants)** göre doğrulayan otomatik test sistemidir.
3. **Golden Master / Deterministic State-to-Render Verification:**  
   Editör önizlemesindeki koordinat, renk ve font ile render motorunun (FFmpeg/libass) ürettiği video piksellerinin matematiksel olarak birbirini tuttuğunu garanti eden metodolojidir.

---

# BÖLÜM 1: Sorunlarımızın Bulunduğu Süreçler Neler?

Kullanıcı arayüzü, ekran görüntüleri ve backend mimarisi boyunca veri akış hattı 7 temel süreçten oluşmaktadır:

```
[SÜREÇ 1: KULLANICI ETKİLEŞİMİ (UI)] 
    │  (Font seçimi, Görsel ölçekleme, Pencere küçültme, Oynatma)
    ▼
[SÜREÇ 2: FRONTEND STATE & DOM RENDER] ────► ❌ SORUN 3: Player Küçülünce Letterbox Kayması
    │                                        ❌ SORUN 4: Görselin Büyütülememesi
    ▼
[SÜREÇ 3: REST API & POSTGRESQL (EDL JSON)]
    │  (PATCH /api/projects/{id}/edl -> EdlSnapshot kaydı)
    ▼
[SÜREÇ 4: RABBITMQ MESSAGE BUS]
    │  (RenderRequestedEvent yayını)
    ▼
[SÜREÇ 5: PYTHON WORKER: TIMELINE MAPPER] ──► ❌ SORUN 1: Sarı Parlama Senkron Kayması
    │  (Kesilen segmentler ve kelime zaman haritalama)
    ▼
[SÜREÇ 6: TEXT_OVERLAY & ASS ÜRETİMİ] ──────► ❌ SORUN 2: Fontun Renderda Kaybolması (Cinzel vs DejaVu)
    │  (\fnCinzel etiketinin üretilmesi)
    ▼
[SÜREÇ 7: FFMPEG DOCKER RENDER MOTORU]
       (libass font eşleme & piksel çizimi)
```

---

### 1.1. Sorun 1 Süreci: Altyazı Sarı Parlamasının (Karaoke) Senkron Bozukluğu

* **Bulunduğu Süreç:** *Süreç 2 (Frontend Oynatma Saati)* ve *Süreç 5 (Timeline Remapping).*
* **Süreç Akışı:**
  1. Whisper modeli ham videoyu çözerek kelime zaman damgalarını (`word.start`, `word.end`) üretir.
  2. Kullanıcı timeline üzerinde sessizlik, retake veya manuel kesimler yapar.
  3. **Kopma Noktası A (Frontend UI):** [`editor.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) dosyasındaki `isWordActive(word)` fonksiyonu şu şekilde çalışmaktadır:
     ```typescript
     return t >= word.start && t <= word.end;
     ```
     Buradaki `t = this.currentTime()` video etiketinin ham oynatma süresidir. Ancak ripple (kesilen kısımları atlayarak oynatma) aktif olduğunda veya timeline haritalandığında, oynatıcının zamanı ile ham Whisper kelime zamanı arasında kesilen kısımlar kadar **kümülatif bir zaman kayması** oluşur.
  4. **Kopma Noktası B (Backend ASS):** [`timeline_mapper.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/timeline_mapper.py) kelimeleri yeni zaman çizgisine kaydırırken Whisper'ın konuşma başlangıcındaki akustik gecikmesi (latency) ve segment birleşim noktalarındaki mikro boşluklar kelime süresine eklendiğinde sarı ışık kelimeden önce yanmaktadır.

---

### 1.2. Sorun 2 Süreci: Yazı Fontunun Render Sonrası Kaybolması (Fallback Fonta Düşmesi)

* **Bulunduğu Süreç:** *Süreç 1 (UI Seçimi) → Süreç 3 (EDL Kaydı) → Süreç 6 (ASS Üretimi) → Süreç 7 (Docker FFmpeg libass).*
* **Süreç Akışı ve Kopma Analizi:**
  1. Kullanıcı arayüzde `<option value="Cinzel">Cinzel (Sinematik Serif)</option>` seçer.
  2. Frontend `index.html` dosyasında Google Fonts'tan `Cinzel:wght@600;800` yüklü olduğu için tarayıcı bu fontu kusursuz gösterir.
  3. `inspectorData.font = 'Cinzel'` değeri EDL JSON'a yazılır ve PostgreSQL veritabanına kaydedilir.
  4. Render istendiğinde Python Worker'daki [`text_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/text_overlay.py) dosyasına `"font": "Cinzel"` olarak gelir.
  5. ASS dosyasına `\fnCinzel` etiketi yazılır.
  6. **Kopma Noktası (Docker & libass):** 
     * FFmpeg'in `libass` motoru fontu bulmak için Linux fontconfig sistemine (`fc-match Cinzel`) danışır.
     * `Dockerfile` satır 23 incelendiğinde:
       ```dockerfile
       curl -sL "https://fonts.google.com/download?family=Cinzel" -o cinzel.zip
       ```
       komutu bulunmaktadır. **Ancak Google Fonts, User-Agent başlığı olmayan ham curl isteklerine ZIP dosyası vermez (403 veya HTML hata sayfası döner).**
     * Ayrıca Docker konteyneri bu değişiklikten sonra yeniden build edilmediyse (`docker compose build`), konteyner içinde font fiziksel olarak hiç bulunmaz.
     * `libass` fontu bulamadığında hata vermez; **sessizce sistemin varsayılan fontuna (DejaVu Sans) düşer.**

---

### 1.3. Sorun 3 Süreci: Tarayıcı Küçültülünce Player'ın ve Yazı/Görsellerin Kayması

* **Bulunduğu Süreç:** *Süreç 2 (Frontend Video Sahnesi Geometrisi).*
* **Süreç Akışı ve Temel Mimari Hatası:**
  1. [`editor.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L386-L408)'de DOM yapısı şöyledir:
     ```html
     <!-- Dış Konteyner (Siyah Kutu) -->
     <div class="relative w-full flex-1 max-w-[860px] bg-black ... flex items-center justify-center">
       
       <!-- Video Elementi -->
       <video class="w-full h-full object-contain max-h-[460px]"></video>
       
       <!-- Overlay Katmanları -->
       <div *ngFor="let ov of activeOverlays()" 
            [style.top]="ov.positionY + '%'" 
            [style.left]="ov.positionX + '%'" 
            class="absolute ...">
       </div>
       
       <!-- Altyazı Katmanı -->
       <div class="absolute left-1/2 -translate-x-1/2 ..."></div>
     </div>
     ```
  2. **Hatanın Kaynağı:** Overlay'ler ve altyazı, `<video>` etiketinin gerçek görüntü piksel alanına (rendered video bounding rect) **bağlı değildir.** Dıştaki esnek `div` konteynerine bağlıdır!
  3. Pencere daraldığında konteyner kareleşir; video 16:9 oranını koruyarak ortada `object-contain` ile küçülür ve üstte/altta **büyük siyah barlar (letterbox)** oluşur.
  4. Overlay'ler dış kutunun `%` koordinatlarına göre konumlandığı için videonun üzerinden kayıp siyah boşluklara savrulur.
  5. Oysa Python Worker render alırken (`text_overlay.py` satır 156) bu koordinatları doğrudan videonun enine (`play_res_x = 1920`) ve boyuna (`play_res_y = 1080`) çarpar. Dolayısıyla **editörde görünen ile render edilen videonun koordinat uzayları birbirinden tamamen kopuktur.**

---

### 1.4. Sorun 4 Süreci: Görselin Büyütülememesi (Küçülüyor ama Büyümüyor)

* **Bulunduğu Süreç:** *Süreç 1 (UI Etkileşimi) → Süreç 2 (CSS Boyutlandırma Sınırları & Drag Mantığı).*
* **Kök Nedenler:**
  1. **CSS `maxHeight` Sınırı:** [`editor.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L430-L431)'de görsel şöyle tanımlıdır:
     ```html
     [style.width]="(160 * (ov.scale || 1.0) / 8.6) + 'cqi'"
     [style.maxHeight]="(120 * (ov.scale || 1.0) / 8.6) + 'cqi'"
     ```
     Görsel bir `img` etiketidir ve `object-cover` kullanmaktadır. Kullanıcı yatay bir görseli (örn: Twitter logosu) büyütmeye çalıştığında, `maxHeight` sınırına anında çarpar ve genişlik artsa bile görsel dikey sınırdan dolayı DOM içinde görsel olarak büyüyemez.
  2. **Resize Handle Vektör Hatası:** Satır 4150'de sürükleme mantığı:
     ```typescript
     const delta = Math.abs(deltaX) >= Math.abs(deltaY) ? deltaX : deltaY;
     let newScale = this.canvasResizeOriginalScale + (delta / 100);
     ```
     Kullanıcı fareyi sağ-alta çekerken (`deltaX > 0, deltaY > 0`) ölçek artmalı, ancak `canvasResizeOriginalScale` değeri her `mousemove` olayında sıfırlanmadığı veya fare videonun dışına taştığında `mouseup` kaçtığı için scale değeri takılı kalmaktadır.
  3. **Signal İmmutability (Değişmezlik) Sorunu:** Slider üzerinden `onInspectorChange()` çalıştığında doğrudan `ov.scale` değeri mutasyona uğratılmakta, ancak Angular Signal tabanlı `activeOverlays` computed fonksiyonu nesnenin referansı değişmediği için şablonu yeniden tetiklememektedir.

---

# BÖLÜM 2: Debugging Scriptler Nasıl Yazılacak? (Metodoloji ve Standartlar)

Sektör standartlarında bir hata tespit sistemi, kodun içine gelişigüzel `console.log` veya `print` serpiştirmek değildir. **Girdi, Durum Değişimi, Çıktı ve Doğrulama Sözleşmesi (Assertion)** içeren yapısal bir teşhis mimarisidir.

### 2.1. Kullanılacak Teknolojiler ve Formatlar

| Katman | Teknoloji / Dil | Kullanım Amacı | Format |
|---|---|---|---|
| **Frontend UI** | TypeScript / Angular Interceptor & Logger Service | Kullanıcı tıklamaları, DOM geometrisi, font yükleme durumları ve EDL state değişimlerini izleme | Structured Browser Console JSON + `window.__OTOEDIT_DIAGNOSTICS__` |
| **Backend API** | C# .NET Middleware / Serilog | REST istekleri, veritabanına yazılan JSON snapshotları ve RabbitMQ event yüklerini doğrulama | CorrelationId zenginleştirmeli JSON Log |
| **Worker & Render** | Python 3.11 / Pydantic V2 & pytest & PIL/NumPy | Docker içi font kontrolü, Timeline remapping matematiği, ASS üretimi ve piksel tabanlı video doğrulama | Dosya bazlı `.log` + `diagnostic_report.json` |

---

### 2.2. Standart Loglama ve Doğrulama Şeması (Trace Event Schema)

Her log olayı aşağıdaki evrensel JSON şemasına sahip olacaktır:

```json
{
  "traceId": "trc_overlay_cinzel_20261008_105500",
  "timestamp": "2026-10-08T10:55:00.123Z",
  "stage": "FONT_RESOLUTION",
  "component": "PythonWorker.TextOverlay",
  "function": "generate_ass",
  "input": {
    "requestedFont": "Cinzel",
    "fontSize": 54,
    "overlayId": "ov_txt_1728374100"
  },
  "output": {
    "resolvedAssFont": "Cinzel",
    "fontconfigMatchedFamily": "DejaVu Sans",
    "isFallback": true
  },
  "assertion": {
    "expected": "resolvedAssFont == fontconfigMatchedFamily",
    "passed": false,
    "errorMessage": "Cinzel fontu sistemde bulunamadı, DejaVu Sans fallback yapıldı!"
  },
  "persistedState": {
    "target": "temp_overlays.ass",
    "assLine": "Dialogue: 1,0:00:30.55,0:00:35.55,Default,,0,0,0,,{\\fnCinzel...}Yeni Metin"
  }
}
```

---

### 2.3. Doğru Girdi ve Çıktılar Nasıl Belirlenecek? (Kontrat Kuralları)

Sistem çalışırken her aşama için bir **Doğruluk Kontratı (Contract Invariant)** tanımlanacaktır:

1. **Font Süreci Kontratı:**  
   * *Girdi:* `inspectorData.font = 'Cinzel'`  
   * *Beklenen Ara Çıktı:* `edl.json -> overlays[0].font == 'Cinzel'`  
   * *Beklenen Docker Çıktısı:* `fc-match 'Cinzel'` çıktısında `family: "Cinzel"` dönmeli.  
   * *Nihai Video Çıktısı:* Videodan 1 kare alınıp OCR/Piksel analizi yapıldığında Serif tırnak pikseli bulunmalı.
2. **Player ve Koordinat Kontratı:**  
   * *Girdi:* Kullanıcı videonun tam ortasına (X: %50, Y: %50) yazı koydu.  
   * *Kontrat:* Tarayıcı genişliği 1920px de olsa, 400px de olsa; yazının merkezi her zaman `<video>` etiketinin fiziksel render alanının (letterbox hariç) tam merkezinde kalmalıdır.  
   * *Hata Durumu:* `Math.abs(overlayCenter - videoCenter) > 2px` ise sistem anında kırmızı alarm logu üretir.
3. **Sarı Parlama Kontratı:**  
   * *Girdi:* Whisper kelime zamanı `start: 30.55s`.  
   * *Kontrat:* Oynatıcı 30.54s iken `isWordActive` FALSE olmalı; 30.55s olduğunda anında TRUE olmalı; kelime bittiğinde FALSE olmalıdır.

---

# BÖLÜM 3: Ne Scriptleri Olacak, Kodlara Yeni Neler Eklenecek ve Mevcut Kodlarda Ne Değişecek?

Bu sistemi hayata geçirmek için hazırlanacak scriptler ve eklenecek log noktalarının tam mimari dökümü aşağıdadır:

---

### 3.1. Hazırlanacak Bağımsız Debugging & Test Scriptleri

Sisteme 3 adet bağımsız teşhis scripti eklenecektir:

#### Script 1: `scripts/debug_e2e_pipeline.py` (Uçtan Uca Boru Hattı Teşhis Scripti)
* **Görevi:** Editörden bağımsız olarak, örnek bir EDL JSON alır (`Cinzel` fontlu metin, ölçeklenmiş görsel, karaoke altyazı içerir).
* **Neyi Denetler?:**
  1. EDL'i `TimelineMapper`'a sokar; kelime ve overlay sürelerinin matematiksel kaymasını denetler.
  2. `TextOverlay.generate_ass` çalıştırır; üretilen `.ass` dosyasındaki font, pos ve karaoke `\k` etiketlerini Regex ile satır satır denetler.
  3. FFmpeg komutunu simüle eder; Docker içinde `Cinzel` fontunun var olup olmadığını `fc-list` ile doğrular.
  4. Çıktı olarak yeşil/kırmızı adımlardan oluşan bir HTML/JSON rapor (`diagnostics_summary.html`) basar.

#### Script 2: `scripts/verify_docker_fonts.sh` (Docker Font Doğrulama Scripti)
* **Görevi:** Python Worker Docker imajı içinde çalıştırılır.
* **Neyi Denetler?:**
  1. `/usr/share/fonts/truetype/custom/` altındaki font dosyalarının bozuk (0 byte / HTML hata sayfası) olup olmadığını kontrol eder.
  2. `fc-list : family` komutunu çalıştırarak `Cinzel`, `Inter`, `Montserrat` fontlarının Linux çekirdeğine tam olarak hangi isimle kaydedildiğini listeler.
  3. `fc-match "Cinzel"` çalıştırarak eşleşmeyi ekrana basar.

#### Script 3: `scripts/inspect_player_geometry.ts` (Frontend DOM Geometri Denetçisi)
* **Görevi:** Tarayıcı konsoluna yapıştırılabilen veya editör geliştirme modunda otomatik çalışan bir yardımcı modüldür.
* **Neyi Denetler?:**
  1. Pencere yeniden boyutlandırıldığında (resize), `<video>` elementinin gerçek boyutlarını (`videoWidth`, `videoHeight`, `getBoundingClientRect()`) hesaplar.
  2. Siyah barların (letterbox/pillarbox) piksel kalınlığını bulur.
  3. Overlay'lerin konumlarının bu siyah barlara göre mi yoksa videoya göre mi konumlandığını ölçer ve konsola tablo (`console.table`) olarak basar.

---

### 3.2. Kodlara Eklenecek Yeni Modüller

1. **Frontend:** `src/OtoEdit.Frontend/src/app/core/services/diagnostics.service.ts`
   * Tüm overlay değişikliklerini, font seçimlerini ve DOM koordinatlarını dinler.
   * `window.__OTOEDIT_DIAGNOSTICS__` nesnesi üzerinden tarayıcı konsolunda canlı telemetri sağlar.
2. **Python Worker:** `src/OtoEdit.PythonWorker/services/pipeline_tracer.py`
   * Her render işleminde oluşturulan `trace_id` için adım adım girdi/çıktı kaydı tutan ve diske `temp/trace_{id}.json` yazan izleme sınıfı.

---

### 3.3. Mevcut Kodlarda Yapılacak Değişiklikler (Planlanan Müdahaleler)

| Dosya | Yapılacak Değişiklik | Amacı |
|---|---|---|
| [`editor.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) | 1. Oynatıcı sahnesine video ile birebir en-boy oranına kilitli bir `<div class="video-overlay-stage">` sarmalayıcısı (aspect-ratio wrapper) eklenecek.<br>2. `onInspectorChange` ve `canvasResize` mantığında Signal immutability düzeltilecek.<br>3. `isWordActive` fonksiyonuna zaman ofset loglayıcısı eklenecek. | 1. Pencere küçülünce yazı ve görsellerin kaymasını önlemek.<br>2. Görsel boyutlandırmanın takılmasını çözmek.<br>3. Sarı parlamanın neden kaydığını UI'da anlık görmek. |
| [`text_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/text_overlay.py) | 1. `generate_ass` metoduna font çözümleme öncesi ve sonrası yapısal trace logları eklenecek.<br>2. Font eşleme sözlüğüne (`font_map`) `Cinzel`, `Bebas Neue` gibi frontend seçenekleri eklenecek.<br>3. Karaoke `\k` sürelerinin segment süresiyle toplamını denetleyen assertion konulacak. | Font kaybolmasını ve sarı parlama zaman hatalarını sıfıra indirmek. |
| [`Dockerfile`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/Dockerfile) | Google Fonts indirme komutuna geçerli bir `User-Agent` eklenecek veya fontlar doğrudan projenin `assets/fonts/` dizininden Docker içine kopyalanacak (`COPY assets/fonts/ ...`). | Cinzel ve diğer fontların Docker içinde kesin olarak var olmasını garanti etmek. |
| [`image_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py) | FFmpeg scale filtresi öncesi ve sonrası görsel genişlik/yükseklik değerlerini loglayan trace adımı eklenecek. | Görsel ölçeğinin render çıktısında doğrulanması. |

---

## 📌 Sonuç ve Sıradaki Eylem

Bu döküman, projenin `docs/` klasörü altına kaydedilmiştir. Hiçbir koda dokunulmamış olup, kodlama aşamasına geçmeden önce izlenecek metodoloji ve kök neden analizleri eksiksiz olarak belgelenmiştir.
