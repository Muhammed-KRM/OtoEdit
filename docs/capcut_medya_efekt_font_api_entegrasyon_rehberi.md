# CapCut & Premiere Pro Seviyesi Açık Kaynak Medya, Ses Efekti, GIF/Çıkartma, Font ve Geçiş Efekti Kütüphanesi Entegrasyon Rehberi

Bu doküman, `OtoEdit` video kurgu stüdyosuna telif hakkı sorunu yaratmadan ve sunucuda gigabaytlarca medya dosyası depolamaya gerek kalmadan entegre edilen **ücretsiz, yasal ve açık kaynaklı API & kütüphane mimarisini** detaylandırır.

---

## 1. Entegre Edilen İçerik Türleri ve Açık Kaynak API / Kütüphane Matrisi

| İçerik Türü | CapCut / Premiere Pro Karşılığı | OtoEdit Entegrasyon Kaynağı & Mimari | Lisans & Maliyet |
| :--- | :--- | :--- | :--- |
| **Ses Efektleri (SFX)** | *Revaçta, Komik, Islık, ASMR, Vlog, Oyun, Makineler, Geçiş (Whoosh)* + Alt Ses Dinleme Çubuğu | **1)** 100+ Yerleşik WebAudio & PCM WAV Stüdyo Sentezleyici (`studio-engine.service.ts`)<br>**2)** **Openverse Audio API (Freesound CC0 HQ MP3)** (`api.openverse.org/v1/audio/`)<br>**3)** **Wikimedia Commons Audio API** (`commons.wikimedia.org/w/api.php`) | **CC0 / Kamu Malı** (API Anahtarsız & CORS Açık) |
| **GIF & Hareketli Çıkartmalar (Stickers)** | *Ok işareti, Abone Ol (Subscribe), Geri Sayım, Sansür Mozaiği, Kırmızı El Çizimi Daire, Tepki GIF'leri* | **1)** **GIPHY v1 Stickers & GIFs API** (`api.giphy.com/v1/stickers/search` & `/gifs/search`)<br>**2)** **Google Noto 881 Hareketli Emoji API** (`googlefonts.github.io/noto-emoji-animation/data/api.json` + `fonts.gstatic.com` 512px GIF CDN)<br>**3)** **Iconify 200.000+ Vektör Sticker API** (`api.iconify.design`)<br>**4)** Yerleşik CapCut Callout SVG/GIF Paketleri | **Apache 2.0 / MIT / Ücretsiz SDK** |
| **Fontlar & Viral Metin Şablonları** | *SUBSCRIBE, Chapter End, BREAKING NEWS, CLOUD, ANGEL, LOCATION, Enjoy your life., LIVE BREAKING NEWS, CALL NOW* | **1)** **125+ Kategorili Google Font** (`latin,latin-ext` Türkçe tam uyumlu)<br>**2)** **1.600+ Google Font Canlı Yükleyici** (`fonts.googleapis.com/css2` üzerinden hem tarayıcıda hem Python `PillowGraphicsEngine` `.ttf` indiricisinde)<br>**3)** **30 CapCut Viral Metin Şablonu (`textPresets`)** | **SIL Open Font License (OFL)** |
| **Sahne Geçiş Efektleri (Transitions)** | *Trend, Kamera, Işık (Güneş Flaşı, Karlı Flaş), Bulanıklık (Sisli Girdap), Slayt (Sol, Sol Alt), 3D (Uçan Kağıt, Küp), Glitch (Blu-ray Tarama)* | **1)** **67 Geçiş Efekti** (`studio-engine.service.ts` + Dual-Layer Canvas 60 FPS Canlı Önizleme)<br>**2)** **GL Transitions & FFmpeg `xfade` + `acrossfade`** (`video_renderer.py` `XFADE_TRANSITION_MAP`) | **MIT / LGPL** |
| **Stok Görsel & B-Roll Arama** | *B-Roll görselleri, tarihi arşivler, doğa/şehir/teknoloji çekimleri* | **1)** **Openverse Image API** (`api.openverse.org/v1/images/`)<br>**2)** **Wikimedia Commons High-Res Image API**<br>**3)** **Pexels / Pixabay / Unsplash** (`web_image_crawler.py` + `VLMAssetVerifier`) | **CC0 / CC-BY / Pexels License** |

---

## 2. Mimari Detaylar ve Kod Konumları

### 2.1. Ses Efektleri (SFX) Kütüphanesi ve Canlı Arama Motoru
- **Frontend Servisi:** [studio-engine.service.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts)
  - `sfxLibrary`: `whoosh`, `pop`, `foley` (ASMR & Makineler), `funny` (Komik & Islık), `ui` (Oyun & Bildirim), `cinematic`, `impact`, `riser`, `ambience`, `musical` kategorilerinde **100+ yerleşik ses efekti**.
  - `searchOnlineSfx(query)`: Kullanıcının Türkçe veya İngilizce aramasını (`"klavye"`, `"typing"`, `"alkış"`, `"whoosh"`, `"gülme"`) otomatik terim sözlüğüyle zenginleştirerek paralel olarak **Openverse Freesound CC0 HQ MP3** ve **Wikimedia Commons Audio** servislerinden gerçek ses dosyalarını çeker.
  - `playSynthesizedSfx(presetId, volume, customAudioUrl)`: Hem yerleşik WebAudio sentezleyicisini hem de uzaktaki `.mp3`/`.ogg`/`.wav` URL'lerini sıfır gecikmeyle çalar.
- **Backend FFmpeg Miksaj Desteği:** [image_overlay.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py) ve [audio_mixer.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/audio_mixer.py)
  - `resolve_image_path()` fonksiyonu `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`, `.aac` uzantılarını ve `data:audio/...` Base64 ses verilerini indirip önbelleğe alır; böylece timeline'a (`A2` kanalına) eklenen tüm online Freesound/Wikimedia ses efektleri final MP4 çıktısına (`AudioMixer.mix_sfx_clips`) birebir gömülür.

### 2.2. GIF, Hareketli Çıkartma (Sticker) ve 881 Google Noto Emoji Motoru
- **Frontend Servisi:** [studio-engine.service.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts)
  - **CapCut Callout Çıkartmaları:** `Geri Sayım (4-3-2-1)`, `SUBSCRIBE + El İmleci`, `Sansür / Pixel Mozaik Bar`, `Kırmızı El Çizimi Daire`, `LIKE • FOLLOW • SHARE`, `Kırmızı Ok (Aşağı)`, `Yükleniyor (Loading Spinner)` ve 35+ şeffaf 512px Google Noto hareketli GIF doğrudan yerleşik kütüphaneye eklendi.
  - `searchIconifyStickers(query, sourceMode)`:
    1. **GIPHY Stickers & GIFs (`api.giphy.com/v1/stickers/search` & `/gifs/search`):** Şeffaf hareketli çıkartmalar ve tepki GIF'leri.
    2. **Google Noto 881 Animated Emoji (`googlefonts.github.io/noto-emoji-animation/data/api.json`):** 881 adet 512px şeffaf animasyonlu emojiyi etiketleriyle (`tags`) indeksler ve arar.
    3. **Iconify (`api.iconify.design`):** 200.000+ açık kaynaklı vektör çıkartma ve ikon.
- **Backend Sonsuz Döngü (Loop) GIF/APNG/WebP Render:** [image_overlay.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py)
  - `_is_animated_image_file()` fonksiyonu `.gif`, animasyonlu `.webp` (`ANIM`/`ANMF`) ve animasyonlu `.png` (`APNG` `acTL`) dosyalarını tespit eder ve FFmpeg'e `-ignore_loop 0` / `-stream_loop -1` parametreleriyle bağlayarak video üzerinde hareketli olarak işler.

### 2.3. 125+ Yerleşik Google Font + 1.600+ Dinamik Font Yükleyici + 30 CapCut Metin Şablonu
- **Frontend Servisi:** [studio-engine.service.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts)
  - `fontLibrary`: 7 kategoride (`Modern & Sans`, `Sinematik & Kalın`, `Tırnaklı & Klasik`, `El Yazısı & Fırça`, `Oyun, Siber & Piksel`, `Çizgi Roman & Eğlenceli`, `Daktilo & Kod`) **125+ Google Font**.
  - `addCustomGoogleFont(rawFamilyName)`: Kullanıcının adını yazdığı herhangi bir Google Font'u (`1.600+` açık kaynaklı font) `https://fonts.googleapis.com/css2?family=...&subset=latin,latin-ext&display=swap` üzerinden anında tarayıcıya yükler ve seçili metne uygular.
  - `textPresets`: CapCut'taki `SUBSCRIBE`, `Chapter End`, `BREAKING NEWS`, `CLOUD`, `ANGEL`, `LOCATION`, `Enjoy your life.`, `LIVE BREAKING NEWS`, `Live Stream Best Moments`, `LIKE / FOLLOW / SHARE`, `FINAL`, `CALL NOW`, `Thanks For Watching`, `TODAY STORY`, `Últimas notícias` dahil **30 hazır metin şablonu**.
- **Backend Otomatik `.ttf` İndirici:** [pillow_graphics_engine.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/pillow_graphics_engine.py)
  - `_ensure_google_font_ttf(family_name, bold)`: Google Fonts CSS2 servisine `User-Agent: Mozilla/5.0` ile istek atarak Türkçe (`latin-ext`: `ĞÜŞİÖÇğüşıöç`) gliflerini eksiksiz içeren `.ttf` dosyasını `/tmp/otoedit_fonts` dizinine otomatik indirir ve önbelleğe alır.

### 2.4. 67 CapCut & GL Transitions Sahne Geçiş Efekti
- **Frontend & Backend Eşleşmesi:** [studio-engine.service.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/studio-engine.service.ts), [editor.component.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) ve [video_renderer.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py)
  - CapCut'taki `Sol`, `Sol Alt`, `Güneş Flaşı (solarflash)`, `Karlı Flaş (snowflash)`, `Yakın Plan Morf (zoommorph)`, `Sisli Girdap (vortexblur)`, `Uçan Kağıt (pagecurl)`, `Işıltı Çemberi (irisglow)`, `Yanmış Portal (burnportal)`, `Blu-ray Tarama (blurayscan)`, `Zoom Snap (zoomsnap)`, `Renkli Makara (reelroll)`, `Bulutlar (clouddissolve)`, `3D Küp Dönüşü (cubespin)`, `3D Kapı Açılışı (doorway)`, `Glitch Anılar (glitchmemories)`, `Yönlü Bükülme (directionalwarp)`, `Rüzgar Gülü (pinwheel)`, `Panjur (windowblinds)`, `Altıgen Mozaik (hexagonalize)`, `Işık Erimesi (luminancemelt)` dahil **67 geçiş efekti** hem 60 FPS çift katmanlı (`Dual-Layer Canvas`) önizleme monitöründe hem de FFmpeg `xfade` render motorunda desteklenir.
