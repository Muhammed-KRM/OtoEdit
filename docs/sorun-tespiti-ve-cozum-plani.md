# OtoEdit: Kurgu Arayüzü Sorun Tespiti ve Çözüm Planı (RCA & Action Plan)

Bu döküman, kullanıcının ilettiği ekran görüntüleri ve geri bildirimler doğrultusunda tespit edilen **8 adet kritik işlevsel ve görsel sorunun kök neden analizini (Root Cause Analysis)** ve **kalıcı mimari çözüm planını** içerir.

---

## Sorun Matrisi ve Öncelik Tablosu

| No | Sorun Başlığı | Kategori | Kök Neden (RCA) | Etki Düzeyi |
|:---|:---|:---|:---|:---|
| **1** | Kırmızı/sarı kesim bloklarının sağa kayması | Timeline / UI | Flexbox kümülatif piksel sapması ve mutlak koordinat uyuşmazlığı | **Kritik** |
| **2** | Ses dalga formunun sahte olması ve konuşmayla uyuşmaması | Waveform / Engine | 500MB+ videonun fetch ile indirilemeyip matematiksel mock sinüs dalgasına düşmesi | **Kritik** |
| **3** | Beyaz oynatma imlecinin (Playhead) tutup sürüklenememesi | UX / Etkileşim | Playhead üzerinde `pointer-events-none` olması ve drag/scrubbing dinleyicisinin bulunmaması | **Yüksek** |
| **4** | Zoom yapıldığında timeline'ın sola dayalı kalıp sağa kaydırılamaması | UI / Navigasyon | Yatay tekerlek kaydırmasının yalnızca `Shift` ile çalışması ve scroll kapsayıcı kısıtları | **Yüksek** |
| **5** | "Geri Yükle" hover butonunun klibin solunda kayık çıkması | UI / CSS | Flexbox kümülatif kayması ve dar kliplerde `inset-0` elemanının taşması | **Orta** |
| **6** | Net kurgu süresinin tüm kesimlere rağmen orijinal süreyle aynı yazması | Mantık / Hesaplama | `visibleDuration` fonksiyonunun görünürlük filtresine bağlı olarak kesimleri de toplaması | **Yüksek** |
| **7** | Inspector inputlarının beyaz zemin üzerine beyaz yazı olması | Tema / Tailwind | `tailwind.config.js` içinde `dark-950` sınıfının tanımlı olmaması nedeniyle browser varsayılanına düşmesi | **Yüksek** |
| **8** | Çift altyazı çıkması ve altyazıların timeline katmanı olarak düzenlenememesi | Altyazı / NLE | Native HTML5 `<track>` etiketinin kapatılamaması ve altyazıların timeline kanalına bağlı olmaması | **Kritik** |

---

## 1. Derin Kök Neden Analizi (Root Cause Analysis)

### Sorun 1: Kırmızı ve Sarı İşaretlerin Kaymış Olması
* **Mevcut Durum:** Ekran görüntüsünde oynatıcı 02:19'da dururken, altındaki kırmızı kesim ve sarı retake blokları olması gereken saniyelerden 10-15 saniye sağa kaymış durumdadır.
* **Kök Nedenler:**
  1. **Flexbox Kümülatif Kutu Modeli Kayması:** Video kanalındaki klipler `<div class="flex">` içerisinde ardışık sıralanmaktadır. 22.5 dakikalık videoda 134 adet kesim ve aralık klibi vardır. Her bir klibin sağ kenarlığı (`border-r border-white/20`), padding'i ve piksel altı (subpixel) yuvarlama payları 130 elemanda toplanarak 100 pikselin üzerinde devasa bir sağa kaymaya (cumulative drift) yol açmaktadır.
  2. **İki Farklı Koordinat Sisteminin Çatışması:** Üstteki zaman cetveli (Ruler ticks) ve oynatıcı iğnesi (Playhead) `position: absolute; left: %` mutlak yüzdelik zaman koordinatı ile çalışırken, video şeridi flexbox göreceli akışıyla (`display: flex`) çalışmaktadır. Bu iki sistem matematiksel olarak örtüşemez.
  3. **Filtre Çarpanı Hatası:** Kliplerin genişlik formülündeki `visibleDuration()` böleni, filtrelerden biri bile açık olsa tüm genişlik hesaplarını bozmaktadır.
* **Kalıcı Çözüm:** Klipler flexbox akışından çıkarılacak; tıpkı katmanlar ve ruler gibi **mutlak koordinat sistemine (`position: absolute; left: (start/dur)*100%; width: (dur/dur)*100%`)** geçirilecektir. Her klip zaman çizelgesindeki milisaniyesine tam kilitlenecektir.

---

### Sorun 2: Ses Dalga Formunun Tamamen Sahte / Yanlış Olması
* **Mevcut Durum:** Ses dalgaları kullanıcının konuştuğu yerle uyuşmamakta, rastgele tekrarlayan dalgalar halinde görünmektedir.
* **Kök Nedenler:**
  1. **Tarayıcı Bellek ve Boyut Sınırı:** Frontend'deki `loadAudioWaveform` fonksiyonu, `fetch(videoUrl).then(res => res.arrayBuffer())` ile 22.5 dakikalık 500MB+ büyüklüğündeki video dosyasını tarayıcı RAM'ine indirmeye çalışmaktadır. Bu istek bellek aşımı, CORS veya zaman aşımı nedeniyle doğrudan `catch` bloğuna düşmektedir.
  2. **Mock Sinüs Dalgası Fallback'i:** İstek hata verdiğinde kod `generateFallbackWaveform()` metodunu çalıştırmaktadır:
     ```typescript
     const seed = Math.sin(i * 0.8) * Math.cos(i * 0.3);
     const val = 0.35 + Math.abs(seed) * 0.55;
     peaks.push(val);
     ```
     Kullanıcının gördüğü ses dalgası gerçek ses değil, **matematiksel bir sinüs eğrisi mock'udur**. Kullanıcının "bu tamamen sahte" tespiti %100 doğrudur.
* **Kalıcı Çözüm:**
  - Tarayıcıda yüzlerce megabaytlık videoyu indirip çözmek yerine; Python Worker arka planda videoyu analiz ederken (zaten FFmpeg ile 16kHz WAV sesini çıkarmış durumdadır), `scipy/numpy` ile 1 saniyede gerçek RMS ses tepelerini (`peaks: [0.04, 0.65, 0.89...]`, 1000 nokta, ~4KB JSON) hesaplayarak EDL modeline veya API'ye teslim edecektir.
  - Frontend bu 4KB'lık hafif veriyi tek milisaniyede yükleyecek; böylece kullanıcının konuşma nefesi, patlamalı sessiz harfleri ve sessizlikleri **%100 gerçek PCM ses dalgası** olarak kusursuz görünecektir.

---

### Sorun 3: Beyaz Zaman İğnesinin (Playhead) Tutup Sürüklenememesi (Scrubbing)
* **Mevcut Durum:** Oynatma imlecine tıklandığında imleç oraya gidiyor, ancak fareyle basılı tutup sürüklendiğinde gelmiyor.
* **Kök Nedenler:**
  1. Oynatma çizgisi div'ine `class="... pointer-events-none"` verilmiştir. Fare olayları iğnenin üzerinden geçip altındaki katmana gitmekte, iğnenin kendisi tıklama ve sürüklemeleri yakalayamamaktadır.
  2. Zaman çizelgesi üzerinde yalnızca tek tıklama (`click`) dinleyicisi vardır. Fareye basılı tutup sağa sola çekildiğinde (`mousedown -> mousemove -> mouseup`) çalışan bir Timeline Scrubbing dinleyicisi kodlanmamıştır.
* **Kalıcı Çözüm:**
  - Playhead tepe çentiğine (`▼`) ve cetvele `mousedown` dinleyicisi bağlanacak.
  - `isScrubbing = true` olduğunda pencere genelinde `window:mousemove` ile video zamanı anlık olarak güncellenecek (`video.currentTime = targetTime`), böylece kullanıcı iğneyi sürüklerken video monitörü de canlı olarak farenin peşinden akacaktır.

---

### Sorun 4: Zoom Yapıldığında Timeline'ın Sola Dayalı Kalıp Sağa Kaydırılamaması
* **Mevcut Durum:** Timeline yakınlaştırıldığında sağdaki kısımlara fare tekerleğiyle ulaşılamıyor.
* **Kök Nedenler:**
  1. `onTimelineWheel` metodunda yatay kaydırma yalnızca `event.shiftKey === true` iken tetiklenmektedir. Kullanıcı Shift tuşuna basmadan tekerleği çevirdiğinde timeline üzerinde dikey kaydırma çubuğu olmadığı için tarayıcı hiçbir şey yapmamaktadır.
  2. Kapsayıcı konteynerin flex ve overflow CSS yapısı, native scrollbar'ı bazen pencere sınırlarının altına itmektedir.
* **Kalıcı Çözüm:**
  - Timeline üzerinde fare tekerleği çevrildiğinde, ek bir tuşa basılmadığında varsayılan olarak **doğrudan yatay kaydırma (`scrollLeft += event.deltaY * 1.5`)** yapılacaktır.
  - `Ctrl + Tekerlek` kombinasyonu mevcut haliyle Zoom yapmaya devam edecektir.
  - Timeline'da boş alana fare orta tuşuyla veya sürükleyerek serbest pan/scroll yapma desteği eklenecektir.

---

### Sorun 5: "Geri Yükle / İptal Et" Yazısının Klibin Solunda Kayık Çıkması
* **Mevcut Durum:** Kırmızı kesim kutusunun üzerine gelindiğinde "↩ Geri Yükle" yazısı klibin üzerinde değil, soluna taşarak görünmektedir.
* **Kök Nedenler:**
  1. Sorun 1'deki flexbox kümülatif kayması burada da elemanın sınırlarını şaşırtmaktadır.
  2. Kısa süreli (< 1.5 saniye) kesimlerde klip genişliği örneğin 15 piksel olmaktadır. İçerisindeki `absolute inset-0 flex justify-center` elemanı 80 piksellik butonu 15 piksellik kutunun merkezine yerleştirmeye çalışırken buton sol kenardan dışarı fırlamaktadır.
* **Kalıcı Çözüm:**
  - Klipler mutlak koordinatlara (`position: absolute`) alındığında referans kutusu tam yerine oturacaktır.
  - Kısa kliplerde buton genişliği kutu içine sığdırılacak (`w-full text-[8px]`), aşırı dar kliplerde ise metin klibin üstünde hover tooltip olarak düzgünce gösterilecektir.

---

### Sorun 6: Net Video Süresinin Orijinal Süreyle Aynı Yazması
* **Mevcut Durum:** Ekran görüntüsünde 130'dan fazla kesim olmasına rağmen transport barında `Net: 22:35` yazmaktadır.
* **Kök Nedenler:**
  - Kodda `visibleDuration` şöyle yazılmıştır:
    ```typescript
    readonly visibleDuration = computed(() => {
       return this.clips().filter(c => this.isVisible(c)).reduce((sum, c) => sum + c.duration, 0);
    });
    ```
  - Kullanıcı toolbar'daki `[AI Açık] [Retake Açık]` filtrelerini açtığında (kesilen kırmızı blokları görmek istediğinde), `isVisible(clip)` kesilen klipler için de `true` döner.
  - Dolayısıyla `visibleDuration`, kesilen kısımları da toplayarak tam 22:35 üretir.
* **Kalıcı Çözüm:**
  - Net Süre, timeline'daki görünürlük filtrelerinden tamamen bağımsız olmalıdır:
    $$\text{Net Süre} = \text{Toplam Süre} - \sum (\text{Tüm Kesim ve Retake Süreleri})$$
  - Formül: `netDuration = totalDuration - cuts.reduce((sum, c) => sum + (c.end - c.start), 0)`.
  - Böylece 22.5 dakikalık videodan 8 dakika kesildiğinde, ekranda hangi filtre açık olursa olsun net süre daima gerçek render süresi olan `14:35` değerini gösterecektir.

---

### Sorun 7: Inspector Inputlarının Beyaz Zemin Üzerine Beyaz Yazı Olması
* **Mevcut Durum:** Sağ paneldeki metin, başlangıç zamanı, süre ve pozisyon inputlarının içi bembeyazdır; yazılar da beyaz olduğu için hiçbir şey okunmamaktadır.
* **Kök Nedenler:**
  - [tailwind.config.js](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/tailwind.config.js) dosyasında `dark` renk paletinde sadece 500, 600, 700, 800, 900 tanımlıdır; `dark-950` tanımlı DEĞİLDİR.
  - Inputlara verilen `class="bg-dark-950"` sınıfı Tailwind tarafından derlenmediği için tarayıcı kendi varsayılan input stilini devreye sokmakta ve arkaplanı beyaz (`#FFFFFF`) yapmaktadır. `text-white` ile birleşince metinler görünmez olmaktadır.
* **Kalıcı Çözüm:**
  - `tailwind.config.js` dosyasına `950: '#060913'` rengi eklenecektir.
  - Tüm input, textarea ve select alanlarına açıkça `bg-dark-900 border border-slate-700 text-white placeholder-slate-500 focus:bg-dark-800 focus:border-brand-cyan` stilleri uygulanacaktır.

---

### Sorun 8: Çift Altyazı Çıkması ve Altyazıların Timeline Katmanı Olarak Düzenlenememesi
* **Mevcut Durum:**
  1. Video üzerinde YouTube tarzı standart siyah kutulu altyazı sürekli çıkmakta ve butonla kapatılamamaktadır.
  2. Kullanıcı altyazıların CapCut'ta olduğu gibi timeline'da ayrı bir altyazı kanalında şerit olarak görünmesini, tıklandığında Inspector'da metninin ve zamanının düzenlenebilmesini istemektedir.
* **Kök Nedenler:**
  1. **Native HTML5 `<track>`:** Video etiketinde `<track kind="subtitles" [src]="vttTrackUrl()" [default]="showSubtitles()">` kullanılmıştır. Tarayıcı native altyazı motorunu çalıştırarak ekrana standart siyah kutulu altyazı basmaktadır. Aynı anda bizim karaoke overlay katmanımız da çalıştığı için ekranda üst üste iki altyazı belirmektedir.
  2. **Altyazıların EDL Katmanı Olmaması:** Whisper transkripti yalnızca `transcript.segments` olarak saklanmakta; timeline'daki `overlayTrackNumbers` (`T1, T2, T3`) katmanlarına dahil edilmemektedir. Bu yüzden kullanıcı altyazıyı timeline üzerinde görüp seçememektedir.
* **Kalıcı Çözüm:**
  1. Native `<track>` etiketi devre dışı bırakılacak; altyazı kontrolü tek elden bizim karaoke motorumuza devredilecektir.
  2. Timeline'a özel bir **`💬 Altyazı (Subtitles)`** kanalı eklenecektir. Whisper segmentleri bu kanalda altın sarısı/cyan renkli altyazı blokları olarak gösterilecektir.
  3. Kullanıcı altyazı klibine tıkladığında sağ paneldeki Inspector'da altyazı metni açılacak, kullanıcı yazım hatalarını anında klavyeden düzeltebilecek ve zamanını kaydırabilecektir.

---

## 2. Adım Adım Mimari Çözüm Planı

### Aşama 1: Backend & Python Worker Ses Dalgası (Waveform API) Entegrasyonu
1. **[analysis_consumer.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py)** ve **[video_preprocessor.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/video_preprocessor.py)**:
   - Video analiz edilirken çıkartılan 16kHz ses dosyasından `scipy.io.wavfile` veya `pydub` ile 800-1000 noktalık gerçek RMS tepe değerleri dizisi hesaplanacak.
   - Bu veri `edl.audioPeaks = [0.05, 0.45, ...]` olarak EDL JSON nesnesine eklenecek.
2. **[EdlModel.cs](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Edl/EdlDtos.cs)**:
   - C# tarafındaki `EdlContent` modeline `List<double>? AudioPeaks` alanı eklenecek.
   - Böylece tarayıcı 500MB video indirmek yerine 4KB'lık gerçek ses dalgası verisini anında alacak.

### Aşama 2: Frontend Zaman Çizelgesi Mutlak Koordinat Dönüşümü
1. **[editor.component.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts)**:
   - `clips()` şeridi `display: flex` yapısından çıkarılacak; mutlak pozisyonlama (`position: absolute; left: ...%; width: ...%`) ile cetvel ve playhead ile birebir piksel hizalanacak.
   - Kırmızı jump-cut ve sarı retake bloklarının kümülatif kayması tamamen sıfırlanacak.
   - "↩ Geri Yükle" hover butonlarının klip sınırları içine tam ortalanması sağlanacak.

### Aşama 3: Timeline Scrubbing & Tekerlek ile Yatay Kaydırma
1. **Playhead Sürükleme (Scrubbing):**
   - Playhead çentiğine `pointer-events-auto cursor-ew-resize` verilecek.
   - `mousedown -> window:mousemove -> window:mouseup` yaşam döngüsü ile fareyi sağa sola çekerken videonun ve zamanın akıcı şekilde ileri-geri oynaması sağlanacak.
2. **Tekerlek Navigasyonu:**
   - Fare tekerleği boşta çevrildiğinde `scrollLeft += event.deltaY * 1.5` ile timeline doğrudan sağa ve sola kayacak.
   - `Ctrl + Tekerlek` ile zoom in/out devam edecek.

### Aşama 4: Net Süre ve Inspector Tema Onarımı
1. **Net Süre:**
   - Görünürlük filtrelerinden bağımsız `netDuration = totalDuration - totalCutDuration` formülü uygulanacak.
2. **Tailwind & Input Teması:**
   - [tailwind.config.js](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/tailwind.config.js) içine `dark: { 950: '#060913', ... }` rengi eklenecek.
   - Inspector'daki tüm inputlar koyu zemin ve canlı beyaz font ile okunabilir hale getirilecek.

### Aşama 5: Çift Altyazıyı Kaldırma & CapCut Altyazı Kanalı (Subtitle Track)
1. Video elementindeki native `<track>` etiketi kaldırılacak.
2. Timeline'a özel **`💬 Altyazı`** kanalı eklenecek; transkriptteki her cümle tıklanabilir ve Inspector'dan metni düzenlenebilir birer klip haline getirilecek.

---

## 3. Doğrulama ve Test Kriterleri

- [ ] **Klip Hizalaması:** 0. saniyeden 22. dakikaya kadar tüm kırmızı/sarı kesimlerin cetvel ve playhead ile milisaniyesi milisaniyesine örtüştüğü doğrulanacak.
- [ ] **Gerçek Ses Dalgası:** Ses dalgalarının konuşmacının ses tonu ve sessizlikleriyle %100 uyuştuğu teyit edilecek.
- [ ] **Playhead Scrubbing:** Beyaz iğne fareyle basılı tutularak sağa-sola çekildiğinde videonun canlı olarak kare kare aktığı doğrulanacak.
- [ ] **Yatay Kaydırma:** Fare tekerleği çevrildiğinde timeline'ın akıcı şekilde sağa sola kaydığı test edilecek.
- [ ] **Net Süre Doğruluğu:** Filtreler açıkken de net sürenin kesimler düşülmüş haliyle (örn. 14:35) doğru yazdığı görülecek.
- [ ] **Inspector Okunabilirliği:** Inputların koyu zemin üzerine net beyaz yazıyla kusursuz göründüğü onaylanacak.
- [ ] **Altyazı Düzenleme:** Çift altyazının bittiği, altyazı kliplerinin timeline'da görünüp Inspector'dan metninin düzenlenebildiği doğrulanacak.
