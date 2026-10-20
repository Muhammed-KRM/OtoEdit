# OtoEdit — Kapsamlı Çözüm, Açık Kaynak Kütüphane Entegrasyonu ve 120 FPS Mimari Uygulama Rehberi

**Tarih:** 20 Ekim 2026  
**Belge Türü:** Uçtan Uca Mühendislik Çözüm Planı & Kod Mimarisi Rehberi  
**İlgili Sorun Analizi Dökümanı:** `D:\OtoEdit\OtoEdit\docs\editor_performans_kutuphane_ve_akilli_kurgu_sorun_analizi.md`

---

## 0. Açık Kaynak Video Editörleri Araştırması ve Mimari Kıyaslama

Modern web tabanlı doğrusal olmayan video kurgu (NLE) projelerinin (**OpenCut**, **Motionity**, **DesignCombo / Remotion Timeline**, **OmniClip**) kaynak kodları ve mimarileri incelendiğinde, tespit ettiğimiz tüm sorunların endüstri standardı çözümleri şu şekilde uygulanmaktadır:

| Açık Kaynak Proje | İncelenen Mimari Yaklaşım | OtoEdit'e Uygulanacak Doğrudan Çözüm Karşılığı |
| :--- | :--- | :--- |
| **OpenCut** (`OpenCut-app/OpenCut`) | Sahne ve klip dizisi (`VideoClipItem[]`) tabanlı çok kanallı EDL yapısı; AI ajanlarının (MCP / Director) öneri listesinde kalmayıp doğrudan timeline JSON'ına `overlays`, `transitions` ve `audioClips` dizmesi. | **`V1` Klip Sıralama (`videoClips` Playlist)** + **`AutoDirectorComposer` (Otonom Kurgu Dizici)** mimarisi. |
| **Motionity** (`alyssaxuu/motionity`) | Sahne üzerindeki metin/görsel sürükleme işlemlerinin React/Angular state döngüsü dışında doğrudan GPU katmanında (`translate3d`) yürütülmesi; Lottie, Hareketli Emoji ve Iconify API entegrasyonu. | **`NgZone.runOutsideAngular` + GPU `translate3d` Sürükleme Motoru** + **Iconify (200.000+ Vektör) & Google Noto Animated Emoji CDN** entegrasyonu. |
| **DesignCombo** (`designcombo`) | Sinyallerin/Store'un izole parçalar halinde (`cutsStore`, `overlaysStore`, `subtitlesStore`, `waveformsStore`) tutulması; bir metin taşındığında ses dalgası veya klip kanallarının asla yeniden render edilmemesi. | **Granular Angular Signals (İzole Alt Sinyaller)** + **Tüm `*ngFor` Döngülerinde Zorunlu `trackBy`** + **`ChangeDetectionStrategy.OnPush`**. |
| **OmniClip** (`omni-media/omniclip`) | Kullanıcının videoyu yüklediği anda 0ms beklemeyle doğrudan timeline'a girmesi (`Direct-to-Timeline`); ağır analizlerin (STT, AI) arka planda veya kullanıcı talep ettiğinde (`On-Demand`) çalışması. | **Tiksiz Yüklemede Sıfır Beklemeyle Direkt Editöre Geçiş (`Direct-to-Editor`)** + **Editör İçi İhtiyaç Anında (`On-Demand`) AI Tetikleme**. |

---

## 1. FAZ A: Her İşlemdeki 2.5 – 5.2 Saniyelik Gecikmeyi (Lag) < 15 Milisaniyeye (120 FPS) İndiren Uçtan Uca Mimari Çözüm

### 1.1. Canlı Sistem Ölçümleriyle Kanıtlanan Sorun Özeti
Canlı PostgreSQL (`edit_decision_lists`, `endpoint_logs`) ve `.NET API (:5001)` + `Angular (:4200)` üzerinde yaptığımız ölçümler, gecikmenin sadece yazı sürüklemede değil **tüm işlemlerde (`id = 9808..9831`: klip silme, çıkartma ekleme, görsel ölçekleme, arka plan kaldırma, Inspector kaydetme)** `2,506 ms` ila `5,228 ms` sürdüğünü kanıtlamıştır:
1. **`EdlJson` İçindeki `2.00 MB` Statik `audioPeaks` Yükü (`168,913 float`):** `fef2ad89-ff4c-4bae-9294-3ad85f4cef02` projesinde (70 dk video) `EdlJson` boyutu **`2,384,160 Byte` (`2.38 MB`)** olup bunun **`2,000,853 Byte` (%84)** kısmı hiç değişmeyen `audioPeaks` dizisidir. Her `PATCH /edl` çağrısında ([EdlManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/EdlManager.cs#L109-L246)) bu `2.38 MB` veri PostgreSQL'den okunmakta, `SaveSnapshotAsync` ile `EdlSnapshots` tablosuna kopyalanmakta, `JsonNode.Parse` ile **168,913 ayrı heap nesnesine** ayrıştırılmakta, tekrar `2.38 MB` string'e serileştirilip veritabanına (`4.76 MB` yazma!) kaydedilmekte ve Redis önbelleği silinmektedir (`410–642 ms`).
2. **Editördeki 31 Metotta Bulunan `.subscribe(() => this.loadEdl())` Fırtınası:** Her işlem (`deleteClip`, `restoreClip`, `addTextOverlay`, `addImageOverlayFromUrl`, `saveInspector`, `onGlobalMouseUp`, `addSfxToTimeline`, `saveCurrentTransition` vb.) sonunda `this.loadEdl()` çağrılarak az önce Redis'ten silinmiş olan **`2.38 MB` JSON ağ üzerinden tekrar indirilmekte** ve `this.edl.set(res.edl)` + `this.audioPeaks.set(res.edl.audioPeaks)` ile tüm sayfa ikinci kez sıfırdan çizilmektedir.
3. **Monolitik `this.edl` Sinyali + `visibleSubtitleSegments()` İçindeki `1.87 Milyon` İterasyonluk Gizli Döngü:** `clips()` (`1,182` klip) ve `visibleSubtitleSegments()` (`634` altyazı segmenti) doğrudan `this.activeEdl()`'i dinlediği için, bir katman (`overlay`) 1 piksel bile oynadığında `visibleSubtitleSegments()` içinde `634 segment × 2 × 1,182 klip` = **`1,873,470` JS döngü adımı** çalışmaktadır!
4. **`*ngFor` Döngülerinde `trackBy` Olmaması (DOM Thrashing):** `clips()` ve `visibleSubtitleSegments()` her seferinde yeni nesne referansları döndürdüğü ve `*ngFor` üzerinde `trackBy` olmadığı için Angular her işlemde **591–1,182 adet `<canvas appClipWaveform>` + `ResizeObserver`**, **634 altyazı kutusu** ve **590 geçiş butonunu** DOM'dan tamamen silip sıfırdan yaratmaktadır!
5. **`RequestResponseLoggingMiddleware.cs` LOH Bellek Kopyalaması ve `proxy.conf.json` IPv6 (`::1`) Gecikmesi:** Her HTTP yanıtı `MemoryStream`'e tamponlanıp `2.38 MB` string üzerinde 3 kez `.Replace("\0", "")` çalıştırılmakta (`7.14 MB` LOH tahsisi) ve `proxy.conf.json` içindeki `localhost:5001` Windows'ta IPv6 `::1` SYN zaman aşımına (`+220ms` – `+2,000ms`) takılmaktadır.

---

### 1.2. Adım Adım Kod Çözümü (FAZ A — Backend + Frontend + Ağ)

#### Çözüm A.1 (Backend): `EdlManager.cs` İçinde `audioPeaks` Verisinin `PATCH /edl`, `GET /edl` ve `EdlSnapshots` Döngüsünden Ayrıştırılması (`2.38 MB` -> `~120 KB`)
* [EdlManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/EdlManager.cs) içerisinde:
  1. `GetEdlAsync(Guid projectId, bool includePeaks = false)` varsayılan olarak `audioPeaks` dizisini ana `GET /edl` JSON yanıtından çıkarır (veya ilk açılışta `GET /edl/waveform` ayrı önbellekli uç noktadan `edl:peaks:{projectId}` Redis anahtarıyla servis edilir). Böylece `GET /edl` boyutu **`2,384 KB`'dan `~120 KB`'a (20 kat küçülme!)** iner.
  2. `PatchEdlAsync` içinde `JsonNode.Parse` yapılmadan önce veya `SaveSnapshotAsync` sırasında `audioPeaks` düğümü `EdlSnapshots` tablosuna **kopyalanmaz** (çünkü `audioPeaks` Undo/Redo ile değişmeyen statik ses verisidir!).
  3. Ayrıca `audioPeaks` kaydedilirken 17 basamaklı float (`0.008999999612569809`) yerine `Math.Round(val, 3)` (`0.009`) ile serileştirilerek boyutu `%70` azaltılır.

#### Çözüm A.2 (Backend & Proxy): `RequestResponseLoggingMiddleware.cs` ve `proxy.conf.json` Hızlandırması
* [RequestResponseLoggingMiddleware.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.API/Middleware/RequestResponseLoggingMiddleware.cs) içerisinde:
  * `/edl` ve `/waveform` gibi büyük JSON yanıtlarında tüm yanıt gövdesini `MemoryStream` + `StreamReader.ReadToEndAsync()` ile belleğe kopyalayıp 3 kez `.Replace("\0", "")` çalıştırmak yerine, yalnızca ilk `4096` byte okunur ve `logService.LogEndpointAsync` yanıt akışını bloklamadan çalışır.
* [proxy.conf.json](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/proxy.conf.json) içerisinde:
  * `"target": "http://localhost:5001"` ifadesi **`"target": "http://127.0.0.1:5001"`** olarak güncellenerek Windows IPv6 (`::1`) bağlantı gecikmesi (`220ms–2000ms`) sıfıra indirilir.

#### Çözüm A.3 (Frontend): Editördeki 31 Noktada Bulunan Gereksiz `this.loadEdl()` Çağrılarının Kaldırılması (Optimistic State)
* [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) içindeki 31 metotta (`deleteClip`, `restoreClip`, `duplicateOverlay`, `splitOverlayAtPlayhead`, `addAssetOverlay`, `assignAssetToSelectedOverlay`, `assignUrlToSelectedOverlay`, `addTextOverlay`, `addImageOverlayFromUrl`, `saveInspector`, `addSfxToTimeline`, `removeSfxClip`, `toggleNormalizeAudio`, `toggleSmartPunchIn`, `saveCurrentTransition`, `applyTransitionToAllCuts`, `removeCurrentTransition`, `acceptSuggestion`, `rejectSuggestion`, `removeOverlay`, `onGlobalMouseUp` vb.):
  * `patchEdl(...)` başarılı olduğunda sunucudan tüm EDL'yi tekrar indiren **`this.loadEdl()` ÇAĞRILMAYACAKTIR!**
  * Yerel sinyal zaten anında (`0 ms`) güncellendiği için ekran hiç titremez, ağdan `2.38 MB` veri tekrar indirilmez ve `audioPeaks.set(...)` tekrar tetiklenmez. (`loadEdl()` yalnızca sayfa ilk açıldığında, Undo/Redo yapıldığında ve AI Sohbet yaması uygulandığında çağrılır).

#### Çözüm A.4 (Frontend): Monolitik `edl` Sinyalini İzole Alt Sinyallere Ayırma (Signal Slicing) ve `O(N log N)` İkili Arama (Binary Search)
1. Bir metin veya görsel katman (`overlays`) güncellendiğinde `clips()` ve `visibleSubtitleSegments()` sinyallerinin **kesinlikle tetiklenmemesi** için `cuts`, `overlays`, `transcriptSegments`, `transitions` ve `sfxClips` için referans koruyucu (`equal` karşılaştırmalı) seçici sinyaller tanımlanır:

```typescript
// 1. Sadece kesimler (cuts) veya videoClips değiştiğinde tetiklenen izole sinyal:
readonly activeCuts = computed<CutItem[]>(() => {
  return this.activeEdl()?.cuts || [];
}, {
  equal: (a, b) => a === b || (a.length === b.length && a.every((c, i) => c.id === b[i]?.id && c.start === b[i]?.start && c.end === b[i]?.end))
});

// 2. Sadece altyazı segmentleri değiştiğinde tetiklenen izole sinyal:
readonly activeTranscriptSegments = computed<TranscriptSegment[]>(() => {
  return this.activeEdl()?.transcript?.segments || [];
}, {
  equal: (a, b) => a === b
});

// 3. Sadece katmanlar (overlays) değiştiğinde tetiklenen izole sinyal:
readonly allOverlays = computed<OverlayItem[]>(() => {
  return this.activeEdl()?.overlays || [];
}, {
  equal: (a, b) => a === b
});
```

2. `visibleSubtitleSegments()` içindeki `1.87 Milyon` iterasyonluk `getVisTimeFromRawTime` çağrıları yerine, `clips()` hesaplanırken her görünür klip için `visStart` (kümülatif görünür başlangıç süresi) kaydedilir ve `getVisTimeFromRawTime` **İkili Arama (`Binary Search - O(log N)`)** kullanır:
   * Böylece `1,873,470` döngü adımı **`~6,000` adıma (300 kat hızlanma, `< 0.4 ms`)** iner!

#### Çözüm A.5 (Frontend): Tüm `*ngFor` Döngülerine `trackBy` Fonksiyonlarının Eklenmesi
[editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) içerisine aşağıdaki `trackBy` metotları eklenir ve şablondaki tüm döngülere bağlanır:

```typescript
trackByClipId = (_index: number, clip: any): string => clip.id;
trackByOverlayId = (_index: number, ov: OverlayItem): string => ov.id;
trackBySubtitleId = (index: number, seg: any): string => `${index}_${seg.start}_${seg.end}`;
trackByBoundaryId = (_index: number, b: any): string => b.id;
trackBySfxId = (_index: number, sfx: EdlSfxClip): string => sfx.id;
trackByTrackNum = (_index: number, trackNum: number): number => trackNum;
trackByFontFamily = (_index: number, font: FontOption): string => font.family;
```

* `<ng-container *ngFor="let clip of clips(); trackBy: trackByClipId">`
* `<div *ngFor="let seg of visibleSubtitleSegments(); trackBy: trackBySubtitleId">`
* `<div *ngFor="let ov of overlaysByTrackMap()[trackNum] || []; trackBy: trackByOverlayId">`
* `<div *ngFor="let ov of activeOverlays(); trackBy: trackByOverlayId">`
* `<button *ngFor="let b of clipTransitionBoundaries(); trackBy: trackByBoundaryId">`

Bu sayede kesimler değişse bile mevcut `591–1,182` adet `<canvas appClipWaveform>` DOM düğümü **asla silinmez**, sadece değişen klibin genişliği güncellenir.

#### Çözüm A.6 (Frontend): Şablon İçi `.filter()` Çağrılarının (`getOverlaysForTrack`, `getFontsByCategory`) Pre-Computed Map Sinyallerine Dönüştürülmesi
HTML içinde her Change Detection'da çalışan `getOverlaysForTrack(trackNum)` ve `getFontsByCategory(cat.id)` kaldırılıp `O(1)` tablolara dönüştürülür:

```typescript
readonly overlaysByTrackMap = computed<Record<number, OverlayItem[]>>(() => {
  const map: Record<number, OverlayItem[]> = {};
  for (const ov of this.allOverlays()) {
    const t = Number(ov.trackId) || 1;
    if (!map[t]) map[t] = [];
    map[t].push(ov);
  }
  return map;
});
```

#### Çözüm A.7 (Frontend): `NgZone.runOutsideAngular` + Doğrudan DOM Stili ile 120 FPS Sürükleme Motoru
`@HostListener('window:mousemove')` kaldırılarak `ngOnInit` içinde **`this.ngZone.runOutsideAngular(...)`** ile `passive: true` olarak bağlanır.
* Fare boşta gezerken (`!isCanvasDragging && !isDraggingOverlay && !isScrubbing ...`) fonksiyon ilk satırda `return` eder ve **Angular Change Detection'ı hiç tetiklemez!**
* Kullanıcı kanvas üzerinde bir yazıyı veya görseli sürüklerken (`isCanvasDragging === true`):
  * Saniyede 120 kez `this.edl.update(...)` **çağrılmaz**!
  * Bunun yerine sürüklenen DOM elemanının referansı (`this.draggedCanvasElement`) üzerinden doğrudan `style.left / style.top` uygulanır (`0.03 ms` / `120+ FPS`).
  * Kullanıcı fareyi bıraktığında (`mouseup`), `this.ngZone.run(...)` içine girilerek son `newX, newY` koordinatı tek seferde `ov.positionX / ov.positionY`'ye yazılır ve `loadEdl()` çağrılmadan sadece `patchEdl` gönderilir.

#### Çözüm A.8 (Frontend): Base64 PNG/WAV Yerine Hafif Asset/Preset Referansı
* `addSfxToTimeline()` içinde `EdlJson`'a yüzlerce KB Base64 WAV gömmek yerine yalnızca `presetId` kaydedilir (`generateSfxWavDataUri` sadece gerektiğinde yerel çalar).
* `removeBackgroundNow()` çıktısı `Blob` olarak `AssetService.uploadAsset` ile MinIO'ya yüklenip kısa URL olarak `ov.source` içine yazılır; böylece `EdlJson` boyutu her zaman hafif kalır.

---

## 2. FAZ B: Yüzlerce Font, Hareketli Çıkartma, 3D Emoji, Vektör İkon, Gerçek SFX, 45 Geçiş ve Canlı Stok Medya Kütüphanesi

### 2.1. Font Kütüphanesi: 120+ Kategorize Font + 1.600 Google Font Canlı Arama + Python Otomatik `.ttf` İndirici
* **Sorun:** Şu an arayüzde 37 font var, Python Worker'da ise sadece 7 gerçek `.ttf` dosyası var ([pillow_graphics_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/pillow_graphics_engine.py#L79-L103) diğerlerini gizlice `Cinzel.ttf` veya `Anton.ttf`'e yönlendiriyor).
* **Çözüm:**
  1. **Frontend'de 100+ Seçkin Türkçe Destekli Font + Canlı Google Font Yükleyici:**
     * `StudioEngineService.fonts` listesi **8 kategoride 100+ profesyonel fonta** çıkarılacak (`Viral & YouTube`, `Modern Sans`, `Sinematik & Serif`, `El Yazısı & İmza`, `Çizgi Roman & Oyun`, `Siber & Teknoloji`, `Retro & Gazete`, `Lüks & Moda`).
     * Kullanıcı listeden bir font seçtiğinde veya özel bir Google Font adı yazdığında, `StudioEngineService.ensureFontLoaded(fontFamily)` fonksiyonu dinamik olarak `https://fonts.googleapis.com/css2?family=...&display=swap` etiketini `<head>` içine ekleyerek sadece kullanılan fontları anında yükleyecek (sayfa açılış hızını hiç yavaşlatmadan yüzlerce font desteği).
  2. **Python Worker'da Otomatik Google Font `.ttf` İndirici (`PillowGraphicsEngine._ensure_google_font_ttf`):**
     * [pillow_graphics_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/pillow_graphics_engine.py) içerisindeki sahte `_LOCAL_ASSET_MAP` yönlendirmeleri kaldırılacak!
     * Render sırasında istenen fontun `.ttf` dosyası `/app/assets/fonts/` içinde yoksa, Python Worker **Google Webfonts Helper API (`https://gwfh.mranftl.com/api/fonts/{slug}`) veya `github.com/google/fonts` CDN'i** üzerinden o fontun gerçek `.ttf` dosyasını **otomatik olarak indirip `/app/assets/fonts/` içine kaydedecek**!
     * Ayrıca `src/OtoEdit.PythonWorker/tools/download_font_pack.py` scripti ile en çok kullanılan fontların `.ttf` dosyaları doğrudan diske indirilecek.

---

### 2.2. Çıkartma (Sticker), Hareketli Emoji, 3D Emoji ve 200.000+ Vektör Arama Motoru
Şu anki 12 sabit çıkartma yerine **4 dev çıkartma kaynağı** doğrudan editörün **"Çıkartmalar & Emoji"** paneline entegre edilecektir:

1. **Google Noto Animated Emojis (400+ Hareketli WebP / GIF Çıkartma):**
   * **Kaynak:** Resmi Google Fonts CDN (`https://fonts.gstatic.com/s/e/notoemoji/latest/{codepoint}/512.gif` ve `512.webp`) + Resmi Metadata (`https://googlefonts.github.io/noto-emoji-animation/data/api.json`).
   * **Özellik:** Alev 🔥, Roket 🚀, Şok 🤯, Kalp ❤️, Kahkaha 😂, Para 🤑, Kutlama 🎉, Alkış 👏, Şimşek ⚡, Taç 👑, Yıldız 🤩, Alarm 🚨, Onay ✅, Patlama 💥, Düşünen 🤔, Ağlayan 😭, Kas 💪, Beyin 🧠, Gözler 👀, Yüzde Yüz 💯 dahil **en popüler 120+ hareketli emoji doğrudan hazır sekmede** yer alacak + `api.json` üzerinden **400+ hareketli emoji içinde arama** yapılabilecek!
   * Hem tarayıcıda canlı hareketli oynar hem de Python FFmpeg (`ignore_loop=0`) render'da hareketli olarak videoya basılır!
2. **Microsoft FluentUI 3D Emojis (Yüzlerce 3 Boyutlu Kil/Modern Çıkartma):**
   * **Kaynak:** `https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@latest/assets/{EmojiName}/3D/{emoji_3d}.png`
   * Yüksek çözünürlüklü 3 boyutlu render edilmiş modern ikon ve emojiler.
3. **Iconify 200.000+ Vektör Çıkartma & İkon Canlı Arama Motoru (`https://api.iconify.design`):**
   * Editördeki Çıkartma paneline **"🔍 200.000+ Çıkartma, Ok, Rozet ve İkon Ara"** arama kutusu eklenecek.
   * Kullanıcı arama yaptığında (örn. `arrow`, `subscribe`, `youtube`, `instagram`, `tiktok`, `fire`, `badge`, `star`, `check`, `warning`, `money`, `crown`, `music`, `camera`, `game`), `https://api.iconify.design/search?query={q}&limit=60` API'sinden anında renkli SVG çıkartmalar (`https://api.iconify.design/{prefix}/{name}.svg?height=256`) çekilip tek tıkla videoya eklenecek!
4. **Sosyal Medya, Oklar, Konuşma Balonları ve Vurgu Rozetleri Paketi (50+ Yerleşik SVG Sticker):**
   * `Abone Ol`, `Beğen`, `Bildirimleri Aç`, `Yorum Yap`, `Kaydet`, `Link Bio'da`, `Yeni Video`, `Canlı Yayın`, `İndirim`, `Dikkat`, `Bomba İpucu`, `10+ Farklı Neon/El Çizimi Ok`, `Konuşma & Düşünce Balonları`, `El Çizimi Daire/Çerçeve Vurgular`.

---

### 2.3. Ses Efektleri (SFX) Kütüphanesi: 75+ Zengin Kategorize Ses Efekti + Özel SFX Dosyası Yükleme
* **Sorun:** Şu an sadece 16 basit ses var.
* **Çözüm:**
  1. **8 Kategoride 75+ Profesyonel SFX Kütüphanesi (`StudioEngineService.sfxLibrary`):**
     * **💨 Geçiş & Rüzgar (Whoosh / Swoosh):** `Hızlı Whoosh`, `Derin Sinematik Swoosh`, `Kısa Whip Pan`, `Ateşli Geçiş (Fire Whoosh)`, `Rüzgar Savrulması`, `Bıçak Keskin Geçiş`, `Çift Swoosh`, `Yumuşak Hava Geçişi`...
     * **🫧 Pop, Plop & Çıkartma (Pop / Bubble / Cartoon):** `Baloncuk Pop`, `Keskin Pop`, `Çift Pop`, `Mantar Tıpası (Cork Pop)`, `Su Damlası (Water Drop)`, `Elastik Yay (Boing)`, `Çizgi Film Zıplama`, `Kağıt Buruşturma`, `Etiket Yapıştırma`...
     * **🔔 Bildirim, Para & UI (Ding / Cash / Tech UI):** `Parlak Çan (Ding)`, `Kasa / Para (Ka-Ching)`, `Altın Sikke (Coin Drop)`, `Seviye Atlama (Level Up)`, `Başarı Akoru (Success)`, `Apple Tarzı Bildirim`, `Mesaj Gönderildi (Swoosh Ding)`, `Onay (Checkmark)`, `Doğru Cevap (Quiz Correct)`...
     * **💣 Sinematik & Darbe (Impact / Boom / Riser):** `Sub Bass Drop (808 Boom)`, `Sinematik Orkestral Hit`, `Metalik Çarpma (Anvil Impact)`, `Derin Deprem (Rumble)`, `Kısa Gerilim Yükseltici (Short Riser)`, `Uzun Sinematik Riser`, `Fragman Braaam (Inception Horn)`, `Kalp Atışı (Heartbeat)`, `Saat Tik-Tak (Countdown Tick)`, `Bomba Patlaması`...
     * **📸 Kamera, Klavye & Ofis (Foley):** `DSLR Kamera Deklanşör`, `Polaroid Fotoğraf Çekimi`, `Film Projektörü`, `Mekanik Klavye Yazımı`, `Daktilo Satır Sonu (Typewriter Bell)`, `Çift Fare Tıklaması`, `Tek Fare Tıklaması`, `Kalemle Çizim (Marker Swipe)`, `Sayfa Çevirme (Page Flip)`...
     * **⚡ Dijital, Glitch & Siber (Sci-Fi / Glitch):** `Dijital Glitch Parazit`, `TV Sinyal Kesilmesi (Static)`, `Siber Lazer`, `Veri Taraması (HUD Scan)`, `Hologram Açılışı`, `Elektrik Kıvılcımı (Zap)`, `Güç Kapanışı (Power Down)`...
     * **😂 Mizah, Tepki & Kalabalık (Funny / Meme / Crowd):** `Plak Durma (Record Scratch)`, `Yanlış Cevap (Error Buzzer)`, `Üzgün Trombon (Wah-Wah)`, `Sansür Bip Sesi (Censor Beep)`, `Kornalı Vurgu (Airhorn)`, `Kısa Alkış`, `Büyük Stadyum Alkışı`, `Davul Şaka Vuruşu (Ba-Dum-Tss)`, `Korku Gerilim Yaylısı (Psycho Violin)`...
  2. **Çok Katmanlı (Multi-Oscillator + Filtered Noise + FM + Reverb Impulse) Zengin Sentezleme + Gerçek `.mp3 / .wav` Yükleme:**
     * Kullanıcının kendi bilgisayarından istediği `.mp3 / .wav / .ogg` ses efektini yükleyip doğrudan `A2 (SFX)` kanalına ekleyebileceği **"📤 Özel Ses Efekti (.mp3/.wav) Yükle"** butonu eklenecek.
     * Ayrıca SFX nesneleri EDL JSON içine devasa Base64 string olarak gömülmeyecek; tarayıcıda `sfxBlobUrlCache` (Bellek Blob URL) kullanılacak ve Python Worker render sırasında `AudioMixer` içinde doğrudan sentezleyip veya ses dosyasını indirip FFmpeg `amix` ile birleştirecek!

---

### 2.4. Geçiş Efektleri (45 FFmpeg `xfade` Geçişinin Tamamı) ve 45+ Katman Animasyonu
1. **FFmpeg `xfade` 45 Yerleşik Geçiş Efektinin Tamamı (7 Kategori):**
   * **Temel & Sinematik:** `fade` (Dissolve), `fadeblack` (Dip to Black), `fadewhite` (White Flash), `fadegrays` (Gri Ton Geçiş), `dissolve` (Kumlanma Dissolve), `distance` (Renk Mesafesi), `hblur` (Yatay Hareket Bulanıklığı / Motion Blur).
   * **Kamera Savurma (Whip / Slide):** `slideleft`, `slideright`, `slideup`, `slidedown`, `smoothleft`, `smoothright`, `smoothup`, `smoothdown`.
   * **Perde Silme (Wipes & Diagonals):** `wipeleft`, `wiperight`, `wipeup`, `wipedown`, `wipetl`, `wipetr`, `wipebl`, `wipebr`, `diagtl`, `diagtr`, `diagbl`, `diagbr`.
   * **Geometrik & Iris Maske:** `circleopen`, `circleclose`, `circlecrop`, `rectcrop`, `vertopen`, `vertclose`, `horzopen`, `horzclose`.
   * **Kaplama & Açığa Çıkarma (Cover / Reveal):** `coverleft`, `coverright`, `coverup`, `coverdown`, `revealleft`, `revealright`, `revealup`, `revealdown`.
   * **Zoom & Sıkıştırma:** `zoomin` (Crash Zoom), `squeezeh` (Yatay Sıkıştırma), `squeezev` (Dikey Sıkıştırma).
   * **Glitch, Dilim & Rüzgar:** `pixelize` (Mozaik), `hlslice`, `hrslice`, `vuslice`, `vdslice`, `hlwind`, `hrwind`, `vuwind`, `vdwind`.
2. **45+ Metin & Görsel Katman Animasyonu (Giriş / Çıkış / Döngü):**
   * **Giriş (20+):** `pop-up`, `bounce`, `elastic-scale`, `zoom-crash`, `zoom-out-in`, `fade`, `slide-up`, `slide-down`, `slide-left`, `slide-right`, `whip-left`, `whip-right`, `typewriter`, `blur-in`, `glitch`, `flip-3d-x`, `flip-3d-y`, `rotate-in`, `swing-in`, `newspaper-spin`.
   * **Çıkış (12+):** `fade`, `scale-out`, `zoom-explosion`, `slide-down`, `slide-up`, `slide-left`, `slide-right`, `blur-out`, `glitch-out`, `flip-out`.
   * **Sürekli Döngü / Loop (15+):** `pulse`, `heartbeat`, `float`, `wiggle`, `shake`, `earthquake`, `neon-flicker`, `pendulum`, `rubber-band`, `jello`, `tada`, `spin-slow`, `breathe`, `wave`, `strobe`.

---

### 2.5. Canlı Stok Görsel & Stok Video (B-Roll) Arama Motoru
* Backend'e (`AssetsController` / `VideosController`) Pexels & Wikimedia/Unsplash destekli **`GET /api/projects/{projectId}/stock-search?query=...&type=photo|video`** uç noktası eklenecek ve zengin kategorize hazır stok fotoğraf + stok video kataloğu (100+ küratörlü HD görsel ve B-Roll video klip) ile birleştirilecek.
* Editörün **Medya** sekmesinde kullanıcı arama kutusuna Türkçe veya İngilizce kelime yazdığında hem **Stok Fotoğraflar** hem de **Stok B-Roll Videolar** listelenecek.

---

## 3. FAZ C: Başlangıç Tiklerinin Düzeltilmesi, Tek Ekranda 4 Hızlı Modla Birleştirilmesi, "Direkt Editör" (0sn Bekleme) ve İhtiyaç Anında (On-Demand) AI

### 3.1. Tespit Edilen 4 Kritik Tik Hatasının Kod Çözümü

1. **Redis Önbellek Anahtarı Hatasının Düzeltilmesi ([analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L132-L144)):**
   * **Mevcut Hata:** `video_hash = self.cache.compute_video_hash(local_video_path)` yalnızca video dosyasını hash'lediği için, aynı videoyu farklı tiklerle yüklediğinizde eski sonucu dönüyordu.
   * **Çözüm:** Önbellek anahtarına tüm seçili bayraklar dahil edilir:
     ```python
     flags_signature = (
         f"fmt={video_format}|jc={int(auto_jumpcut)}|rt={int(auto_retake)}|"
         f"br={int(auto_broll)}|sub={int(auto_subtitles)}|"
         f"gest={int(gesture_enabled)}|aud={int(audio_enhancement)}"
     )
     cache_key = f"{video_hash}:{hashlib.md5(flags_signature.encode()).hexdigest()[:10]}"
     ```

2. **"Dinamik Kelime Altyazısı" (`autoSubtitles`) Tikinin Gerçekten Bağlanması ([analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L342) & [edl_builder.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py#L53)):**
   * `edl_builder.build(..., auto_subtitles=auto_subtitles)` parametresi eklenir ve `EdlSettings(subtitlesEnabled=auto_subtitles, ...)` olarak kaydedilir.
   * Eğer kullanıcı `Dinamik Kelime Altyazısı` tikini **işaretlemediyse (`False`)**, editör açıldığında `showSubtitles()` kapalı (`false`) başlar ve render'da videonun üzerine zorla altyazı basılmaz!

3. **"Otomatik Ses İyileştirme" (`audioEnhancementEnabled`) Tikinin Hem Önizleme Hem Render'a Bağlanması ([edl_builder.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py) & [video_renderer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py)):**
   * `audioEnhancementEnabled=True` seçildiğinde:
     * `EdlSettings.normalizeAudio = True` ve `EdlSettings.audioEnhancementEnabled = True` otomatik olarak aktif edilir.
     * `VideoRenderer.render()` aşamasında hem FFmpeg `afftdn=nf=-25` + `highpass=f=80` (stüdyo gürültü ve uğultu temizleme) hem de `AudioMixer.apply_loudnorm(target_i=-14.0)` filtresi doğrudan ana video sesine uygulanır!

4. **"El Hareketi Komutları" (`gestureCommandsEnabled`) Tikinin Bağımsız Jestlerle de Çalışması ([multimodal_command_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/multimodal_command_engine.py#L34-L55)):**
   * Konuşmacı sesli olarak `"burayı kes"` demese bile, videodaki sessiz duraklama pencerelerinde (`silence_windows`) kameraya yapılan belirgin **👎 (Thumbs Down)** veya **✋ (Open Palm)** hareketlerinin MediaPipe ile taranıp kesim/işaret olarak algılanması sağlanır.

---

### 3.2. Tiklerin Tek Ekranda Birleştirilmesi ve 4 Hazır Kurgu Modu ([project-list.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-list/project-list.component.ts) & [project-detail.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-detail/project-detail.component.ts))

* `Yeni Kurgu Projesi` oluşturma modalındaki (`project-list.component.ts`) dağınık 2 tik kaldırılarak tüm ayarlar **Video Yükleme (`project-detail.component.ts`)** ekranındaki tek bir **"Akıllı Kurgu & İşlem Tercihleri"** panelinde toplanacaktır.
* Panelin en üstünde tek tıkla seçilebilen **4 Hızlı Kurgu Modu (Preset)** yer alacaktır:

| Hızlı Mod | Jump-Cut | Retake | Otonom Kurgu (Yazı+Görsel+Geçiş+SFX) | Dinamik Altyazı | Ses İyileştirme | El Hareketi | Ne Yapar? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. ⚡ Direkt Editör (İşlemsiz / Manuel)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **Hiçbir AI analizi veya kesim yapmaz.** Videoyu yükler yüklemez **0 saniye beklemeyle doğrudan Editör ekranını açar!** |
| **2. ✨ Kesilmiş Videoyu Kurgula (Oto Zenginleştir)** | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | **Önceden kesilmiş videolar için özel mod!** Videoyu tekrar kesmez; konuşmayı analiz edip timeline'a otomatik **Vurgu Başlıkları, B-Roll Görseller, Geçiş Efektleri, SFX ve Altyazı** dizer. |
| **3. ✂️ Sadece Kesim & Temiz Ses** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | Sadece sessizlikleri (`Jump-Cut`) ve hatalı tekrarları (`Retake`) keser, sesi temizler; ekrana yazı/görsel koymaz. |
| **4. 🚀 Tam Otonom Stüdyo (Hepsi Açık)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ham çekimi baştan sona keser, temizler ve tüm yazı, görsel, geçiş, SFX ve altyazıları timeline'a otomatik dizer. |

---

### 3.3. Hiçbir Kutucuk Seçili Değilken "Direkt Editöre Geçiş" (`Direct-to-Editor`) ve Editör İçi İhtiyaç Anında (`On-Demand`) AI

1. **Sıfır Bekleme ile Direkt Editöre Geçiş (`Direct-to-Editor`):**
   * Kullanıcı video yüklerken hiçbir kutucuğu seçmediyse (`!autoJumpcut && !autoRetake && !autoBroll && !autoSubtitles && !gestureCommands && !audioEnhancement`):
   * [VideoManager.cs](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/VideoManager.cs) ve [analysis_consumer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py) içerisinde **"Hızlı Passthrough (Direct-to-Editor) Yolu"** çalışır:
     * Whisper STT, MediaPipe Yüz/El Takibi, Gemini LLM ve Pexels aramaları **kesinlikle çalıştırılmaz**.
     * Yalnızca `~0.4 saniyede` FFmpeg ile videonun süresi (`duration`) ve gerçek ses dalgası (`audioPeaks`) çıkarılır, kesimsiz (`cuts: []`) bir başlangıç EDL'si oluşturulup `AnalysisCompletedEvent` yayınlanır.
     * [project-detail.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-detail/project-detail.component.ts) tüm kutucuklar kapalıysa yükleme biter bitmez kullanıcıyı analiz ekranında bekletmeden **`this.router.navigate(['/project', p.id, 'editor'])`** ile doğrudan editöre sokar!

2. **Editör İçinde İhtiyaç Anında (`On-Demand`) Akıllı Özellik Çalıştırma:**
   * Kullanıcı videoyu işlemsiz olarak direkt editöre attıktan sonra, editörün içindeyken:
     * **"Yönetmen" sekmesinde:** *"✨ Otonom Kurguyu Şimdi Timeline'a Diz (Yazı + Görsel + Geçiş + SFX)"* veya *"💡 AI Önerileri Üret"* butonuna basabilir.
     * **"Altyazı / Transkript" sekmesinde:** Eğer transkript boşsa *"🎙️ Şimdi Konuşmaları Metne Dök & Altyazı Oluştur"* butonuna basabilir (`POST /api/projects/{projectId}/edl/analyze-on-demand`).
     * Bu işlem kullanıcının editörde yaptığı **manuel kesimleri ve eklediği katmanları kesinlikle silmeden** sadece eksik olan transkript veya otonom kurgu öğelerini mevcut EDL'ye birleştirir!

---

## 4. FAZ D: `AutoDirectorComposer` — Kesilmiş veya Ham Videoya Otomatik Yazı, Görsel, Geçiş ve SFX Dizme Motoru

**Sorun:** Şu an `autoBroll` açık olduğunda [auto_broll_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/auto_broll_engine.py) sadece 2–4 adet Pexels fotoğrafı koyuyor; stilize başlık/vurgu yazıları, geçiş efektleri ve ses efektleri timeline'a dizilmiyor (sadece öneri listesinde bekliyor).

**Çözüm:** Hem Python Worker'da ([auto_broll_engine.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/auto_broll_engine.py) & [edl_builder.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py)) hem de Angular Editör'de (`StudioEngineService.autoComposeTimeline(edl)`) çalışan tam kapsamlı bir **Otonom Kurgu Dizici (`AutoDirectorComposer`)** devreye alınacaktır:

1. **Otomatik Stilize Vurgu Başlıkları (`type: 'text'`):**
   * Videonun açılışında (0.5sn – 4.0sn) konuşmanın ilk cümlesinden çıkarılan **Viral Kanca Başlığı** (`Anton` / `Montserrat`, çift konturlu, sarı-kırmızı degrade dolgulu, `pop-up` animasyonlu) `T1` katmanına yerleştirilir.
   * Konuşma boyunca her 10–14 saniyede bir en güçlü vurgu kelimesi/ifadesi seçilerek (`hormozi_yellow`, `neon_cyber`, `marker_highlighter`, `pill_badge` şablonlarıyla dönüşümlü olarak) `T1` katmanına dizilir.
2. **Otomatik Görsel & Hareketli Çıkartma Zenginleştirmesi (`type: 'image'`):**
   * Pexels/Stok görseller `T2` katmanına yerleştirilir.
   * Duygusal/vurgu anlarına uygun **Hareketli Google Noto Emoji Çıkartması** (🔥, 🚀, 💡, ⚡, 💰) `T3` katmanına eklenir.
3. **Otomatik Sahne Geçiş Efektleri (`edl.transitions`):**
   * Kesim noktalarına veya 12–15 saniyelik konu geçiş sınırlarına otomatik olarak yumuşak ve dinamik geçişler (`fade`, `slideleft`, `zoomin`, `smoothright`) yerleştirilir.
4. **Otomatik Senkronize Ses Efektleri (`edl.sfxClips` — `A2` Kanalı):**
   * Ekrana her otomatik başlık veya çıkartma girdiğinde tam o saniyeye (`timestamp`) uygun bir **`pop-bubble`**, **`whoosh-fast`** veya **`ding-bell`** ses efekti `A2 (SFX)` kanalına otomatik olarak dizilir!
5. **Editör İçi Tek Tıkla Otomatik Kurgulama Butonu:**
   * Kullanıcı editörün içindeyken bile sol paneldeki **"🎬 Yönetmen"** sekmesinde yer alan **"🪄 Tüm Videoyu Otomatik Kurgula (Yazı + Görsel + Geçiş + SFX Diz)"** butonuna bastığında, 1 saniye içinde tüm timeline zenginleştirilir (ve kullanıcı beğenmediği parçayı tek tıkla silebilir veya `Ctrl+Z` ile geri alabilir).

---

## 5. FAZ E: `V1` Kliplerinin Yerini Değiştirme (Drag & Drop Reorder) ve İçine Başka Video Klipleri Koyma Mimarisi

### 5.1. `V1` Kanalında Kliplerin Yerini Oynatma (Sürükle-Bırak ve `⬅️ / ➡️` Sıra Değiştirme)

* **Mevcut Kısıtlama:** [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L3962) içindeki `clips()` hesaplaması her zaman `Array.from(allPoints).sort((a,b) => a-b)` yaptığı için bölünen bir klibin sırası değiştirilemiyordu.
* **Yeni Mimari (`EdlVideoClipItem[]` Sekans Motoru):**
  1. **Veri Modeli (`edl.model.ts` & `edl_model.py`):**
     ```typescript
     export interface EdlVideoClipItem {
       id: string;
       sourceVideoId?: string;
       sourceUrl?: string;      // Eklenen dış videonun stream URL'si (boşsa ana proje videosu)
       objectKey?: string;      // MinIO nesne anahtarı (render motoru için)
       title?: string;
       start: number;           // Kaynak video içindeki başlangıç saniyesi (sourceStart)
       end: number;             // Kaynak video içindeki bitiş saniyesi (sourceEnd)
       duration: number;
       order: number;           // Timeline üzerindeki kullanıcı sıralaması!
       speed?: number;
       volume?: number;
       isExternalVideo?: boolean;
     }
     ```
     `EdlContent` içerisine `videoClips?: EdlVideoClipItem[]` alanı eklenir.
  2. **Sürükle-Bırak (Drag & Drop) ve Araç Çubuğu ile Sıra Değiştirme:**
     * `V1` kanalındaki her sağlam klip (`!clip.isCut`) üzerinde:
       * Fare ile klibi tutup sağa/sola başka bir klibin üzerine sürükleyerek **yerini değiştirme (`onClipDragStart`, `onClipDropOnTarget`)**,
       * Seçili klip için üst araç çubuğunda ve sağ tık menüsünde **`⬅️ Klibi Sola Taşı`** ve **`➡️ Klibi Sağa Taşı`** butonları.
  3. **Canlı Önizleme Oynatıcısında (`<video>`) Sırası Değişmiş Klipleri Oynatma:**
     * `onTimeUpdate()` içerisinde oynatıcı bir klibin sonuna (`clip.end`) geldiğinde, `videoClips` dizisindeki **bir sonraki sıradaki klibin** `start` saniyesine (veya farklı bir kaynak video ise onun `sourceUrl` + `start` saniyesine) kesintisiz geçiş yapar!
  4. **Python FFmpeg Render Motorunda (`video_renderer.py`) Sırası Değişmiş ve Çoklu Videoları Birleştirme:**
     * [video_renderer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py) içerisinde eğer `edl_json.get("videoClips")` mevcutsa, `_cut_segments` fonksiyonu parçaları kronolojik sırayla değil, **`videoClips` listesindeki kullanıcı sırasına göre** (ve her klibin kendi `sourceUrl / objectKey` video dosyasından) kesip FFmpeg `concat` ile birleştirir!

---

### 5.2. Editörün İçine Başka Video Klipleri Koyma (Hem `V1` Ana Kanala Klip Ekleme Hem `T1` PiP Video Overlay)

1. **Medya Sekmesinde Video Dosyası Yükleme (`accept="image/*,video/*,audio/*"`):**
   * [editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L1204) içindeki dosya yükleme input'u `.mp4, .mov, .webm, .mkv` video dosyalarını da kabul edecek şekilde güncellenir (`AssetManager.cs` zaten `video/mp4`, `video/webm`, `video/quicktime` MIME türlerini desteklemektedir!).
2. **Yüklenen veya Stoktan Seçilen Videoyu 2 Farklı Şekilde Kullanma:**
   Medya sekmesindeki her video kartının altında **2 net buton** yer alacaktır:
   * **Buton 1 — `🎬 Ana Kanala (V1) Ekle` (`addVideoClipToMainTrack(asset)`):**
     * Videonun süresini otomatik algılar ve `V1` ana video kanalına (seçili klibin hemen arkasına veya timeline sonuna) yeni bir **`EdlVideoClipItem`** olarak ekler!
     * Kullanıcı bu yeni video klibini `V1` üzerinde bölebilir (`B`), hızını değiştirebilir, geçiş efekti (`⚡`) ekleyebilir ve sürükleyip diğer kliplerin arasına taşıyabilir!
   * **Buton 2 — `📺 Üst Katmana (T1 PiP) Ekle` (`addAssetOverlay(asset)`):**
     * Videoyu `T1/T2` katmanına `type: 'video'` olarak ekler.
     * Video Önizleme Monitörüne ([editor.component.ts](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L708)) `<video *ngIf="ov.type === 'video'" [src]="ov.source" muted autoplay loop>` desteği eklenerek üst katmandaki B-Roll / Picture-in-Picture videoların da tıpkı görseller gibi boyutlandırılması, döndürülmesi, çerçevelenmesi ve canlı oynatılması sağlanır.
     * Python Worker'da [image_overlay.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py) ve [video_renderer.py](file:///D:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py) içerisine `ov.type == "video"` katmanlarını FFmpeg `overlay` filtresiyle ana videonun üzerine basma desteği eklenir.

---

## 6. FAZ F: Uygulama Sırası ve Doğrulama Planı

| Sıra | Faz | Hedef Dosyalar | Doğrulama Kriteri |
| :---: | :--- | :--- | :--- |
| **1** | **FAZ A: 120 FPS Performans & Sıfır Gecikme** | `editor.component.ts` | Metin/görsel sürükleme gecikmesinin 2000ms'den **<1ms'ye (120 FPS)** düşmesi; sürükleme sırasında `<canvas appClipWaveform>` elemanlarının yeniden çizilmemesi. |
| **2** | **FAZ B: Dev Açık Kaynak Kütüphaneler** | `studio-engine.service.ts`, `editor.component.ts`, `pillow_graphics_engine.py`, `animation_effects.py` | 100+ Google Font + otomatik `.ttf` indirici, 120+ Google Noto Hareketli Emoji + Iconify 200.000+ vektör çıkartma arama, 75+ SFX + özel ses yükleme, 45 FFmpeg `xfade` geçişi, 45+ animasyon ve canlı Stok Görsel/Video arama. |
| **3** | **FAZ C: Tikler, 4 Hızlı Mod & Direkt Editör** | `project-list.component.ts`, `project-detail.component.ts`, `VideoManager.cs`, `analysis_consumer.py`, `edl_builder.py` | Tüm tiklerin tek ekranda 4 hazır modla çalışması, Redis hash düzeltmesi, tiksiz yüklemede 0sn beklemeyle direkt editöre geçiş ve editör içi On-Demand AI. |
| **4** | **FAZ D: `AutoDirectorComposer` (Otonom Kurgu)** | `auto_broll_engine.py`, `edl_builder.py`, `studio-engine.service.ts`, `editor.component.ts` | Kesilmiş veya ham videoya tek tıkla / yükleme anında otomatik Vurgu Başlıkları, B-Roll Görseller, Hareketli Emojiler, Geçişler ve SFX dizilmesi. |
| **5** | **FAZ E: `V1` Klip Sıralama & Çoklu Video Ekleme** | `edl.model.ts`, `editor.component.ts`, `EdlManager.cs`, `video_renderer.py`, `image_overlay.py` | Bölünen kliplerin `V1` üzerinde sürükle-bırak ve `⬅️/➡️` ile yer değiştirmesi + dışarıdan yeni video kliplerinin `V1` ve `T1`'e eklenip oynatılması ve render edilmesi. |
| **6** | **FAZ F: Test & Canlı Tarayıcı Doğrulaması** | `tests/test_professional_editor_features.py`, `OtoEdit.UnitTests`, Chrome CDP | Tüm Python (`pytest`) ve .NET (`dotnet test`) birim testlerinin %100 geçmesi ve tarayıcıda canlı doğrulama. |
