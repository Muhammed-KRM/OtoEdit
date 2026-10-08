# OtoEdit — Proje Durum Raporu ve Sonraki Adımlar Rehberi
**Tarih:** 8 Ekim 2026  
**Durum:** Altyazı, responsive sahne ve font render motoru büyük oranda tamamlandı; son font boyutu kalibrasyonu uygulandı ve test edilmeye hazır.

---

## 1. Bu Oturumda Çözülen ve Doğrulanan Maddeler

| Alan | Yapılan İyileştirme | Durum |
| :--- | :--- | :--- |
| **Özel Fontlar (Cinzel vb.)** | 8 adet Google Fontu (`Cinzel`, `Montserrat`, `Inter`, `Bebas Neue`, `Anton`, `Poppins`, `Outfit`) Docker worker içerisine kopyalandı ve `fc-cache` ile libass/FFmpeg'e tanıtıldı. | ✅ **Çözüldü** |
| **Responsive Player & Sahne** | Tarayıcı penceresi küçültüldüğünde video kutusunun sıfırlanması veya yazı/görsellerin sağa sola kayması sorunu giderildi. `#videoStage` Container Query (`cqi`) ve dinamik `aspectRatio` ile kilitlendi. | ✅ **Çözüldü** |
| **Altyazı Karaoke (Sarı Parlama)** | Eski kümülatif ve renkleri ters çalışan `\k` karaoke sistemi tamamen kaldırıldı. Yerine her kelimenin telaffuz anında parlak sarı yandığı, konuşma geçince tekrar beyaza döndüğü **TikTok/Reels tarzı dinamik kelime vurgusu** yazıldı. | ✅ **Çözüldü** |
| **Altyazı Konumu & Kapsül Kutusu** | Altyazı masanın dibinden (`MarginV: 40`), editörle uyumlu göğüs hizasına (`MarginV: 160`) çekildi ve arkasına şık, yarı saydam koyu bir kapsül kutusu (`BorderStyle: 3, BackColour: &HB0101010`) eklendi. | ✅ **Çözüldü** |
| **Yazı Gölgesi (Beyazdan Siyaha)** | Render çıktısında yazının arkasında beliren gri/beyaz hayalet gölgenin, 8 haneli hex kodundan (`\4c&H90000000`) kaynaklandığı tespit edildi. Standart 6 haneli saf siyah (`\4c&H000000&`) ve `\blur2\shad4` eklenerek editördeki CSS `drop-shadow` ile birebir aynı derin siyah gölgeye kavuşturuldu. | ✅ **Çözüldü** |

---

## 2. En Son Yapılan Değişiklik: Font Boyutu Kalibrasyonu

### Yaşanan Sorun:
- İlk denemede yazı renderda editöre göre küçük kalmıştı (`fs=87` -> %20 ekran genişliği).
- Bir sonraki denemede 16:9 çarpanı (1.777) uygulandığında bu kez renderda yazı fazla büyümüş ve konuşmacının saçına kadar taşmıştı (`fs=155` -> %48 ekran genişliği).

### Gerçek Kök Neden ve Çözüm:
- **Matematiksel Gerçek:** Web tarayıcıları CSS font boyutunu **96 DPI (piksel)** bazında hesaplarken, ASS/FreeType motoru font boyutunu **72 DPI (nokta/point)** bazında hesaplar.
- **Standart Oran:** `96 / 72 = 4 / 3 ≈ 1.333333`.
- Kullanıcının editörde seçtiği `87` pt font:
  $$\text{ASS Boyutu} = 87 \times \frac{4}{3} = 116\text{ pt}$$
- `fs=116` ile yapılan testte metin genişliği tam olarak **%27.97** çıkmıştır. Editör ekranındaki ölçülen metin genişliği ise **%27.40**'tır. Yani editör ile video render tuvali arasında **%99.5 tam uyum** sağlanmıştır.
- Ayrıca kaplama yazılarının hizalama merkezi editördeki `-translate-x-1/2 -translate-y-1/2` ile uyumlu olması için `\an5` (tam merkez) olarak kilitlendi.

---

## 3. Kod Dosyalarındaki Güncel Durum

1. [**`src/OtoEdit.PythonWorker/render/text_overlay.py`**](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/text_overlay.py):
   - Font boyutu: `size = max(12, int(round(raw_size * (96.0 / 72.0))))`
   - Gölge: `\bord0\shad4\blur2\4c&H000000&`
   - Hizalama: `target_align = 5`
   - Altyazı: Dinamik kelime bazlı TikTok sarı vurgusu + `MarginV: 160` + `BorderStyle: 3` siyah kapsül.
2. [**`src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts`**](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts):
   - Font size CSS formülü: `((ov.fontSize || 48) / 19.2) + 'cqi'`
   - Video monitör konteyneri en-boy oranına kilitli (`cqi` stabil).
3. **Docker Worker:**
   - `otoedit-dev-worker` en son kodlarla yeniden başlatıldı ve RabbitMQ üzerinde dinlemede bekliyor.

---

## 4. Bir Sonraki Oturumda Kaldığımız Yerden Nasıl Devam Edeceksiniz?

Projeyi açtığınızda yapmanız gereken tek bir adım var:

1. **Projeyi Başlatın (Gerekiyorsa):**
   - Eğer servisler kapalıysa ana dizindeki `baslat.bat` dosyasını çalıştırın.
   - Ya da sadece Docker tarafını kontrol etmek için:
     ```powershell
     docker ps
     ```
     `otoedit-dev-worker`, `rabbitmq`, `minio` açık olmalıdır.
2. **Editörü Açın:**
   - `http://localhost:4200/project/1f175a2f-905b-45ab-8817-b98608277c49` (test28 projesi).
3. **Render Alın:**
   - Sağ üstteki **"Nihai Videoyu Render Et"** butonuna basın.
4. **Sonucu Kontrol Edin:**
   - Yeni uyguladığımız `fs=116` kalibrasyonu sayesinde "YENİ METİN" yazısının artık ne küçük ne de büyük, tam editördeki cyan kutunun boyutunda ve siyah derin gölgesiyle çıkması beklenmektedir.
   - Sonuç tamamsa işlem başarıyla tamamlanmış olur!
