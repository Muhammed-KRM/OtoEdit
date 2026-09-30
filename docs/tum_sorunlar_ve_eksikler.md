# 📋 OtoEdit — Tüm Sorunlar, Eksikler ve Geliştirme Yol Haritası

> **Tarih:** 30 Eylül 2026  
> **Konum:** `docs/tum_sorunlar_ve_eksikler.md`  
> **Amaç:** OtoEdit'in mevcut durumundaki tüm hataları, eksik özellikleri ve yarım kalmış işlevleri tek bir yerde toplayarak geliştirme önceliklerini belirlemek.

---

## Bölüm A: Aktif Hatalar (Buglar)

Uygulamanın şu an çalışan kısımlarında tespit edilen ve düzeltilmesi gereken hatalar.

---

### A1. Altyazılar ~1 Saniye Erken Görünüyor
- **Konum:** Render motoru (video_renderer.py + timeline_mapper.py)
- **Belirti:** Render edilen nihai videoda altyazılar konuşmacının ağzından kelime çıkmadan yaklaşık 1-2 kelime (0.5-1.5 saniye) önce ekranda görünüyor.
- **Kök Neden:** FFmpeg segment kesimlerinde `-ss` input seeking kullanıldığında keyframe'e snap etme davranışının yarattığı PTS (Presentation Timestamp) kayması. Bu kayma segment birleştirmesi sonrasında altyazı zamanlarıyla video kareleri arasında ufak bir desenkronizasyona neden oluyor.
- **Çözüm Planı:** [Kritik 3 Sorun Çözüm Planı — Sorun 1](file:///d:/OtoEdit/OtoEdit/docs/kritik_3_sorun_cozum_plani.md)
- **Öncelik:** 🔴 Yüksek

---

### A2. Metin Overlay'lerin Fontu Editördekinden Farklı
- **Konum:** text_overlay.py (backend) + editor.component.ts (frontend)
- **Belirti:** Editörde yazı kaplamaları belirli bir fontta (örn: Inter) görünürken, render edilmiş videoda farklı bir font (sistem varsayılanı) kullanılıyor.
- **Kök Neden:**
  1. Frontend varsayılan fontu `Inter`, backend varsayılan fontu `Montserrat-Bold` — uyumsuzluk var.
  2. Docker konteynerinde (render ortamında) özel fontlar (Inter, Montserrat, Poppins vb.) yüklü değil. FFmpeg/libass istenen fontu bulamadığında varsayılan sistem fontuna (DejaVu Sans veya benzeri) düşüyor.
- **Çözüm Planı:** [Kritik 3 Sorun Çözüm Planı — Sorun 2](file:///d:/OtoEdit/OtoEdit/docs/kritik_3_sorun_cozum_plani.md)
- **Öncelik:** 🟡 Orta

---

### A3. Görsel (Image) Overlay'ler Render Edilen Videoda Hiç Yok
- **Konum:** video_renderer.py
- **Belirti:** Editörde kullanıcının eklediği görseller (logolar, sticker'lar, B-Roll görseller) timeline'da ve önizlemede görünüyor, ancak render edilen nihai videoda hiç yok.
- **Kök Neden:** `ImageOverlay` sınıfı import edilip instance oluşturulmuş (`self.image_overlay`) ancak `render()` metodu içinde `apply_image_overlays()` fonksiyonu **hiçbir yerde çağrılmıyor**. Ayrıca `ImageOverlay` sınıfı `ffmpeg-python` kütüphanesi ile çalışırken, render motoru subprocess tabanlı FFmpeg CLI kullanıyor — bu mimari uyumsuzluk nedeniyle doğrudan entegrasyon mümkün değil.
- **Çözüm Planı:** [Kritik 3 Sorun Çözüm Planı — Sorun 3](file:///d:/OtoEdit/OtoEdit/docs/kritik_3_sorun_cozum_plani.md)
- **Öncelik:** 🔴 En Yüksek (Temel özellik tamamen çalışmıyor)

---

### A4. OtoCut Nadiren Erken Kesiyor
- **Konum:** Sessizlik algılama modülü (silence_detector.py / pipeline)
- **Belirti:** OtoCut sessizlik algılama genel olarak iyi çalışıyor, ancak bazı durumlarda ses çok alçaldığında (fısıldama, düşük tonlu konuşma) sistemi sessizlik olarak algılayıp konuşmayı biraz erken kesiyor. Konuşmacının son hecesi veya son kelimesi bazen budanıyor.
- **Kök Neden:** Sessizlik eşik değeri (threshold) sabit veya çok katı ayarlanmış olabilir. Ses seviyesi aşırı düşük olmadığı sürece (yumuşak konuşma, alçalan ton) bu bölgeleri ses olarak kabul edip kesim noktasını en son mümkün noktaya (konuşmanın tam bitişine) taşıması gerekiyor.
- **Olası Çözüm:** Sessizlik algılama eşik değerine dinamik bir tolerans marjı eklemek. Ses seviyesi düşük olsa bile belirli bir minimumun üzerindeyse "sessizlik" yerine "ses" olarak kabul edip kesimi birkaç yüz milisaniye geç yapmak (trailing buffer / padding).
- **Öncelik:** 🟡 Orta

---

### A5. Retake (Hatalı Tekrar) Algılama Sonucu Doğrudan Kullanılabilir Değil
- **Konum:** Retake detector modülü (retake_detector.py / pipeline)
- **Belirti:** Retake algılama mekanizması çalışıyor ve hatalı tekrarları buluyor, ancak sonuç doğrudan kullanılabilir, temiz bir video üretmiyor. Bazen anlamsız kesimler, kendini tekrar eden cümleler veya bağlam kopuklukları kalıyor.
- **Kök Neden:** Retake algılama sonrasında kesilen parçaların ardından kalan transkriptin anlamlılığının kontrol edilmemesi. Sistem "retake buldum, kestim" diyor ama "kalan metin tutarlı mı?" sorusunu sormadan bırakıyor.
- **Olası Çözüm:** Tüm kesim ve retake işlemleri bittikten sonra yapay zekanın (Gemini) kalan transkripti gözden geçirip anlamlı bir bütün oluşturup oluşturmadığını kontrol etmesi. Tekrar eden cümleler, saçma kesimler veya bağlam kopuklukları varsa bunları düzeltmesi gerekiyor.
- **Öncelik:** 🟡 Orta

---

### A6. Katman Ekleme/Silme Seçimi Yapılamıyor
- **Konum:** Editor frontend (editor.component.ts)
- **Belirti:** Editörde "Katman Ekle" ve "Katman Sil" butonları mevcut, ancak kullanıcı hangi katmanı silmek istediğini seçemiyor. Silme işlemi her zaman en son katmanı siliyor. Araya eklenmiş bir katmanı (örn: Katman #2) silmek mümkün değil.
- **Kök Neden:** Katman silme mantığı, belirli bir katman ID'si veya indeksini parametre olarak almak yerine, her zaman listenin son elemanını siliyor.
- **Olası Çözüm:** Silme fonksiyonuna aktif seçili katmanın ID'sini geçirmek. Kullanıcı bir katmana tıklayarak veya sağ tık menüsünden "Bu katmanı sil" seçerek belirli bir katmanı hedefleyebilmeli.
- **Öncelik:** 🟢 Düşük-Orta

---

## Bölüm B: Eksik Özellikler (Henüz Geliştirilmemiş)

Uygulamada bulunmayan ancak olması gereken ve kullanıcı deneyimini önemli ölçüde artıracak özellikler.

---

### B1. Görsel Otomatik Arkaplan Kaldırma
- **Açıklama:** Kullanıcı bir görsel eklediğinde (logo, sticker, ürün fotoğrafı vb.) arka planının otomatik olarak kaldırılıp sadece nesnenin/logonun şeffaf olarak videoya eklenmesi.
- **Mevcut Durum:** Hiçbir arkaplan kaldırma işlevi yok.
- **Olası Çözüm:** `rembg` kütüphanesi veya benzeri bir AI tabanlı arkaplan kaldırma aracı entegre edilebilir. Görsel overlay eklenmeden önce opsiyonel olarak çalıştırılabilir.
- **Öncelik:** 🟡 Orta

---

### B2. Renk Ayarları (Color Grading)
- **Açıklama:** Videonun parlaklık, kontrast, doygunluk, sıcaklık (warm/cool) gibi temel renk parametrelerini ayarlama.
- **Mevcut Durum:** Hiçbir renk ayar aracı yok.
- **Olası Çözüm:** FFmpeg'in `eq` (brightness, contrast, saturation, gamma) ve `colorbalance` (renk dengesi) filtrelerini kullanarak basit bir renk ayar paneli eklenebilir.
- **Öncelik:** 🟢 Düşük

---

### B3. Gelişmiş Yazı Editörü
- **Açıklama:** Mevcut yazı ekleme aracı temel düzeyde çalışıyor ancak daha ayrıntılı ve gelişmiş ayar yapılabilmesi gerekiyor. Şu an font, boyut, renk, animasyon var ama daha fazlası lazım.
- **Eksik Olan Ayarlar:**
  - Yazı gölgesi (shadow) açma/kapama ve gölge rengi/mesafesi ayarı
  - Yazı kenarlık (outline/border) kalınlığı ve rengi
  - Harfler arası boşluk (letter spacing)
  - Satır yüksekliği (line height)
  - Yazı arka plan kutusu (text box/banner) şekli ve yuvarlaklığı
  - Birden fazla satır/paragraf desteği
  - Yazı dönüşümü (rotation/eğim)
  - Ek font seçenekleri (Google Fonts kütüphanesi entegrasyonu)
  - Yazı şeffaflığı (opacity) ayarı
- **Mevcut Durum:** Temel font, boyut, renk ve animasyon ayarları çalışıyor.
- **Öncelik:** 🟡 Orta

---

### B4. Gelişmiş Altyazı Özelleştirme
- **Açıklama:** Whisper'dan gelen otomatik altyazıların görünümünü detaylı olarak özelleştirebilme.
- **Eksik Olan Ayarlar:**
  - Altyazı fontu seçimi
  - Altyazı font boyutu ayarı
  - Altyazı rengi (birincil, ikincil, karaoke vurgu rengi)
  - Altyazı konum ayarı (alt, üst, orta, serbest konum)
  - Altyazı arka plan stili (kutu, yarı saydam bant, gölge)
  - Altyazı kenarlık kalınlığı
  - Altyazı animasyon stili (karaoke, kelime kelime belirme, satır satır belirme)
  - Altyazı gösterim süresi ayarı (minimum/maksimum kelime başına süre)
- **Mevcut Durum:** Altyazılar sabit stil (`Subtitle` style) ile ASS dosyasına yazılıyor, kullanıcı tarafından özelleştirilemiyor.
- **Öncelik:** 🟡 Orta

---

### B5. Ses Ayarları ve Kontrolleri
- **Açıklama:** Videonun ses kısmı üzerinde kullanıcının kontrol sahibi olması.
- **Eksik Olan Özellikler:**
  - Genel ses seviyesi (volume) ayarı
  - Orijinal (iyileştirilmemiş) sesi dinleme/karşılaştırma seçeneği
  - Belirli zaman aralıklarında ses seviyesini artırma/azaltma
  - Fade in / fade out ses geçişleri
  - Arka plan müziği ekleme ve ses seviyesi ayarı
  - Ses ekolayzer (EQ) ayarları
  - Gürültü azaltma seviyesi kontrolü
- **Mevcut Durum:** Otomatik ses iyileştirme var ancak manuel ses ayarı, orijinal sesi dinleme veya ses seviyesi kontrolü yok.
- **Öncelik:** 🟡 Orta

---

### B6. Hız Kontrolü (Speed Ramp)
- **Açıklama:** Videonun belirli bölümlerini hızlandırma veya yavaşlatma.
- **Eksik Olan Özellikler:**
  - Seçili zaman aralığını 1.5x, 2x, 3x hızlandırma
  - Seçili zaman aralığını 0.5x, 0.25x yavaşlatma
  - Yumuşak hız geçişleri (speed ramp)
  - Hızlandırılan kısımlarda sesin pitch düzeltmesi (chipmunk sesi olmaması)
- **Mevcut Durum:** Hiçbir hız kontrol özelliği yok.
- **Öncelik:** 🟡 Orta

---

### B7. Katman Kontrolü (Mute, Hide, Lock)
- **Açıklama:** Her bir timeline katmanı üzerinde CapCut benzeri kontroller.
- **Eksik Olan Özellikler:**
  - Katmanın sesini kapatma (mute)
  - Katmanın görüntüsünü gizleme (hide/visibility toggle)
  - Katmanı kilitleme (lock — yanlışlıkla düzenlemeyi önleme)
  - Katmanı solo modda izleme (sadece o katmanın oynatılması)
  - Belirli bir katmanı seçerek silme (şu an sadece en son katman silinebiliyor — Bug A6)
- **Mevcut Durum:** Katman ekleme ve son katmanı silme dışında hiçbir katman kontrolü yok.
- **Öncelik:** 🟢 Düşük-Orta

---

## Bölüm C: Yarım Kalmış / Yarı Çalışan Özellikler

Tasarlanmış ve kısmen geliştirilmiş ancak tam olarak çalışır hale getirilmemiş özellikler.

---

### C1. OtoEdit — Yapay Zeka Otomatik Düzenleme
- **Açıklama:** OtoEdit'in ana vizyonu: Yapay zekanın videoyu izleyip nerelere ne tür edit yapılabileceğini (yazı ekleme, görsel koyma, kesim, efekt) belirleyip kullanıcıya önermesi. Kullanıcı onaylarsa uygulaması, reddederse revize edip yeni öneri sunması.
- **Mevcut Durum:** AI chat sistemi ve öneri mekanizması kısmen var ancak tam bir otomasyon döngüsü çalışmıyor. AI'ın önerilerini otomatik uygulaması (yazı koyma, görsel ekleme) tam entegre değil.
- **Tam Çalışması İçin Gerekenler:**
  1. AI videoyu analiz ederek "Şuraya şu yazıyı koy, şuraya şu görseli ekle" şeklinde yapılandırılmış öneriler üretmeli.
  2. Kullanıcıya öneriler gösterilmeli (preview).
  3. Kullanıcı onaylarsa EDL'e otomatik uygulanmalı.
  4. Kullanıcı reddederse AI neden reddedildiğini anlayıp revize edilmiş yeni öneri sunmalı.
  5. Görseller için: Kullanıcı görsel vermediyse AI internette arama yapıp en alakalı görseli bulmalı, birkaç alternatif kontrol etmeli ve en uygun olanı seçmeli.
  6. Seçilen görsele gerekirse arkaplan kaldırma, renk düzenleme gibi işlemler uygulamalı.
  7. Görseli ve yazıyı doğru saniyelere, doğru konuma ve doğru animasyonla yerleştirmeli.
- **Öncelik:** 🔴 Yüksek (Ana vizyon özelliği)

---

### C2. AI Transkript Doğrulama (Post-Processing)
- **Açıklama:** Tüm kesim, retake silme ve montaj işlemleri bittikten sonra yapay zekanın kalan transkripti gözden geçirmesi.
- **Mevcut Durum:** Retake algılama ve sessizlik kesimi çalışıyor, ancak sonuç transkriptinin anlamlılık kontrolü yapılmıyor.
- **Tam Çalışması İçin Gerekenler:**
  1. Tüm kesimler uygulandıktan sonra kalan transkript bir bütün olarak AI'a gönderilmeli.
  2. AI metnin anlamlı bir bütün oluşturup oluşturmadığını kontrol etmeli.
  3. Kendini tekrarlayan cümleler, yarım kalan ifadeler, bağlam kopuklukları veya saçma kesimler varsa tespit etmeli.
  4. Sorun bulursa ilgili kesim noktalarını düzeltmeli veya kullanıcıya uyarı göstermeli.
- **Öncelik:** 🟡 Orta

---

## Özet Tablo — Tüm Sorunlar ve Öncelikler

| # | Kategori | Sorun / Eksiklik | Öncelik |
|---|---|---|---|
| A1 | 🐛 Bug | Altyazılar ~1 sn erken görünüyor | 🔴 Yüksek |
| A2 | 🐛 Bug | Metin overlay fontu editördekinden farklı | 🟡 Orta |
| A3 | 🐛 Bug | Görsel overlay'ler render edilen videoda yok | 🔴 En Yüksek |
| A4 | 🐛 Bug | OtoCut nadiren konuşmayı erken kesiyor | 🟡 Orta |
| A5 | 🐛 Bug | Retake sonucu doğrudan kullanılabilir video çıkmıyor | 🟡 Orta |
| A6 | 🐛 Bug | Katman silme seçimi yapılamıyor (hep son katman) | 🟢 Düşük-Orta |
| B1 | ⭐ Eksik | Görsel otomatik arkaplan kaldırma | 🟡 Orta |
| B2 | ⭐ Eksik | Renk ayarları (color grading) | 🟢 Düşük |
| B3 | ⭐ Eksik | Gelişmiş yazı editörü (gölge, border, spacing vb.) | 🟡 Orta |
| B4 | ⭐ Eksik | Gelişmiş altyazı özelleştirme (font, renk, konum) | 🟡 Orta |
| B5 | ⭐ Eksik | Ses ayarları ve kontrolleri | 🟡 Orta |
| B6 | ⭐ Eksik | Hız kontrolü (speed ramp) | 🟡 Orta |
| B7 | ⭐ Eksik | Katman kontrolü (mute, hide, lock) | 🟢 Düşük-Orta |
| C1 | 🔧 Yarım | OtoEdit AI otomatik düzenleme tam çalışmıyor | 🔴 Yüksek |
| C2 | 🔧 Yarım | AI transkript doğrulama (post-processing) | 🟡 Orta |

---

## Hemen Çözülmesi Gerekenler (İlk 3)

1. **A3 — Görsel Overlay Render Entegrasyonu** → Kullanıcının eklediği görseller videoda hiç görünmüyor.
2. **A1 — Altyazı Zamanlama Düzeltmesi** → Altyazılar konuşmadan ~1 sn önce çıkıyor.
3. **A2 — Font Uyumsuzluğu Giderme** → Yazılar editörde başka, videoda başka font ile çıkıyor.

Bu üç sorunun detaylı teşhis ve çözüm planı: [`docs/kritik_3_sorun_cozum_plani.md`](file:///d:/OtoEdit/OtoEdit/docs/kritik_3_sorun_cozum_plani.md)
