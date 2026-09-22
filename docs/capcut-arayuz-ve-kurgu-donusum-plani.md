# CapCut Tarzı Kurgu Arayüzü & Akıllı NLE Dönüşüm Planı

Bu doküman, OtoEdit kurgu deneyimini endüstri standardı **CapCut / Premiere Pro** ergonomisine kavuşturmak için hazırlanmış detaylı teknik uygulama planıdır.

---

## 1. Mevcut Arayüzün Sorunları ve Dönüşümün Amacı

### Mevcut Sorunlar
1. **Dikey Bölünme Kısıtlaması:** Ekran sol (Video + Timeline) ve sağ (Chat/Inspector) olarak ikiye bölünmüştür. 20+ dakikalık bir videoda yatay zaman çizgisini dar bir alanda yönetmek ergonomik değildir.
2. **Toolbar Kalabalığı:** Zaman çizgisinin üstünde 11'den fazla karmaşık buton yan yana yığılmıştır; bu durum görsel karmaşaya yol açmaktadır.
3. **Sahte Dalga Formu (CSS Bars):** Kliplerin altında rastgele CSS yükseklikleri gösterilmektedir; gerçek ses genliğini yansıtmadığı için jump-cut'ların doğru çalışıp çalışmadığı anlaşılamamaktadır.
4. **Kısayol Eksikliği:** CapCut'ın en temel kullanım alışkanlığı olan `Ctrl + Mouse Tekerleği` ile zaman çizgisine odaklı zoom yapma imkânı bulunmamaktadır.

### Dönüşüm Hedefi
CapCut'ın başarısını sağlayan **"3 Üst Panel + 1 Tam Genişlik Alt Timeline" (3+1)** mimarisine geçmek; butonları sağ tık menüsüne taşımak; Web Audio API ile gerçek ses dalgalarını çizmek ve jump-cut doğruluğunu milisaniye tamponlarıyla güvenceye almak.

---

## 2. Arayüz Mimarisi: "3 Üst Panel + 1 Tam Genişlik Alt Timeline"

```
+-------------------------------------------------------------------------------------------------------+
|  [Logo OtoEdit]  |  Proje: 2026-09-15  |  ● Canlı Senkron  |             [ 🚀 Nihai Videoyu Render Et ]|
+------------------------------------+------------------------------------+-----------------------------+
|  1. SOL PANEL (Kütüphane & AI)     |  2. ORTA PANEL (Önizleme Monitörü) |  3. SAĞ PANEL (Özellikler)  |
|  Genişlik: ~28%                    |  Genişlik: ~46%                    |  Genişlik: ~26%             |
|  --------------------------------- |  --------------------------------- |  -------------------------  |
|  Sekmeler:                         |  - 16:9 Video Canvas Önizleme      |  - Bağlamsal Inspector:     |
|  📁 Medya (Varlıklar & Yükleme)    |  - Canlı Altyazı & Metin/Görsel    |    * Seçili Klip Detayı     |
|  🤖 AI Kurgu Asistanı (Sohbet)     |  - Alt Kontroller:                 |    * Metin & Font Ayarları  |
|  📝 Transkript (Kelime/Segmentler) |    * 00:00:12:16 / 00:22:35:00     |    * Katman Kanalı / Sırası |
|  🥞 Katman Listesi                 |    * [⏮] [ ▶ / ⏸ ] [⏭] [🔊] [⛶]    |    * Giriş/Çıkış Animasyonu |
+------------------------------------+------------------------------------+-----------------------------+
|  4. ALT PANEL: TAM GENİŞLİK KURGU TİMELİNE'I (%100 Ekran Genişliği - Yükseklik: ~42vh)                 |
|  [İnce Toolbar: ↖ Seçim | ✂ Böl | 🗑 Sil | ⟲ Geri | ⟳ İleri | 🧲 Mıknatıs | Zoom: - ═══○═══ + ]       |
|  ---------------------------------------------------------------------------------------------------  |
|  [Zaman Cetveli:  00:00        00:05        00:10        00:15        00:20        00:25        00:30] |
|  [T3] Katman 3  |              [ Varsayılan Metin 3 ]                                                 |
|  [T2] Katman 2  |   [ Varsayılan Metin 2 ]                                                            |
|  [T1] Katman 1  |                      [ Varsayılan Metin 1 ]                                         |
|  [V1] Ana Video | [=== Gerçek Ses Dalgası ===] [=== Ses ===]       [======= Gerçek Ses Dalgası =======]|
+-------------------------------------------------------------------------------------------------------+
```

### Değişecek Alanlar:
1. **Sol Panel (Top-Left):** AI Sohbeti artık ekranın sağ yarısını kaplamayacak. Medya yükleme, AI Sohbeti ve Transkript sekmeler halinde bu panelde toplanacak.
2. **Orta Panel (Top-Center):** Video oynatıcı sahnenin odak noktası olacak; altında oynat/duraklat, saniye sayacı ve tam ekran kontrolleri yer alacak.
3. **Sağ Panel (Top-Right):** Yalnızca aktif seçili nesnenin özelliklerini gösteren temiz Inspector alanı olacak.
4. **Alt Panel (Bottom):** Zaman çizelgesi ekranın **sol ucundan sağ ucuna kadar %100 genişlikte** uzanacak. Kullanıcı 20 dakikalık videonun tüm akışını ferahça görecek.

---

## 3. Sağ Tık (Context Menu) Mimarisi ve Buton Temizliği

Toolbar'daki buton kalabalığı kaldırılarak kurgu işlemlerinin %80'i sağ tık menüsüne aktarılacaktır:

### Sağ Tık Menü Yapısı:
1. **Video Klibine Sağ Tık:**
   - ✂ **Buradan Böl (Split - Kısayol: B)**
   - 🔇 **Bu Aralığı Kes (Jump-Cut Yap)**
   - 🔄 **Hatalı Tekrar (Retake) Olarak İşaretle**
   - 🔗 **Seçili Klipleri Birleştir (Merge - Kısayol: M)**
   - 🗑 **Klibi Sil (Kısayol: Del)**
   - ↩ **Kesimi İptal Et / Sahneyi Geri Getir**
2. **Metin / Görsel Katmanına Sağ Tık:**
   - 📋 **Katmanı Çoğalt (Duplicate - Kısayol: Ctrl+D)**
   - 🔼 **Bir Üst Kanala Taşı (Move to Track Above)**
   - 🔽 **Bir Alt Kanala Taşı (Move to Track Below)**
   - 🎨 **Rengi / Stili Hızlı Değiştir**
   - 🗑 **Katmanı Sil (Kısayol: Del)**
3. **Boş Zaman Çizgisine veya Cetvele Sağ Tık:**
   - ➕ **Buraya Metin Ekle**
   - 🖼️ **Buraya Görsel / B-Roll Ekle**
   - 📍 **Buraya İşaretçi (Marker) Bırak**
   - ⏱️ **İmleci Buraya Getir**

### Teknik Uygulama:
- Angular'da `(contextmenu)="$event.preventDefault(); openContextMenu($event, targetType, targetData)"` olayı bağlanır.
- Tıklanan fare koordinatlarına (`clientX, clientY`) göre ekran dışına taşmayan (`overflow-safe`) yarı saydam dark-glass menü açılır.
- Dışarıya tıklandığında veya `Esc` tuşuna basıldığında menü otomatik kapanır (`@HostListener('document:click')`).

---

## 4. Profesyonel Kurgu Kısayolları (Shortcuts)

CapCut ve masaüstü NLE reflekslerini web tarayıcısına getirecek kısayol haritası:

| Kısayol | İşlev | Teknik Detay |
| :--- | :--- | :--- |
| **`Ctrl + Mouse Scroll`** | **İmleç Odaklı Timeline Zoom** | Fare imlecinin altındaki saniye sabit kalacak şekilde zaman çizelgesini genişletir/daraltır. |
| **`Shift + Mouse Scroll`** | **Yatay Kaydırma (Horizontal Pan)** | Zaman çizelgesini yatayda akıcı kaydırır (`scrollLeft += deltaY`). |
| **`Space (Boşluk)`** | **Oynat / Duraklat** | Form input'ları dışındayken videoyu başlatır veya durdurur. |
| **`B` veya `Ctrl + B`** | **Klip Bölme (Split)** | Oynatıcı imlecinin bulunduğu saniyeden klibi ikiye ayırır. |
| **`Del` veya `Backspace`** | **Silme (Delete)** | Seçili klibi veya katmanı kaldırır. |
| **`Ctrl + Z` / `Ctrl + Y`** | **Geri Al / İleri Al** | EDL geçmişinde geri/ileri gider. |
| **`J - K - L`** | **Hızlı Kurgu Taraması (Shuttle)** | `L` ileri hızlandırır (1x, 2x), `K` durdurur, `J` geri sarar. |
| **`M`** | **Birleştir (Merge)** | Seçili ardışık klipleri aradaki kesimleri silerek birleştirir. |

---

## 5. Gerçek Ses Dalga Formu (Web Audio API) & Jump-Cut Doğruluğu

### Neden Şu Anki Gösterge Hata Veriyor ve Kötü Görünüyor?
1. Şu anki görselleştirme **sahte CSS çizgilerinden** ibarettir; gerçek ses frekansını ve genliğini göstermez.
2. Sessizlik algılayıcı (`silence_detector.py`) sabit bir desibel sınırında çalıştığı için mikrofon kazancı düşük olan yerlerde kelimelerin başını veya sonunu kesebilmektedir.
3. Ekranda gerçek ses dalgası olmadığı için kullanıcı kesimin doğru yere mi denk geldiğini görememektedir.

### 1. Web Audio API ile Gerçek Dalga Formu Çizimi
- Videonun ses kanalı tarayıcıda `AudioContext.decodeAudioData()` ile çözümlenir (`ArrayBuffer`).
- Her saniye için 50 adet RMS (Root-Mean-Square) ve Pik genlik verisi hesaplanır (`peaks: Float32Array`).
- Video şeridinin arka planına bir HTML5 `<canvas>` yerleştirilir:
  - **Sesli Konuşma Alanları:** Canlı zümrüt yeşili / turkuaz simetrik tepecikler.
  - **Sessizlik Alanları:** Sıfır çizgisine inen ince karanlık çizgi.
  - **Jump-Cut Kesim Alanları:** Ses dalgasının üstüne binen yarı saydam kırmızı/bordo maske.

### 2. Jump-Cut Kelime Yutma Sorununun Çözümü (Akıllı Tampon Payı)
- Python Worker tarafında (`silence_detector.py` ve `edl_builder.py`):
  - **Pre-Padding (Ön Koruma Payı -80ms):** Konuşma başlamadan önceki 80 milisaniyelik nefes ve harf patlamaları (`P`, `T`, `K`, `S`) kesimden muaf tutulur.
  - **Post-Padding (Arka Koruma Payı +120ms):** Konuşma bittikten sonraki 120 milisaniye korunarak hece sonlarının yutulması engellenir.
  - **Adaptif Gürültü Eşiği (Dynamic Threshold):** Sabit -30dB yerine, videonun arka plan dip ses seviyesi (Noise Floor) tespit edilip gürültü tabanının 6dB üzeri dinamik sınır olarak belirlenir.

---

## 6. Değiştirilecek Bileşenler ve Dosyalar

### Frontend ([OtoEdit.Frontend](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend))
- **[editor.component.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts)**:
  - Template yapısı `3 Üst Panel + 1 Tam Genişlik Alt Timeline` grid sistemine dönüştürülecek.
  - Sağ tık menüsü (`ContextMenuComponent` veya inline directive) eklenecek.
  - `@HostListener('wheel')` ile `Ctrl + Scroll` imleç odaklı zoom ve `Shift + Scroll` yatay kaydırma eklenecek.
  - Web Audio API ile video sesinden canvas üzerine gerçek dalga formu çizici eklenecek.
  - Buton kalabalığı temizlenip CapCut stili minimal timeline toolbar kurulacak.

### Backend & Worker ([OtoEdit.PythonWorker](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker))
- **[silence_detector.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/silence_detector.py)**:
  - Pre-padding (-80ms) ve Post-padding (+120ms) güvenlik marjları eklenecek.
  - Adaptif gürültü eşiği algoritması devreye alınacak.
- **[edl_builder.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py)**:
  - Sessizlik kesimleri birleştirilirken konuşma sınırlarına tecavüz etmeyecek tampon filtreleri işletilecek.

---

## 7. Doğrulama ve Test Planı

1. **Görsel & Ergonomik Doğrulama:**
   - Sayfa açıldığında timeline'ın ekranın %100'ünü kapladığı, video monitörünün ortada, kütüphanenin solda, özelliklerin sağda olduğu doğrulanacak.
   - `Ctrl + Mouse Tekerleği` ile zaman çizgisinin akıcı şekilde büyüyüp küçüldüğü test edilecek.
2. **Sağ Tık Menüsü Testi:**
   - Kliplere, katmanlara ve boş alana sağ tıklandığında doğru menülerin açıldığı ve Böl/Sil/Birleştir işlemlerinin çalıştığı denetlenecek.
3. **Gerçek Ses Dalgası & Jump-Cut Doğrulaması:**
   - Kullanıcının `2026-09-15 10-09-13.mp4` test videosu yüklenerek konuşulan yerlerde yeşil dalgaların yükseldiği, sessizliklerde düştüğü teyit edilecek.
   - Kesilen kırmızı alanların kelimelerin başlangıç veya bitişlerini yutmadığı görsel olarak incelenecek.
4. **Birim Testler:**
   - .NET unit testleri (`dotnet test`) ve Python Worker testleri (`pytest`) çalıştırılarak %100 yeşil olduğu doğrulanacak.
