# OtoEdit: Uçtan Uca Donanım Bazlı (GPU/VRAM) Kurgu Motoru Planı

Bu devasa doküman, OtoEdit sistemindeki CPU (İşlemci) darboğazlarını, RAM-VRAM arası ping-pong maliyetlerini ve filtre patlaması sorunlarını çözerek, render sürelerini dakikalardan saniyelere indirecek mimariyi sıfırdan kurmayı hedefler.

Plan; araştırma sonuçları, diğer yapay zeka analizleri ve mevcut kod tabanınız sentezlenerek **fazlara (aşamalar)** bölünmüş olarak hazırlanmıştır.

---

## 1. Amaç ve Uyulacak Kurallar

### 🎯 Amaç (Kuzey Yıldızı)
OtoEdit'in dışa aktarma (render) ve analiz (transkripsiyon/yüz tespiti) işlemlerini tamamen ekran kartı belleği (VRAM) üzerinde **"Sıfır Kopya (Zero-Copy)"** mantığıyla gerçekleştirmek. Sistemin 545 kesimli veya 10.000 kesimli bir videoyu bile sanki tek parça video render ediyormuşçasına anında işleyebileceği bir **VRAM-Centric NLE (Non-Linear Editor)** motoruna dönüşmesini sağlamak.

### 📜 Uyulacak Katı Kurallar
1. **Sıfır RAM Kopyası (Zero-Copy):** Kodlanmış MP4 dosyası okunduktan sonra elde edilen ham kareler (frames) GPU'da kalacaktır. İşlemciye (CPU/RAM) indirme (hwdownload) işlemi kesinlikle yasaktır veya sadece kaçınılmaz çok ufak grafik operasyonlarında asenkron yapılacaktır.
2. **Kademeli Geçiş (Graceful Degradation):** Yeni GPU mimarisi yazılırken eski CPU mimarisi silinmeyecek, bir hata durumunda "Fallback (Yedek)" render motoru olarak hayatta tutulacaktır.
3. **Kapsüller Arası İzolasyon:** Kurgu (Trim/Concat), Efekt (Scale/Crop), Altyazı (Overlay) görevleri birbirine bağımlı spagetti kodlar yerine, pipeline'dan sırayla geçen bağımsız modüller olacaktır.
4. **Proxy Önizleme Kuralı:** UI tarafında devasa videoların tarayıcıyı kitlememesi için, sisteme video yüklendiği an arka planda saniyeler içinde 720p/360p çok hafif bir "Proxy Video" üretilecektir. Tarayıcı sadece proxy ile konuşacaktır. Orijinal 4K/1080p dosya yalnızca nihai render sunucusunda elden geçirilecektir.

---

## 2. Kullanılacak Teknolojiler ve Yığın (Tech Stack)

### Ana Rendering ve Donanım Araçları
1. **PyNvVideoCodec (Eski adıyla VPF):** Python üzerinden doğrudan Nvidia NVDEC (Çözücü) ve NVENC (Kodlayıcı) çiplerine ulaşarak FFmpeg'in aracı process (alt-işlem) yükünü ortadan kaldıran resmi SDK. Nihai kurgu motorunun kalbi olacaktır.
2. **CuPy (veya PyTorch Tensörleri):** VRAM üzerinde tutulan ham video karelerine (piksel dizilerine) anında müdahale etmek için kullanılacaktır. Altyazı bindirme (Alpha Blending) ve kırpma (Crop) işlemleri CuPy ile yazılacak özel CUDA çekirdeklerinde milisaniyeler içinde yapılacaktır.
3. **FFmpeg (Gelişmiş Concat Demuxer & overlay_cuda):** PyNvVideoCodec geliştirilmesi uzun sürebileceğinden, **1. Faz (Hızlı Kazanım)** aşamasında mevcut FFmpeg komutları devasa `filter_complex` sarmalından kurtarılıp, `-f concat` demuxer'ına ve VRAM içi `overlay_cuda` katmanlarına geçirilecektir.

### Analiz (Yapay Zeka) Araçları
1. **faster-whisper (CTranslate2 Backend):** OpenAI API bağımlılığından ve yavaşlığından kurtulmak için. VRAM üzerinde (FP16 veya INT8 kuantizasyonu ile) 1 saatlik sesi 2 dakikada hatasız döken kütüphane.
2. **Redis:** Parametreye duyarlı (Auto Jumpcut=True/False, Format=9:16 vs) cache anahtarları oluşturularak, aynı videonun farklı türevleri anında önbellekten çekilecektir.

---

## 3. Önerilen Dosya Yapısı (Architecture Layout)

`src/OtoEdit.PythonWorker/` altında yeni nesil render mimarisi için aşağıdaki klasör yapısı oluşturulacaktır:

```text
src/OtoEdit.PythonWorker/
├── render/
│   ├── __init__.py
│   ├── base_renderer.py           # (Tüm render motorlarının türeyeceği arayüz sınıfı)
│   ├── ffmpeg_cpu_renderer.py     # (Eski, mevcut çalışan CPU tabanlı sistem - YEDEK)
│   ├── ffmpeg_gpu_demuxer.py      # (FAZ 1: ffconcat ve overlay_cuda kullanan hızlı geçiş motoru)
│   ├── pynv_gpu_renderer.py       # (FAZ 2: VRAM içi çalışan, sıfır kopyalı asıl NLE motoru)
│   └── filter_builder.py          # (EDL JSON'dan ffconcat listesi veya CuPy tensor talimatları üreten modül)
├── analysis/
│   ├── fast_transcriber.py        # (faster-whisper entegrasyonu)
│   ├── video_proxy_generator.py   # (UI için 720p/360p hafif video üreten modül)
│   └── ...
├── models/
│   └── edl_models.py              # (EDL verilerini doğrulayan Pydantic veya Dataclass modelleri)
└── consumers/
    └── render_consumer.py         # (RabbitMQ'dan mesajı alıp donanım yeteneğine göre Renderer seçecek)
```

---

## 4. Kod Örnekleri ve Mimari Tasarım

### A. Faz 1: Concat Demuxer ve `overlay_cuda` Örneği (Hızlı Çözüm)
CPU'yu kilitleyen `filter_complex [0:v]trim=...[v0];` mantığını bırakıp, metin tabanlı kesim (ffconcat) yöntemine geçişin Python kodu:

```python
# render/ffmpeg_gpu_demuxer.py
import os
import subprocess

def create_concat_file(edl_data, output_path, video_path):
    concat_txt_path = os.path.join(output_path, "cuts.txt")
    with open(concat_txt_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for segment in edl_data["segments"]:
            if not segment.get("isCut", False): # Sadece tutulacak kısımlar
                f.write(f"file '{video_path}'\n")
                f.write(f"inpoint {segment['start']}\n")
                f.write(f"outpoint {segment['end']}\n")
    return concat_txt_path

def render_with_concat(video_path, concat_txt_path, output_mp4):
    cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda", 
        "-hwaccel_output_format", "cuda", # Pikseller VRAM'de kalsın
        "-f", "concat", "-safe", "0",
        "-i", concat_txt_path,
        "-c:v", "h264_nvenc",
        "-preset", "p4", "-b:v", "6M",
        "-c:a", "aac",
        output_mp4
    ]
    subprocess.run(cmd, check=True)
```

### B. Faz 2: PyNvVideoCodec ve CuPy ile Sıfır-Kopya NLE Motoru
Gelecekteki asıl hedefimiz: FFmpeg process'i yerine tamamen Python içinde GPU'da kurgu yapmak.

```python
# render/pynv_gpu_renderer.py
import PyNvCodec as nvc
import cupy as cp

def render_zero_copy(video_path, output_path, edl_data):
    # 1. Donanımsal Çözücü (Decoder) ve Kodlayıcı (Encoder) başlatılır
    nvDec = nvc.PyNvDecoder(video_path, 0) # 0: GPU ID
    width, height = nvDec.Width(), nvDec.Height()
    
    nvEnc = nvc.PyNvEncoder(
        {'preset': 'P4', 'tuning_info': 'high_quality', 'codec': 'h264', 
         's': f'{width}x{height}', 'b': '6M'}, 0)
    
    # 2. EDL'ye göre sadece gereken kareleri çöz ve hemen kodla
    # (Bu işlemde RAM kullanılmaz, veriler hep VRAM'dedir)
    for segment in edl_data["segments"]:
        if not segment["isCut"]:
            start_frame = int(segment["start"] * nvDec.Framerate())
            end_frame = int(segment["end"] * nvDec.Framerate())
            
            # Zaman çizelgesine atla (Seek)
            # nvDec.DecodeSingleSurface() ile frame alınıp nvEnc.EncodeSingleSurface() ile yazılır.
            # Altyazı eklenecekse araya CuPy tensor matris çarpımı girer.
            pass 
```

---

## 5. Aşama Aşama (Faz) Uygulama Rehberi

OtoEdit sistemini durdurmadan (sıfır kesinti) bu devasa yapıya geçiş için aşağıdaki adımlar sırayla izlenmelidir.

### FAZ 1: Kanamayı Durdurmak (Hızlı Kazanım)
*Hedef: 30 dakikalık render süresini anında 2-3 dakikaya indirmek.*
1. `video_renderer.py` içindeki `_execute_ffmpeg_with_script` metodu tamamen iptal edilecek.
2. Yerine yukarıda örneği verilen **Concat Demuxer** mantığı yazılacak.
3. Python, `cuts.txt` adında basit bir liste dosyası oluşturacak (EDL'ye bakarak).
4. FFmpeg bu `cuts.txt` dosyasını okuyup `-c:v h264_nvenc` ile anında çıktı verecek. (CPU üzerinde karmaşık filtreler kurulmayacağı için sistem darboğazdan kurtulacak).

### FAZ 2: Altyazı ve Görselleri VRAM'e Taşımak
*Hedef: Altyazı yakma işlemini CPU'dan kurtarmak.*
1. Altyazılar (ASS), Python'da şeffaf (Alpha channel) bir WebM videosuna dönüştürülecek.
2. Bu şeffaf altyazı videosu, Concat edilen asıl videonun üzerine `-hwaccel cuda` ve `-filter_complex "[0:v][1:v]overlay_cuda=0:0"` komutuyla **doğrudan Ekran Kartı (VRAM) içinde** bindirilecek.
3. Bu sayede `libass` CPU yükü sıfırlanmış olacak.

### FAZ 3: Transkripsiyon (Yapay Zeka) Optimizasyonu
*Hedef: Analiz işlemlerini hızlandırmak.*
1. OpenAI Whisper API maliyeti ve gecikmesinden kurtulmak için `faster-whisper` kütüphanesi Worker imajına eklenecek.
2. GPU'nun `INT8` kuantizasyon gücü kullanılarak 10 dakikalık bir videonun transkripti 10 saniyede lokalde çıkarılacak.

### FAZ 4: Nihai Mimari (PyNvVideoCodec Entegrasyonu)
*Hedef: FFmpeg alt-sürecinden tamamen kurtulup endüstri standardı NLE olmak.*
1. Yukarıdaki Kod Örneği B'de gösterilen `pynv_gpu_renderer.py` modülü sisteme eklenecek.
2. Arayüzden gelen render komutu RabbitMQ'ya düştüğünde, sistem FFmpeg yerine kendi yerel GPU döngüsünü (PyNvCodec) başlatıp %100 VRAM-Centric kurgu yapacak.
3. Bu faz tamamlandığında OtoEdit, CapCut veya Adobe Premiere'in bulut versiyonları kadar hızlı render alan profesyonel bir yapıya kavuşmuş olacaktır.

---

## 6. Kritik Teknik Tuzaklar ve Çözümleri (Risk Management)

Başka bir yapay zeka tarafından yapılan incelemeler ışığında, bu mimariyi uygularken karşılaşabileceğimiz 5 büyük teknik risk ve çözüm yöntemleri aşağıda detaylandırılmıştır:

### ⚠️ Risk 1: FFmpeg Concat Demuxer'da Ses-Görüntü Senkron Kayması (AV Desync)
* **Tehlike:** 545 farklı `inpoint/outpoint` tanımlandığında, kaynak videonun değişken kare hızına (VFR) veya eksik Keyframe aralıklarına bağlı olarak her kesimde milisaniyelik kaymalar birikebilir.
* **Çözüm:** FFmpeg komutunda mutlaka sabit kare hızı (`-fps_mode cfr` veya `-r`) zorlanmalıdır. Seste oluşabilecek taşmaları engellemek için `-af "aresample=async=1000"` ses filtresi eklenerek senkron kilitlenmelidir.

### ⚠️ Risk 2: `overlay_cuda` Piksel Formatı Uyuşmazlığı
* **Tehlike:** VRAM içindeki ana video `nv12` formatındayken, dışarıdan gelen şeffaf altyazı videosu (alpha channel) uyumsuz olabilir.
* **Çözüm:** Altyazı videosu FFmpeg'e verildiğinde anında VRAM'de `rgba` formatına çevrilip overlay yapılmalıdır:
  `-filter_complex "[1:v]hwupload_cuda,format=rgba[sub];[0:v][sub]overlay_cuda=0:0:format=nv12"`

### ⚠️ Risk 3: PyNvVideoCodec (Sadece Görüntü İşler)
* **Tehlike:** `PyNvVideoCodec` ses (Audio) çözme/kodlama yeteneğine sahip değildir. 
* **Çözüm:** Kurgu işlemi sadece görüntü pikselleriyle bitmez. Faz 4'te Python koduna geçilirken, ses parçaları paralel olarak `PyAV` (veya `pydub`) ile işlemci (CPU) tarafında çok hızlıca kesilip, en son adımda GPU'dan çıkan görüntü (H.264 bitstream) ile birleştirilecektir (Muxing).

### ⚠️ Risk 4: Proxy Videonun Zaman Kodu (Timecode) Sadakati
* **Tehlike:** Frontend için 720p proxy üretilirken kare atlaması yaşanırsa, kullanıcının UI'da seçtiği saniye ile asıl videodaki saniye eşleşmeyebilir.
* **Çözüm:** Proxy üretilirken kesinlikle orijinal FPS değeri korunmalı, `-fps_mode cfr` ile kodlanmalı ve kare düşmesine izin verilmemelidir.

### ⚠️ Risk 5: Yapay Zeka Modellerinin VRAM Çakışması (OOM)
* **Tehlike:** `faster-whisper` modeli VRAM'e yüklendiğinde, ardından render başladığında 8GB altı ekran kartlarında bellek taşması (Out of Memory) yaşanabilir.
* **Çözüm:** PyTorch veya CuPy kullanan yapay zeka analiz adımları biter bitmez modeller bellekten zorla atılmalı (`del model; torch.cuda.empty_cache()`) ve render'a temiz bir VRAM bırakılmalıdır.

---

## 7. Güncellenmiş ve Optimize Edilmiş Yol Haritası

Teknik inceleme sonrası Faz 3'ün öne çekilmesiyle yeniden düzenlenen 4 aşamalı sprint planı:

| Aşama | Görev | Tahmini Efor | Hedef Kazanım |
| --- | --- | --- | --- |
| **Aşama 1** | **Faz 1 (Concat Demuxer):** FFmpeg `filter_complex` iptal edilip, metin tabanlı (`ffconcat`) hızlı kesim yöntemine geçilir. | 1-2 Gün | Render 40 dakikadan **3-5 dakikaya** düşer. Sistemin kilitlenmesi son bulur. |
| **Aşama 2** | **Faz 3 (faster-whisper):** Render motorunu değiştirmeyi beklemeden analiz tarafı hızlandırılır. | 1-2 Gün | Transkript maliyeti sıfırlanır, analiz 10 kat hızlanır. |
| **Aşama 3** | **Faz 2 (overlay_cuda):** Altyazı ve görseller şeffaf video olarak üretilip GPU içinde videoya bindirilir. | 3-4 Gün | Render süresi **1 dakikanın** altına iner. |
| **Aşama 4** | **Faz 4 (PyNvVideoCodec + CuPy):** FFmpeg tamamen çıkarılıp kendi sıfır kopyalı Python NLE kurgu motorumuz yazılır (Ses için PyAV kullanılır). | Uzun Vade | Render **saniyeler içinde** biter (Bulut mimarisine geçiş). |

---
*(Doküman Tamamlandı)*
