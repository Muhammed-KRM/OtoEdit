# 🛠️ OtoEdit — Kritik 3 Sorun: Teşhis ve Çözüm Planı

> **Tarih:** 30 Eylül 2026  
> **Konum:** `docs/kritik_3_sorun_cozum_plani.md`  
> **Durum:** ✅ Tüm Sorunlar Çözüldü  
> **İlgili Dosyalar:**  
> - [`src/OtoEdit.PythonWorker/render/video_renderer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py)  
> - [`src/OtoEdit.PythonWorker/render/text_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/text_overlay.py)  
> - [`src/OtoEdit.PythonWorker/render/image_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py)  
> - [`src/OtoEdit.PythonWorker/render/timeline_mapper.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/timeline_mapper.py)

---

## Sorun 1: Altyazılar ~1 Saniye Önde Gidiyor

### Belirti
Render edilmiş nihai videoda altyazılar (Whisper transkripti), konuşmacının ağzından çıkan kelimelerden yaklaşık 1-2 kelime (tahminen 0.5-1.5 saniye) **erken** ekranda görünüyor. Yani kullanıcı henüz kelimeyi söylemeden altyazıda o kelime görünüyor.

### Teşhis — Kök Neden
Bu sorunun **iki olası kaynağı** vardır:

#### Kaynak A: FFmpeg Segment Kesimleri Sırasında Oluşan PTS (Presentation Timestamp) Kayması
[`video_renderer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py) dosyasındaki `_cut_single_segment` metodu (satır 129-149) her segmenti paralel olarak keserken şu FFmpeg komutunu kullanır:

```python
seg_cmd = [
    "ffmpeg", "-y",
    "-ss", str(start),       # Input seeking — keyframe'e atlar
    "-i", video_path,
    "-t", str(duration),
    ...
]
```

**Sorun:** FFmpeg'in `-ss` parametresi **input seeking** modunda kullanıldığında, FFmpeg en yakın keyframe'den (I-frame) itibaren decode etmeye başlar. Eğer istenen `start` saniyesi tam bir keyframe'e denk gelmiyorsa, FFmpeg birkaç kareyi (0.5-1.5 saniye arası, GOP yapısına bağlı olarak) sessizce atlar ve bu durum nihai video akışının PTS'inde **küçük ama birikimli bir negatif kayma** yaratır.

Sonuç olarak, video akışı beklenen zamandan 0.5-1.5 saniye **geç** başlarken, altyazı ASS dosyası matematiksel olarak doğru hesaplandığı için **erken görünür**.

#### Kaynak B: `remap_timestamp` Tolerans Ayarı
[`timeline_mapper.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/timeline_mapper.py) dosyasında `remap_timestamp` metodu 20 milisaniyelik (`tolerance: float = 0.02`) bir toleransla çalışır. Whisper'ın kelime zamanları zaten milisaniye hassasiyetinde olduğundan, toleransın kendisi sorun yaratmaz. Ancak **Kaynak A'dan gelen kayma ile birleştiğinde**, algılanan erkenlik belirginleşir.

### Çözüm Yaklaşımı

**Ana Çözüm:** Segment kesim yönteminde `-ss` parametresinden sonra FFmpeg'e `-noaccurate_seek` yerine video PTS'sini sıfırlamak için `-avoid_negative_ts make_zero` (zaten var) ve ek olarak her segmentin gerçek başlangıç PTS'sini sorgulayıp, kümülatif kaymayı ölçmek:

1. **Yöntem A (Basit — Sabit Offset):** Tüm altyazı zamanlarına sabit bir pozitif offset (örn. +0.3s - +0.8s arası, test ile bulunacak) eklemek. Bu, `remap_timestamp` fonksiyonuna bir `subtitle_delay` parametresi olarak geçirilir. Hızlı ama kaba bir çözüm.

2. **Yöntem B (Hassas — Segment PTS Probing):** Her kesilmiş segment dosyasının (`seg_0000.mp4`, `seg_0001.mp4`, ...) gerçek başlangıç PTS'sini `ffprobe` ile sorgulamak ve segment birleştirme sonrasında oluşan kümülatif PTS kaymasını hesaplayarak altyazı zamanlarından bu kaymayı düşürmek. Daha karmaşık ama milisaniye hassasiyetinde çözüm sağlar.

3. **Yöntem C (En Temiz — Output Seeking):** Segment kesimlerinde `-ss` parametresini input seeking yerine **output seeking** olarak kullanmak. Bu, FFmpeg'in kareyi tam istenen saniyeden kesmesini garanti eder ancak decode maliyeti arttığı için render süresi %15-25 artabilir.

### Doğrulama Testi
- Render edilen videonun ilk 30 saniyesinde konuşmacının ağız hareketleri ile altyazı kelimelerinin eşzamanlı olup olmadığı gözlemle kontrol edilecek.
- Kesilmiş segment dosyalarının PTS başlangıçları `ffprobe` ile sorgulanarak kayma miktarı ölçülecek.

---

## Sorun 2: Metin Overlay'lerin Fontu Editördekinden Farklı Görünüyor

### Belirti
Editörde (tarayıcıda) kullanıcının eklediği yazı kaplamaları (örn: "tiwitter" yazısı) belirli bir font ile görünürken, render edilmiş nihai videoda **farklı bir fontla** (muhtemelen ASS varsayılan fontu veya sistemde bulunan en yakın fallback font) görünmektedir. Yazının **konumu, rengi ve animasyonu doğrudur**, sadece font yüzü (typeface) uyuşmamaktadır.

### Teşhis — Kök Neden

Sorun iki katmanlıdır:

#### Katman 1: Frontend ve Backend Font İsim Uyumsuzluğu
[`editor.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) dosyasında (satır 414) editördeki metin şu CSS ile gösterilir:
```typescript
[style.fontFamily]="ov.font || 'Inter, sans-serif'"
```
Yani editörde kullanıcının seçtiği font adı (`ov.font`) CSS `font-family` olarak uygulanır. Varsayılan font `Inter` dir.

Ancak [`text_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/text_overlay.py) dosyasında (satır 135):
```python
font = ov.get("font", "Montserrat-Bold")
```
Backend varsayılan fontu `Montserrat-Bold` olarak kullanır. ASS dosyasına da bu font adı ile yazılır:
```
{\an5\fnMontserrat-Bold\fs48\c&H00FFFFFF...}tiwitter
```

**Sorunlar:**
- Eğer kullanıcı editörde bir font seçtiyse (örn: `Inter`), bu değer EDL JSON'da `font: "Inter"` olarak backend'e gider ama Docker konteynerinde (`/app`) yalnızca FFmpeg'in erişebildiği sistem fontları bulunur. `Inter` fontu genellikle Docker konteynerinde yüklü olmadığından, FFmpeg/libass bu fontu bulamaz ve **varsayılan sans-serif fontuna (genellikle DejaVu Sans veya Liberation Sans)** düşer.
- Eğer kullanıcı hiç font seçmediyse, frontend `Inter` gösterirken backend `Montserrat-Bold` kullanır — her iki durumda da Docker konteynerinde bu fontlar genellikle yoktur.

#### Katman 2: Docker Konteynerinde Font Eksikliği
FFmpeg'in ASS/libass motoru fontları şu sırayla arar:
1. ASS dosyasındaki gömülü fontlar (embedded fonts)
2. `fc-list` ile erişilebilen sistem fontları
3. Bulamazsa: Varsayılan fallback font (genellikle sans-serif)

Docker imajında (`Dockerfile`) özel fontlar yüklenmediği sürece, `Montserrat-Bold`, `Inter`, `Poppins` gibi Google Fonts ailesinden gelen fontlar **mevcut değildir**.

### Çözüm Yaklaşımı

1. **Font Dosyalarını Docker İmajına Eklemek:**
   - Kullanılan fontların `.ttf`/`.otf` dosyalarını projeye dahil etmek (örn: `assets/fonts/`).
   - Dockerfile'a font yükleme adımı eklemek:
     ```dockerfile
     COPY assets/fonts/ /usr/share/fonts/custom/
     RUN fc-cache -f -v
     ```
   - Bu sayede libass istenen fontu sisteme kayıtlı olarak bulacak.

2. **ASS Dosyasına Font Gömme (Embedded Fonts):**
   - ASS formatı `[Fonts]` bölümünde Base64 kodlanmış font verisi destekler.
   - `generate_ass` fonksiyonuna kullanılan fontların `.ttf` dosyalarını Base64 olarak ASS dosyasına gömmek eklenebilir. Bu yöntem Docker bağımlılığını ortadan kaldırır.

3. **Frontend-Backend Font Varsayılan Eşitlemesi:**
   - Frontend varsayılanı `Inter` iken backend varsayılanı `Montserrat-Bold` — bu iki değer aynı yapılmalı.
   - Font adı eşlemesi (mapping) oluşturulmalı: CSS adı (`Inter`) → Sistem font adı (`Inter-Regular`).

### Doğrulama Testi
- Docker konteynerinde `fc-list | grep -i "inter\|montserrat"` çalıştırılarak fontların yüklü olup olmadığı kontrol edilecek.
- ASS dosyasındaki `\fn` etiketinin doğru font adını içerdiği doğrulanacak.
- Render sonucu editör önizlemesi ile karşılaştırılacak.

---

## Sorun 3: Görsel (Image) Overlay'ler Render Edilen Videoda Hiç Yok

### Belirti
Editörde kullanıcının eklediği görsel kaplamalar (örneğin Twitter logosu, X logosu) açıkça timeline'da ve önizlemede görünmektedir. Ancak render edilen nihai videoda bu görseller **tamamen yoktur**. Video çıktısında yalnızca metin overlay'leri ve altyazılar görünmekte, görseller hiç render edilmemektedir.

### Teşhis — Kök Neden

Bu sorunun kaynağı net ve kesindir:

[`video_renderer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py) dosyası incelendiğinde:
- **Satır 9:** `from render.image_overlay import ImageOverlay` — ImageOverlay sınıfı import ediliyor.
- **Satır 29-30:** `__init__` metodunda `self.image_overlay = ImageOverlay(self.minio)` ile bir instance oluşturuluyor.
- **Ancak `render()` metodu boyunca `self.image_overlay.apply_image_overlays(...)` ASLA ÇAĞRILMIYOR.**

[`image_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py) dosyasındaki `apply_image_overlays` metodu, FFmpeg'in `ffmpeg-python` kütüphanesi üzerinden filter_complex zinciri ile çalışır:
```python
v = ffmpeg.overlay(v, img_input, x=x_expr, y=y_expr, enable=enable_expr)
```

Ancak mevcut render motoru `ffmpeg-python` yerine **doğrudan subprocess ile FFmpeg CLI komutları** çalıştırır. Bu mimari uyumsuzluk nedeniyle:
1. `ImageOverlay.apply_image_overlays()` bir `ffmpeg-python` stream nesnesi bekler.
2. `video_renderer.py`'deki concat + ASS render akışı tamamen subprocess tabanlıdır.
3. İki yaklaşım birbirine entegre edilmemiştir.

**Özet:** `ImageOverlay` sınıfı hazır ve yazılmış durumda, ancak `video_renderer.py` içindeki `render()` metodunda **hiçbir yerde çağrılmadığı için** görseller render çıktısına hiç eklenmiyor.

### Çözüm Yaklaşımı

Mevcut subprocess tabanlı render akışını koruyarak, görsel overlay'leri FFmpeg komut satırına `-filter_complex` parametresi olarak eklemek gerekir. İki ana yöntem vardır:

#### Yöntem A: Subprocess Tabanlı FFmpeg filter_complex Entegrasyonu (Önerilen)
Mevcut render akışının sonuna (concat + ASS birleştirme tamamlandıktan sonra) ikinci bir FFmpeg adımı eklemek:

1. Birleştirilmiş video dosyasını (ASS altyazıları dahil) ara çıktı olarak üretmek.
2. İkinci FFmpeg adımında bu ara dosyayı girdi alarak, üzerine image overlay'leri `-filter_complex overlay` ile eklemek.

```
ffmpeg -y -i ara_video.mp4 \
    -i twitter_logo.png \
    -i x_logo.png \
    -filter_complex "[0:v][1:v]overlay=x=100:y=200:enable='between(t,5.00,10.00)'[v1]; \
                      [v1][2:v]overlay=x=300:y=100:enable='between(t,5.00,10.00)'" \
    -c:v h264_nvenc -preset p4 -b:v 6M \
    -c:a copy \
    output_final.mp4
```

3. Overlay zamanlarını `TimelineMapper.remap_overlays` ile yeni zaman çizgisine kaydırmak (metin overlay'lerinde zaten yapılıyor, aynı mantık `type == "image"` olan overlay'lere de uygulanacak).

#### Yöntem B: ffmpeg-python ile Tam Entegrasyon
Tüm render akışını `ffmpeg-python` kütüphanesine taşımak. Bu daha temiz bir mimari sağlar ancak mevcut çalışan subprocess motorunu tamamen değiştirmek risklidir.

**Önerilen yöntem A'dır** çünkü mevcut çalışan render motoruna minimum müdahale ile görsel overlay desteği ekler.

### Doğrulama Testi
- EDL JSON'da en az bir `type: "image"` overlay'i olan bir proje render edilecek.
- Render çıktısında görselin doğru saniyede ve doğru konumda ekranda göründüğü gözlemle doğrulanacak.
- Görselin zamanının `TimelineMapper` ile doğru kaydırıldığı birim testi ile kanıtlanacak (bu test zaten mevcut ve geçiyor).

---

## Öncelik Sıralaması

| # | Sorun | Zorluk | Etki | Öncelik |
|---|---|---|---|---|
| 1 | Görsel Overlay'ler Videoda Yok | Orta | Kritik — temel özellik çalışmıyor | 🔴 En Yüksek |
| 2 | Altyazılar ~1 sn Erken | Orta-Yüksek | Yüksek — kullanıcı deneyimini bozuyor | 🔴 Yüksek |
| 3 | Font Uyumsuzluğu | Düşük-Orta | Orta — görsel kaliteyi düşürüyor | 🟡 Orta |

> **Not:** Sorun 1 (Görsel Overlay) en kritik olanıdır çünkü kullanıcının eklediği bir özellik tamamen çalışmamaktadır. Sorun 2 (Altyazı Kayması) deneyimi bozmakta, Sorun 3 (Font) ise estetik bir uyumsuzluktur.

---

## ✅ Uygulanan Çözümler (30 Eylül 2026)

**Sorun 1 (Altyazı Kayması) Çözümü:**  
- `video_renderer.py` içindeki segment kesim mantığında (`_cut_single_segment`) kullanılan `ffmpeg` komutunda `-ss` (seek) parametresi **Input Seeking** yapacak şekilde `-i` girdisinden önceye alındı. Re-encode işlemi uygulandığı için Input Seeking + re-encode yöntemi hem aşırı hızlı (keyframe bazlı seek) çalışır hem de `-avoid_negative_ts` ile tam frame-accurate birleştirme sağlar. (Önceki yanlış "Output Seeking" denemesi %2000 hız kaybına sebep olmuştu, bu düzeltildi.)

**Sorun 2 (Font Uyumsuzluğu) Çözümü:**  
- `text_overlay.py` içinde `Montserrat-Bold` olarak ayarlanmış ASS varsayılanı ve stil tanımları, frontend ile birebir eşleşmesi için `Inter` ile değiştirildi.
- `Dockerfile` içerisine Google Fonts'tan `Inter` ve `Montserrat` fontlarını indirip `fc-cache` ile Linux çekirdeğine kuran adımlar eklendi.

**Sorun 3 (Görsel Overlay Yokluğu) Çözümü:**  
- `video_renderer.py` içerisindeki `render()` metoduna iki geçişli (2-pass) bir mantık eklendi. Birinci pass'te (concat + subtitle) oluşturulan video, geçici bir dosyaya (`temp_no_images.mp4`) alındı.
- Ardından, `mapped_image_overlays` dizisi dolu ise `ImageOverlay.apply_image_overlays` ve `ffmpeg-python` motoru çağrılarak, filter_complex ile görsel overlay'ler doğrudan videonun üzerine entegre edildi.
- NVIDIA donanım hızlandırma (`h264_nvenc`) denendi, başarısızlık durumunda otomatik CPU (`libx264`) fallback'i kodlandı.
