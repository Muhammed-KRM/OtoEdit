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

### A4. OtoCut Nadiren Erken Kesiyor — ✅ ÇÖZÜLDÜ (13 Ekim 2026)
- **Konum:** Sessizlik algılama modülü (`pipeline/silence_detector.py`, `pipeline/audio_analysis.py`)
- **Belirti:** OtoCut sessizlik algılama konuşmanın son hecesini veya düşük tondaki kelimeleri erken kesiyordu.
- **Kök Neden:** Sabit dBFS pydub eşiği konuşmacının fısıltı ve ton düşüşlerini sessizlik sanıyordu.
- **Uygulanan Çözüm (Jump-Cut v2):**
  1. **Silero VAD:** Tek kaynak `AudioAnalyzer` ile konuşma bölgeleri tespit edilir.
  2. **Kelime Koruması (Word Guard):** Transkript kelimeleri `±150ms` koruma kalkanıyla korunur; hiçbir kesim kelimeye değemez.
  3. **Güvenlik Payı (Padding):** Konuşma sınırlarından içeri `200ms` çekilir.
  4. **Kenar İnce Ayarı:** Kesim kenarları lokal RMS minimumuna oturtularak tık/patlama sesleri yok edilir.
  5. **Ada Birleştirme:** 300ms'den kısa yetim konuşma adaları birleştirilerek mikro-klip sayısı 0'a indirildi.
- **Detaylı Rehber:** [Çözüm Rehberi — Transkript Motoru ve Oto Jump-Cut](file:///d:/OtoEdit/OtoEdit/docs/cozum_rehberi_transkript_ve_jumpcut.md)
- **Durum:** ✅ Tamamen Çözüldü ve Test Edildi (74 test passed, 0 micro-clips).

---

### A5. Retake (Hatalı Tekrar) Algılama Sonucu Doğrudan Kullanılabilir Değil
- **Konum:** Retake detector modülü (`pipeline/retake_detector.py`, `pipeline/transcript_verifier.py`)
- **Belirti:** Retake algılama mekanizması çalışıyor ve hatalı tekrarları buluyordu, ancak farklı kelimelerle yapılan takılmalar (semantic retake) ve askıda kalan yetim bağlaçlar ("Ve burada aslında...") temizlenemiyordu.
- **Kök Neden:** Transkript üzerinde anlamsal (LLM) bütünlük denetimi olmaması ve sadece lokal kelime benzerliğine bakılması.
- **Uygulanan Çözüm:** Gemini 3.8 Flash kurgu denetçisi (`TranscriptVerifier`) geliştirildi. Yarım kalan cümleler, anlamsal tekrarlar ve stüdyo outtake'leri tespit edilip kelime sınırlarına ve lokal RMS dip noktalarına oturtularak temiz kesimler üretildi.
- **Durum:** ✅ **Çözüldü ve Test Edildi** (86 test geçti).

---

### A6. Katman Ekleme/Silme Seçimi Yapılamıyor
- **Konum:** Editor frontend (`editor.component.ts`)
- **Belirti:** Editörde "Katman Ekle" ve "Katman Sil" butonları mevcuttu, ancak kullanıcı hangi katmanı silmek istediğini seçemiyordu; her zaman en son katman siliniyordu.
- **Kök Neden:** Katman silme mantığının parametre almayıp sadece `customTrackCount - 1` yapması.
- **Uygulanan Çözüm:** Her katman başlığına özel hedefli silme butonu (`deleteTrackLane(trackNum)`), gizleme (`👁️`) ve kilitleme (`🔒`) kontrolleri eklendi. Silinen katmandaki öğeler kaldırılıp üst katman indeksleri otomatik olarak aşağı kaydırıldı ve backend senkronizasyonu sağlandı.
- **Durum:** ✅ **Çözüldü ve Test Edildi** (Production build başarılı).

---

### A7. Ses Başlangıcı (Lead-in) Kesilmesi ve STT Kotası Kaynaklı Transkript Çökmesi
- **Konum:** `pipeline/audio_analysis.py`, `pipeline/silence_detector.py`, `pipeline/stt/rate_limiter.py`, `pipeline/stt/gemini_transcribe.py`, `pipeline/transcriber.py`
- **Belirti:** Konuşma başlangıçlarındaki ilk heceler/harfler kırmızı kesim alanı içine taşıyordu (kesimden konuşmaya sadece 86ms kalıyordu). Uzun videolarda STT ikinci parçada 429 kotasına çarpınca tüm transkript çöpe atılıp ekrana `[TRANSKRİPT ÇIKARILAMADI]` basılıyordu.
- **Kök Neden:**
  1. Silero VAD'de `speech_pad_ms=0` olması sebebiyle yumuşak ünsüzlerin ve nefesin 150ms geç algılanması.
  2. Jump-Cut v2 simetrik padding'inin konuşma başlangıcında yetersiz kalması.
  3. STT hız sınırlayıcısının `max_wait_sec=45s` olması (Google'ın 50s soğuma süresini beklememesi).
  4. `transcriber.py` içinde parça bazlı hata izolasyonu olmaması (tek parça hatasında tüm kelimelerin silinmesi).
- **Uygulanan Çözüm:**
  1. `speech_pad_ms=150` yapılarak ünsüzler erken yakalandı.
  2. Asimetrik padding getirildi: Konuşma öncesi `pad_lead_sec=0.35` (350ms pay), konuşma sonrası `pad_trailing_sec=0.20` (200ms pay). Kalan güvenlik payı 86ms'den **386ms'ye** çıkarıldı.
  3. Snapping (`find_energy_minimum`) tek yönlü hale getirilerek kesim kenarlarının konuşma içine kayması engellendi.
  4. `GeminiKeyRotator` maksimum bekleme süresi 180s'ye çıkarıldı; `gemini_transcribe` içine 429 retry eklendi.
  5. `transcriber.py` parça bazlı izole edildi; bir parça hata alsa dahi önceki parçaların kelimeleri korunur.
- **Detaylı Rapor:** [Teşhis ve Kesin Çözüm Raporu](file:///d:/OtoEdit/OtoEdit/docs/teshis_ve_kesin_cozum_ses_kesilmesi_ve_transkript.md)
- **Durum:** ✅ **Çözüldü ve Test Edildi** (90 test geçti).

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

| # | Kategori | Sorun / Eksiklik | Öncelik | Durum (13 Ekim 2026) |
|---|---|---|---|---|
| A1 | 🐛 Bug | Altyazılar ~1 sn erken görünüyor | 🔴 Yüksek | ✅ **Çözüldü** (Frame-accurate seek + remapping) |
| A2 | 🐛 Bug | Metin overlay fontu editördekinden farklı | 🟡 Orta | ✅ **Çözüldü** (Google fontları yüklendi, 4/3 DPI kalibrasyonu yapıldı) |
| A3 | 🐛 Bug | Görsel overlay'ler render edilen videoda yok | 🔴 En Yüksek | ✅ **Çözüldü** (2-pass filter_complex ile render'a eklendi) |
| A4 | 🐛 Bug | OtoCut konuşmayı erken kesiyor (fısıltı/hece) | 🔴 Acil | ✅ **Çözüldü** (Silero VAD + Jump-Cut v2 + 150ms Word Guard) |
| A5 | 🐛 Bug | Retake sonucu doğrudan kullanılabilir video çıkmıyor | 🟡 Orta | ✅ **Çözüldü** (Gemini 3.8 Flash kurgu denetçisi + RMS dip hizalaması) |
| A6 | 🐛 Bug | Katman silme seçimi yapılamıyor (hep son katman) | 🟢 Düşük-Orta | ✅ **Çözüldü** (Hedefli katman silme `deleteTrackLane`) |
| B1 | ⭐ Eksik | Görsel otomatik arkaplan kaldırma | 🟡 Orta | ⏳ Beklemede |
| B2 | ⭐ Eksik | Renk ayarları (color grading) | 🟢 Düşük | ⏳ Beklemede |
| B3 | ⭐ Eksik | Gelişmiş yazı editörü (gölge, border, spacing vb.) | 🟡 Orta | ⚠️ Kısmen yapıldı (Gölge ve font boyutu tamamlandı) |
| B4 | ⭐ Eksik | Gelişmiş altyazı özelleştirme (font, renk, konum) | 🟡 Orta | ⚠️ Kısmen yapıldı (TikTok sarı stil & gizleme toggle tamamlandı) |
| B5 | ⭐ Eksik | Ses ayarları ve kontrolleri | 🟡 Orta | ⏳ Beklemede |
| B6 | ⭐ Eksik | Hız kontrolü (speed ramp) | 🟡 Orta | ⏳ Beklemede |
| B7 | ⭐ Eksik | Katman kontrolü (mute, hide, lock) | 🟢 Düşük-Orta | ✅ **Çözüldü** (Göz 👁️, Kilit 🔒, Sil ✕ kontrolleri tamamlandı) |
| C1 | 🔧 Yarım | OtoEdit AI otomatik düzenleme tam çalışmıyor | 🔴 Yüksek | ⏳ Beklemede (Pexels 401 hatası ve AI döngüsü) |
| C2 | 🔧 Yarım | AI transkript doğrulama (post-processing) | 🟡 Orta | ✅ **Çözüldü** (`TranscriptVerifier` ile post-cut denetimi aktif) |


---

## Güncel Öncelikler (13 Ekim 2026 İtibarıyla)

1. **A4 — Sessizlik Kesimi (Jump-Cut) İyileştirmesi:** Konuşmacının hecelerini ve fısıltılarını kesmemesi için `-50 dBFS`, `800ms min_silence` ve `250ms padding` parametrelerinin Python Worker'a işlenmesi ve servisin yeniden başlatılması.
2. **Pexels API 401 Hatası Giderme:** `.env` dosyasındaki geçersiz Pexels API anahtarının güncellenmesi.
3. **A5 & C2 — Retake ve Transkript Bütünlüğü:** Gemini tabanlı kurgu denetiminin devreye alınması.

Detaylı konsol incelemesi ve dalga formu görsel analizi için bakınız: [`docs/guncel_durum_ve_kalan_sorunlar_raporu.md`](file:///d:/OtoEdit/OtoEdit/docs/guncel_durum_ve_kalan_sorunlar_raporu.md)
