# 📋 OtoEdit — Eksikler, Kalan Sorunlar ve Geliştirme Yol Haritası Dökümanı

> **Tarih:** 15 Ekim 2026  
> **Konum:** `docs/eksikler_ve_kalan_sorunlar_dokumani.md`  
> **Hazırlayan:** Antigravity AI — OtoEdit Çekirdek Mimari Ekibi  
> **Durum:** Güncel Eksikler ve Sistem Teşhisi  

---

## 📌 Yönetici Özeti (Executive Summary)

OtoEdit projesinde **Jump-Cut (v2/v3)**, **Silero VAD**, **Word Guard**, **Milisaniye Bazlı Toplu Kesim Payı (Trim)**, **Retake (Hatalı Tekrar) Algılama & Geri Alma**, **Çok Kanallı Katman Yönetimi (Gizle / Kilitle / Sil)** ve **EDL Render Motoru** başarıyla devreye alınmış ve stabil hale getirilmiştir.

Ancak projenin **"CapCut kalitesinde yapay zeka destekli otonom video kurgu stüdyosu"** vizyonuna ulaşabilmesi için çözülmesi gereken temel eksikler, yarım kalan entegrasyonlar ve kullanıcı deneyimini doğrudan etkileyen unsurlar bu dökümanda ayrıntılı olarak raporlanmıştır.

---

## 🔍 Bölüm 1: Yapay Zeka Kurgu Asistanı (AI Chat & Director) Eksikleri

### 1.1. Zaman Aralığı ile Yazı Ekleme Komutunun Timeline'a Düşmemesi
* **Mevcut Sorun:** Kullanıcı `[Seçili Aralık: 1026.5s - 1033.9s] imam gazali yazılacak buraya` dediğinde yapay zeka "ayarlar hazırlandı" yanıtı veriyor ancak video ve timeline üzerine katman yerleşmiyordu.
* **Kök Neden:** Sistemin niyet (intent) motoru, bu komutu `clarification` (ek form doldurma) olarak sınıflandırıyordu. Kullanıcıdan font/renk seçmesi bekleniyor fakat form arayüzde görünmediği veya tıklandığında EDL'e doğrudan patch atılmadığı için işlem askıda kalıyordu.
* **Uygulanan & Gereken Çözüm:** Kullanıcı zaman aralığı ve metin belirttiğinde intent doğrudan `command` olmalı; arka planda `pendingEdlPatch` üretilerek sohbette **"🔍 Önizle"** ve **"Onayla"** butonları çıkmalı. Onay verildiğinde katman anında T1/T2/T3 kanallarına ve video oynatıcısına eklenmelidir.

### 1.2. Transkript İçi Soru Cevaplama ve İçerik Arama Arızası
* **Mevcut Sorun:** Kullanıcı `tüm videoda kaçıncı saniyede bediüzzamandan bahsettin` gibi videonun içeriğine dair soru sorduğunda, yapay zeka metni bulamayıp jenerik *"Komutunuz incelendi..."* mesajı dönüyordu.
* **Kök Neden:** Arka planda `ChatManager.cs`, transkripti veritabanındaki `video_transcripts` tablosundan çekmeye çalışıyordu. Oysa STT çıktısı doğrudan `edit_decision_lists` tablosunun `edl_json->transcript` alanı içerisine kaydediliyordu. Bu nedenle `VideoTranscripts` tablosu boş (`0 satır`) kalıyor ve LLM'e `[TRANSKRİPT BULUNAMADI]` metni gidiyordu.
* **Uygulanan & Gereken Çözüm:** `ChatManager.cs` içine EDL JSON'daki transkript segmentlerini saniye ve dakika damgalarıyla (`[33:32 (2012.6s)] ...`) okuyan köprü eklendi. Böylece kullanıcı herhangi bir kelime veya konuyu sorduğunda transkript taranarak kesin saniye bilgisi verilebilir hale getirildi.

### 1.3. Otonom Video Yönetmeni (Proaktif AI) Eksikliği
* **Eksiklik:** Şu anda yapay zeka sadece kullanıcı ona komut yazdığında yanıt veriyor. Oysa OtoEdit'in ana vaadi: **"Videoyu yükle, yapay zeka baştan sona izlesin; önemli yerlere başlık atsın, B-Roll stok görsel önersin, vurgulu yerleri öne çıkarsın."**
* **Gereken Geliştirme:** Video yüklendiğinde arka planda çalışan bir `VideoDirectorService` olmalı; transkripti baştan sona analiz edip 3-5 adet zengin öneri (`suggestions`) üretmeli (örn: "Girişte başlık", "5. dakikada konu başlığı", "12. dakikada ilgili kavram görseli") ve editörün öneriler sekmesinde kullanıcı onayına sunmalıdır.

---

## 🎨 Bölüm 2: Zaman Çizelgesi (Timeline) ve Video Kanvası Eksikleri

### 2.1. Kanvas Üzerinde Doğrudan Serbest Düzenleme (Interactive Bounding Box)
* **Eksiklik:** Editör ekranındaki video oynatıcı üzerinde eklenen yazılar ve görseller statik olarak duruyor. Kullanıcı mouse ile yazıyı tutup istediği yere sürükleyemiyor, köşelerinden tutup boyutlandıramıyor veya döndüremiyor (rotation handle).
* **Etki:** Kullanıcı konumu değiştirmek için sağdaki veya soldaki konum yüzdeleriyle (X: %50, Y: %85) uğraşmak zorunda kalıyor.
* **Çözüm:** Video oynatıcı üzerine bir HTML5 Canvas veya şeffaf interaktif SVG/Div katmanı bindirilerek CapCut benzeri 8 noktalı tutamaç (bounding box) eklenmelidir.

### 2.2. Manyetik Timeline ve Akıllı Boşluk Kapatma (Ripple Edit)
* **Eksiklik:** Zaman çizelgesinde bir klip silindiğinde veya kısaltıldığında arkadaki kliplerin otomatik olarak öne kayıp boşluğu kapatması (Magnetic Ripple) tam otomatik çalışmıyor.
* **Etki:** Manuel kesim yapan kullanıcı, kestiği her sahneden sonra arkadaki klipleri eliyle sola yanaştırmak zorunda kalabiliyor.

### 2.3. Çoklu Klip Seçimi (Multi-Select) ve Toplu İşlemler
* **Eksiklik:** `Ctrl` veya `Shift` tuşuna basılı tutarak birden fazla klibi veya katmanı seçip topluca silme, taşıma veya toplu süre uzatma özelliği henüz bulunmuyor.

---

## 🖼️ Bölüm 3: Medya, B-Roll ve Stok Görsel İşleme Eksikleri

### 3.1. Pexels API Anahtarı ve Otomatik B-Roll İndirme
* **Mevcut Durum:** `.env` dosyasında `PEXELS_API_KEY=your_pexels_api_key_here` şeklinde varsayılan anahtar duruyor.
* **Etki:** Yapay zeka veya kullanıcı stok görsel aradığında veya öneri kabul edildiğinde görsel MinIO'ya indirilemiyor ve 401 Unauthorized hatası alınıyor.
* **Gereken:** Ücretsiz bir Pexels API anahtarının `.env` dosyasına girilmesi ve Pexels servisinde arama terimlerinin İngilizceye otomatik çevrilmesi (Türkçe "hukuk mahkemesi" -> "courtroom law").

### 3.2. Otomatik Arka Plan Kaldırma (Background Removal / Sticker Maker)
* **Eksiklik:** Kullanıcı bir PNG/JPG görsel eklediğinde (örneğin konuşmacının bahsettiği bir kitap kapağı, logo veya portre), görselin arka planındaki beyaz/siyah fon videonun üzerine kare kutu gibi biniyor.
* **Çözüm:** Python Worker içerisine `rembg` (U2Net AI) kütüphanesi entegre edilerek tek tıkla "Arka Planı Kaldır (Şeffaf Yap)" özelliği getirilmelidir.

### 3.3. Video B-Roll (PIP / Resim İçinde Resim & Cutaway)
* **Eksiklik:** Şu anda overlay katmanlarına sadece yazı ve resim konulabiliyor. Kısa video klipleri (B-Roll video) ikinci kanala yerleştirip sesini kısarak konuyu destekleme özelliği henüz desteklenmiyor.

---

## 🔊 Bölüm 4: Ses (Audio) Miksajı ve İyileştirme Eksikleri

### 4.1. Arka Plan Müziği (BGM) Auto-Ducking (Otomatik Kısma)
* **Mevcut Durum:** Editör arayüzünde BGM müziği seçme ve ses düzeyi ayarı mevcut, ancak nihai render alınırken konuşma başladığında müziğin sesini otomatik olarak %15'e kısıp, konuşma bitince tekrar yükselten dinamik ducking filtresi (`sidechaincompress`) FFmpeg render zincirine tam bağlanmamıştır.
* **Gereken:** `video_renderer.py` içine FFmpeg `-filter_complex` seviyesinde konuşma algılandığında müziği kısan ducking filtresi entegrasyonu.

### 4.2. Orijinal Ses ve Geliştirilmiş Ses A/B Karşılaştırması
* **Eksiklik:** Sistem ses iyileştirme (RNNoise veya gürültü filtresi) uyguluyor ancak kullanıcı videoyu düzenlerken orijinal ham ses ile işlenmiş sesi tek tıkla dinleyip aradaki farkı kıyaslayamıyor.

### 4.3. Ses Ekolayzerı ve Ses Yükseltme (Normalization - LUFS)
* **Eksiklik:** YouTube ve TikTok standartlarına (-14 LUFS) uygun otomatik ses seviyesi normalizasyonu (loudnorm) manuel ayarlanabilir değil.

---

## ✍️ Bölüm 5: Gelişmiş Altyazı ve Tipografi Eksikleri

### 5.1. Dinamik Karaoke Kelime Vurgulama
* **Mevcut Durum:** Altyazılar sabit sarı veya beyaz bloklar halinde görünüyor.
* **Eksiklik:** CapCut, Submagic veya OpusClip'te olduğu gibi konuşmacının o an söylediği kelimenin anlık olarak parlaması / renk değiştirmesi (Kelime bazlı Karaoke efekti).
* **Gereken:** Whisper kelime zaman damgalarının (`words: [{word, start, end}]`) ASS altyazı dosyasında `{\k...}` karaoke etiketlerine dönüştürülmesi.

### 5.2. Altyazı Düzenleme & Zaman Kaydırma
* **Eksiklik:** Transkriptte yanlış anlaşılan bir kelimeyi kullanıcının doğrudan altyazı kutusuna çift tıklayarak düzeltmesi ve düzeltmenin anında hem videoya hem EDL'e yansıması tam iki yönlü senkronize edilmelidir.

---

## ⚡ Bölüm 6: Hız (Speed Ramp) ve Renk (Color Grading) Eksikleri

### 6.1. Hız Kontrolü (Speed Ramp & Slow-Motion)
* **Eksiklik:** Bir sahneyi 1.5x / 2x hızlandırma veya 0.5x yavaşlatma imkanı yok. Hızlandırıldığında sesin tonunun bozulmaması (chipmunk etkisi olmaması) için FFmpeg `atempo` filtresi desteği gerekiyor.

### 6.2. Renk Düzeltme (Color Grading)
* **Eksiklik:** Videonun parlaklık (brightness), kontrast (contrast), doygunluk (saturation) ve renk sıcaklığı (temperature) ayarları için temel bir panel henüz bulunmuyor.

---

## 📊 Eksikler ve Öncelik Matrisi (Priority Action Table)

| Kod | Özellik / Eksiklik | Kategori | Öncelik | Zorluk | Hedef Aşama |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **E1** | AI Chat Yazı Ekleme & Onaylama (Pending Patch) | Yapay Zeka | 🔴 P0 (Acil) | Düşük | Tamamlandı / Doğrulandı |
| **E2** | Transkript İçi Soru Cevaplama (Bediüzzaman vb.) | Yapay Zeka | 🔴 P0 (Acil) | Düşük | Tamamlandı / Doğrulandı |
| **E3** | Otonom Video Yönetmeni (Proaktif AI Önerileri) | Yapay Zeka | 🟡 P1 (Yüksek) | Orta | Sonraki Adım |
| **E4** | Kanvas Üzerinde Serbest Sürükleme/Boyutlandırma | Arayüz (UI) | 🟡 P1 (Yüksek) | Orta | Sonraki Adım |
| **E5** | Dinamik Karaoke Kelime Altyazı (CapCut Stili) | Altyazı | 🟡 P1 (Yüksek) | Orta | Sonraki Adım |
| **E6** | Pexels Gerçek API Key & Otomatik B-Roll İndirme | Medya | 🟡 P1 (Yüksek) | Düşük | Kullanıcı Yapılandırması |
| **E7** | Görsel Arka Plan Kaldırma (`rembg` AI) | Medya | 🟢 P2 (Orta) | Orta | Faz 2 |
| **E8** | BGM Auto-Ducking (FFmpeg Sidechain) | Ses | 🟢 P2 (Orta) | Orta | Faz 2 |
| **E9** | Renk Ayarları (Color Grading Paneli) | Video İşleme | ⚪ P3 (Düşük) | Düşük | Faz 3 |
| **E10**| Hız Kontrolü (Speed Ramp & Pitch Koruması) | Video İşleme | ⚪ P3 (Düşük) | Orta | Faz 3 |

---

## 🎯 Sonuç ve Tavsiye Edilen İlk Adım

1. **Yapay Zeka Sohbeti ve Katman Ekleme**: Yapılan düzeltmelerle birlikte artık `[Seçili Aralık: ...] yazı` denildiğinde doğrudan onaylanabilir katman üretiliyor; içerik soruları ise EDL'deki transkript taranarak kesin dakika/saniyesiyle yanıtlanıyor.
2. **Kullanıcı İçin İlk İşlem**: `.env` dosyasındaki `PEXELS_API_KEY` alanına ücretsiz bir anahtar eklenmesi B-Roll stok görsel motorunu anında çalışır hale getirecektir.
3. Bir sonraki yazılım geliştirme odak noktası: **Kanvas üzerinde mouse ile serbest sürükleme (E4)** ve **Dinamik kelime karaoke altyazısı (E5)** olmalıdır.
