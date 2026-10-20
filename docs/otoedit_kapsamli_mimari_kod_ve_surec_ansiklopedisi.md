# 🎬 OtoEdit — Kapsamlı Mimari, Dosya/Fonksiyon Rehberi ve Uçtan Uca Süreç Ansiklopedisi

> **Doküman Amacı:** Bu doküman, **OtoEdit** projesinin kaynak kodlarına doğrudan bakmaya gerek kalmadan; projenin ne olduğunu, hangi teknolojileri neden kullandığını, projedeki **her bir klasörün, her bir dosyanın ve içindeki her bir sınıf/fonksiyonun ne işe yaradığını** ve kullanıcının arayüzde yaptığı her işlemin (video yükleme, klip bölme, silme, geri alma, altyazı düzenleme, katman sürükleme, yapay zeka ile sohbet etme, dışa aktarma) tıklama anından başlayarak Frontend, Backend API, Veritabanı, RabbitMQ, Python Worker ve FFmpeg katmanlarından geçip tekrar ekrana nasıl döndüğünü bir kitap akıcılığında anlatmak için hazırlanmıştır.

---

## İçindekiler

1. [BÖLÜM 1: Projenin Amacı, Felsefesi ve Çalışma Mantığı](#bölüm-1-projenin-amacı-felsefesi-ve-çalışma-mantığı)
2. [BÖLÜM 2: Kullanılan Teknolojiler, Kütüphaneler ve Ekosistem](#bölüm-2-kullanılan-teknolojiler-kütüphaneler-ve-ekosistem)
3. [BÖLÜM 3: Tüm Projenin Klasör ve Dosya Yapısı (Tam Harita)](#bölüm-3-tüm-projenin-klasör-ve-dosya-yapısı-tam-harita)
4. [BÖLÜM 4: Kök Dizin, Altyapı (Docker/Nginx) ve Veri Katmanı (`OtoEdit.Data`) Detaylı İncelemesi](#bölüm-4-kök-dizin-altyapı-dockernginx-ve-veri-katmanı-otoeditdata-detaylı-incelemesi)
5. [BÖLÜM 5: İş Mantığı Katmanı (`OtoEdit.Business`) Detaylı Dosya ve Fonksiyon İncelemesi](#bölüm-5-iş-mantığı-katmanı-otoeditbusiness-detaylı-dosya-ve-fonksiyon-incelemesi)
6. [BÖLÜM 6: Web API Katmanı (`OtoEdit.API`) ve Birim Testleri (`OtoEdit.UnitTests`) Detaylı İncelemesi](#bölüm-6-web-api-katmanı-otoeditapi-ve-birim-testleri-otoedittests-detaylı-incelemesi)
7. [BÖLÜM 7: Python Worker, AI Analiz Pipeline ve FFmpeg Render Motoru (`OtoEdit.PythonWorker`) Detaylı İncelemesi](#bölüm-7-python-worker-ai-analiz-pipeline-ve-ffmpeg-render-motoru-otoeditpythonworker-detaylı-incelemesi)
8. [BÖLÜM 8: Angular Frontend (`OtoEdit.Frontend`) Detaylı Dosya, Bileşen, Sinyal ve Fonksiyon İncelemesi](#bölüm-8-angular-frontend-otoeditfrontend-detaylı-dosya-bileşen-sinyal-ve-fonksiyon-incelemesi)
9. [BÖLÜM 9: Uçtan Uca Kullanıcı Süreçleri (UI Tıklamasından Backend, Worker ve Ekrana Dönüşe Kadar Adım Adım Akışlar)](#bölüm-9-uçtan-uca-kullanıcı-süreçleri-ui-tıklamasından-backend-worker-ve-ekrana-dönüşe-kadar-adım-adım-akışlar)
10. [BÖLÜM 10: Tüm Dosyaların, Sınıfların ve Fonksiyonların Tam Teknik Referans Sözlüğü (Ekler)](#bölüm-10-tüm-dosyaların-sınıfların-ve-fonksiyonların-tam-teknik-referans-sözlüğü-ekler)
    - **EK A:** .NET Backend (`OtoEdit.Data`, `OtoEdit.Business`, `OtoEdit.API`, `OtoEdit.UnitTests`) ve Altyapı Tam Dosya & Fonksiyon Referansı
    - **EK B:** Python Worker (`OtoEdit.PythonWorker` ve `PythonWorker.Tests`) Tam Dosya & Fonksiyon Referansı
    - **EK C:** Angular Frontend (`OtoEdit.Frontend`) Tam Dosya, Sinyal & Fonksiyon Referansı

---

## BÖLÜM 1: Projenin Amacı, Felsefesi ve Çalışma Mantığı

### 1.1. OtoEdit Nedir ve Hangi Problemi Çözer?
Bir video içerik üreticisi, eğitmen, akademisyen veya sosyal medya yayıncısı kamera karşısına geçip 30–60 dakikalık bir video kaydettiğinde, çekim bittikten sonra saatler süren yorucu bir kurgu (post-prodüksiyon) süreci başlar. Konuşmacı çekim sırasında zaman zaman duraksar, nefes alır, cümleye yanlış başlayıp *"pardon, baştan alıyorum"* diyerek aynı cümleyi ikinci veya üçüncü kez tekrar okur (retake), arka planda dip gürültüsü oluşur, konuşmayı destekleyecek görseller (B-Roll) ve vurgu yazıları eklenmesi gerekir, ayrıca kelimesi kelimesine senkronize TikTok/CapCut tarzı dinamik (karaoke) altyazılar hazırlanmalıdır.

**OtoEdit**, tüm bu tekrarlayan ve uzmanlık gerektiren video kurgu işlemlerini **yapay zeka ve sinyal işleme algoritmalarıyla uçtan uca otomatize eden**, aynı zamanda kullanıcıya hem **modern bir çok kanallı (Multi-Track NLE) Timeline ve Canvas editörü** hem de **doğal dilde konuşarak kurgu yapabilen bir Yönetmen AI (Sohbet Asistanı)** sunan hibrit bir platformdur.

### 1.2. Sistemin Kalbi: Tahribatsız Kurgu ve EDL (Edit Decision List) Felsefesi
Geleneksel video işleme araçlarında videodan bir parçayı kestiğinizde veya üzerine bir yazı eklediğinizde video dosyası yeniden işlenir. Oysa 4K veya 1080p uzun bir videoyu her düzenlemede yeniden encode etmek dakikalar sürer ve kullanıcı deneyimini tamamen öldürür.

OtoEdit bu sorunu **EDL (Edit Decision List — Kurgu Karar Listesi)** mimarisiyle çözer:
1. **Ham Video Asla Bozulmaz:** Kullanıcının yüklediği orijinal video MinIO (S3) depolama alanında olduğu gibi korunur.
2. **Her Şey Bir JSON Belgesidir (`EdlJson`):** Videonun neresinin kesileceği (`cuts`), hangi saniyede ekranda hangi yazının veya görselin çıkacağı (`overlays`), kelime bazlı transkript ve altyazı zamanlamaları (`transcript`), altyazı font/renk şablonu (`settings.subtitleStyle`), arka plan müziği ve ses kısma ayarları (`settings.backgroundMusic`), renk filtreleri (`settings.colorGrading`), yüz takip koordinatları (`repurposing.faceTrackingData`) ve ses dalga formu tepe noktaları (`audioPeaks`) PostgreSQL veritabanında `edit_decision_lists` tablosunda tek bir `JSONB` belgesi olarak tutulur.
3. **Anlık Tarayıcı Simülasyonu (Sıfır Render Bekleme):** Angular tabanlı editör ekranı, ham videoyu `<video>` oynatıcısında oynatırken arka planda saniyede onlarca kez EDL JSON verisini kontrol eder. Oynatma iğnesi (Playhead) `cuts` dizisindeki kesilmiş bir saniyeye ulaştığı anda, oynatıcı milisaniyeler içinde kesimin bitiş saniyesine atlar (`video.currentTime = finalJumpTime`). Metinler, görseller, rozetler, renk filtreleri ve karaoke altyazılar ise HTML5/CSS/Canvas katmanları olarak videonun üzerinde gerçek zamanlı çizilir. Bu sayede kullanıcı 1 saatlik bir videoda bir sahneyi sildiğinde veya yazı eklediğinde **0 saniye bekleyerek** sonucu anında izler.
4. **Tek Seferlik Gerçek Render (2-Pass FFmpeg NVENC):** Kullanıcı kurgusunu bitirip **"Nihai Videoyu Render Et"** butonuna bastığında, son halini almış EDL JSON belgesi RabbitMQ üzerinden Python Worker'a gönderilir. Python Worker, FFmpeg ve NVIDIA GPU donanım hızlandırmasını (`h264_nvenc`) kullanarak tüm kesimleri, kadrajlamayı, `.ass` karaoke altyazılarını, Pillow ile üretilen 2x supersampled rozetleri, AI ile arka planı silinmiş çıkartmaları ve Sidechain Auto-Ducking uygulanmış arka plan müziğini videoya kalıcı olarak işleyip indirilebilir `.mp4` dosyasını üretir.

### 1.3. OtoEdit'in 6 Çekirdek Yapay Zeka Yeteneği
1. **Çok Motorlu & Kendi Kendini Onaran Transkripsiyon (STT):** Sesi önce Silero VAD ile analiz eder, uzun videoları kelimeleri bölmeden en derin sessizlik anlarından 10 dakikalık parçalara ayırır (`AudioChunker`), sırasıyla **Gemini 3.5 Transcribe -> Groq Whisper Large v3 Turbo -> Antigravity Proxy -> Yerel Faster-Whisper (GPU/CPU)** zinciriyle metne döker. Atlanan konuşma adacıklarını `GapFiller` ile yeniden tarar ve `WordRefiner` ile kelime başlangıç/bitiş zamanlarını gerçek ses enerjisine (RMS zarfına) milimetrik olarak kilitler.
2. **Akıllı Hatalı Tekrar Eleyici (Smart Retake Detector v3):** Konuşmacının bir cümleyi söylerken takılıp yeniden başladığı anları **Sağdan Sola Hizalama (`TakeAligner`)**, Türkçe sondan eklemeli dil kök/ek analizi, stüdyo içi meta-konuşma yakalayıcı (*"baştan alıyorum"*, *"pardon olmadı"*) ve **Gemini Semantik Denetçi (`TranscriptVerifier`)** ile tespit eder. Her zaman en son ve en temiz okumayı koruyup önceki hatalı denemeleri otomatik keser.
3. **Kelime Korumalı Jump-Cut Motoru (Jump-Cut v3):** Korunan kelimeler arasındaki duraklamaları analiz eder. Cümle içi ve cümle sonu nefes paylarını asimetrik olarak korur, kelime sonlarındaki yumuşak ünsüzlerin (`-r, -s, -ş`) yutulmasını önlemek için akustik güvenlik ağı (`_protect_speech_edges`) uygular ve kesim noktalarını ses dalgasının sıfıra en yakın olduğu yerel enerji minimumuna (`find_energy_minimum`) yaslayarak "tık/patlama" seslerini engeller.
4. **Çoklu-Modal El Hareketi ve Sesli Komut Motoru:** Konuşmacı çekim sırasında kameraya el işareti yapıp aynı anda (±2 saniye içinde) sesli komut verdiğinde (örneğin 👎 + *"Burayı kes"*, ✌️ + *"Buraya Abone Ol yazısını yaz"*, 🖐️ + *"Buraya beyin resmi koy"*, ✊ + *"Şu cümleye kadar sil"*), MediaPipe Hands 21 eklem noktası analizi ve Türkçe Regex ayrıştırıcı bu komutu yakalar, komutu yerine getirir ve komutun verildiği anı da videodan otomatik keser.
5. **Otomatik B-Roll, Öneri ve Viral Klip (Repurposing) Motoru:** Konuşma metnini Gemini ile analiz ederek videonun en vurucu anlarına uygun İngilizce arama terimleri üretir, Pexels / Unsplash / Wikimedia üzerinden telifsiz görselleri indirip timeline katmanlarına yerleştirir ve uzun videodan en yüksek viral potansiyele sahip 30–90 saniyelik Reels/Shorts kliplerini çıkarır.
6. **Yönetmen AI (Human-in-the-Loop Kurgu Sohbet Asistanı):** Kullanıcı editördeki sohbet panelinden doğal dilde *"15. saniyeye kırmızı bir uyarı yazısı ekle"* veya timeline'da bir aralığı seçip *"Seçili aralıktaki konuşmayı özetleyen bir başlık koy"* dediğinde; AI asistanı ya doğrudan önizlenebilir bir EDL yaması (`pending` patch) üretir ya da eksik bilgi varsa sohbet balonunun içinde **16:9 interaktif mini sahne** ve renk/font seçiciler içeren dinamik bir form (`clarification`) açar. Kullanıcı mini sahneye tıkladıkça ana video üzerinde canlı bir taslak (`Ghost Preview`) görür.

---

## BÖLÜM 2: Kullanılan Teknolojiler, Kütüphaneler ve Ekosistem

OtoEdit, her katmanda o iş için en uygun dili ve kütüphaneyi kullanan dağıtık, olay güdümlü (Event-Driven) bir mikroservis mimarisine sahiptir:

### 2.1. Backend (.NET 10 — Clean Architecture)
* **Çalışma Zamanı ve Çatı:** `.NET 10.0` (`ASP.NET Core Web API`)
* **Veritabanı ve ORM:**
  * `PostgreSQL 16`: İlişkisel tabloların yanı sıra `EditDecisionList`, `EdlSnapshot`, `VideoTranscript`, `ChatMessage` ve `RenderJob` tablolarında yüksek performanslı `JSONB` belge saklama özelliği için kullanılır.
  * `Entity Framework Core 10.0.5` & `Npgsql.EntityFrameworkCore.PostgreSQL 10.0.1`: Code-First veritabanı modelleme, Fluent API konfigürasyonları ve otomatik migration yönetimi için kullanılır.
* **Asenkron Mesajlaşma ve Kuyruk:**
  * `RabbitMQ 3 (Management Alpine)`: .NET API ile Python Worker arasındaki ağır video analiz ve render görevlerinin asenkron iletimi için kullanılır.
  * `MassTransit 8.3.6` & `MassTransit.RabbitMQ`: .NET tarafında olay yayınlama (`IPublishEndpoint`) ve tüketme (`IConsumer<T>`) işlemleri için kullanılır. Python Worker ile doğrudan haberleşebilmek adına `UseRawJsonSerializer()` ve `UseRawJsonDeserializer()` ile yapılandırılmıştır.
* **Önbellekleme (Caching):**
  * `Redis 7 Alpine` & `StackExchange.Redis 3.1.31`: Proje detaylarının (`project:{id}`), EDL dokümanlarının (`edl:{projectId}`), sohbet geçmişinin (`chat:{projectId}:history`) ve Python tarafında video SHA-256 analiz sonuçlarının (`otoedit:analysis:edl:{hash}`) önbelleklenmesi için kullanılır.
* **Nesne Depolama (Object Storage):**
  * `MinIO (S3 Uyumlu Depolama)` & `Minio .NET SDK 7.0.0` / `AWSSDK.S3`: Ham videoların (`videos/`), gürültüsü temizlenmiş seslerin (`audio/`), kullanıcı medya varlıklarının (`assets/`) ve render edilmiş nihai videoların (`renders/`) saklanması ve Presigned URL ile sunulması için kullanılır.
* **Gerçek Zamanlı İletişim:**
  * `ASP.NET Core SignalR`: `/pipeline-hub` üzerinden Angular arayüzüne canlı analiz yüzdesi (`AnalysisProgress`), analiz bitişi (`AnalysisCompleted`), render yüzdesi (`RenderProgress`), render bitişi (`RenderCompleted`) ve hata (`PipelineError`) bildirimlerini WebSocket ile anlık iletmek için kullanılır.
* **Yapay Zeka, Doğrulama, Dayanıklılık ve Loglama:**
  * `Mscc.GenerativeAI 3.1.0`: .NET içerisinden Google Gemini modellerine doğrudan erişim için kullanılır.
  * `FluentValidation 12.1.1`: DTO doğrulamaları için kullanılır.
  * `Microsoft.Extensions.Http.Resilience 10.10.0`: Dış HTTP çağrılarında (Pexels vb.) standart retry/circuit-breaker dayanıklılığı için kullanılır.
  * `Serilog.AspNetCore 10.0.0`: Yapılandırılmış konsol ve dosya loglaması için kullanılır.
  * `xUnit 2.9.3`, `Moq 4.20.72`, `FluentAssertions 7.2.0`: Backend birim testleri için kullanılır.

### 2.2. Python Worker (`Python 3.11` — AI, Sinyal İşleme ve Render Motoru)
* **Ses İşleme, VAD ve Sinyal Analizi:**
  * `faster-whisper >= 1.0.0` & `ctranslate2`: Hem yerel GPU/CPU Whisper STT dönüşümü hem de içinde gömülü gelen **Silero VAD** (`faster_whisper.vad`) modeliyle konuşma bölgelerinin tespiti için kullanılır.
  * `numpy >= 1.26.0` & `scipy >= 1.10.0`: 16 kHz PCM ses sinyali üzerinde 10 ms'lik RMS enerji zarfı çıkarma, yerel enerji minimumu (`argmin`) bulma, clipping (ses patlaması) hesabı ve CIE LAB renk uzayı matris işlemleri için kullanılır.
  * `noisereduce >= 3.0.0`: Spektral kapılama (spectral gating) ile ham videodaki dip gürültüsünü temizlemek için kullanılır.
  * `pydub >= 0.25.0`: Ses segmentasyonu, dBFS hesabı ve akustik puanlama için kullanılır.
* **Görüntü İşleme, Bilgisayarlı Görü ve Grafik:**
  * `mediapipe >= 0.10.0`: `mp.solutions.hands` ile 21 el eklem noktasından (landmark) jest/komut algılama ve `mp.solutions.face_detection` ile dikey (9:16) videolarda konuşmacı yüz takibi için kullanılır.
  * `opencv-python (cv2) >= 4.8.0`: Video karelerine hızlı atlama (`CAP_PROP_POS_FRAMES`), `GrabCut` arka plan ayırma, morfolojik genişletme (`cv2.dilate`) ile çıkartma konturu oluşturma ve LAB renk uzayı dönüşümleri için kullanılır.
  * `rembg[cpu] >= 2.0.50`: `u2netp` derin öğrenme modeliyle görsel katmanların arka planını tek tıkla şeffaf PNG'ye dönüştürmek için kullanılır.
  * `Pillow (PIL) >= 10.0.0`: CapCut tarzı hap/rozet (`pill`, `rounded`, `badge`) metin kutularını 2x supersampling ve Gaussian gölge ile pürüzsüz PNG olarak çizmek ve dairesel/yuvarlak maskeler üretmek için kullanılır.
* **Video Kurgu ve Render:**
  * `FFmpeg 6+` (`h264_nvenc` / `libx264`, `libass`, `sidechaincompress`) & `ffmpeg-python >= 0.2.0`: Frame-accurate paralel segment kesimi, 8ms mikro-fade, ASS karaoke altyazı gömme, çok katmanlı görsel kaplama ve konuşma başladığında müziği kısan Sidechain Auto-Ducking filtre grafiği için kullanılır.
* **Dil Modelleri, Mesajlaşma ve Veri Doğrulama:**
  * `google-generativeai >= 0.3.0` & `openai >= 1.0.0`: Gemini ve OpenAI/Groq/Proxy modelleriyle STT, semantik retake denetimi, viral klip seçimi ve B-Roll üretimi için kullanılır.
  * `pika >= 1.3.0`: RabbitMQ kuyruklarını dinlemek ve olay yayınlamak için kullanılır.
  * `pydantic >= 2.5.0`: EDL JSON şema doğrulaması ve serileştirme için kullanılır.

### 2.3. Frontend (`Angular 18.2` — Standalone NLE & AI Stüdyosu)
* **Çatı ve Durum Yönetimi:** `Angular 18.2.0` (Standalone Components, Angular **Signals** `signal()` ve `computed()`, `RxJS 7.8.1`).
* **Gerçek Zamanlı İletişim:** `@microsoft/signalr 8.0.7`.
* **Stil ve Tasarım:** `TailwindCSS 3.4.10`, özel Glassmorphism (`backdrop-filter: blur(12px)`) paneller, Google Fonts (`Montserrat`, `Inter`, `Outfit`, `Bebas Neue`, `Anton`, `Cinzel`, `Poppins` vb.) ve CSS Keyframe giriş/çıkış animasyonları.
* **Tarayıcı Medya API'leri:** HTML5 `<video>` (`fastSeek`, `timeupdate`), `Web Audio API` (`AudioContext.decodeAudioData` ile gerçek zamanlı ses dalga formu çıkarma), SVG dinamik `<path>` çizimi ve Pointer Capture API (`setPointerCapture` ile akıcı timeline/canvas sürükleme).

---

## BÖLÜM 3: Tüm Projenin Klasör ve Dosya Yapısı (Tam Harita)

Aşağıdaki ağaç yapısı, `D:\OtoEdit\OtoEdit` içerisindeki her bir klasörün ve kaynak dosyanın tam yerini ve tek cümlelik görevini göstermektedir. (Sonraki bölümlerde bu dosyaların her birinin içindeki sınıflar ve fonksiyonlar tek tek açıklanmıştır.)

```text
D:\OtoEdit\OtoEdit\
├── OtoEdit.slnx                                    # .NET 10 XML tabanlı Solution dosyası
├── docker-compose.yml                              # Tüm servisleri (API, Worker, DB, Redis, RMQ, MinIO, UI, Nginx) içeren tam Production orkestrasyonu
├── docker-compose.dev.yml                          # Geliştirme ortamı Docker orkestrasyonu (Altyapı + GPU Python Worker)
├── baslat.bat                                      # Windows'ta tek tıkla Docker + .NET API + Angular UI başlatan geliştirici scripti
├── durdur.bat                                      # Çalışan tüm OtoEdit konteyner ve süreçlerini temiz şekilde kapatan script
├── .env / .env.example                             # Ortam değişkenleri (DB, Redis, MinIO, Gemini/Groq API anahtarları, JumpCut/VAD ayarları)
├── nginx/
│   └── nginx.conf                                  # Üretim ortamı Reverse Proxy (2GB upload limiti, WebSocket/SignalR tünelleme)
├── docs/                                           # Mimari analiz, çözüm planları ve geliştirici dökümanları klasörü
│
├── src/
│   ├── OtoEdit.Data/                               # [KATMAN 1] .NET Veri Erişim ve Veritabanı Katmanı (EF Core + PostgreSQL)
│   │   ├── OtoEdit.Data.csproj                     # Data katmanı proje dosyası
│   │   ├── ServiceRegistration.cs                  # DbContext ve Repository DI kayıtlarını yapan sınıf
│   │   ├── Context/
│   │   │   └── AppDbContext.cs                     # 12 tabloyu yöneten ana EF Core DbContext sınıfı
│   │   ├── Enums/
│   │   │   ├── LogSeverity.cs                      # Log önem derecesi (Information, Warning, Error, Critical)
│   │   │   ├── PipelineAsamasi.cs                  # 10 aşamalı pipeline enum'u (SesIyilestirme, Stt, SessizlikAlgilama... Tamamlandi)
│   │   │   ├── ProjectDurumu.cs                    # Proje yaşam döngüsü durumu (Taslak, VideoYuklendi, AnalizEdiliyor... Tamamlandi, Hata)
│   │   │   ├── RenderDurumu.cs                     # Render işi durumu (Kuyrukta, RenderEdiliyor, Tamamlandi, Hata)
│   │   │   ├── VideoFormati.cs                     # Hedef video en-boy oranı (Yatay_16_9, Dikey_9_16, Kare_1_1)
│   │   │   └── VideoIslemDurumu.cs                 # Videonun alt analiz aşaması durumu
│   │   ├── Entities/
│   │   │   ├── Project.cs                          # Ana proje tablosu varlığı (projects)
│   │   │   ├── Video.cs                            # Yüklenen kaynak video varlığı (videos)
│   │   │   ├── VideoTranscript.cs                  # STT ham metin ve kelime zaman damgaları varlığı (video_transcripts)
│   │   │   ├── EditDecisionList.cs                 # Projenin aktif EDL JSONB belgesi ve versiyonu (edit_decision_lists)
│   │   │   ├── EdlSnapshot.cs                      # Undo/Redo (Memento) için geçmiş EDL anlık görüntüleri (edl_snapshots)
│   │   │   ├── ChatMessage.cs                      # Yönetmen AI sohbet geçmişi, bekleyen yamalar ve formlar (chat_messages)
│   │   │   ├── ProjectAsset.cs                     # Kullanıcının yüklediği görsel/ses/video varlıkları (ProjectAssets)
│   │   │   ├── RenderJob.cs                        # FFmpeg dışa aktarma iş kayıtları (render_jobs)
│   │   │   ├── Template.cs                         # Kurumsal video şablonları (templates)
│   │   │   ├── EndpointLog.cs                      # HTTP Request/Response log tablosu (endpoint_logs)
│   │   │   ├── FunctionLog.cs                      # Fonksiyon/Metot seviyesi hata log tablosu (function_logs)
│   │   │   └── PipelineLog.cs                      # AI ve Render pipeline aşama log tablosu (pipeline_logs)
│   │   ├── Configurations/                         # Tüm Entity'lerin PostgreSQL tablo, sütun, JSONB ve indeks eşlemeleri (11 dosya)
│   │   ├── Repositories/
│   │   │   ├── IRepository.cs & GenericRepository.cs       # Temel CRUD ve sorgulama Generic Repository yapısı
│   │   │   ├── IProjectRepository.cs & ProjectRepository.cs # Proje detaylarını ilişkileriyle çeken özel repository
│   │   │   └── IVideoRepository.cs & VideoRepository.cs     # Video ve transkript sorgulama/durum güncelleme repository'si
│   │   └── Migrations/                             # EF Core veritabanı şema geçmişi (InitialCreate, AddEdlSnapshots, AddProjectAssets)
│   │
│   ├── OtoEdit.Business/                           # [KATMAN 2] .NET İş Mantığı, AI, Önbellek, Depolama ve Kuyruk Katmanı
│   │   ├── OtoEdit.Business.csproj                 # Business katmanı proje dosyası
│   │   ├── DependencyInjection.cs                  # Servis, Validator, MinIO, Redis, Gemini ve MassTransit/RabbitMQ kayıt merkezi
│   │   ├── DTOs/                                   # API ile dış dünya arasındaki Veri Transfer Nesneleri (Asset, Chat, Edl, Pipeline, Project, Render, Template, Video)
│   │   ├── Events/                                 # RabbitMQ üzerinden Python Worker ile alışverişi yapılan 6 olay sözleşmesi
│   │   │   ├── VideoUploadedEvent.cs               # .NET -> Python: Video yüklendi, analizi başlat
│   │   │   ├── PipelineStageChangedEvent.cs        # Python -> .NET: Analiz/Render aşaması ve yüzdesi değişti
│   │   │   ├── AnalysisCompletedEvent.cs           # Python -> .NET: Analiz bitti, üretilen EDL JSON burada
│   │   │   ├── RenderRequestedEvent.cs             # .NET -> Python: Bu EDL JSON ile FFmpeg render başlat
│   │   │   ├── RenderCompletedEvent.cs             # Python -> .NET: Render bitti, MinIO çıktı yolu burada
│   │   │   └── PipelineErrorEvent.cs               # Python -> .NET: Pipeline sırasında hata oluştu
│   │   ├── Exceptions/                             # BusinessException, NotFoundException, PipelineException
│   │   ├── Helpers/                                # HashHelper (SHA-256) ve SensitiveDataMasker (Loglarda şifre/token maskeleme)
│   │   ├── Validators/                             # FluentValidation kuralları (ProjectValidators, OtherValidators)
│   │   ├── Interfaces/                             # Tüm iş ve altyapı servislerinin soyut arayüz sözleşmeleri (12 arayüz)
│   │   ├── Infrastructure/
│   │   │   ├── AI/
│   │   │   │   ├── GeminiChatProvider.cs           # 4 kademeli LLM zinciri (Proxy -> Groq -> Gemini -> Yerel Heuristics) ile çalışan Yönetmen AI motoru
│   │   │   │   └── PexelsService.cs                # Pexels API'den görsel arayıp MinIO'ya proje varlığı olarak kaydeden servis
│   │   │   ├── Cache/
│   │   │   │   └── RedisCacheService.cs            # Fail-safe StackExchange.Redis önbellek servisi
│   │   │   └── Storage/
│   │   │       ├── MinioFileStorageService.cs      # MinIO S3 dosya yükleme, indirme, silme ve Presigned URL üretme servisi
│   │   │       └── LocalFileStorageService.cs      # Yerel disk tabanlı yedek depolama servisi
│   │   └── Services/
│   │       ├── ProjectManager.cs                   # Proje CRUD, Redis cache ve MinIO dizin temizliği yöneticisi
│   │       ├── VideoManager.cs                     # Ham video doğrulama, MinIO yükleme, stream ve VideoUploadedEvent tetikleyicisi
│   │       ├── EdlManager.cs                       # EDL okuma, akıllı JSON Delta Patch birleştirme ve Memento Undo/Redo yöneticisi
│   │       ├── ChatManager.cs                      # AI sohbet, Human-in-the-Loop (pending patch) ve Clarification Form yöneticisi
│   │       ├── AssetManager.cs                     # Kullanıcı medya dosyası (görsel/ses/video) yükleme ve yönetimi
│   │       ├── RenderManager.cs                    # Render talebi oluşturma, durum takibi ve indirme URL'si yöneticisi
│   │       ├── TemplateManager.cs                  # Kurumsal şablon listeleme servisi
│   │       ├── LogManager.cs                       # 3 katmanlı veritabanı log (Endpoint, Function, Pipeline) yöneticisi
│   │       └── PipelineNotificationManager.cs      # SignalR proje odalarına canlı bildirim gönderen köprü servis
│   │
│   ├── OtoEdit.API/                                # [KATMAN 3] .NET Sunum, REST API, Middleware, SignalR ve Consumer Katmanı
│   │   ├── OtoEdit.API.csproj                      # Web API proje dosyası
│   │   ├── Program.cs                              # Uygulama başlatıcı, Kestrel 50GB limit, CORS, RateLimiter, DI ve Middleware hattı
│   │   ├── Middleware/
│   │   │   ├── ApiKeyAuthMiddleware.cs             # X-API-Key ve query string (?apiKey=) güvenlik doğrulayıcısı
│   │   │   ├── ExceptionHandlingMiddleware.cs      # Global hata yakalayıcı, DB loglayıcı ve RFC 7231 ProblemDetails üreticisi
│   │   │   └── RequestResponseLoggingMiddleware.cs # Tüm HTTP trafiğini süre ve maskelenmiş gövdeyle DB'ye kaydeden middleware
│   │   ├── Hubs/
│   │   │   └── PipelineHub.cs                      # /pipeline-hub WebSocket sunucusu (JoinProjectGroup / LeaveProjectGroup)
│   │   ├── Consumers/                              # Python Worker'dan gelen RabbitMQ mesajlarını yakalayıp DB + SignalR'a ileten 4 Consumer
│   │   │   ├── PipelineStageChangedConsumer.cs
│   │   │   ├── AnalysisNotificationConsumer.cs
│   │   │   ├── RenderNotificationConsumer.cs
│   │   │   └── PipelineErrorConsumer.cs
│   │   └── Controllers/                            # Frontend'in çağırdığı 9 REST API Controller sınıfı
│   │       ├── ProjectsController.cs               # /api/projects
│   │       ├── VideosController.cs                 # /api/projects/{projectId}/videos & /api/videos/{videoId}/stream
│   │       ├── EdlController.cs                    # /api/projects/{projectId}/edl (GET, PATCH, undo, redo)
│   │       ├── ChatController.cs                   # /api/projects/{projectId}/chat (POST, GET, apply, form)
│   │       ├── AssetsController.cs                 # /api/projects/{projectId}/assets
│   │       ├── RenderController.cs                 # /api/projects/{projectId}/render
│   │       ├── PipelineController.cs               # /api/pipeline
│   │       ├── InternalLogsController.cs           # /api/internal/logs/pipeline (Python Worker doğrudan HTTP log/progress uç noktası)
│   │       └── TemplatesController.cs              # /api/templates
│   │
│   ├── OtoEdit.PythonWorker/                       # [KATMAN 4] Python AI Analiz, Sinyal İşleme ve FFmpeg Render Mikroservisi
│   │   ├── main.py                                 # Worker giriş noktası; AnalysisConsumer ve RenderConsumer thread'lerini başlatır
│   │   ├── config.py                               # Tüm .env ayarlarını ve AI/VAD/JumpCut sabitlerini yöneten merkezi sınıf
│   │   ├── requirements.txt                        # Python kütüphane bağımlılıkları
│   │   ├── Dockerfile                              # FFmpeg + Özel Fontlar + CUDA/Python 3.11 konteyner tanımı
│   │   ├── assets/fonts/                           # Render ve Pillow için 8 adet TrueType font (Montserrat, Inter, Cinzel, Anton vb.)
│   │   ├── consumers/
│   │   │   ├── heartbeat_manager.py                # Ağır işlemlerde RabbitMQ bağlantısının düşmesini önleyen Heartbeat thread'i
│   │   │   ├── analysis_consumer.py                # video-uploaded kuyruğunu dinleyip 14 adımlı paralel AI analizini yöneten orkestratör
│   │   │   └── render_consumer.py                  # render-requested kuyruğunu dinleyip FFmpeg render ve MinIO yüklemesini yöneten sınıf
│   │   ├── models/
│   │   │   ├── command_model.py                    # Çoklu-modal komut türleri (CommandType) ve ParsedCommand modeli
│   │   │   ├── edl_model.py                        # Pydantic v2 tabanlı tam EDL JSON şeması (CutItem, OverlayItem, EdlDocument vb.)
│   │   │   ├── gesture_model.py                    # El hareketi enum'u (GestureType) ve GestureResult modeli
│   │   │   └── transcript_model.py                 # WordTimestamp, TranscriptSegment ve TranscriptResult veri sınıfları
│   │   ├── pipeline/
│   │   │   ├── audio_analysis.py                   # Tek geçişte 16kHz PCM, Silero VAD, 10ms RMS zarfı ve 1000 peak çıkaran temel analizör
│   │   │   ├── audio_enhancer.py                   # noisereduce ve FFmpeg afftdn ile arka plan gürültü temizleyici
│   │   │   ├── acoustic_scorer.py                  # RAM önbellekli ses patlaması (clipping), seviye (RMS) ve süreklilik puanlayıcı
│   │   │   ├── transcriber.py                      # Chunker + STTEngineChain + GapFiller + WordRefiner orkestratörü ve kesim duyarlı segment üretici
│   │   │   ├── word_refiner.py                     # Şişmiş kelime zamanlarını gerçek konuşma enerjisi kümelerine kilitleyen 2 aşamalı modül
│   │   │   ├── take_aligner.py                     # Türkçe kök/ek korumalı, sağdan sola (Right-Anchored) deterministik Retake hizalayıcı
│   │   │   ├── retake_detector.py                  # TakeAligner + AcousticScorer + TranscriptVerifier birleşik Retake orkestratörü
│   │   │   ├── transcript_verifier.py              # Gemini LLM ile anlamsal tekrar ve yarım bırakılmış cümle denetçisi
│   │   │   ├── silence_detector.py                 # Kelime korumalı ve akustik güvenlik ağlı Jump-Cut v3 / v2 / legacy sessizlik kesici
│   │   │   ├── gesture_detector.py                 # MediaPipe Hands 21 landmark sınıflandırıcı (Smart Windowing destekli)
│   │   │   ├── voice_command_parser.py             # Transkript içinde Türkçe sesli komutları yakalayan Regex ayrıştırıcı
│   │   │   ├── multimodal_command_engine.py        # El hareketi ile sesli komutu ±2.0s toleransla eşleştiren doğrulama motoru
│   │   │   ├── face_tracker.py                     # MediaPipe Face Detection + EMA/Deadzone yumuşatmalı dikey kadraj yüz takipçisi
│   │   │   ├── auto_broll_engine.py                # Gemini + Pexels ile konuşmaya uygun otomatik stok görsel katmanı üreticisi
│   │   │   ├── repurposing_engine.py               # Uzun videodan viral Reels/Shorts klipleri çıkaran motor
│   │   │   ├── suggestion_engine.py                # Kullanıcı onayına sunulan B-Roll ve vurgu yazısı öneri motoru
│   │   │   ├── edl_builder.py                      # Tüm analiz çıktılarını birleştiren ve kesim türlerini koruyan EDL inşa edici
│   │   │   └── stt/                                # Çoklu STT Motor Paketi
│   │   │       ├── base.py                         # Word, TranscriptionResult ve BaseSTTEngine soyut sınıfı
│   │   │       ├── chunker.py                      # Uzun sesleri VAD sessizlik ortalarından 10 dakikalık MP3 parçalarına bölen modül
│   │   │       ├── rate_limiter.py                 # Çoklu Gemini API anahtarı rotasyonu ve 429 cooldown yöneticisi
│   │   │       ├── gemini_transcribe.py            # Birincil STT: Google gemini-3.5-transcribe (verbatim + kelime zaman damgalı)
│   │   │       ├── groq_engine.py                  # İkincil STT: Groq Cloud whisper-large-v3-turbo
│   │   │       ├── proxy_gemini.py                 # Üçüncül STT: Antigravity Proxy gemini-3.8-flash-tiered
│   │   │       ├── local_whisper.py                # Dördüncül STT: Yerel GPU/CPU faster-whisper çevrimdışı motoru
│   │   │       ├── engine_chain.py                 # 4 STT motoru arasında otomatik Failover ve kota takibi yapan zincir
│   │   │       └── gap_filler.py                   # VAD'ın konuşma bulup STT'nin atladığı boşlukları yeniden tarayan kurtarıcı
│   │   ├── render/
│   │   │   ├── video_renderer.py                   # 2-Pass FFmpeg NVENC/libx264, paralel kesim, 8ms mikro-fade ve birleştirme motoru
│   │   │   ├── timeline_mapper.py                  # Kesimler sonrası tüm altyazı ve overlay zamanlarını yeni videoya haritalayan matematik motoru
│   │   │   ├── text_overlay.py                     # Serbest metinleri ve Karaoke kelime vurgulu altyazıları .ass dosyasına çeviren motor
│   │   │   ├── pillow_graphics_engine.py           # 2x supersampling ile hap/rozet (pill/rounded/badge) PNG üreten grafik motoru
│   │   │   ├── image_overlay.py                    # Görsel/B-Roll/Sticker katmanlarını Z-Index sırasıyla FFmpeg overlay filtrelerine bağlayan modül
│   │   │   ├── audio_mixer.py                      # Arka plan müziği döngüsü ve Sidechain Compression (Auto-Ducking) ses mikseri
│   │   │   ├── animation_effects.py                # Giriş ve çıkış animasyonları için ASS etiketleri ve FFmpeg koordinat formülleri
│   │   │   ├── dynamic_subtitle_generator.py       # 4'er kelimelik gruplar halinde dinamik ASS altyazı üreticisi
│   │   │   └── template_applier.py                 # Kurumsal logo ve konuşmacı alt bandını (Lower Third) EDL'ye işleyen modül
│   │   ├── services/
│   │   │   ├── analysis_cache.py                   # Hızlı 3-blok SHA-256 video hash ve Redis EDL idempotency servisi
│   │   │   ├── bg_remover.py                       # Rembg u2netp arka plan silme, GrabCut, CIE LAB Chroma Key, şekil maskesi ve Sticker konturu
│   │   │   ├── gemini_client.py                    # Proxy ve resmi Gemini SDK destekli LLM istemcisi
│   │   │   ├── minio_client.py                     # MinIO video/ses/render indirme ve yükleme istemcisi
│   │   │   ├── pexels_client.py                    # Pexels fotoğraf arama ve indirme istemcisi
│   │   │   ├── stock_media_fallback.py             # Pexels yedekleri: Unsplash Public NAPI ve Wikimedia Commons API istemcisi
│   │   │   ├── pipeline_logger.py                  # 3 katmanlı (Konsol + RabbitMQ + HTTP API) fail-safe ilerleme kaydedici
│   │   │   └── rabbitmq_publisher.py               # Thread-safe RabbitMQ fanout event yayınlayıcı
│   │   └── utils/ & tools/
│   │       ├── constants.py                        # Enum, kuyruk ve tolerans sabitleri
│   │       ├── janitor.py                          # Geçici dosya ve yetim render klasörü temizleyici
│   │       ├── logger.py                           # UTF-8 dosya ve konsol log yapılandırması
│   │       ├── cut_benchmark.py                    # Sessizlik kesimi ve mikro-klip benchmark aracı
│   │       └── eval_edit.py                        # İnsan kurgusu ile OtoEdit EDL kurgusunu kelime bazında karşılaştıran doğruluk ölçüm aracı
│   │
│   └── OtoEdit.Frontend/                           # [KATMAN 5] Angular 18 Standalone Web Uygulaması ve NLE Kurgu Stüdyosu
│       ├── package.json & angular.json             # NPM bağımlılıkları ve Angular CLI yapılandırması
│       ├── tailwind.config.js & src/styles.scss    # Karanlık tema, renkler, glassmorphism ve giriş/çıkış animasyonları
│       ├── proxy.conf.json & nginx.conf            # Geliştirme ve üretim ortamı API / SignalR proxy yönlendirmeleri
│       └── src/app/
│           ├── app.component.ts                    # Kök <router-outlet> bileşeni
│           ├── app.config.ts                       # Zone.js, Router, HttpClient (apiKeyInterceptor) ve Animations sağlayıcıları
│           ├── app.routes.ts                       # 4 ana sayfa rotası ('', 'project/:id', 'project/:id/editor', 'project/:id/render/:renderJobId')
│           ├── core/
│           │   ├── interceptors/api-key.interceptor.ts # Her HTTP isteğine X-API-Key başlığı ekleyen fonksiyonel interceptor
│           │   ├── models/                         # TypeScript veri modelleri (asset, chat, edl, project, render, template, video)
│           │   └── services/                       # 10 çekirdek servis (api, asset, chat, diagnostics, edl, project, render, signalr, template, video)
│           ├── shared/
│           │   ├── components/                     # Ortak UI bileşenleri (navbar, progress-bar, status-badge)
│           │   └── pipes/                          # Formatlama boruları (duration.pipe.ts: MM:SS, file-size.pipe.ts: MB/GB)
│           └── features/
│               ├── project-list/project-list.component.ts     # Proje listeleme, silme ve yeni proje oluşturma modalı ekranı
│               ├── project-detail/project-detail.component.ts # Sürükle-bırak video yükleme, AI pipeline tercihleri, şablon seçimi ve canlı analiz ekranı
│               ├── editor/editor.component.ts                 # 6142 satırlık Tam Teşekküllü NLE Timeline, Canvas, Altyazı, Waveform ve AI Kurgu Stüdyosu
│               └── render-result/render-result.component.ts   # Canlı FFmpeg render ilerlemesi, video önizleme ve MP4 indirme ekranı
│
└── tests/
    ├── OtoEdit.UnitTests/                          # .NET Backend xUnit + Moq + InMemory DB birim testleri (19 test dosyası)
    └── PythonWorker.Tests/                         # Python Worker pytest birim testleri
```

---

## BÖLÜM 4: Kök Dizin, Altyapı (Docker/Nginx) ve Veri Katmanı (`OtoEdit.Data`) Detaylı İncelemesi

Bu bölümde projenin nasıl ayağa kalktığını sağlayan altyapı dosyalarını ve veritabanı mimarisini oluşturan `OtoEdit.Data` katmanındaki her bir dosyayı ve fonksiyonu inceliyoruz.

### 4.1. Kök Dizin ve Altyapı Dosyaları

#### 1. [`OtoEdit.slnx`](file:///d:/OtoEdit/OtoEdit/OtoEdit.slnx)
.NET 10 ile gelen yeni nesil XML tabanlı Solution dosyasıdır. İçerisinde `/src/` klasörü altında `OtoEdit.API`, `OtoEdit.Business`, `OtoEdit.Data` projelerini ve `/tests/` klasörü altında `OtoEdit.UnitTests` projesini birbirine bağlar.

#### 2. [`docker-compose.yml`](file:///d:/OtoEdit/OtoEdit/docker-compose.yml) ve [`docker-compose.dev.yml`](file:///d:/OtoEdit/OtoEdit/docker-compose.dev.yml)
* **`docker-compose.yml` (Tam Konteyner / Production Modu):** Tüm 7 servisi (`otoedit-api`, `otoedit-worker`, `otoedit-postgres`, `otoedit-redis`, `otoedit-rabbitmq`, `otoedit-minio`, `otoedit-frontend`, `otoedit-nginx`) Docker ağında ayağa kaldırır. `python-worker` servisi `deploy.resources.reservations.devices` altında `driver: nvidia`, `capabilities: [gpu]` tanımlamasıyla ana makinenin NVIDIA ekran kartına doğrudan erişir.
* **`docker-compose.dev.yml` (Hibrit Geliştirici Modu):** Geliştirme yaparken `.NET API` ve `Angular Frontend`'i Windows üzerinde doğrudan (Hot-Reload ve Debugger ile) çalıştırabilmek için yalnızca altyapı servislerini (`postgres`, `redis`, `rabbitmq`, `minio`) ve GPU'lu `python-worker` servisini Docker'da başlatır.
  * **Kritik RabbitMQ Ayarı:** Uzun süren 1 saatlik video analizlerinde RabbitMQ'nun tüketiciyi zaman aşımına uğratıp bağlantıyı kesmemesi için `RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS: "-rabbit consumer_timeout 36000000"` (10 saat timeout) parametresi verilmiştir.
  * **Canlı Kod Bağlantısı:** `./src/OtoEdit.PythonWorker:/app` volume bağlaması sayesinde Python kodlarında yapılan değişiklikler konteyneri yeniden build etmeye gerek kalmadan anında yansır.

#### 3. [`baslat.bat`](file:///d:/OtoEdit/OtoEdit/baslat.bat) ve [`durdur.bat`](file:///d:/OtoEdit/OtoEdit/durdur.bat)
* **`baslat.bat`:** Geliştiricinin projeyi tek tıkla başlatması için yazılmış otomasyon betiğidir:
  1. Önceki çalışmadan kalan açık `OtoEdit.API.exe` ve konsol pencerelerini temizler.
  2. `.env` dosyası yoksa `.env.example`'dan oluşturur ve içindeki tüm değişkenleri Windows ortam değişkenlerine (`set "KEY=VALUE"`) yükler.
  3. `docker-compose -f docker-compose.dev.yml up -d --wait` komutuyla PostgreSQL, Redis, RabbitMQ, MinIO ve Python Worker'ı başlatıp sağlık kontrollerinin (`healthy`) geçmesini bekler.
  4. `dotnet build OtoEdit.slnx -c Debug` ile .NET çözümünü derler.
  5. Üç ayrı terminal penceresi açarak birinde `.NET API`'yi (`http://localhost:5001`), ikincisinde `docker logs -f otoedit-dev-worker` ile Python loglarını, üçüncüsünde ise `npm start` ile Angular arayüzünü (`http://localhost:4200`) başlatır ve tarayıcıda otomatik açar.
* **`durdur.bat`:** `docker-compose -f docker-compose.dev.yml stop` ile konteynerleri durdurur ve açık olan API, Worker log ve UI konsol pencerelerini kapatır.

#### 4. [`nginx/nginx.conf`](file:///d:/OtoEdit/OtoEdit/nginx/nginx.conf)
Ters vekil (Reverse Proxy) sunucu ayarlarını içerir. Büyük video yüklemeleri için `client_max_body_size 2048M;` (ve Frontend Nginx'te `50G`) sınırını tanımlar. `/api/` isteklerini arka plandaki .NET API sunucusuna iletirken, `/pipeline-hub` isteklerinde `Upgrade` ve `Connection "upgrade"` başlıklarını ve `86400s` (24 saat) okuma süresini tanımlayarak SignalR WebSocket bağlantılarının kopmadan açık kalmasını sağlar.

---

### 4.2. Veri Erişim Katmanı (`src/OtoEdit.Data`)

`OtoEdit.Data` katmanı, uygulamanın veritabanı şemasını, varlıklarını (Entities), durum sabitlerini (Enums) ve veritabanı sorgularını (Repositories) barındırır.

#### 1. [`ServiceRegistration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/ServiceRegistration.cs) ve [`Context/AppDbContext.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Context/AppDbContext.cs)
* **`ServiceRegistration.AddDataLayer(this IServiceCollection services, string connectionString)`:**
  * `AppDbContext` sınıfını PostgreSQL sürücüsü (`UseNpgsql`) ile Dependency Injection konteynerine kaydeder.
  * `IRepository<T>` -> `GenericRepository<T>`, `IProjectRepository` -> `ProjectRepository` ve `IVideoRepository` -> `VideoRepository` servislerini `Scoped` (HTTP isteği başına bir örnek) olarak bağlar.
* **`AppDbContext`:**
  * Veritabanındaki **12 tabloyu** temsil eden `DbSet<T>` özelliklerini barındırır: `Projects`, `Videos`, `VideoTranscripts`, `EditDecisionLists`, `EdlSnapshots`, `Templates`, `ChatMessages`, `RenderJobs`, `EndpointLogs`, `FunctionLogs`, `PipelineLogs` ve `ProjectAssets`.
  * **`OnModelCreating(ModelBuilder modelBuilder)`:** `ApplyConfigurationsFromAssembly` metodunu çağırarak `Configurations/` klasöründeki tüm tablo tasarım sınıflarını otomatik olarak yükler.

#### 2. `Enums/` Klasöründeki Durum Sabitleri
1. **[`ProjectDurumu.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Enums/ProjectDurumu.cs):** Bir projenin yaşam döngüsünü belirler: `Taslak (0)` (yeni açıldı), `VideoYuklendi (1)`, `AnalizEdiliyor (2)` (Python Worker çalışıyor), `AnalizTamamlandi (3)` (EDL hazır, editörde düzenlenebilir), `RenderEdiliyor (4)` (FFmpeg çalışıyor), `Tamamlandi (5)` (MP4 hazır) ve `Hata (99)`.
2. **[`PipelineAsamasi.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Enums/PipelineAsamasi.cs):** `[JsonConverter(typeof(JsonStringEnumConverter))]` özniteliği taşır; böylece JSON içinde sayı yerine metin olarak serileşir. Değerleri: `SesIyilestirme (0)`, `Stt (1)`, `SessizlikAlgilama (2)`, `KomutAlgilama (3)`, `YuzTakibi (4)`, `Repurposing (5)`, `OneriOlusturma (6)`, `EdlOlusturma (7)`, `Render (8)`, `Tamamlandi (9)`.
3. **[`VideoFormati.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Enums/VideoFormati.cs):** `Yatay_16_9 (0)` (YouTube/Masaüstü), `Dikey_9_16 (1)` (Reels/Shorts/TikTok), `Kare_1_1 (2)` (Instagram Post).
4. **[`VideoIslemDurumu.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Enums/VideoIslemDurumu.cs):** Videonun alt işlem durumunu tutar (`Bekliyor`, `SesIyilestirmeBasladi`, `SttBasladi`, `SttTamamlandi`, `SessizlikAlgilamaBasladi`, `KomutAlgilamaBasladi`, `YuzTakibiBasladi`, `AnalizTamamlandi`, `Hata`).
5. **[`RenderDurumu.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Enums/RenderDurumu.cs):** `Kuyrukta (0)`, `RenderEdiliyor (1)`, `Tamamlandi (2)`, `Hata (99)`.
6. **[`LogSeverity.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Enums/LogSeverity.cs):** `Information (0)`, `Warning (1)`, `Error (2)`, `Critical (3)`.

#### 3. `Entities/` ve `Configurations/` Klasörlerindeki Veritabanı Tabloları
Her bir Entity sınıfı ve onun `Configurations/` altındaki Fluent API eşleme dosyası birlikte çalışarak PostgreSQL şemasını oluşturur:

1. **[`Project.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/Project.cs) & [`ProjectConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/ProjectConfiguration.cs) (`projects` tablosu):**
   * Projenin kimliğini (`Id`), adını (`Ad`), açıklamasını (`Aciklama`), hedef formatını (`VideoFormati`), seçili şablonunu (`TemplateId`), el hareketi komutlarının açık olup olmadığını (`GestureCommandsEnabled`), ses iyileştirme tercihini (`AudioEnhancementEnabled`) ve durumunu (`Durum`) tutar.
   * **İlişkiler:** Bir projenin 1 adet `Video`'su (1:1 Cascade), 1 adet `EditDecisionList`'i (1:1 Cascade), N adet `ChatMessage`'ı (1:N Cascade), N adet `RenderJob`'ı (1:N Cascade) ve N adet `ProjectAsset`'i vardır. Yani proje silindiğinde veritabanındaki tüm bağlı kayıtlar otomatik silinir.
2. **[`Video.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/Video.cs) & [`VideoConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/VideoConfiguration.cs) (`videos` tablosu):**
   * Yüklenen ham videonun başlığını (`Baslik`), MinIO üzerindeki nesne anahtarını (`DosyaYolu`), gürültüsü temizlenmiş ses dosyasının MinIO yolunu (`TemizSesYolu`), süresini (`Sure`), bayt cinsinden boyutunu (`DosyaBoyutu`) ve işlem durumunu (`IslemDurumu`) saklar.
3. **[`VideoTranscript.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/VideoTranscript.cs) & [`VideoTranscriptConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/VideoTranscriptConfiguration.cs) (`video_transcripts` tablosu):**
   * Videonun tam konuşma metnini (`HamMetin`), kelime ve segment bazlı zaman damgalarını (`ZamanDamgalari` — `jsonb` sütunu), dilini (`Dil`), kelime sayısını (`KelimeSayisi`), kullanılan STT modelini (`SttModel`) ve işlem süresini (`SttSuresiMs`) tutar.
4. **[`EditDecisionList.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/EditDecisionList.cs) & [`EditDecisionListConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/EditDecisionListConfiguration.cs) (`edit_decision_lists` tablosu):**
   * Projenin aktif kurgu belgesidir. `EdlJson` (`jsonb`) sütununda tüm kesimler, katmanlar, altyazılar ve ayarlar tutulur. Her değişiklikte `Versiyon` (`int`) alanı 1 artırılır.
5. **[`EdlSnapshot.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/EdlSnapshot.cs) & [`EdlSnapshotConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/EdlSnapshotConfiguration.cs) (`edl_snapshots` tablosu):**
   * Kullanıcı editörde `Ctrl+Z` (Geri Al) veya `Ctrl+Y` (İleri Al) yaptığında kullanılan **Memento** geçmiş tablosudur. `ProjectId`, `Versiyon`, `EdlJson` (`jsonb`), `Aciklama` ve `Kaynak` (`"system"` = Undo yığını, `"system_undo"` = Redo yığını) alanlarını içerir. `(project_id, versiyon)` üzerinde Unique indeks vardır.
6. **[`ChatMessage.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/ChatMessage.cs) & [`ChatMessageConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/ChatMessageConfiguration.cs) (`chat_messages` tablosu):**
   * Yönetmen AI sohbet geçmişini tutar. `Rol` (`"user"` / `"assistant"`), `Mesaj`, uygulanan yama veya clarification form alanlarını tutan `EdlPatch` (`jsonb`), henüz kullanıcı onayı bekleyen yamayı tutan `PendingEdlPatch` (`jsonb`) ve `PatchDurumu` (`"none"`, `"pending"`, `"applied"`, `"rejected"`, `"clarification"`) sütunlarına sahiptir.
7. **[`ProjectAsset.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/ProjectAsset.cs) (`ProjectAssets` tablosu):**
   * Kullanıcının editördeki "Medya" sekmesinden yüklediği görsel, müzik veya B-Roll videolarının dosya adını (`DosyaAdi`), MIME türünü (`MimeTuru`), MinIO anahtarını (`StorageKey`), Presigned URL'sini (`Url`) ve boyutunu (`BoyutByte`) saklar.
8. **[`RenderJob.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/RenderJob.cs) & [`RenderJobConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/RenderJobConfiguration.cs) (`render_jobs` tablosu):**
   * Her "Render Et" talebinde o anki EDL'nin kopyasını (`EdlSnapshot` — `jsonb`), render durumunu (`Durum`), tamamlandığında oluşan MP4 dosyasının MinIO yolunu (`CiktiYolu`), başlangıç/bitiş zamanlarını, süresini (`SureMs`) ve varsa hata mesajını (`HataMesaji`) tutar.
9. **[`Template.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/Template.cs) & [`TemplateConfiguration.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Configurations/TemplateConfiguration.cs) (`templates` tablosu):**
   * Kurumsal video şablonlarını (logo yolu, logo konumu, konuşmacı adı gösterimi, varsayılan altyazı stili/fontu/rengi) tutar.
10. **Log Tabloları ([`EndpointLog.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/EndpointLog.cs), [`FunctionLog.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/FunctionLog.cs), [`PipelineLog.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Entities/PipelineLog.cs)):**
    * `endpoint_logs`: Gelen her HTTP isteğinin metodunu, yolunu, maskelenmiş istek/yanıt gövdesini, durum kodunu ve milisaniye süresini tutar.
    * `function_logs`: Kod içinde yakalanan istisnaların hangi sınıf, hangi metot, hangi dosya ve hangi satır numarasında (`LineNumber`) patladığını ve StackTrace bilgisini tutar.
    * `pipeline_logs`: Python Worker'daki her bir AI analiz ve render aşamasının başlangıç, bitiş, yüzde, girdi/çıktı JSONB metadata ve hata detaylarını tutar.

#### 4. `Repositories/` Klasöründeki Veri Erişim Sınıfları ve Fonksiyonları
1. **[`IRepository.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Repositories/IRepository.cs) & [`GenericRepository.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Repositories/GenericRepository.cs):**
   * Tüm tablolar için ortak olan `GetByIdAsync(Guid id)`, `GetAllAsync(bool asNoTracking = true)`, `FindAsync(predicate, asNoTracking)`, `Query(asNoTracking)`, `AddAsync(entity)`, `Update(entity)`, `Delete(entity)` ve `SaveChangesAsync()` fonksiyonlarını sağlar. Okuma sorgularında varsayılan olarak `AsNoTracking()` kullanarak EF Core bellek takibi yükünü ortadan kaldırır.
2. **[`IProjectRepository.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Repositories/IProjectRepository.cs) & [`ProjectRepository.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Repositories/ProjectRepository.cs):**
   * **`GetProjectWithDetailsAsync(Guid id, bool asNoTracking = true)`:** Tek bir SQL sorgusuyla projeyi; bağlı `Video`, videonun `Transcript`'i, `Template`, `EditDecisionList` ve `RenderJobs` tablolarıyla birlikte (`Include` / `ThenInclude`) getirir.
   * **`GetProjectsPagedAsync(int pageNumber, int pageSize, bool asNoTracking = true)`:** Projeleri oluşturulma tarihine göre yeniden eskiye (`OrderByDescending`) sıralayarak sayfalı biçimde ve toplam kayıt sayısıyla birlikte döner.
   * **`UpdateStatusAsync(Guid id, ProjectDurumu durum)`:** Projenin yalnızca `Durum` ve `GuncellemeTarihi` alanlarını hızlıca güncelleyip kaydeder.
3. **[`IVideoRepository.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Repositories/IVideoRepository.cs) & [`VideoRepository.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Data/Repositories/VideoRepository.cs):**
   * **`GetByProjectIdAsync(Guid projectId, bool asNoTracking = true)`:** Projeye ait videoyu `Transcript` tablosuyla birlikte getirir.
   * **`UpdateStatusAsync(Guid videoId, VideoIslemDurumu status)`:** Videonun analiz aşaması durumunu günceller; eğer yeni durum `AnalizTamamlandi` ise `IslemTamamlanmaTarihi = DateTime.UtcNow` atamasını otomatik yapar.

---

## BÖLÜM 5: İş Mantığı Katmanı (`OtoEdit.Business`) Detaylı Dosya ve Fonksiyon İncelemesi

`OtoEdit.Business` katmanı, uygulamanın beyin kısmıdır. Veri doğrulama, Redis önbellekleme, MinIO S3 dosya yönetimi, RabbitMQ olay mesajlaşması, 4 kademeli LLM (Yapay Zeka) sohbet motoru, Memento tabanlı Undo/Redo sistemi ve tüm iş kuralları bu katmanda yer alır.

### 5.1. Bağımlılık Enjeksiyonu Merkezi: [`DependencyInjection.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DependencyInjection.cs)
* **`AddBusinessLayer(this IServiceCollection services, IConfiguration configuration, Action<IBusRegistrationConfigurator>? configureMassTransit = null)`:**
  1. Derlemedeki tüm `FluentValidation` doğrulayıcılarını otomatik kaydeder.
  2. `Minio:Endpoint`, `AccessKey`, `SecretKey` ayarlarıyla resmi MinIO istemcisini ve `IFileStorageService` -> `MinioFileStorageService` sınıfını bağlar.
  3. `Redis:ConnectionString` (`AbortOnConnectFail = false`) ile `IConnectionMultiplexer` ve `ICacheService` -> `RedisCacheService` sınıfını `Singleton` olarak bağlar.
  4. `IChatProvider` -> `GeminiChatProvider` ve 9 ana Manager servisini (`LogManager`, `PipelineNotificationManager`, `ProjectManager`, `VideoManager`, `EdlManager`, `ChatManager`, `RenderManager`, `AssetManager`, `TemplateManager`, `PexelsService`) kaydeder.
  5. **MassTransit & RabbitMQ Yapılandırması:** Normalde MassTransit mesajları kendi özel zarfı (envelope) içine sarar; ancak karşı tarafta `.NET` değil `Python (pika)` çalıştığı için `cfg.UseRawJsonSerializer()` ve `cfg.UseRawJsonDeserializer()` çağrılarak mesajların saf JSON olarak gönderilip alınması sağlanır. Ayrıca `cfg.UseMessageRetry(r => r.Exponential(3, ...))` ile geçici hatalarda 3 kez üstel bekleme ile yeniden deneme politikası uygulanır.

---

### 5.2. Veri Transfer Nesneleri (`DTOs/`) ve Olay Sözleşmeleri (`Events/`)

#### 1. `DTOs/` Klasöründeki Tüm Dosyalar
* **[`DTOs/Project/ProjectCreateDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Project/ProjectCreateDto.cs), [`ProjectUpdateDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Project/ProjectUpdateDto.cs), [`ProjectListDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Project/ProjectListDto.cs), [`ProjectDetailDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Project/ProjectDetailDto.cs):** Proje oluşturma, güncelleme, ana sayfa kart listesi ve detay sayfası veri modelleridir. `ProjectDetailDto` içerisinde projenin bağlı `VideoDetailDto` nesnesi, aktif `EdlVersiyon` numarası, `ChatMesajSayisi` ve en son `RenderStatusDto` bilgisi yer alır.
* **[`DTOs/Video/VideoUploadDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Video/VideoUploadDto.cs), [`VideoDetailDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Video/VideoDetailDto.cs), [`VideoListDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Video/VideoListDto.cs):** `VideoUploadDto` sınıfı `IFormFile File` ile birlikte kullanıcının seçtiği 4 akıllı yönetmen bayrağını (`AutoJumpcut = true`, `AutoRetake = true`, `AutoBroll = true`, `AutoSubtitles = false`) taşır.
* **[`DTOs/Edl/EdlDtos.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Edl/EdlDtos.cs):** `EdlDto` (`ProjectId`, `Versiyon`, `JsonElement Edl`, `GuncellemeTarihi`), `EdlPatchDto` ve `EdlPatchResponseDto` kayıtlarını içerir.
* **[`DTOs/Chat/ChatDtos.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Chat/ChatDtos.cs):** Kullanıcı mesajını (`ChatMessageDto`), geçmiş listesini (`ChatMessageHistoryDto`), LLM iç sonucunu (`ChatResult`: `intent`, `mesaj`, `edlPatch`, `formFields`) ve API yanıtını (`ChatResponseDto`) tanımlar.
* **[`DTOs/Asset/AssetDtos.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Asset/AssetDtos.cs), [`DTOs/Render/RenderStatusDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Render/RenderStatusDto.cs), [`DTOs/Template/TemplateDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Template/TemplateDto.cs), [`DTOs/Pipeline/PipelineStatusDto.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/DTOs/Pipeline/PipelineStatusDto.cs):** Medya varlıkları, render durumu, şablon ve pipeline ilerleme modelleri.

#### 2. `Events/` Klasöründeki RabbitMQ Mesaj Sözleşmeleri
1. **[`VideoUploadedEvent.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Events/VideoUploadedEvent.cs) (.NET -> Python):** Kullanıcı videoyu yüklediği anda fırlatılır. İçinde `VideoId`, `ProjectId`, `DosyaYolu` (MinIO anahtarı), `VideoFormati`, `GestureCommandsEnabled`, `AudioEnhancementEnabled`, `AutoJumpcutEnabled`, `AutoRetakeEnabled`, `AutoBrollEnabled` ve `AutoSubtitlesEnabled` alanlarını taşır.
2. **[`PipelineStageChangedEvent.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Events/PipelineStageChangedEvent.cs) (Python -> .NET):** Python Worker her analiz adımında (`ProjectId`, `VideoId`, `Asama`, `Yuzde`, `Mesaj`) bu olayı yayınlar.
3. **[`AnalysisCompletedEvent.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Events/AnalysisCompletedEvent.cs) (Python -> .NET):** Analiz bittiğinde üretilen tam `EdlJson` (`JsonDocument`) belgesini .NET API'ye taşır.
4. **[`RenderRequestedEvent.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Events/RenderRequestedEvent.cs) (.NET -> Python):** Kullanıcı "Render Et" dediğinde `RenderJobId`, `ProjectId` ve güncel `EdlJson` belgesini Python Render Consumer'a iletir.
5. **[`RenderCompletedEvent.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Events/RenderCompletedEvent.cs) (Python -> .NET):** FFmpeg render tamamlandığında `RenderJobId`, `ProjectId` ve MinIO çıktı yolunu (`IndirmeUrl`) bildirir.
6. **[`PipelineErrorEvent.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Events/PipelineErrorEvent.cs) (Python -> .NET):** Analiz veya render sırasında oluşan kritik hatayı (`Asama`, `HataMesaji`) bildirir.

---

### 5.3. İstisnalar (`Exceptions/`), Yardımcılar (`Helpers/`) ve Doğrulayıcılar (`Validators/`)

* **[`Exceptions/BusinessException.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Exceptions/BusinessException.cs), [`NotFoundException.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Exceptions/NotFoundException.cs), [`PipelineException.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Exceptions/PipelineException.cs):** İş kuralı ihlallerinde fırlatılan özel istisna sınıflarıdır. `ExceptionHandlingMiddleware` tarafından yakalanıp otomatik olarak uygun HTTP durum koduna (`400 Bad Request` veya `404 Not Found`) çevrilirler.
* **[`Helpers/HashHelper.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Helpers/HashHelper.cs):**
  * **`ComputeSha256Hash(string rawData)`:** Verilen metnin UTF-8 baytları üzerinden 64 karakterlik küçük harf hexadecimal SHA-256 özetini hesaplar.
* **[`Helpers/SensitiveDataMasker.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Helpers/SensitiveDataMasker.cs):**
  * **`Mask(string? input)` & `MaskJson(string? input)`:** Log veritabanına (`endpoint_logs`, `function_logs`, `pipeline_logs`) kayıt atılmadan önce derlenmiş (`RegexOptions.Compiled`) düzenli ifadelerle JSON içindeki `password`, `token`, `apiKey`, `api_key`, `secret`, `authorization` alanlarını `"***"` ile, e-posta adreslerini ise `***@***.***` ile maskeleyerek güvenlik sızıntılarını önler.
* **[`Validators/ProjectValidators.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Validators/ProjectValidators.cs) & [`OtherValidators.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Validators/OtherValidators.cs):**
  * `ProjectCreateValidator` / `ProjectUpdateValidator`: Proje adının boş olmamasını ve maksimum 200 karakter olmasını denetler.
  * `VideoUploadValidator`: Yüklenen videonun boş olmamasını, maksimum **50 GB** (`53.687.091.200` byte) olmasını ve uzantısının `.mp4, .mkv, .avi, .mov, .webm` formatlarından biri olmasını zorunlu kılar.
  * `ChatMessageValidator`: Sohbet mesajının boş olmamasını ve 4000 karakteri aşmamasını denetler.

---

### 5.4. Altyapı Servisleri (`Infrastructure/`)

#### 1. [`Infrastructure/AI/GeminiChatProvider.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs) (`IChatProvider`)
Editör ekranındaki **Yönetmen AI (Sohbet Asistanı)** özelliğinin beynidir. Kullanıcının doğal dilde yazdığı mesajı, videonun transkriptini, son sohbet geçmişini ve mevcut EDL JSON belgesini alarak yapılandırılmış bir `ChatResult` döner.

* **`ProcessCommandAsync(string userMessage, string currentEdlJson, string? transcriptText, List<ChatHistoryItem> history, CancellationToken ct)`:**
  1. **Sistem Promptu İnşası:** Yapay zekaya 4 farklı `intent` (niyet) türünden birini seçmesini emreden detaylı bir Türkçe sistem yönergesi hazırlar:
     * `information`: Kullanıcı sadece videonun içeriği hakkında soru soruyorsa (örn. *"Tevekkül kelimesi hangi saniyede geçiyor?"*).
     * `suggestion`: Kullanıcı tavsiye istiyorsa.
     * `command`: Kullanıcının isteği netse ve doğrudan EDL yaması (`edlPatch`) üretilebiliyorsa (örn. *"10. saniyeden 15. saniyeye kadar olan kısmı kes"* veya *"[Seçili Aralık: 12.0s - 18.0s] Buraya Abone Ol yaz"*).
     * `clarification`: Kullanıcı *"Ekrana bir başlık ekle"* gibi eksik parametreli bir emir verdiyse (ne yazılacağı, rengi, konumu veya animasyonu belli değilse). Bu durumda AI bir `formFields` dizisi (`text`, `position`, `color`, `select`) üretir.
  2. **4 Kademeli LLM Fallback (Hata Devretme) Zinciri:**
     * **Kademe 1 — Antigravity Proxy (`CallOpenAiCompatibleAsync`):** Yerel `http://localhost:8045/v1` proxy sunucusu aktifse `gemini-3.8-flash-tiered` modeline 8 saniye zaman aşımıyla JSON formatında istek atar.
     * **Kademe 2 — Groq Cloud API:** Proxy yanıt vermezse ve `GROQ_API_KEY` tanımlıysa `https://api.groq.com/openai/v1` üzerinden `openai/gpt-oss-120b` modeline 15 saniye zaman aşımıyla istek atar.
     * **Kademe 3 — Resmi Google Gemini API:** İlk iki adım başarısızsa `Mscc.GenerativeAI` SDK'sı ile resmi `gemini-2.0-flash` modelini (503/timeout durumunda 2 kez yeniden deneyerek) çağırır.
     * **Kademe 4 — Yerel Sezgisel Motor (`ParseWithLocalHeuristics`):** Eğer internet yoksa veya tüm API anahtarları kotaya takıldıysa sistem çökmez! Yerel C# algoritması devreye girer:
       * Mesajda `[Seçili Aralık: X.Xs - Y.Ys] ...` kalıbı varsa, başlangıç ve bitiş saniyelerini Regex ile ayıklar, cümle sonundaki *"yazılacak buraya, ekle, koy"* gibi emir eklerini temizler ve doğrudan o saniye aralığına metin katmanı ekleyen geçerli bir `edlPatch` üretir.
       * Soru cümlesi ise Türkçe bağlaç/edatları temizleyip kelimelerin ilk 4 harfiyle (Türkçe kök eşleşmesi) transkript satırlarını tarar ve ilgili cümleleri saniyeleriyle birlikte kullanıcıya listeler.

#### 2. [`Infrastructure/AI/PexelsService.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Infrastructure/AI/PexelsService.cs) (`IPexelsService`)
* **`SearchPhotoUrlAsync(string query, string orientation = "landscape", CancellationToken ct)`:** Pexels REST API'ye (`https://api.pexels.com/v1/search`) sorgu atarak ilk fotoğrafın yüksek çözünürlüklü URL'sini döner.
* **`SearchAndSaveAssetAsync(Guid projectId, string query, string orientation = "landscape", CancellationToken ct)`:** Bulduğu stok fotoğrafı indirip `IFileStorageService.UploadFileAsync` ile MinIO'ya `assets/{projectId}/{assetId}.jpg` olarak kaydeder.

#### 3. [`Infrastructure/Cache/RedisCacheService.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Infrastructure/Cache/RedisCacheService.cs) (`ICacheService`)
* **`GetAsync<T>(key)`, `SetAsync<T>(key, value, expiry)`, `RemoveAsync(key)`, `RemoveByPrefixAsync(prefix)`:** `StackExchange.Redis` üzerinden JSON serileştirmeli önbellek işlemleri yapar. Tüm metotlar `try/catch` ile sarılmıştır; Redis sunucusu kapansa bile uygulama hata fırlatmaz, doğrudan PostgreSQL veritabanından çalışmaya devam eder.

#### 4. [`Infrastructure/Storage/MinioFileStorageService.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Infrastructure/Storage/MinioFileStorageService.cs) & [`LocalFileStorageService.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Infrastructure/Storage/LocalFileStorageService.cs) (`IFileStorageService`)
* **`EnsureBucketExistsAsync`:** `"otoedit"` adındaki S3 bucket'ı yoksa otomatik oluşturur.
* **`UploadFileAsync(objectKey, content, contentType)`:** Dosya akışını (`Stream`) MinIO'ya yükler.
* **`DownloadFileAsync(objectKey)`:** MinIO'daki nesneyi `MemoryStream` olarak indirir.
* **`GetPresignedUrlAsync(objectKey, expiry)`:** Tarayıcının veya video oynatıcısının dosyayı doğrudan MinIO'dan okuyabilmesi için geçici imzalı URL üretir.
* **`DeleteFileAsync(objectKey)` & `DeleteDirectoryAsync(prefix)`:** Tekil dosyayı veya bir klasör önek체 altındaki tüm dosyaları (`Recursive = true`) siler.

---

### 5.5. İş Mantığı Yöneticileri (`Services/`)

#### 1. [`Services/ProjectManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/ProjectManager.cs) (`IProjectService`)
* **`GetAllAsync()`:** `ProjectRepository.GetProjectsPagedAsync(1, 100)` çağırarak tüm projeleri listeler.
* **`GetByIdAsync(Guid id)`:** Önce Redis'te `project:{id}` anahtarını kontrol eder. Yoksa veritabanından projeyi, videosunu, transkript durumunu, EDL versiyonunu ve en son `RenderJob` kaydını çekip `ProjectDetailDto` oluşturur, Redis'e **5 dakika** süreyle yazar ve döner.
* **`CreateAsync(ProjectCreateDto dto)`:** FluentValidation ile doğrular, `ProjectDurumu.Taslak` durumunda yeni proje oluşturur.
* **`UpdateAsync(Guid id, ProjectUpdateDto dto)`:** Proje bilgilerini (format, şablon, jest/ses ayarları) günceller ve Redis `project:{id}` önbelleğini temizler.
* **`DeleteAsync(Guid id)`:** Önce MinIO üzerindeki `videos/{id}/`, `audio/{id}/` ve `renders/{id}/` klasörlerini tamamen siler, ardından veritabanından projeyi siler ve Redis önbelleğini temizler.
* **`UpdateStatusAsync(Guid id, ProjectDurumu durum)`:** Proje durumunu güncelleyip Redis önbelleğini geçersiz kılar (invalidate eder).

#### 2. [`Services/VideoManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/VideoManager.cs) (`IVideoService`)
* **`UploadVideoAsync(Guid projectId, IFormFile file, bool autoJumpcut, bool autoRetake, bool autoBroll, bool autoSubtitles, CancellationToken ct)`:**
  1. Projenin varlığını, dosyanın boş olmadığını, 50 GB sınırını aşmadığını ve geçerli bir video uzantısına sahip olduğunu doğrular.
  2. Videoyu belleğe kopyalamadan doğrudan `file.OpenReadStream()` akışıyla MinIO'ya `videos/{projectId}/{videoId}{ext}` anahtarıyla yükler.
  3. `videos` tablosuna `VideoIslemDurumu.Bekliyor` durumunda yeni kayıt ekler.
  4. Projenin durumunu `ProjectDurumu.AnalizEdiliyor` olarak günceller.
  5. RabbitMQ'ya `VideoUploadedEvent` olayını fırlatarak Python Worker'daki analiz sürecini tetikler.
* **`GetVideoByProjectIdAsync(Guid projectId)`:** Projeye ait video bilgilerini döner.
* **`GetVideoUrlAsync(Guid videoId)`:** MinIO'dan 12 saatlik Presigned URL alır. Docker iç ağında `http://minio:9000` olarak üretilen adresi, kullanıcının tarayıcısının erişebilmesi için `http://localhost:9000` olarak dönüştürür.
* **`GetVideoStreamAsync(Guid videoId)` & `DeleteVideoAsync(Guid projectId)`:** Video akışı açma ve video/temiz ses dosyalarını silme işlemlerini yürütür.

#### 3. [`Services/EdlManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/EdlManager.cs) (`IEdlService`)
Editördeki her tıklamanın (kesme, bölme, altyazı değiştirme, katman taşıma, geri alma) veritabanındaki JSON üzerinde nasıl işlendiğini yöneten en kritik servistir.

* **`GetEdlAsync(Guid projectId)`:**
  1. Redis'te `edl:{projectId}` varsa doğrudan döner.
  2. Veritabanından `EditDecisionList` kaydını okur.
  3. **Otomatik Transkript Enjeksiyonu:** Eğer `EdlJson` içinde `transcript.segments` boşsa, `video_transcripts` tablosundaki `ZamanDamgalari` JSON verisini okuyup EDL'nin içine otomatik yerleştirir.
  4. Sonucu Redis'e **2 dakika** TTL ile yazar ve `EdlDto` döner.
* **`PatchEdlAsync(Guid projectId, JsonElement patch)` (Akıllı JSON Delta Birleştirici):**
  1. **Memento Kaydı:** Değişiklik yapılmadan hemen önce `SaveSnapshotAsync(projectId, edl, "EDL Patch Öncesi", "system")` çağrısıyla mevcut EDL'yi `edl_snapshots` tablosuna kaydeder.
  2. Gelen `patch` JSON'u içindeki özellikleri mevcut `EdlJson` ağacıyla birleştirir:
     * **`cuts`, `overlays`, `suggestions` Dizileri İçin Akıllı Merge:** Gelen dizideki her bir öğenin `id` ve `action` alanlarına bakar:
       * Eğer `"action": "remove"` ise, mevcut dizide o `id`'ye sahip öğeyi bulup siler (örneğin kesimi iptal etme veya katman silme).
       * Eğer `"action": "update"` veya `"add"` ise ve aynı `id` mevcut dizide zaten varsa, öğeyi silip baştan yazmak yerine **mevcut öğenin yalnızca gönderilen alanlarını günceller** (örneğin bir katman sürüklendiğinde sadece `positionX` ve `positionY` güncellenir, fontu ve rengi korunur).
       * Eğer o `id` mevcut dizide yoksa, yeni öğe olarak diziye ekler.
     * **`settings` Nesnesi:** Alt alan bazında (`subtitleStyle`, `backgroundMusic`, `colorGrading`, `subtitlesEnabled` vb.) mevcut ayarları ezmeden birleştirir.
     * **`transcript` Nesnesi:** Altyazı düzenlemelerinde gönderilen yeni transkript ağacını günceller.
  3. `edl.Versiyon` numarasını 1 artırır, veritabanına kaydeder ve Redis `edl:{projectId}` önbelleğini siler.
* **`UndoAsync(Guid projectId)` (Geri Al — `Ctrl+Z`):**
  1. `edl_snapshots` tablosundan bu projeye ait `Kaynak == "system"` olan en son anlık görüntüyü (`lastSystemSnapshot`) bulur.
  2. Kullanıcının daha sonra `Ctrl+Y` (Redo) yapabilmesi için şu anki aktif EDL'yi `Kaynak = "system_undo"` olarak yeni bir snapshot kaydı şeklinde saklar.
  3. Aktif EDL'nin `EdlJson` içeriğini `lastSystemSnapshot.EdlJson` ile değiştirir, `Versiyon` numarasını 1 artırır, kullanılan `lastSystemSnapshot` kaydını tablodan siler ve Redis önbelleğini temizler.
* **`RedoAsync(Guid projectId)` (İleri Al — `Ctrl+Y`):**
  1. `edl_snapshots` tablosundan `Kaynak == "system_undo"` olan en son kaydı (`redoSnapshot`) bulur.
  2. Mevcut durumu tekrar `Kaynak = "system"` olarak kaydeder, aktif EDL'yi `redoSnapshot.EdlJson` değerine geri yükler, `Versiyon` numarasını 1 artırır ve kullanılan `redoSnapshot` kaydını siler.
* **`SaveSnapshotAsync(...)`:** Yeni bir kullanıcı düzenlemesi (`Kaynak == "system"`) geldiğinde eski `"system_undo"` (Redo) geçmişini sıfırlar ve veritabanının şişmemesi için proje başına en fazla **50 snapshot** tutar (50'yi aşarsa en eskiyi siler).
* **`CreateOrUpdateAsync(Guid projectId, JsonDocument edlJson)`:** Python Worker analizi bitirdiğinde ilk taslak EDL'yi oluşturur veya günceller.

#### 4. [`Services/ChatManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/ChatManager.cs) (`IChatService`)
* **`SendMessageAsync(Guid projectId, string message)`:**
  1. Son 10 sohbet mesajını Redis'ten (`chat:{projectId}:history`) veya DB'den çeker.
  2. Mevcut EDL JSON'u ve zaman damgalı video transkript metnini hazırlar.
  3. Kullanıcının mesajını `chat_messages` tablosuna (`Rol = "user"`) kaydeder.
  4. `GeminiChatProvider.ProcessCommandAsync` metodunu çağırır.
  5. **Human-in-the-Loop (İnsan Onaylı) Karar Akışı:**
     * Eğer AI bir `EdlPatch` ürettiyse (`intent == "command"` veya `"suggestion"`), içinde görsel katmanı varsa `EnrichImageOverlaysWithPexelsAsync` ile Pexels'ten gerçek stok fotoğraf indirip MinIO URL'siyle zenginleştirir. Ardından bu yamayı doğrudan EDL'ye yazmak yerine mesajın `PendingEdlPatch` sütununa kaydeder ve `PatchDurumu = "pending"` yapar. Böylece kullanıcı arayüzde önce **"Önizle"** veya **"Onayla"** diyebilir!
     * Eğer AI eksik bilgi tespit edip `intent == "clarification"` döndürdüyse, üretilen dinamik form şemasını (`FormFields`) kaydeder ve `PatchDurumu = "clarification"` yapar.
* **`ApplyPendingPatchAsync(Guid messageId)`:** Kullanıcı sohbet balonundaki **"Onayla"** butonuna bastığında çağrılır; `PendingEdlPatch` verisini `EdlManager.PatchEdlAsync` ile kalıcı olarak EDL'ye uygular ve mesaj durumunu `"applied"` yapar.
* **`SubmitFormAsync(Guid projectId, Guid messageId, Dictionary<string, string> parameters)`:** Kullanıcı sohbet içindeki dinamik formu (16:9 mini sahne konumu, renk, yazı, süre vb.) doldurup **"Onayla ve Ekle"** dediğinde çağrılır; form verilerinden yeni bir `OverlayItem` JSON yaması oluşturup `EdlManager.PatchEdlAsync` ile EDL'ye işler.
* **`GetHistoryAsync(Guid projectId)`:** Projenin tüm sohbet geçmişini kronolojik olarak döner.

#### 5. [`Services/AssetManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/AssetManager.cs) (`IAssetService`)
* **`UploadAssetAsync(Guid projectId, IFormFile file)`:** Kullanıcının yüklediği görsel (`.png, .jpg, .webp, .gif, .svg`), ses (`.mp3, .wav, .aac, .m4a, .ogg`) veya video (`.mp4, .mov, .webm`) dosyasını (maksimum 50 MB) doğrular, MinIO'ya `assets/{projectId}/{assetId}{ext}` olarak yükler, `ProjectAssets` tablosuna kaydeder ve 24 saatlik Presigned URL ile döner.
* **`GetProjectAssetsAsync`, `DeleteAssetAsync`, `GetAssetStreamAsync`, `GetAssetUrlAsync`:** Medya kütüphanesi listeleme, silme ve akış metodları.

#### 6. [`Services/RenderManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/RenderManager.cs) (`IRenderService`)
* **`RequestRenderAsync(Guid projectId, RenderRequestDto? requestDto)`:** Projenin güncel `EdlJson` kopyasını alarak `render_jobs` tablosuna `RenderDurumu.Kuyrukta` durumunda yeni bir kayıt açar, proje durumunu `RenderEdiliyor` yapar ve RabbitMQ'ya `RenderRequestedEvent` fırlatır.
* **`GetRenderStatusAsync(Guid projectId, Guid renderJobId)`:** Render işinin durumunu döner.
* **`GetDownloadUrlAsync(Guid projectId, Guid renderJobId)`:** Tamamlanan render çıktısı (`CiktiYolu`) için MinIO'dan 2 saatlik Presigned indirme bağlantısı üretir.
* **`CompleteRenderAsync(Guid renderJobId, string indirmeUrl)` & `FailRenderAsync(Guid renderJobId, string hataMesaji)`:** Python Worker'dan gelen sonuca göre `RenderJob` ve `Project` durumlarını günceller.

#### 7. [`Services/TemplateManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/TemplateManager.cs), [`LogManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/LogManager.cs) ve [`PipelineNotificationManager.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Business/Services/PipelineNotificationManager.cs)
* **`TemplateManager`:** Aktif kurumsal şablonları (`GetAllAsync`, `GetByIdAsync`) döner.
* **`LogManager`:** `LogEndpointAsync`, `LogPipelineStartAsync`, `LogPipelineEndAsync`, `LogPipelineErrorAsync` ve `[CallerMemberName]` / `[CallerLineNumber]` destekli `LogFunctionErrorAsync` metodlarıyla 3 log tablosuna maskelenmiş kayıt atar.
* **`PipelineNotificationManager`:** `SendSignalRMessageAsync` delegesi üzerinden SignalR `PipelineHub`'daki `project-{projectId}` odasına canlı bildirimleri iletir.

---

## BÖLÜM 6: Web API Katmanı (`OtoEdit.API`) ve Birim Testleri (`OtoEdit.UnitTests`) Detaylı İncelemesi

`OtoEdit.API` katmanı, dış dünyadan (Angular Frontend ve Python Worker HTTP loglayıcısından) gelen HTTP ve WebSocket isteklerini karşılayan, güvenlik/hata/loglama ara katmanlarını (Middleware) çalıştıran ve RabbitMQ Consumer'larını barındıran katmandır.

### 6.1. Uygulama Başlatıcı: [`Program.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Program.cs)
Uygulama ayağa kalkarken sırasıyla şu işlemleri gerçekleştirir:
1. Üst dizinlerdeki `.env` dosyasını bularak içindeki tüm anahtarları hem işletim sistemi ortam değişkenlerine hem de `builder.Configuration` içine yükler.
2. Kestrel web sunucusunun `MaxRequestBodySize` ve `FormOptions.MultipartBodyLengthLimit` sınırlarını **50 GB** olarak ayarlar (büyük ham videoların kesintisiz yüklenebilmesi için).
3. `AddDataLayer` ve `AddBusinessLayer` metodlarını çağırır; MassTransit içerisine 4 RabbitMQ Consumer sınıfını kaydeder.
4. `"AllowFrontend"` CORS politikasını ve dakikada 100 istek sınırına sahip `"fixed"` Rate Limiter'ı yapılandırır.
5. `PipelineNotificationManager.SendSignalRMessageAsync` delegesini `IHubContext<PipelineHub>` ile bağlayarak Business katmanının SignalR'a doğrudan mesaj gönderebilmesini sağlar.
6. Başlangıçta `db.Database.Migrate()` çağırarak eksik PostgreSQL tablolarını/migration'larını otomatik uygular.

---

### 6.2. Ara Katmanlar (`Middleware/`)

1. **[`Middleware/ApiKeyAuthMiddleware.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Middleware/ApiKeyAuthMiddleware.cs):**
   * Gelen her HTTP isteğini kontrol eder. CORS `OPTIONS` isteklerini ve `/swagger`, `/health`, `/pipeline-hub` yollarını serbest bırakır.
   * Diğer tüm `/api/...` isteklerinde önce `X-API-Key` HTTP başlığına, eğer orada yoksa (HTML5 `<video src="...">` ve `<img>` etiketleri özel HTTP başlığı gönderemediği için) URL'deki `?apiKey=` veya `?access_token=` query parametresine bakar. Anahtar `SUPER_SECRET_OTOEDIT_KEY_123!` (veya `.env`'deki `ADMIN_API_KEY`) ile eşleşmiyorsa `401 Unauthorized` döner.
2. **[`Middleware/ExceptionHandlingMiddleware.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Middleware/ExceptionHandlingMiddleware.cs):**
   * Tüm Controller ve Servis çağrılarını bir `try/catch` bloğu içinde çalıştırır.
   * Bir hata fırlatıldığında önce `ILogService.LogFunctionErrorAsync` ile hatayı veritabanındaki `function_logs` tablosuna kaydeder; ardından istemciye standart `ProblemDetails` JSON formatında yanıt döner (`NotFoundException` -> `404`, `BusinessException` / `ValidationException` -> `400`, diğer hatalar -> `500`).
3. **[`Middleware/RequestResponseLoggingMiddleware.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Middleware/RequestResponseLoggingMiddleware.cs):**
   * Dosya yüklemeleri (`multipart/form-data`) ve SignalR dışındaki tüm HTTP istek ve yanıt gövdelerini okur, `Stopwatch` ile işlem süresini (`DurationMs`) ölçer ve `endpoint_logs` tablosuna kaydeder.

---

### 6.3. SignalR Hub (`Hubs/`) ve RabbitMQ Tüketicileri (`Consumers/`)

* **[`Hubs/PipelineHub.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Hubs/PipelineHub.cs) (`/pipeline-hub`):**
  * **`JoinProjectGroup(string projectId)`:** Tarayıcıdaki kullanıcı bir proje veya editör sayfasını açtığında bağlantısını `project-{projectId}` adlı özel SignalR odasına ekler.
  * **`LeaveProjectGroup(string projectId)`:** Kullanıcı sayfadan ayrıldığında bağlantıyı odadan çıkarır.
* **[`Consumers/PipelineStageChangedConsumer.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Consumers/PipelineStageChangedConsumer.cs):** Python Worker'dan gelen `PipelineStageChangedEvent` mesajını yakalar ve `project-{ProjectId}` odasına `"AnalysisProgress"` (`{ projectId, asama, yuzde, mesaj }`) WebSocket paketi olarak fırlatır.
* **[`Consumers/AnalysisNotificationConsumer.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Consumers/AnalysisNotificationConsumer.cs):** Python Worker analizi bitirip `AnalysisCompletedEvent` yayınladığında:
  1. `EdlManager.CreateOrUpdateAsync` ile üretilen EDL JSON'u veritabanına kaydeder.
  2. `ProjectManager.UpdateStatusAsync` ile projenin durumunu `AnalizTamamlandi` yapar.
  3. SignalR üzerinden `"AnalysisCompleted"` bildirimini göndererek kullanıcının ekranında *"Editör & Timeline'a Git"* butonunu aktif hale getirir.
* **[`Consumers/RenderNotificationConsumer.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Consumers/RenderNotificationConsumer.cs):** Python Worker FFmpeg render işlemini bitirip `RenderCompletedEvent` yayınladığında `RenderManager.CompleteRenderAsync` metodunu çağırır ve SignalR üzerinden `"RenderCompleted"` mesajını gönderir.
* **[`Consumers/PipelineErrorConsumer.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Consumers/PipelineErrorConsumer.cs):** Python Worker'dan `PipelineErrorEvent` geldiğinde proje ve render durumunu `Hata` olarak işaretler ve SignalR üzerinden `"PipelineError"` mesajını yayınlar.

---

### 6.4. REST API Controller Sınıfları ve Endpoint'leri (`Controllers/`)

1. **[`Controllers/ProjectsController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/ProjectsController.cs) (`/api/projects`):**
   * `GET /api/projects` -> `GetAll()`: Tüm projeleri listeler.
   * `GET /api/projects/{id}` -> `GetById(Guid id)`: Proje detayını döner.
   * `POST /api/projects` -> `Create(ProjectCreateDto dto)`: Yeni proje oluşturur.
   * `PUT /api/projects/{id}` -> `Update(Guid id, ProjectUpdateDto dto)`: Proje ayarlarını günceller.
   * `DELETE /api/projects/{id}` -> `Delete(Guid id)`: Projeyi ve tüm MinIO dosyalarını siler.
2. **[`Controllers/VideosController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/VideosController.cs):**
   * `POST /api/projects/{projectId}/videos` -> `UploadVideo(Guid projectId, [FromForm] VideoUploadDto dto)`: 50 GB limitli ham video yükler ve AI analizini başlatır.
   * `GET /api/projects/{projectId}/video` -> `GetVideo(Guid projectId)`: Projenin aktif video bilgisini döner.
   * `DELETE /api/projects/{projectId}/video` -> `DeleteVideo(Guid projectId)`: Videoyu siler.
   * `GET /api/videos/{videoId}/stream` -> `StreamVideo(Guid videoId)`: MinIO üzerindeki videonun Presigned URL'sine `302 Redirect` yapar (böylece HTML5 `<video>` oynatıcısı Byte-Range / parçalı ileri-geri sarma desteğiyle videoyu doğrudan MinIO'dan akıtır).
3. **[`Controllers/EdlController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/EdlController.cs) (`/api/projects/{projectId}/edl`):**
   * `GET /api/projects/{projectId}/edl` -> `GetEdl(Guid projectId)`: Projenin güncel EDL JSON belgesini döner.
   * `PATCH /api/projects/{projectId}/edl` -> `PatchEdl(Guid projectId, [FromBody] JsonElement patch)`: Kesim, katman, altyazı veya ayar yamasını uygular.
   * `POST /api/projects/{projectId}/edl/undo` -> `UndoEdl(Guid projectId)`: Son EDL işlemini geri alır.
   * `POST /api/projects/{projectId}/edl/redo` -> `RedoEdl(Guid projectId)`: Geri alınan işlemi ileri alır.
4. **[`Controllers/ChatController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/ChatController.cs) (`/api/projects/{projectId}/chat`):**
   * `POST /api/projects/{projectId}/chat` -> `SendMessage(Guid projectId, ChatMessageDto dto)`: Yönetmen AI'a mesaj gönderir.
   * `GET /api/projects/{projectId}/chat` -> `GetHistory(Guid projectId)`: Sohbet geçmişini getirir.
   * `POST /api/projects/{projectId}/chat/{messageId}/apply` -> `ApplyPendingPatch(Guid projectId, Guid messageId)`: Onay bekleyen AI yamasını EDL'ye uygular.
   * `POST /api/projects/{projectId}/chat/{messageId}/form` -> `SubmitForm(Guid projectId, Guid messageId, Dictionary<string, string> parameters)`: Kullanıcıdan alınan clarification formunu katman olarak EDL'ye işler.
5. **[`Controllers/AssetsController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/AssetsController.cs) (`/api/projects/{projectId}/assets`):**
   * `POST /api/projects/{projectId}/assets` -> `UploadAsset`: Projeye yeni görsel/ses/video varlığı yükler.
   * `GET /api/projects/{projectId}/assets` -> `GetAssets`: Proje varlıklarını listeler.
   * `DELETE /api/projects/{projectId}/assets/{assetId}` -> `DeleteAsset`: Varlığı siler.
   * `GET /api/projects/{projectId}/assets/{assetId}/stream` -> `StreamAsset`: Varlığın MinIO Presigned URL'sine `302 Redirect` yapar.
6. **[`Controllers/RenderController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/RenderController.cs):**
   * `POST /api/projects/{projectId}/render` -> `RequestRender`: FFmpeg render işini başlatır (`202 Accepted`).
   * `GET /api/projects/{projectId}/render/{renderJobId}` -> `GetRenderStatus`: Render durumunu sorgular.
   * `GET /api/projects/{projectId}/render/{renderJobId}/download` -> `Download`: Tamamlanan MP4 dosyasının Presigned indirme linkini döner.
7. **[`Controllers/PipelineController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/PipelineController.cs), [`InternalLogsController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/InternalLogsController.cs) ve [`TemplatesController.cs`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.API/Controllers/TemplatesController.cs):**
   * `InternalLogsController.LogPipelineProgress` (`POST /api/internal/logs/pipeline`): Python Worker'daki `PipelineLogger` servisinin doğrudan HTTP POST ile aşama ilerlemesini veritabanına yazmasını ve aynı anda SignalR ile ekrana yansıtmasını sağlar.
   * `TemplatesController`: Kurumsal şablonları (`GET /api/templates`, `GET /api/templates/{id}`) sunar.

### 6.5. Backend Birim Testleri (`tests/OtoEdit.UnitTests/`)
`OtoEdit.UnitTests` klasöründeki **19 test dosyası** (`xUnit`, `Moq`, `FluentAssertions` ve `EF Core InMemory` kullanarak); Controller uç noktalarını, RabbitMQ Consumer'larını, `EdlManager` JSON yama ve büyük/küçük harf duyarsız (`cuts`/`overlays`) birleştirme mantığını, `ChatManager` Human-in-the-Loop ve Pexels zenginleştirme akışını, `ApiKeyAuthMiddleware` güvenliğini, `SensitiveDataMasker` maskelemesini ve `FluentValidation` kurallarını izole olarak doğrular.

---

## BÖLÜM 7: Python Worker, AI Analiz Pipeline ve FFmpeg Render Motoru (`OtoEdit.PythonWorker`) Detaylı İncelemesi

`OtoEdit.PythonWorker`, sistemin tüm ağır sinyal işleme, konuşma tanıma (STT), bilgisayarlı görü (MediaPipe), doğal dil anlama (Gemini) ve video/ses render (FFmpeg + Pillow + Rembg) işlemlerini yürüten bağımsız Python mikroservisidir.

### 7.1. Kök Dosyalar (`main.py`, `config.py`, `Dockerfile`, `requirements.txt`)

#### 1. [`main.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/main.py)
Worker konteyneri ayağa kalktığında çalışan ilk dosyadır:
* **`run_analysis_consumer()`:** `AnalysisConsumer` sınıfını başlatıp `video-uploaded` RabbitMQ kuyruğunu dinleme döngüsüne sokar.
* **`run_render_consumer()`:** `RenderConsumer` sınıfını başlatıp `render-requested` RabbitMQ kuyruğunu dinleme döngüsüne sokar.
* **`main()`:**
  1. `Config.ensure_directories()` ile `temp/` ve `logs/` klasörlerini oluşturur.
  2. `run_janitor()` fonksiyonunu çağırarak önceki çalışmalardan kalan 2 saatten eski geçici dosyaları ve yarım kalmış `render_*` klasörlerini temizler.
  3. `AnalysisConsumerThread` ve `RenderConsumerThread` adında iki ayrı arka plan iş parçacığı (`daemon=True`) başlatır; böylece sistem bir yandan yeni yüklenen bir videoyu analiz ederken aynı anda başka bir projenin dışa aktarma (render) işlemini paralel yürütebilir.

#### 2. [`config.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/config.py)
Tüm ortam değişkenlerini `.env` dosyasından okuyup merkezi `Config` sınıfında toplar:
* **STT Motor Sırası:** `STT_ENGINE_ORDER = ["gemini_transcribe", "groq", "proxy_gemini", "local_whisper"]`, `STT_CHUNK_MAX_SEC = 600` (10 dk), `LOCAL_WHISPER_MODEL = "large-v3-turbo"`.
* **VAD ve Jump-Cut v2/v3 Eşikleri:** `VAD_THRESHOLD = 0.4`, `VAD_MIN_SILENCE_MS = 500`, `JUMPCUT_ENGINE = "v2"`, `JUMPCUT_MIN_SILENCE_MS = 700`, `JUMPCUT_PAD_LEAD_MS = 350`, `JUMPCUT_PAD_TRAILING_MS = 200`, `JUMPCUT_WORD_GUARD_MS = 150`, `JUMPCUT_MIN_ISLAND_MS = 300`.
* **Altyapı ve API Anahtarları:** RabbitMQ, MinIO, Redis (`ENABLE_ANALYSIS_CACHE`), `.NET API` (`API_BASE_URL`), `GEMINI_API_KEYS` (çoklu anahtar listesi), `GROQ_API_KEY`, `ANTIGRAVITY_PROXY_URL` ve `PEXELS_API_KEY`.

#### 3. [`Dockerfile`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/Dockerfile) ve `assets/fonts/`
`python:3.11-slim` üzerine `ffmpeg`, `fontconfig` ve OpenCV sistem kütüphanelerini kurar. `assets/fonts/` içindeki 8 özel TrueType fontu (`Anton.ttf`, `BebasNeue.ttf`, `Cinzel.ttf`, `Inter.ttf`, `Montserrat.ttf`, `Outfit.ttf`, `Poppins-Bold.ttf`, `Poppins-Regular.ttf`) Linux sistem font dizinine (`/usr/share/fonts/truetype/custom/`) kopyalayıp `fc-cache -f -v` çalıştırır. Bu sayede FFmpeg `libass` altyazı motoru ve `PillowGraphicsEngine` Türkçe karakterleri ve modern kurgu fontlarını eksiksiz çizer.

---

### 7.2. RabbitMQ Tüketicileri (`consumers/`)

#### 1. [`consumers/heartbeat_manager.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/heartbeat_manager.py) (`RabbitHeartbeatKeeper`)
* **Çözdüğü Problem:** Python `pika.BlockingConnection` tek iş parçacıklıdır. 45 dakikalık bir videonun STT veya FFmpeg render işlemi sürerken ana iş parçacığı meşgul olduğu için RabbitMQ sunucusunun gönderdiği "Heartbeat" yoklamalarına yanıt veremez ve bağlantı kopar (`StreamLostError`).
* **Fonksiyonları (`start()`, `stop()`, `_run()`):** İş başladığında arka planda bir thread açar ve her **10 saniyede bir** `connection.process_data_events(time_limit=0)` çağırarak RabbitMQ soketini canlı tutar; iş bittiğinde `stop()` ile kapanır.

#### 2. [`consumers/analysis_consumer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py) (`AnalysisConsumer`)
RabbitMQ'daki `video-uploaded` kuyruğunu dinleyen ve **14 adımlı paralel AI analiz hattını** yöneten ana orkestratördür:
* **`start(self)`:** `video-uploaded` kuyruğunu hem yalın `VideoUploadedEvent` hem de MassTransit'in `OtoEdit.Business.Events:VideoUploadedEvent` fanout exchange'ine bağlar ve `prefetch_count=1` ile dinler.
* **`_on_message(self, ch, method, properties, body)` (14 Adımlı Analiz Orkestrasyonu):**
  1. **Girdi Ayrıştırma:** Mesajdan `videoId`, `projectId`, `dosyaYolu`, `videoFormati` ve kullanıcının seçtiği `autoJumpcutEnabled`, `autoRetakeEnabled`, `autoBrollEnabled`, `autoSubtitlesEnabled`, `gestureCommandsEnabled`, `audioEnhancementEnabled` bayraklarını okur.
  2. **Heartbeat Başlatma:** `RabbitHeartbeatKeeper` başlatılır.
  3. **MinIO İndirme (%5):** `self.minio.download_video(...)` ile ham videoyu yerel `temp/` klasörüne indirir.
  4. **Redis SHA-256 Idempotency Kontrolü:** `self.cache.compute_video_hash(local_video_path)` ile videonun özetini çıkarır. Eğer `ENABLE_ANALYSIS_CACHE` açıksa ve bu video daha önce analiz edilmişse, tüm aşamaları atlayıp önbellekteki EDL'yi anında yayınlar (%100).
  5. **Ses İyileştirme (%12):** `audio_enhancement` aktifse `self.audio_enhancer.enhance(local_video_path)` ile dip gürültüsünü temizler ve temiz sesi MinIO'ya yükler.
  6. **Tek Kaynak Ses Analizi (%18):** `self.audio_analyzer.analyze(local_video_path)` ile 16 kHz PCM ses üzerinden Silero VAD konuşma bölgelerini, 10 ms'lik RMS enerji zarfını ve UI dalga formu için 1000 noktalı `audio_peaks` dizisini üretir.
  7. **Paralel Grup 1 — STT + Yüz Takibi (%25–%55):** `ThreadPoolExecutor(max_workers=2)` ile iki ağır işi aynı anda çalıştırır:
     * İş 1: `self.transcriber.transcribe(...)` ile kelime zaman damgalı transkripti çıkarır.
     * İş 2: Eğer hedef format Dikey (`9:16`) veya Kare (`1:1`) ise `self.face_tracker.track(...)` ile konuşmacının yüz koordinatlarını çıkarır.
  8. **Akıllı Retake Taraması (%65):** `auto_retake` aktifse `self.retake_detector.detect_retakes(...)` ile hatalı tekrar okumaları, yarım başlangıçları ve anlamsal tekrarları bulur (`retake_cuts`).
  9. **Kelime Korumalı Jump-Cut v3 (%75):** `auto_jumpcut` aktifse `self.silence_detector.detect_v2(..., transcript_words=transcript.words, existing_cuts=retake_cuts)` çağrısıyla (kelimeler olduğu için otomatik `detect_v3` çalışır) korunan kelimeler arasındaki sessizlikleri keser (`silence_cuts`).
  10. **Altyazı Segmentlerini Kesim Sınırlarına Göre Yeniden Üretme:** `self.transcriber.regenerate_segments_with_cuts(words=transcript.words, cuts=retake_cuts + silence_cuts)` çağrılarak kesilen kelimeler altyazıdan temizlenir ve altyazı bloklarının kesim noktalarının üzerinden taşması engellenir.
  11. **Paralel Grup 2 — Jest Komutları + Viral Klip + Öneriler + Otomatik B-Roll (%85–%88):** `ThreadPoolExecutor(max_workers=4)` ile dört motoru aynı anda koşturur:
      * `self.command_engine.detect(local_video_path, transcript)`
      * `self.repurposing.analyze(transcript)`
      * `self.suggestion_engine.generate_suggestions(transcript)`
      * `self.auto_broll_engine.generate_broll_overlays(transcript, video_format_str)`
  12. **EDL İnşası (%95):** `self.edl_builder.build(...)` ile tüm sonuçları tek bir `EdlDocument` JSON sözlüğünde birleştirir.
  13. **Tamamlama Yayını (%100):** `self.publisher.publish_analysis_completed(project_id, video_id, edl_dict)` ile sonucu RabbitMQ üzerinden .NET API'ye gönderir ve mesajı `basic_ack` ile onaylar.
  14. **Geçici Dosya Temizliği:** `finally` bloğunda `cleanup_files` ile yerel video ve ses dosyalarını siler.

#### 3. [`consumers/render_consumer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/render_consumer.py) (`RenderConsumer`)
RabbitMQ'daki `render-requested` kuyruğunu dinler:
* **`_on_message(self, ch, method, properties, body)`:**
  1. `renderJobId`, `projectId` ve `edlJson` verilerini alır, `temp/render_{render_job_id}/edl_debug.json` olarak kaydeder.
  2. `_resolve_source_video(...)` ile kaynak videoyu MinIO'dan indirir (%10).
  3. `self.renderer.render(edl_json, local_video_path, local_output_path, temp_dir)` ile 2-Pass FFmpeg render işlemini gerçekleştirir (%30 -> %85).
  4. `self.minio.upload_render_output(...)` ile üretilen MP4 dosyasını MinIO'da `renders/{project_id}/{render_job_id}.mp4` yoluna yükler.
  5. `self.publisher.publish_render_completed(...)` ile .NET API'ye haber verir (%100) ve geçici render klasörünü temizler.

---

### 7.3. Veri Modelleri (`models/`)

* **[`models/command_model.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/models/command_model.py):** `CommandType` enum'unu (`START_MARKER`, `CUT`, `ADD_TEXT`, `ADD_IMAGE`, `REWIND_CUT`) ve `ParsedCommand` dataclass'ını tanımlar.
* **[`models/gesture_model.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/models/gesture_model.py):** `GestureType` enum'unu (`THUMBS_UP`, `THUMBS_DOWN`, `PEACE_OR_T`, `OPEN_PALM`, `FIST`) ve `GestureResult` dataclass'ını tanımlar.
* **[`models/transcript_model.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/models/transcript_model.py):** `WordTimestamp` (`word`, `start`, `end`, `confidence`), `TranscriptSegment` (`start`, `end`, `text`, `words`) ve `TranscriptResult` (`full_text`, `segments`, `words`, `duration`) veri yapılarını tanımlar.
* **[`models/edl_model.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/models/edl_model.py):** Pydantic `BaseModel` tabanlı tam EDL şemasıdır (`CutItem`, `OverlayItem`, `SuggestionItem`, `ViralClipItem`, `RepurposingData`, `SubtitleStyleConfig`, `BackgroundMusicConfig`, `EdlSettings`, `EdlDocument`).

---

### 7.4. Analiz Pipeline Modülleri (`pipeline/` ve `pipeline/stt/`)

#### 1. Tek Kaynak Ses Analizörü: [`pipeline/audio_analysis.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/audio_analysis.py) (`AudioAnalyzer` & `AudioAnalysis`)
* **`AudioAnalyzer.extract_pcm(media_path)`:** FFmpeg'i alt süreç (`subprocess.run`) olarak çalıştırıp diskte dev bir WAV dosyası oluşturmadan doğrudan RAM borusu (`stdout` pipe) üzerinden 16 kHz mono 16-bit PCM ses dizisini `[-1.0, 1.0]` `float32` NumPy dizisi olarak çeker.
* **`AudioAnalyzer.analyze(media_path, vad_threshold, min_silence_ms, num_peaks=1000)`:**
  1. **Silero VAD:** `faster_whisper.vad.get_speech_timestamps` ile tüm konuşma bölgelerini (`SpeechRegion(start, end)`) milisaniye hassasiyetinde çıkarır.
  2. **10 ms RMS Enerji Zarfı (`rms_envelope`):** Ses sinyalini 160 örneklik (10 ms = saniyede 100 nokta) pencerelere bölüp her pencerenin RMS enerjisini hesaplar.
  3. **UI Dalga Formu (`peaks`):** RMS zarfını 1000 dilime bölüp `[0.0, 1.0]` aralığında normalize ederek Frontend'in timeline üzerinde çizeceği `audioPeaks` dizisini üretir.
* **`AudioAnalysis.find_energy_minimum(center_sec, search_window_sec=0.05, direction="both")`:**
  * Bir ses kesimi tam konuşma dalgasının tepesinde yapılırsa hoparlörde "çıt/pat" sesi duyulur. Bu fonksiyon hedef kesim noktasının etrafındaki pencerede RMS enerjisinin en düşük olduğu yerel minimum saniyesini (`np.argmin`) bulur. Ayrıca `direction="backward_only"` veya `"forward_only"` parametreleriyle kesimin kelimenin içine doğru kaymasını kesin olarak engeller.

#### 2. Ses İyileştirici ve Akustik Puanlayıcı: [`pipeline/audio_enhancer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/audio_enhancer.py) & [`pipeline/acoustic_scorer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/acoustic_scorer.py)
* **`AudioEnhancer.enhance(video_path)`:** Videodan sesi ayıklar, `noisereduce.reduce_noise(prop_decrease=0.6)` ile arka plan gürültüsünü temizler (hata olursa FFmpeg `afftdn=nf=-25` filtresine düşer) ve `192k` MP3 olarak kaydeder.
* **`AcousticScorer.score_audio_segment(audio_path, start_sec, end_sec, prev_segment_rms)`:**
  * Sesi RAM'de önbelleğe alır (`load_audio`). Verilen saniye aralığındaki sesin **Clipping (Patlama) Puanını** (%45 ağırlık), **İdeal Ses Seviyesi (`-26` ile `-14` dBFS) Puanını** (%35 ağırlık) ve **Önceki Cümleyle Ses Tonu Sürekliliği Puanını** (%20 ağırlık) hesaplayarak `0–100` arası kalite puanı döner.

#### 3. Çok Motorlu STT Orkestratörü ve Alt Paketleri: [`pipeline/transcriber.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py) & `pipeline/stt/`
* **[`pipeline/stt/chunker.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/chunker.py) (`AudioChunker`):**
  * **`calculate_split_points(analysis)` & `split(media_path, analysis)`:** Uzun videoları 600 saniyelik (10 dk) parçalara bölerken asla cümlenin ortasından bölmez; 600. saniyenin `±60` saniye etrafındaki **en uzun VAD sessizliğinin tam orta noktasını** bulup oradan böler. Tamamen sessiz olan parçalar için STT çağrısı yapmaz.
* **[`pipeline/stt/rate_limiter.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/rate_limiter.py) (`GeminiKeyRotator`):**
  * `.env` içindeki birden fazla Gemini API anahtarını (`GEMINI_API_KEYS`) sırayla (Round-Robin) kullanır. Bir anahtar HTTP 429 (kota aşımı) alırsa Google'ın döndürdüğü `retryDelay` süresini okuyup o anahtarı soğumaya (`mark_rate_limited`) alır ve anında diğer anahtara geçer.
* **[`pipeline/stt/gemini_transcribe.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/gemini_transcribe.py) (`GeminiTranscribeEngine`):**
  * Google'ın `gemini-3.5-transcribe` modelini `VERBATIM` (birebir/kelimesi kelimesine) ve `word_timestamp=True` modunda çağırır. Türkçe konuşma içindeki Arapça/Osmanlıca terimlerin (örn. *"Bismillahirrahmanirrahim"*) yutulmaması için dil kısıtlaması göndermez.
* **[`pipeline/stt/groq_engine.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/groq_engine.py) (`GroqEngine`):** Groq Cloud üzerinde `whisper-large-v3-turbo` modelini kelime zaman damgalarıyla çalıştırır.
* **[`pipeline/stt/proxy_gemini.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/proxy_gemini.py) (`ProxyGeminiEngine`):** Antigravity Proxy üzerinden `gemini-3.8-flash-tiered` modelini çalıştırır.
* **[`pipeline/stt/local_whisper.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/local_whisper.py) (`LocalWhisperEngine`):** İnternet veya API anahtarı olmasa bile yerel GPU (`cuda`, `int8_float16`) veya CPU üzerinde `faster-whisper` (`large-v3-turbo` / `base`) modelini çevrimdışı çalıştırır.
* **[`pipeline/stt/engine_chain.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/engine_chain.py) (`STTEngineChain`):** Yukarıdaki 4 motoru sırayla dener; kotası biten motoru `exhausted_engines` listesine alıp sonraki parçalarda doğrudan çalışan motora geçer.
* **[`pipeline/stt/gap_filler.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/gap_filler.py) (`GapFiller`):**
  * **`find_untranscribed_gaps` & `fill_gaps`:** Silero VAD'ın *"burada en az 0.40 saniyelik konuşma var"* dediği ancak STT motorunun hiçbir kelime döndürmediği boşlukları tespit eder. O küçük aralıkları `±0.5s` payla kesip yeniden STT'ye göndererek yutulan kelimeleri kurtarır.
* **[`pipeline/word_refiner.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/word_refiner.py) (`refine_word_boundaries`):**
  * STT modelleri bazen 5 saniyelik bir sessizlikten sonra söylenen 0.4 saniyelik bir kelimenin başlangıcını 5 saniye önceden başlatır (şişmiş kelime damgası). `refine_word_boundaries` iki aşamalı çalışır:
    1. **Küme Kırpması (`> 0.65s` kelimeler):** Kelime aralığındaki gerçek RMS ses enerjisi kümelerini (`_speech_clusters`) bulur, harf sayısına göre beklenen konuşma süresini hesaplar ve sessiz kısmı kelimeden kesip atar.
    2. **Histerezis Kenar Koruması (Tüm kelimeler):** Kelime sonlarındaki düşük enerjili ünsüzlerin (`-r, -s, -ş, -k`) kesilmemesi için kelime sonunu ses enerjisi gürültü tabanının (`low` eşiği) altına düşene kadar ileri doğru en fazla `0.25s`, kelime başını ise geriye doğru en fazla `0.15s` genişletir.
* **[`pipeline/transcriber.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py) (`Transcriber`):**
  * **`transcribe(...)`:** Yukarıdaki tüm STT hattını (Chunker -> EngineChain -> GapFiller -> WordRefiner -> Altyazı Segmentleme) uçtan uca çalıştırır.
  * **`regenerate_segments_with_cuts(words, cuts, max_words=6, max_duration=3.0)`:** Kesim (`cuts`) aralıklarının içine düşen kelimeleri altyazıdan siler ve iki kelime arasında bir kesim varsa altyazı segmentini oradan ikiye bölerek altyazının kesilen yerlerde asılı kalmasını önler.

#### 4. Akıllı Retake Eleyici (v3): [`pipeline/take_aligner.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/take_aligner.py), [`pipeline/retake_detector.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/retake_detector.py) & [`pipeline/transcript_verifier.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcript_verifier.py)
* **`TakeAligner` (`take_aligner.py`):**
  * **`is_word_match(w1, w2)` (Türkçe Sondan Eklemeli Dil Koruması):** Türkçede *"hükümlerinin"* ve *"bölümlerinin"* gibi kelimelerin son ekleri aynı olduğu için standart benzerlik algoritmaları bunları aynı kelime sanabilir. `is_word_match`, kelimelerin eşleşmesi için **ilk 3 harfinin (kök başlangıcının) aynı olmasını** veya edit mesafesinin en fazla 1 harf olmasını şart koşar.
  * **`detect_retakes(raw_words)` (3 Aşamalı Sağdan Sola Hizalama):**
    1. **Meta-Konuşma & Halüsinasyon Temizliği:** *"başa sar"*, *"baştan al"*, *"olmadı"*, *"pardon"* gibi stüdyo içi cümleleri ve Whisper sessizlik halüsinasyonlarını (`"altyazı m.k."`) doğrudan keser.
    2. **Sağdan Sola (Right-Anchored) Restart/Retake Tespiti:** Kelimeleri `>= 0.50s` duraklamalardan konuşma öbeklerine (`SpeechChunk`) ayırır. Her öbeğin ilk kelimelerini geriye doğru 30 kelime / 25 saniye içindeki önceki kelimelerle karşılaştırır. Eşleşme ve kuyruk kapsaması (`>= %55`) bulunduğunda **son (başarılı) okumayı korur**, önceki hatalı okumadaki kelimeleri `RetakeCut` olarak işaretler.
    3. **Yarım Başlangıç (False Start) Tespiti:** En fazla 3 kelimelik yarım bir girişten sonra `>= 2.0` saniye sessizlik varsa ve konuşmacı aynı kelimeyle cümleye yeniden başlıyorsa ilk yarım girişi keser.
* **`TranscriptVerifier` (`transcript_verifier.py`):**
  * **`audit_transcript(transcript, analysis, existing_cuts)`:** Konuşmacı bir cümleyi tamamen farklı kelimelerle yeniden kurduğunda (anlamsal tekrar / `semantic_retake`) veya cümleyi yarım bıraktığında (`aborted_sentence`), segmentleri 100'erli gruplar halinde Gemini LLM'e denetletir ve elenen segmentleri `source="ai_verifier"` kesimine dönüştürür.
* **`RetakeDetector` (`retake_detector.py`):**
  * **`detect_retakes(...)`:** `TakeAligner` ve `TranscriptVerifier` sonuçlarını birleştirir, sıra sayı sıfatlarını (*"Birinci öncül..."*, *"İkinci öncül..."*) korur ve tüm kesim sınırlarını `AudioAnalysis.find_energy_minimum` ile sesin dip noktasına yaslar.

#### 5. Kelime Korumalı Jump-Cut Motoru (v3/v2): [`pipeline/silence_detector.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/silence_detector.py) (`SilenceDetector`)
* **`detect_v3(audio_path, analysis, transcript_words, existing_cuts)`:**
  1. Retake kesimlerinin dışında kalan **korunan kelimeleri (`preserved_words`)** alır.
  2. Ardışık iki korunan kelime arasındaki boşluk `>= 0.40s` ise; cümle sonu/içi durumuna göre kelime sonuna `0.22s–0.28s` sönümlenme payı (`pad_trail`), sonraki kelime başına `0.14s–0.18s` nefes/atak payı (`pad_lead`) bırakır ve aradaki fazlalık boşluğu kesim adayı yapar.
  3. `_subtract_intervals` ile Retake bölgelerini sessizlik kesimlerinden çıkarır (böylece Timeline'da Retake kesimleri ile Sessizlik kesimleri birbirine karışmaz).
  4. **`_protect_speech_edges` (Akustik Güvenlik Ağı):** Eğer STT bir kelimenin zamanını biraz yanlış tahmin ettiyse bile, kesim sınırının `0.45s` yakınında gerçek ses enerjisi (RMS) tespit edilirse kesim sınırını konuşmanın dışına iter.
  5. Kesim başlangıcını ileri doğru (`forward_only`), bitişini geriye doğru (`backward_only`) RMS enerji minimumuna yaslar.

#### 6. Bilgisayarlı Görü, Çoklu-Modal Komut, Viral Klip ve B-Roll Motorları
* **[`pipeline/gesture_detector.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/gesture_detector.py) (`GestureDetector`):**
  * **`detect_gestures(video_path, target_windows)` & `classify_landmarks(landmarks)`:** MediaPipe Hands ile 21 eklem noktasının 3B Öklid mesafelerini ölçerek 👍 (`THUMBS_UP`), 👎 (`THUMBS_DOWN`), ✊ (`FIST`), 🖐️ (`OPEN_PALM`) ve ✌️ (`PEACE_OR_T`) işaretlerini sınıflandırır. `target_windows` (Smart Windowing) sayesinde videonun tamamını taramak yerine yalnızca sesli komut verilen saniyelerin etrafındaki kareleri OpenCV `seek` ile tarar.
* **[`pipeline/voice_command_parser.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/voice_command_parser.py) (`VoiceCommandParser`) & [`pipeline/multimodal_command_engine.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/multimodal_command_engine.py) (`MultimodalCommandEngine`):**
  * Önce `VoiceCommandParser.parse_transcript` ile metinde sesli komut arar. Hiç sesli komut yoksa MediaPipe'ı hiç çalıştırmaz! Sesli komut varsa o saniyenin `±2.0` saniye etrafında uyumlu el hareketi olup olmadığını kontrol eder ve eşleşen komutları onaylar.
* **[`pipeline/face_tracker.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/face_tracker.py) (`FaceTracker`):**
  * **`track(video_path, sample_interval_sec=0.4)`:** MediaPipe Face Detection ile her 0.4 saniyede bir konuşmacının yüz merkezini bulur. Dikey (9:16) kadrajın titrememesi için `%4` ölü bölge (`deadzone = 0.04`) ve Üstel Hareketli Ortalama (`ema_alpha = 0.15`) filtresi uygulayarak yumuşatılmış `smoothed_crop_x` koordinatlarını üretir.
* **[`pipeline/auto_broll_engine.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/auto_broll_engine.py) (`AutoBrollEngine`), [`pipeline/repurposing_engine.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/repurposing_engine.py) (`RepurposingEngine`) & [`pipeline/suggestion_engine.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/suggestion_engine.py) (`SuggestionEngine`):**
  * `AutoBrollEngine.generate_broll_overlays`: Gemini ile konuşmadaki görsel kavramları çıkarır, Pexels'ten stok fotoğraf bulur ve en az 4 saniye aralıklı `OverlayItem` katmanları üretir.
  * `RepurposingEngine.analyze`: En yüksek viral puanlı 30–90 saniyelik Reels/Shorts kliplerini çıkarır.
  * `SuggestionEngine.generate_suggestions`: Kullanıcı onayına sunulacak `pending` durumunda görsel ve metin önerileri üretir.
* **[`pipeline/edl_builder.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/edl_builder.py) (`EdlBuilder`):**
  * **`build(...)` & `_merge_overlapping_cuts(cuts)`:** Tüm motorların çıktısını tek bir `EdlDocument` sözlüğünde birleştirir. `_merge_overlapping_cuts` metodu, `silence` (sessizlik) kesimleri ile `smart_retake` / `gesture_dislike` (öncelikli) kesimlerini birbirine karıştırmaz; sessizlik kesimlerini retake sınırlarından kırpar. Böylece kullanıcı editörde bir retake kesimini geri aldığında yanındaki sessizlik kesimi bozulmaz.

---

### 7.5. Render Motoru Modülleri (`render/`)

Kullanıcı "Render Et" dediğinde çalışan ve tarayıcıdaki önizlemeyi piksel piksel gerçek MP4 videosuna dönüştüren katmandır:

#### 1. [`render/timeline_mapper.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/timeline_mapper.py) (`TimelineMapper`)
* **Çözdüğü Problem:** Örneğin 60 saniyelik bir videonun `10.0s - 20.0s` arası kesildiğinde, orijinal videonun `35.0.` saniyesinde duran bir altyazı veya görsel katman artık yeni videonun `25.0.` saniyesinde görünmelidir. Ayrıca FFmpeg ile kesilen her parçanın gerçek süresi (`actual_durations`), ses çerçevesi yuvarlamalarından dolayı matematiksel süreden birkaç milisaniye farklı olabilir.
* **Fonksiyonları (`remap_timestamp`, `remap_range`, `remap_overlays`, `remap_transcript`):** FFprobe ile ölçülen gerçek segment sürelerini (`actual_durations`) kullanarak tüm metin/görsel katmanlarının ve karaoke kelimelerinin zamanlarını milisaniye hassasiyetinde yeni zaman çizgisine kaydırır; kesilen bölgelerin içinde kalan katmanları ve kelimeleri otomatik eler.

#### 2. [`render/pillow_graphics_engine.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/pillow_graphics_engine.py) (`PillowGraphicsEngine`)
* **`render_text_badge(...)`:** FFmpeg'in standart `drawtext` veya `libass` filtreleri yuvarlatılmış hap (`pill`) kutuları çizemez (yalnızca sivri köşeli dikdörtgen çizer). Bu yüzden `boxStyle` değeri `"pill"`, `"rounded"` veya `"badge"` olan tüm metin katmanları bu motor tarafından **2x Supersampling (2 kat yüksek çözünürlükte çizip LANCZOS ile küçültme)** tekniğiyle, Gaussian bulanık gölgeli, konturlu ve yuvarlak köşeli şeffaf PNG görsellerine dönüştürülür ve FFmpeg'e görsel katman olarak verilir.

#### 3. [`render/text_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/text_overlay.py) (`TextOverlay`)
* **`generate_ass(overlays, transcript, output_path, play_res_x, play_res_y, subtitle_style)`:**
  * Kutusuz serbest metin katmanlarını ve konuşma altyazılarını `.ass` (Advanced SubStation Alpha) formatına çevirir.
  * **Karaoke Kelime Vurgusu:** Her altyazı segmentindeki her bir kelimenin okunduğu zaman aralığı için ayrı bir `Dialogue:` satırı üretir ve aktif kelimeye `{\c&H...&\t(0,90,\fscx110\fscy110)}` etiketi ekleyerek kelimenin okunduğu anda seçilen vurgu rengine (örn. TikTok Sarısı) dönüşüp `%110` oranında büyümesini sağlar.

#### 4. [`render/image_overlay.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/image_overlay.py) (`ImageOverlay`) & [`services/bg_remover.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/bg_remover.py) (`BackgroundRemoverService`)
* **`ImageOverlay.apply_image_overlays(...)`:**
  1. Görsel katmanları ve Pillow tarafından PNG'ye çevrilen metin rozetlerini `trackId` (Z-Index) sırasına göre alttan üste doğru sıralar.
  2. Görsel üzerinde aktifse `BackgroundRemoverService` metodlarını sırasıyla uygular:
     * `remove_background`: `rembg` (`u2netp` derin öğrenme modeli, hata verirse OpenCV `GrabCut`) ile görselin arka planını siler.
     * `apply_chroma_key`: CIE LAB renk uzayında yeşil/mavi ekranı temizler.
     * `apply_shape_mask`: 4x supersampling ile görseli daire (`circle`) veya yuvarlatılmış kare (`rounded`) içine maskeler.
     * `add_sticker_outline`: OpenCV morfolojik genişletme (`cv2.dilate`) ile görselin etrafına CapCut tarzı beyaz çıkartma konturu ve gölgesi çizer.
  3. Görseli hedef çözünürlüğe ölçekler (`scale`), varsa döndürme açısını (`rotation`) uygular ve `enable='between(t,start,end)'` ifadesiyle FFmpeg `overlay` filtre zincirine bağlar.

#### 5. [`render/audio_mixer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/audio_mixer.py) (`AudioMixer`)
* **`apply_bgm_with_ducking(...)`:** Arka plan müziğini video süresince döngüye sokar (`aloop`), başlangıç ve bitişte yumuşak ses geçişi (`afade`) uygular ve `auto_ducking=True` ise FFmpeg'in **`sidechaincompress`** filtresini (`ratio=5, attack=150, release=650`) kullanarak konuşmacı konuşmaya başladığı anda müziğin sesini otomatik kısıp konuşmacı sustuğunda tekrar yükseltir.

#### 6. Ana Render Orkestratörü: [`render/video_renderer.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/render/video_renderer.py) (`VideoRenderer`)
* **`render(edl_json, video_path, output_path, temp_dir)` (2-Pass Sıfır Kaymalı Render Mimarisi):**
  1. **Şablon Zenginleştirme:** `TemplateApplier.enrich_edl_with_template` ile varsa kurumsal logo ve konuşmacı alt bandını katmanlara ekler.
  2. **Adım 1 — Paralel Frame-Accurate Kesim (`_cut_segments`):** Korunan her bir video parçasını (`keep_segments`), NVIDIA NVENC oturum sınırını aşmamak için 2 paralel iş parçacığıyla (`ThreadPoolExecutor(max_workers=2)`), kesim uçlarında "tık" sesini önleyen **8 milisaniyelik ses mikro-fade** (`afade=t=in:ss=0:d=0.008`) ve sabit kare hızı (`-fps_mode cfr`) uygulayarak ayrı `.mp4` dosyaları olarak keser. Ardından her parçanın gerçek süresini `ffprobe` ile ölçer (`actual_durations`).
  3. **Adım 2 — Zaman Haritalama ve Grafik Hazırlığı:** `TimelineMapper` ile tüm altyazı ve katmanları `actual_durations` sürelerine göre yeni zaman çizgisine oturtur, `PillowGraphicsEngine` ile rozetleri PNG yapar ve `TextOverlay.generate_ass` ile `.ass` altyazı dosyasını üretir.
  4. **Adım 3 — 1. Geçiş (`_concat_segments`):** Kesilen parçaları birleştirirken aynı anda hedef formata göre yüz takipli kırpma (`crop`) ve `.ass` altyazı yakma (burn-in) işlemini gerçekleştirir.
  5. **Adım 4 — 2. Geçiş (Görsel Katmanlar + Auto-Ducking BGM):** Eğer projede görsel/rozet katmanı veya arka plan müziği varsa, 1. geçiş çıktısı üzerine `ImageOverlay.apply_image_overlays` ve `AudioMixer.apply_bgm_with_ducking` filtre grafiğini uygulayarak nihai `.mp4` dosyasını (`h264_nvenc` GPU, yoksa `libx264` CPU ile) üretir.

---

### 7.6. Dış Servisler (`services/`), Yardımcılar (`utils/`), Araçlar (`tools/`) ve Testler (`tests/`)

* **[`services/analysis_cache.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/analysis_cache.py) (`AnalysisCacheService`):** 30 MB'dan büyük videolarda dosyanın tamamını okumak yerine **dosya boyutu + ilk 10 MB + ortadaki 10 MB + son 10 MB** bloklarından milisaniyeler içinde SHA-256 özeti (`compute_video_hash`) çıkarır ve EDL sonucunu 7 gün boyunca Redis'te saklar.
* **[`services/gemini_client.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/gemini_client.py) (`GeminiClient`):** Üstel bekleme (`_execute_with_retry`) ve bozuk JSON temizleyici (`_safe_parse_json`) ile çalışan LLM istemcisidir.
* **[`services/pexels_client.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/pexels_client.py) & [`services/stock_media_fallback.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/stock_media_fallback.py):** Pexels API'den fotoğraf arar; anahtar yoksa veya hata alırsa otomatik olarak **Unsplash Public NAPI** ve **Wikimedia Commons API** üzerinden ücretsiz stok görsel bulur.
* **[`services/pipeline_logger.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/pipeline_logger.py) (`PipelineLogger`) & [`services/rabbitmq_publisher.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/services/rabbitmq_publisher.py) (`RabbitMQPublisher`):** Aşama ilerlemelerini hem konsola/dosyaya, hem RabbitMQ'ya hem de doğrudan `.NET InternalLogsController` HTTP uç noktasına gönderir.
* **[`tools/eval_edit.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/tools/eval_edit.py) & [`tools/cut_benchmark.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/tools/cut_benchmark.py):** Bir insan kurgucunun yaptığı kurgu ile OtoEdit'in otomatik kurgusunu kelime kelime karşılaştırıp doğruluk (`TP`, `FP`, `FN`, `clipped_words`) raporu çıkaran mühendislik araçlarıdır.
* **Python Birim ve Entegrasyon Testleri (`src/OtoEdit.PythonWorker/tests/` — 33 dosya):** `pytest` ile çalışan bu testler; `TakeAligner` Türkçe kök eşleşmesini, `Jump-Cut v2/v3` kelime korumasını, `AudioChunker` sessizlikten bölme mantığını, `GapFiller`'ı, `GeminiKeyRotator` 429 soğuma mekanizmasını, `TimelineMapper` kaydırmalarını ve FFmpeg görsel piksel doğrulamalarını (`test_visual.py`) test eder.

---

## BÖLÜM 8: Angular Frontend (`OtoEdit.Frontend`) Detaylı Dosya, Bileşen, Sinyal ve Fonksiyon İncelemesi

`OtoEdit.Frontend`, **Angular 18.2 Standalone Components** ve reaktif **Angular Signals (`signal`, `computed`)** mimarisiyle inşa edilmiş modern bir NLE (Non-Linear Editor) kurgu stüdyosudur.

### 8.1. Kök Yapılandırma, Ortam ve Başlatma Dosyaları

* **[`package.json`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/package.json) & [`angular.json`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/angular.json):** Angular 18.2, `@microsoft/signalr 8.0.7`, `rxjs 7.8.1` ve `tailwindcss 3.4.10` paketlerini barındırır. `ng serve` komutu `proxy.conf.json` üzerinden `/api` ve `/pipeline-hub` isteklerini `http://localhost:5001` (.NET API) adresine yönlendirir (büyük video yüklemeleri için 30 dakika proxy timeout tanımlıdır).
* **[`tailwind.config.js`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/tailwind.config.js) & [`src/styles.scss`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/styles.scss):** Karanlık mod renk paletini (`dark-950`..`dark-500`, `brand-indigo`, `brand-purple`, `brand-cyan`), `.glass-panel` bulanık cam görünümünü ve katmanların ekrandan ayrılırken kullandığı çıkış animasyonlarını (`animate-fade-out`, `animate-slide-down-out`, `animate-slide-up-out`, `animate-scale-out`) tanımlar.
* **[`src/index.html`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/index.html):** Kurgu şablonlarında ve altyazılarda kullanılan 12 Google Font ailesini (`Anton`, `Bangers`, `Bebas Neue`, `Cinzel`, `Fira Code`, `Inter`, `Montserrat`, `Oswald`, `Outfit`, `Playfair Display`, `Poppins`, `Syne`) yükler.
* **[`src/app/app.config.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/app.config.ts) & [`src/app/app.routes.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/app.routes.ts):**
  * `appConfig`: `provideHttpClient(withFetch(), withInterceptors([apiKeyInterceptor]))` ile her HTTP isteğine `X-API-Key` başlığı eklenmesini sağlar.
  * `routes`: 4 ana rotayı tanımlar:
    1. `''` -> `ProjectListComponent`
    2. `'project/:id'` -> `ProjectDetailComponent`
    3. `'project/:id/editor'` -> `EditorComponent`
    4. `'project/:id/render/:renderJobId'` -> `RenderResultComponent`

---

### 8.2. Core Katmanı: Interceptor, Veri Modelleri ve Servisler (`src/app/core/`)

#### 1. [`core/interceptors/api-key.interceptor.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/interceptors/api-key.interceptor.ts)
* **`apiKeyInterceptor(req, next)`:** Giden her HTTP isteğini klonlayıp `headers` içine `'X-API-Key': environment.apiKey` (`'SUPER_SECRET_OTOEDIT_KEY_123!'`) başlığını otomatik ekler.

#### 2. `core/models/` Klasöründeki TypeScript Arayüzleri
* **[`edl.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/edl.model.ts):** Frontend'deki tüm kurgu durumunu temsil eden `CutItem`, `OverlayItem`, `TranscriptWord`, `TranscriptSegment`, `TranscriptData`, `ViralClipItem`, `SuggestionItem`, `SubtitleStyleConfig`, `BackgroundMusicConfig`, `ColorGradingConfig`, `EdlSettings`, `EdlContent`, `EdlDto` ve `EdlPatchDto` arayüzlerini içerir.
* **[`chat.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/chat.model.ts):** `FormFieldDto` (`text | color | select | number | position`), `ChatMessageDto` ve `ChatResponseDto` arayüzlerini tanımlar.
* **[`project.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/project.model.ts), [`video.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/video.model.ts), [`asset.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/asset.model.ts), [`render.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/render.model.ts), [`template.model.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/models/template.model.ts):** İlgili backend DTO'larının birebir TypeScript karşılıklarıdır.

#### 3. `core/services/` Klasöründeki 10 Çekirdek Servis ve Fonksiyonları
1. **[`api.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/api.service.ts) (`ApiService`):** `get<T>`, `post<T>`, `patch<T>`, `put<T>`, `delete<T>` jenerik HTTP çağrılarını `/api` önekiyle yürütür.
2. **[`project.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/project.service.ts) (`ProjectService`):** `getAll()`, `getById(id)`, `create(dto)`, `update(id, dto)`, `delete(id)` metodlarını içerir.
3. **[`video.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/video.service.ts) (`VideoService`):**
   * **`uploadVideo(projectId, file, options)`:** `FormData` içine video dosyasını ve `autoJumpcut`, `autoRetake`, `autoBroll`, `autoSubtitles` tercihlerini ekleyip `{ reportProgress: true, observe: 'events' }` ile yükleme yüzdesini anlık raporlayarak gönderir.
   * **`getVideo(projectId)`:** Projenin video detaylarını getirir.
4. **[`edl.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/edl.service.ts) (`EdlService`):** `getEdl(projectId)`, `patchEdl(projectId, patch)`, `undoEdl(projectId)` ve `redoEdl(projectId)` metodlarıyla EDL okuma, yamama ve geri/ileri alma işlemlerini yapar.
5. **[`chat.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/chat.service.ts) (`ChatService`):** `sendMessage(projectId, mesaj)`, `getHistory(projectId)`, `applyPendingPatch(projectId, messageId)` ve `submitForm(projectId, messageId, parameters)` metodlarını barındırır.
6. **[`asset.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/asset.service.ts) (`AssetService`):** `getAssets(projectId)`, `uploadAsset(projectId, file)` ve `deleteAsset(projectId, assetId)` metodlarını içerir.
7. **[`render.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/render.service.ts) (`RenderService`):** `requestRender(projectId, dto)`, `getRenderStatus(projectId, renderJobId)` ve `getDownloadUrl(projectId, renderJobId)` metodlarını içerir.
8. **[`template.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/template.service.ts) (`TemplateService`):** `getAll()` ve `getById(id)` ile şablonları getirir.
9. **[`signalr.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/signalr.service.ts) (`SignalrService`):**
   * **`initConnection()`, `registerHandlers()`, `startConnection()`:** `/pipeline-hub` adresine WebSockets + LongPolling ve otomatik yeniden bağlanma (`[0, 2000, 5000, 10000, 30000]` ms) ile bağlanır. `'AnalysisProgress'`, `'AnalysisCompleted'`, `'RenderProgress'`, `'RenderCompleted'` ve `'PipelineError'` olaylarını yakalayıp ilgili RxJS `Subject` akışlarına ve sinyallere aktarır.
   * **`joinProjectGroup(projectId)` & `leaveProjectGroup(projectId)` & `rejoinActiveGroups()`:** Proje odasına katılır; bağlantı kopup yeniden geldiğinde aktif odalara otomatik tekrar katılır.
10. **[`diagnostics.service.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/core/services/diagnostics.service.ts) (`DiagnosticsService`):**
    * **`logTrace(...)` & `printSummary()`:** Editördeki geometri ve durum değişimlerini kaydeder ve `window.__OTOEDIT_DIAGNOSTICS__` üzerinden konsolda tablo halinde incelenmesini sağlar.

---

### 8.3. Ortak Bileşenler (`shared/`) ve Sayfa Bileşenleri (`features/`)

* **[`shared/components/navbar/navbar.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/shared/components/navbar/navbar.component.ts) (`NavbarComponent`):** Üst bar; proje başlığını ve SignalR canlı bağlantı durumunu (`Canlı Senkron` / `Bağlanıyor...`) gösterir.
* **[`shared/components/progress-bar/progress-bar.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/shared/components/progress-bar/progress-bar.component.ts) (`ProgressBarComponent`) & [`status-badge.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/shared/components/status-badge/status-badge.component.ts) (`StatusBadgeComponent`):** Yüzdelik ilerleme çubuğu ve duruma göre renklenen rozet bileşenleri.
* **[`shared/pipes/duration.pipe.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/shared/pipes/duration.pipe.ts) (`DurationPipe`) & [`file-size.pipe.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/shared/pipes/file-size.pipe.ts) (`FileSizePipe`):** Saniyeyi `MM:SS` formatına ve baytı `MB/GB` formatına çeviren borular.
* **[`features/project-list/project-list.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-list/project-list.component.ts) (`ProjectListComponent`):**
  * `loadProjects()`, `submitCreate()`, `deleteProject(e, id)`, `navigateToProject(id)` metodlarıyla projeleri listeler, yeni proje modalını yönetir ve detay sayfasına yönlendirir.
* **[`features/project-detail/project-detail.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/project-detail/project-detail.component.ts) (`ProjectDetailComponent`):**
  * `loadProject(id)`, `loadTemplates()`, `setupSignalR(projectId)`, `uploadFile(file)`, `updateFormat(format)`, `selectTemplate(templateId)` ve `goToEditor()` metodlarıyla video yükleme, pipeline tercihleri, canlı analiz yüzdesi izleme ve editöre geçiş işlemlerini yönetir.
* **[`features/render-result/render-result.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/render-result/render-result.component.ts) (`RenderResultComponent`):**
  * `setupSignalR()`, `startPolling()` (3 saniyede bir yedek durum sorgulama), `checkStatus()`, `fetchDownloadUrl()` ve `retryRender()` metodlarıyla FFmpeg dışa aktarma sürecini takip eder, tamamlandığında videoyu oynatır ve MP4 indirme bağlantısını sunar.

---

### 8.4. Ana Kurgu Stüdyosu: [`features/editor/editor.component.ts`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts) (`EditorComponent`)

6142 satırlık bu bileşen, uygulamanın tüm NLE kurgu yeteneklerini tek bir entegre stüdyoda toplar. İçindeki temel hesaplanmış sinyaller (`computed`) ve fonksiyon grupları şunlardır:

1. **Çekirdek Hesaplanmış Sinyaller (`computed`):**
   * **`activeEdl`:** Eğer kullanıcı AI sohbetinde bir yamayı önizliyorsa `previewEdl()` değerini, değilse gerçek `edl()` değerini döner. Tüm ekran `activeEdl()` üzerinden beslendiği için AI önizlemesi tek satır kodla tüm timeline ve video üzerinde canlı simüle edilir.
   * **`clips`:** `0`, `totalDuration`, kullanıcının eklediği `splitMarkers` (bölme noktaları) ve `edl.cuts` içindeki her bir kesimin `start` ve `end` saniyelerini tek bir sıralı dizide birleştirir. Ardışık her iki sınır arasını bir klip nesnesi (`{ id, start, end, duration, isCut, cutObj }`) olarak üretir.
   * **`visibleDuration`:** Aktif olan sıkıştırma (`rippleAi`, `rippleRetake`, `rippleManual`) filtrelerine göre gizlenmeyen (`isVisible(clip) === true`) kliplerin toplam süresini hesaplar.
   * **`activeOverlays`:** Gizli olmayan kanallarda (`!hiddenTracks.has(trackId)`) o anki `currentTime()` saniyesine denk gelen metin ve görsel katmanları filtreler.
   * **`currentSubtitleSegment`:** O anki saniye kesilmiş bir bölgede değilse ve `showSubtitles()` açıksa, o saniyeye denk gelen altyazı segmentini döner.
   * **`ghostPreview`:** Kullanıcı AI sohbetinde bir `clarification` formunu doldururken seçtiği metin, renk, font ve 16:9 mini sahne konumunu gerçek zamanlı olarak video monitörü üzerinde kesikli çerçeveli bir taslak katman olarak gösterir.

2. **Zaman Haritalama ve Oynatma Fonksiyonları:**
   * **`getVisTimeFromRawTime(rawTime)` & `getRawTimeFromVisTime(visTime)`:** Sıkıştırılmış (Ripple) timeline açıkken gerçek video saniyesi ile timeline üzerindeki görsel konum arasındaki çift yönlü matematiksel dönüşümü yapar.
   * **`onTimeUpdate()`:** Video oynarken her karede çalışır; eğer `video.currentTime` gizlenmiş/kesilmiş bir klibin içine girerse, ardışık tüm kesilmiş kliplerin sonuna `+ 0.04s` ekleyerek anında sağlam klibe zıplar (`video.currentTime = finalJumpTime`).
   * **`loadAudioWaveform(url)` & `getWaveformPathForClip(clip)`:** EDL'de `audioPeaks` varsa onu kullanır, yoksa Web Audio API (`AudioContext.decodeAudioData`) ile sesi çözüp RMS + Peak dalga formunu çıkarır ve her klibin içine renkli SVG `<path>` olarak çizer.

3. **Klip, Altyazı, Katman ve AI Kurgu Fonksiyonları:**
   * **Klip:** `addSplitMarker()` (`B`), `rippleDeleteLeft()` (`V`), `deleteSelectedClips()` (`Del`), `restoreSelectedCuts()`, `mergeSelectedClips()` (`M`), `applyBatchCutAdjustment()` (toplu milisaniye kesim kaydırma), `undo()` (`Ctrl+Z`), `redo()` (`Ctrl+Y`).
   * **Altyazı:** `startEditSubtitle(seg)` (çift tıkla satır içi düzenleme), `saveSubtitleEdit(seg, newText)`, `onSubtitleDragStart`, `onSubtitleResizeStart`, `applySubtitlePreset(preset)`, `persistSubtitleStyle()`, `convertSubtitleToOverlay()`, `deleteSubtitleSegment()`, `isWordActive(word)` (Karaoke kelime parlama kontrolü).
   * **Katman (Overlay) & Çoklu Kanal:** `autoAssignOverlayTracks(overlays)`, `addTrackLane()`, `deleteTrackLane(trackNum)`, `toggleTrackVisibility(trackNum)`, `toggleTrackLock(trackNum)`, `addTextOverlay()`, `addImageOverlayFromUrl()`, `addAssetOverlay()`, `onCanvasDragStart` (video üzerinde fareyle taşıma), `onCanvasResizeStart` (video üzerinde köşeden boyutlandırma), `onOverlayDragStart` (timeline'da yatay/dikey kanal taşıma), `onOverlayResizeStart`, `saveInspector()`, `duplicateOverlay()` (`Ctrl+D`), `splitOverlayAtPlayhead()`.
   * **AI Chat, BGM, Color Grading & Export:** `sendChatMessage()`, `previewPatch(msg)`, `applyPatch(msg)`, `cancelPatch(msg)`, `onMiniStageClick(event, msg, fieldId)`, `submitForm(msg)`, `setBgmPreset()`, `toggleAutoDucking()`, `applyColorPreset()`, `saveColorGrading()`, `requestExport()`.

---

## BÖLÜM 9: Uçtan Uca Kullanıcı Süreçleri (UI Tıklamasından Backend, Worker ve Ekrana Dönüşe Kadar Adım Adım Akışlar)

Bu bölümde, bir kullanıcının OtoEdit arayüzünde yaptığı tüm temel işlemlerin perde arkasında hangi dosyalar, hangi fonksiyonlar ve hangi servisler üzerinden nasıl gerçekleştiğini adım adım takip ediyoruz.

---

### Süreç 1: Yeni Proje Oluşturma, Ham Video Yükleme ve Yapay Zeka Analizinin Canlı Takibi

1. **Kullanıcı Aksiyonu (Proje Oluşturma):**
   * Kullanıcı ana sayfada (`ProjectListComponent` — `project-list.component.ts`) **"Yeni Proje Oluştur"** butonuna basar, proje adını yazar, formatı (`9:16 Reels` veya `16:9 Yatay`) seçer ve **"Projeyi Başlat"** butonuna tıklar.
2. **Frontend -> Backend İsteği:**
   * `ProjectListComponent.submitCreate()` fonksiyonu tetiklenir ve `ProjectService.create(this.newProject)` üzerinden `ApiService.post('/projects', dto)` çağrılır.
   * `apiKeyInterceptor` isteğin başlığına `X-API-Key` ekler ve istek `.NET API`'ye ulaşır.
3. **Backend İşleyişi (`ProjectsController` -> `ProjectManager` -> DB):**
   * `ProjectsController.Create(ProjectCreateDto dto)` uç noktası isteği karşılar ve `ProjectManager.CreateAsync(dto)` metodunu çağırır.
   * `ProjectCreateValidator` proje adını doğrular; `ProjectRepository.AddAsync(project)` ile PostgreSQL `projects` tablosuna `Durum = ProjectDurumu.Taslak` olarak kayıt atılır ve oluşturulan `ProjectDetailDto` (HTTP 201) döndürülür.
4. **Detay Sayfasına Yönlendirme ve SignalR Odasına Katılım:**
   * Frontend dönen `res.id` ile kullanıcıyı `/project/{id}` (`ProjectDetailComponent` — `project-detail.component.ts`) sayfasına yönlendirir.
   * `ProjectDetailComponent.ngOnInit()` -> `setupSignalR(id)` çalışır ve `SignalrService.joinProjectGroup(id)` üzerinden `/pipeline-hub` (`PipelineHub.JoinProjectGroup`) çağrılarak tarayıcı `project-{id}` WebSocket odasına abone edilir.
5. **Kullanıcı Aksiyonu (Ham Video Yükleme):**
   * Kullanıcı `ProjectDetailComponent` ekranında `autoJumpcut`, `autoRetake`, `autoBroll`, `autoSubtitles` tercihlerini seçer ve `.mp4` videosunu sürükleyip bırakır (`onFileDrop`).
   * `uploadFile(file)` metodu `VideoService.uploadVideo(projectId, file, options)` fonksiyonunu çağırır. Bu fonksiyon `FormData` oluşturup `POST /api/projects/{projectId}/videos` adresine `reportProgress: true` ile gönderir.
   * Dosya giderken `HttpEventType.UploadProgress` olayları `uploadPercentage` sinyalini `0`'dan `100`'e kadar canlı günceller.
6. **Backend Video Kaydı ve Kuyruğa Mesaj Atma (`VideosController` -> `VideoManager` -> MinIO & RabbitMQ):**
   * `VideosController.UploadVideo` isteği alır ve `VideoManager.UploadVideoAsync(...)` metoduna iletir.
   * `VideoManager` dosyayı doğrular ve `MinioFileStorageService.UploadFileAsync` ile MinIO'daki `videos/{projectId}/{videoId}.mp4` yoluna stream olarak yazar.
   * PostgreSQL `videos` tablosuna kayıt ekler, `projects` tablosundaki durumu `AnalizEdiliyor` yapar ve MassTransit `IPublishEndpoint.Publish` ile RabbitMQ'ya **`VideoUploadedEvent`** mesajını fırlatır.
7. **Python Worker Analizi ve Canlı İlerleme Bildirimleri (`AnalysisConsumer` -> SignalR -> UI):**
   * Python Worker'daki `AnalysisConsumer._on_message` (`analysis_consumer.py`) mesajı yakalar.
   * Videoyu MinIO'dan indirir (%5), gürültüyü temizler (%12), Silero VAD + RMS analizini yapar (%18), STT ve Yüz Takibini paralel çalıştırır (%25–%55), Retake v3 (%65) ve Jump-Cut v3 (%75) kesimlerini hesaplar, B-Roll/Öneri/Viral Klipleri paralel üretir (%85) ve `EdlBuilder.build()` ile taslak EDL JSON'u inşa eder (%95).
   * Her aşamada `PipelineLogger.log_progress` hem RabbitMQ'ya `PipelineStageChangedEvent` atar hem de `.NET InternalLogsController.LogPipelineProgress` (`POST /api/internal/logs/pipeline`) uç noktasını çağırır.
   * `.NET API` bu ilerlemeleri `PipelineNotificationManager` üzerinden SignalR `project-{id}` odasına `"AnalysisProgress"` olayı olarak basar.
   * `ProjectDetailComponent` içindeki `signalr.analysisProgress$` aboneliği bu mesajları yakalayıp ekrandaki ilerleme çubuğunu (`analysisPercentage`) ve aşama yazısını (`analysisStageMessage`) saniye saniye günceller.
8. **Analiz Tamamlanması ve Editöre Geçiş:**
   * Python Worker `RabbitMQPublisher.publish_analysis_completed` ile **`AnalysisCompletedEvent`** (içinde üretilen tam EDL JSON ile birlikte) yayınlar.
   * `.NET API`'deki `AnalysisNotificationConsumer.Consume` bu olayı yakalar; `EdlManager.CreateOrUpdateAsync` ile EDL JSON'u PostgreSQL `edit_decision_lists` tablosuna (`Versiyon = 1`) kaydeder, proje durumunu `AnalizTamamlandi` yapar ve SignalR'a `"AnalysisCompleted"` gönderir.
   * `ProjectDetailComponent` `"AnalysisCompleted"` sinyalini alınca `loadProject(projectId)` çağırır, `canGoToEditor()` `true` olur ve ekranda **"Editör & Timeline'a Git →"** butonu belirir.

---

### Süreç 2: Videodan Bir Parçayı Bölme (`B`), Silme/Kesme (`Del`), Solu Kırpma (`V`) ve Kesilen Parçayı Geri Yükleme

1. **Kullanıcı Aksiyonu (Bölme — `B` Tuşu veya Makas Butonu):**
   * Kullanıcı editörde (`EditorComponent` — `editor.component.ts`) videonun `24.5.` saniyesine gelir ve klavyeden `B` tuşuna (veya araç çubuğundaki **"✂️ Böl"** butonuna) basar.
   * `onGlobalKeyDown` -> `addSplitMarker()` fonksiyonu çalışır.
   * `24.5` değeri `splitMarkers` sinyaline (`signal<number[]>`) eklenir.
   * `clips` computed sinyali `splitMarkers` değişimini anında algılar ve örneğin `15.0s - 40.0s` arasındaki sağlam klibi `15.0s - 24.5s` ve `24.5s - 40.0s` olarak iki ayrı seçilebilir klibe böler (henüz bir yer silinmediği için videoda kesinti olmaz, sadece klip iki parçaya ayrılmıştır).
2. **Kullanıcı Aksiyonu (Seçili Klibi Silme / Kesme — `Del` Tuşu veya Çift Tıklama):**
   * Kullanıcı böldüğü `24.5s - 40.0s` klibine tıklar (`selectClip`) ve `Delete` / `Backspace` tuşuna (veya **"🗑 Seçiliyi Kes"** butonuna) basar.
   * `deleteSelectedClips()` (veya tek klip için `deleteClip(clip)`) fonksiyonu tetiklenir.
3. **Frontend Patch Hazırlığı ve HTTP İsteği:**
   * `deleteSelectedClips()` seçili olan sağlam kliplerin her biri için şu yama nesnesini oluşturur:
     ```json
     {
       "cuts": [
         {
           "id": "manual_cut_1729410000_0",
           "start": 24.5,
           "end": 40.0,
           "reason": "Manuel kesim",
           "source": "user",
           "action": "add"
         }
       ]
     }
     ```
   * Ardından `this.edlService.patchEdl(this.projectId, patch)` çağrılır ve `PATCH /api/projects/{projectId}/edl` isteği `.NET API`'ye gönderilir.
4. **Backend İşleyişi (`EdlController` -> `EdlManager.PatchEdlAsync` -> DB & Redis):**
   * `EdlController.PatchEdl` isteği alır ve `EdlManager.PatchEdlAsync(projectId, patch)` metodunu çağırır.
   * **Adım A (Snapshot):** `EdlManager` önce `SaveSnapshotAsync` ile kesim yapılmadan önceki EDL JSON'u `edl_snapshots` tablosuna (`Kaynak = "system"`) kaydeder (kullanıcı birazdan `Ctrl+Z` yaparsa geri dönebilmek için).
   * **Adım B (JSON Merge):** Mevcut `EdlJson` içindeki `cuts` dizisine `manual_cut_1729410000_0` öğesini ekler.
   * **Adım C (Versiyon & Cache):** `edl.Versiyon` değerini 1 artırır, `edit_decision_lists` tablosunu günceller ve Redis'teki `edl:{projectId}` önbelleğini siler. Yeni versiyon numarasını (`{ projectId, versiyon, mesaj }`) Frontend'e döner.
5. **Ekrana Geri Dönüş ve Anlık Güncelleme:**
   * `deleteSelectedClips()` içindeki `.subscribe({ next: () => this.loadEdl() })` tetiklenir.
   * `loadEdl()` -> `GET /api/projects/{projectId}/edl` ile güncel EDL'yi çeker ve `this.edl.set(res.edl)` yapar.
   * `clips` computed sinyali yeniden hesaplanır: `24.5s - 40.0s` aralığı artık `isCut: true` (`reason: 'Manuel kesim'`) olur. Eğer `🖐 Manuel Sıkışık` (`rippleManual`) açıksa bu parça timeline'dan anında gizlenir ve sağındaki klipler sola kayıp boşluğu kapatır!
6. **Alternatif: Solu Kırp & Birleştir (`V` Tuşu — `rippleDeleteLeft()`):**
   * Kullanıcı bir klibin ortasında (örn. `18.2s`) durup `V` tuşuna basarsa `rippleDeleteLeft()` çalışır: Klibin başlangıcından (`15.0s`) imlecin olduğu saniyeye (`18.2s`) kadar olan sol parçayı otomatik olarak `cuts` listesine ekleyip `patchEdl` ile kaydeder.
7. **Kesilen Bir Parçayı Geri Yükleme (`restoreClip` / `restoreSelectedCuts`):**
   * Kullanıcı sıkıştırma filtresini kapatıp kırmızı/kehribar renkli kesilmiş bir klibe çift tıklarsa veya seçip **"✨ Kesimi İptal Et"** butonuna basarsa; `restoreSelectedCuts()` fonksiyonu ilgili kesimin ID'si ile `{ cuts: [{ id: cut.id, start: 0, end: 0, action: 'remove' }] }` yamasını `PATCH /api/projects/{projectId}/edl` adresine gönderir.
   * `EdlManager.PatchEdlAsync` `"action": "remove"` komutunu görünce o kesimi `cuts` dizisinden siler ve sahne videoya geri döner.

---

### Süreç 3: Sıkıştırılmış (Ripple/Manyetik) Timeline Üzerinde Gezinme ve Canlı Önizleme Oynatıcısının Kesilen Kısımları Atlaması

1. **Sıkıştırılmış Timeline Matematiği (`TimelineMapper` Frontend Karşılığı):**
   * Diyelim ki 60 saniyelik bir videonun `10.0s - 20.0s` arası kesildi ve üst barda `🤖 AI Sıkışık` (`rippleAi = true`) açık.
   * Artık `visibleDuration()` `50.0` saniyedir. Timeline'ın tam ortası (`%50`) gerçek videonun `30.` saniyesi değil, `35.` saniyesidir!
   * Kullanıcı fareyle timeline'ın ortasına tıkladığında (`onTimelineTrackMouseDown` -> `startScrubbing(clientX)` -> `getTimeAtClientX(clientX)`):
     * Tıklanan piksel oranı (`percentage = 0.50`) görünür süreyle çarpılır (`visTime = 25.0s`).
     * `getRawTimeFromVisTime(25.0)` fonksiyonu görünür klipleri baştan itibaren toplar: 1. klip (`0.0s - 10.0s`, süre `10s`) + 2. klip (`20.0s - 60.0s` içinden `15s` ilerle) = gerçek video zamanını **`35.0s`** olarak bulur ve `video.currentTime = 35.0` yapar!
   * Tersine, Playhead iğnesi ve katman kutuları ekranda çizilirken `getVisTimeFromRawTime(35.0)` çağrılır, kesilen 10 saniye düşülerek `25.0 / 50.0 = %50` konumuna yerleştirilir.
2. **Oynatma Sırasında Kesilen Bölgelerin Anında Atlanması (`onTimeUpdate`):**
   * Kullanıcı `Space` tuşuna basıp videoyu oynatmaya başlar (`togglePlayPause()`).
   * Tarayıcı `<video>` elementi oynarken saniyede birçok kez `(timeupdate)="onTimeUpdate()"` olayını tetikler.
   * `onTimeUpdate()` o anki `video.currentTime` değerinin (örneğin `10.02s`) hangi klibin içine düştüğünü bulur (`currentClip`).
   * `!this.isVisible(currentClip)` kontrolüyle bu klibin kesilmiş ve gizlenmiş olduğunu fark ettiği anda:
     * Bu kesimin ve hemen peşinden gelen ardışık diğer kesilmiş kliplerin bitiş saniyesini (`targetJumpTime = 20.0s`) bulur.
     * Tarayıcı çözücüsünün aynı kareye geri yuvarlanıp sonsuz döngüye girmesini önlemek için `+ 0.04` saniye (1 kare tampon) ekleyerek `video.currentTime = 20.04` ataması yapar!
     * Kullanıcı hiçbir render beklemeden `9.99.` saniyeden doğrudan `20.04.` saniyeye pürüzsüzce geçiş yapan kurgulanmış videoyu izler.

---

### Süreç 4: Toplu Milisaniye Kesim İnce Ayarı ve Geri Al / İleri Al (`Undo / Redo`)

1. **Toplu Milisaniye Kesim İnce Ayarı (`applyBatchCutAdjustment`):**
   * Kullanıcı AI'ın yaptığı sessizlik kesimlerinin kelimelere çok yakın olduğunu hissederse üst bardaki **"🎛 Kesim Payı Ayarla"** butonuna tıklar (`openCutAdjustModal()`).
   * Modal pencerede kapsamı (`Kısa Kesimler < 1sn`, `Uzun Kesimler >= 1sn` veya `Tüm Otomatik Kesimler`) seçer ve başlangıç/bitiş kaydırma çubuklarını örneğin `+120 ms` / `-100 ms` olarak ayarlar.
   * Kaydırıcı oynatıldıkça `onCutStartInput()` / `onCutEndInput()` fonksiyonları yerel sinyal üzerinde değişikliği anında simüle eder (canlı önizleme).
   * Kullanıcı **"Değişiklikleri Kaydet"** butonuna bastığında `applyBatchCutAdjustment()` çalışır:
     * Hedef kesimlerin orijinal sınırlarına (`origStart`, `origEnd`) milisaniye ofsetlerini ekler.
     * Eğer daraltma sonucunda süresi `60 ms` (`0.06s`) altına düşen bir kesim kalırsa onu `action: 'remove'` olarak, diğerlerini ise yeni `start`/`end` ve `origStart`/`origEnd` değerleriyle `action: 'update'` olarak tek bir toplu `patchEdl` isteğiyle Backend'e kaydeder.
2. **Geri Al (`Undo` — `Ctrl+Z`) ve İleri Al (`Redo` — `Ctrl+Y`):**
   * Kullanıcı yaptığı kesim veya katman işlemini beğenmeyip `Ctrl+Z` tuşuna (veya üst bardaki **Geri Al** ikonuna) basar.
   * `EditorComponent.undo()` -> `EdlService.undoEdl(projectId)` -> `POST /api/projects/{projectId}/edl/undo` çağrılır.
   * Backend'de `EdlController.UndoEdl` -> `EdlManager.UndoAsync(projectId)` çalışır:
     * `edl_snapshots` tablosundan en son `"system"` kaydını alır, şu anki EDL'yi `"system_undo"` olarak Redo yığınına kaydeder ve aktif EDL'yi önceki haline döndürüp `EdlDto` olarak Frontend'e döner.
   * Frontend dönen `res.edl` verisini doğrudan `this.edl.set(res.edl)` ile sinyale yazar ve tüm ekran bir önceki adıma geri döner.

---

### Süreç 5: Altyazı (Karaoke Subtitle) Düzenleme, Taşıma ve Serbest Katmana Dönüştürme

1. **Çift Tıklayarak Satır İçi (Inline) Altyazı Düzenleme:**
   * Kullanıcı timeline'daki `"💬 Altyazı"` kanalında bulunan bir altyazı kutusuna çift tıklar (`(dblclick)="startEditSubtitle(seg)"`).
   * `editingSubtitleId` sinyali o segmentin ID'sine eşitlenir ve kutunun içinde anında bir `<input>` alanı açılır.
   * Kullanıcı yazıyı düzeltip `Enter` tuşuna bastığında (veya dışarı tıkladığında) `saveSubtitleEdit(seg, newText)` çalışır:
     * Segmentin `text` alanını günceller.
     * Eğer segment içinde Karaoke kelime dizisi (`seg.words`) varsa ve kelime sayısı aynıysa her kelimenin metnini birebir günceller; kelime sayısı değiştiyse segmentin süresini yeni kelimelere eşit olarak paylaştırıp `seg.words` dizisini yeniden oluşturur (böylece Karaoke vurgusu bozulmaz!).
     * Güncellenmiş `transcript` nesnesini `edlService.patchEdl(projectId, { transcript: edl.transcript })` ile Backend'e kaydeder.
2. **Altyazıyı Timeline Üzerinde Sürükleme ve Uzatıp Kısaltma:**
   * Kullanıcı altyazı kutusunu fareyle tutup sağa/sola sürüklediğinde `onSubtitleDragStart(event, seg)` ve `onGlobalMouseMove(event)` çalışır; segmentin `start`, `end` ve içindeki tüm `words` zaman damgaları `deltaTime` kadar kaydırılır.
   * Kutunun sol veya sağ kenarındaki tutamaçtan sürüklendiğinde `onSubtitleResizeStart(event, seg, edge)` segmentin süresini uzatır veya kısaltır.
   * Kullanıcı fare tuşunu bıraktığında (`onGlobalMouseUp`) yeni `transcript` otomatik olarak `patchEdl` ile veritabanına kaydedilir.
3. **Altyazı Stil Şablonu Seçme ve Serbest Katmana Dönüştürme:**
   * Kullanıcı altyazıya tıkladığında sağdaki **Inspector (Özellikler)** paneli `"Altyazı Özellikleri"` moduna geçer. Buradan `TikTok Sarı`, `Sinematik`, `Opaque Kutu` veya `Neon Glow` şablonlarından birine tıkladığında `applySubtitlePreset(preset)` -> `persistSubtitleStyle()` çalışır ve `settings.subtitleStyle` nesnesi `patchEdl` ile kaydedilir.
   * Kullanıcı **"✨ Serbest Katmana Dönüştür"** butonuna basarsa `convertSubtitleToOverlay()` çalışır: O altyazı segmentini `transcript.segments` dizisinden siler ve aynı metin, başlangıç süresi ve stil özellikleriyle `overlays` dizisine bağımsız bir `OverlayItem` (video üzerinde istenilen yere sürüklenebilen katman) olarak ekler!

---

### Süreç 6: Video Üzerine Yazı, Görsel/B-Roll veya Medya Katmanı Ekleme, Canvas Üzerinde Fareyle Sürükleme ve AI Arka Plan Silme

1. **Katman Ekleme (Yazı, Kendi Medyan veya Stok B-Roll):**
   * **Yazı Ekleme:** Kullanıcı `T` tuşuna veya `"+ Yazı"` butonuna basar (`addTextOverlay()`). İmlecin bulunduğu saniyede (`currentTime()`), o saniyede dolu olmayan ilk uygun kanal (`trackId: 1, 2, 3...`) otomatik hesaplanır ve varsayılan `positionX: 50, positionY: 80` koordinatlarında yeni bir metin katmanı `patchEdl` ile eklenir.
   * **Kendi Medyasını Yükleme ve Ekleme:** Sol paneldeki `"Medya"` sekmesinden kullanıcı bilgisayardan bir PNG/JPG görsel sürükler (`onAssetDrop` -> `uploadFile` -> `AssetService.uploadAsset` -> `POST /api/projects/{id}/assets`). `AssetsController.UploadAsset` -> `AssetManager.UploadAssetAsync` dosyayı MinIO'ya yükler ve `ProjectAssets` tablosuna kaydeder. Kullanıcı yüklenen görselin üzerindeki `"+ Katman Ekle"` butonuna bastığında `addAssetOverlay(asset)` görseli timeline'a ekler.
2. **Video Monitörü (Canvas) Üzerinde Fareyle Sürükleme ve Boyutlandırma:**
   * Kullanıcı video önizleme ekranının üzerindeki metin veya görsel katmanını fareyle tutup sürüklediğinde `(mousedown)="onCanvasDragStart($event, ov.id)"` çalışır.
   * Fare hareket ettikçe (`onGlobalMouseMove`), video konteynerinin piksel genişlik ve yüksekliği (`getBoundingClientRect()`) baz alınarak farenin hareketi `%0` ile `%100` arasında `positionX` ve `positionY` yüzdesel koordinatlarına dönüştürülür ve katman ekranda canlı kayar.
   * Katmanın sağ alt köşesindeki `⤡` boyutlandırma tutamacından sürüklendiğinde (`onCanvasResizeStart`), görsel katmanlarda `scale` (`0.1`..`3.0`), metin katmanlarında ise `fontSize` (`12px`..`140px`) canlı büyütülüp küçültülür.
   * Fare bırakıldığında (`onGlobalMouseUp`), katmanın yeni `positionX`, `positionY`, `scale` veya `fontSize` değerleri `edlService.patchEdl` ile Backend'e kaydedilir.
3. **Inspector'dan AI Arka Plan Silme (`removeBg`), Çıkartma Konturu ve Rozet Kutu Ayarları:**
   * Kullanıcı katmana tıklayıp sağdaki **Inspector** panelinden:
     * Metin katmanı için **Kutu Stili** (`Hap / Pill`, `Yuvarlak`, `Rozet`), **Kontur** veya **Giriş/Çıkış Animasyonu** seçebilir;
     * Görsel katmanı için **`🪄 AI Arka Plan Sil (removeBg)`**, **`⬜ Beyaz Sticker Konturu`**, **Döndürme (`rotation`)** veya **Dairesel Maske (`circle`)** özelliklerini açıp **"Değişiklikleri Kaydet"** (`saveInspector()`) butonuna basar.
   * Bu ayarlar `OverlayItem` üzerinde `patchEdl` ile kaydedilir; hem tarayıcı önizlemesinde CSS filtreleriyle simüle edilir hem de dışa aktarma (render) sırasında Python Worker'daki `BackgroundRemoverService` (`rembg`) ve `PillowGraphicsEngine` tarafından gerçek piksel işleme ile videoya basılır.

---

### Süreç 7: Yönetmen AI (Sohbet Asistanı) ile Doğal Dilde Kurgu Yapma (Önizleme, Onaylama ve 16:9 Mini Sahneli Netleştirme Formu)

1. **Kullanıcı Aksiyonu (Sohbet Mesajı Gönderme):**
   * Kullanıcı sol paneldeki `"🤖 AI Kurgu"` sekmesini açar. İsterse önce timeline üzerinde bir veya birkaç klibi seçer, ardından sohbet kutusuna örneğin *"Buraya 'Kanala Abone Ol' yazısı ekle"* veya *"Ekrana dikkat çekici bir uyarı koy"* yazıp gönderir (`sendChatMessage()`).
   * Eğer timeline'da seçili klip varsa `sendChatMessage()` mesajın başına otomatik olarak `[Seçili Aralık: 14.0s - 19.5s] ` bilgisini ekler ve `ChatService.sendMessage(projectId, fullPrompt)` (`POST /api/projects/{projectId}/chat`) çağrısını yapar.
2. **Backend İşleyişi (`ChatController` -> `ChatManager` -> `GeminiChatProvider`):**
   * `ChatController.SendMessage` -> `ChatManager.SendMessageAsync` çalışır.
   * `ChatManager` son 10 mesajı, mevcut EDL JSON'u ve video transkriptini alıp `GeminiChatProvider.ProcessCommandAsync` metoduna verir.
   * `GeminiChatProvider` 4 kademeli LLM zinciriyle (Antigravity Proxy -> Groq -> Resmi Gemini -> Yerel Sezgisel Motor) komutu analiz eder ve iki ana kurgu senaryosundan biri gerçekleşir:
3. **Senaryo A — Net Komut ve Onay Bekleyen Yama (`patchDurumu = 'pending'`):**
   * Kullanıcının komutu netse AI doğrudan `edlPatch` üretir. `ChatManager` (varsa görsel aramalarını `PexelsService` ile MinIO'ya indirip zenginleştirerek) bu yamayı mesajın `PendingEdlPatch` sütununa yazar ve Frontend'e `patchDurumu: 'pending'` döner.
   * Sohbet balonunda **"🔍 Önizle"**, **"Onayla"** ve **"İptal"** butonları belirir:
     * Kullanıcı **"🔍 Önizle"** (`previewPatch(msg)`) butonuna basarsa: Frontend mevcut EDL'yi klonlar, bekleyen yamayı geçici `previewEdl` sinyaline uygular ve videoyu değişikliğin 2 saniye öncesine sarıp oynatır. Kullanıcı yamayı onaylamadan önce sonucu videoda canlı izler!
     * Kullanıcı **"Onayla"** (`applyPatch(msg)`) butonuna basarsa: `ChatService.applyPendingPatch` (`POST /api/projects/{id}/chat/{messageId}/apply`) çağrılır -> `ChatManager.ApplyPendingPatchAsync` yamayı `EdlManager.PatchEdlAsync` ile kalıcı olarak EDL'ye yazar -> Frontend `loadEdl()` ile gerçek durumu yükler.
4. **Senaryo B — Eksik Bilgi ve 16:9 Mini Sahneli Netleştirme Formu (`patchDurumu = 'clarification'` + `Ghost Preview`):**
   * Kullanıcı *"Ekrana bir başlık ekle"* gibi detayları eksik bir komut verdiyse, AI `intent: 'clarification'` ve `formFields` (Metin kutusu, Renk paleti, Font/Animasyon seçici ve Konum seçici) döndürür.
   * Sohbet balonunun içinde interaktif bir form ve **16:9 Mini Sahne (`Mini Stage`)** kutusu açılır.
   * Kullanıcı formda yazıyı yazarken, renk seçerken veya 16:9 Mini Sahne üzerinde istediği noktaya tıklarken (`onMiniStageClick(event, msg, fieldId)`), `ghostPreview` computed sinyali devreye girer ve **ana video oynatıcısının üzerinde kesikli çerçeveli `📍 Taslak` katmanını canlı olarak o konumda ve renkte gösterir!**
   * Kullanıcı **"✨ Onayla ve Ekle"** (`submitForm(msg)`) butonuna bastığında `ChatService.submitForm` (`POST /api/projects/{id}/chat/{messageId}/form`) çağrılır -> `ChatManager.SubmitFormAsync` form parametrelerinden `OverlayItem` oluşturup `EdlManager.PatchEdlAsync` ile EDL'ye kaydeder -> Katman timeline'daki yerini alır.

---

### Süreç 8: Arka Plan Müziği (Auto-Ducking BGM) ve Renk Düzenleme (Color Grading) Uygulama

1. **Arka Plan Müziği ve Auto-Ducking (`persistBgmSettings`):**
   * Kullanıcı üst araç çubuğundaki **"🎵 Müzik"** butonuna tıklar (`isBgmSelectorOpen.set(true)`).
   * Açılan menüden hazır telifsiz müziklerden birini seçer (`setBgmPreset(url, title)`), ses seviyesini (`bgmVolume`) ayarlar ve **"Konuşmada Müziği Kıs (Auto-Ducking)"** anahtarını (`toggleAutoDucking()`) açar.
   * `persistBgmSettings()` fonksiyonu `settings.backgroundMusic` nesnesini `PATCH /api/projects/{projectId}/edl` ile Backend'e kaydeder.
2. **Renk Düzenleme (`saveColorGrading`):**
   * Kullanıcı üst bardaki **"🎨 Renk"** butonuna tıklar (`showColorModal.set(true)`).
   * `Doğal`, `Canlı`, `Sinematik`, `Soğuk` veya `S&B` hazır filtrelerinden birini seçer (`applyColorPreset`) ya da Parlaklık (`videoBrightness`), Kontrast (`videoContrast`), Doygunluk (`videoSaturation`) ve Sıcaklık (`videoTemperature`) sürgülerini kaydırır.
   * Sürgüler kaydırıldıkça `videoFilterStyle` computed sinyali `<video>` elementinin `[style.filter]` özelliğini anında günceller.
   * **"Uygula ve Kaydet"** (`saveColorGrading()`) tıklandığında `settings.colorGrading` verisi `patchEdl` ile EDL'ye kaydedilir.

---

### Süreç 9: Nihai Videoyu Dışa Aktarma (`Render Et`), FFmpeg 2-Pass Render Süreci ve MP4 İndirme

1. **Kullanıcı Aksiyonu (`Render Et` Butonu):**
   * Kullanıcı tüm kurgusunu tamamlayıp sağ üst köşedeki **"🎬 Nihai Videoyu Render Et"** butonuna tıklar (`EditorComponent.requestExport()`).
2. **Frontend -> Backend Render İsteği:**
   * `requestExport()` önce `showSubtitles()` durumunu `edlService.patchEdl` ile senkronize eder, hemen ardından `RenderService.requestRender(projectId)` (`POST /api/projects/{projectId}/render`) çağrısını yapar.
3. **Backend İşleyişi (`RenderController` -> `RenderManager` -> RabbitMQ):**
   * `RenderController.RequestRender` -> `RenderManager.RequestRenderAsync(projectId)` çalışır.
   * Projenin son `EdlJson` belgesi kopyalanarak PostgreSQL `render_jobs` tablosuna `Durum = RenderDurumu.Kuyrukta` olarak yeni bir `RenderJob` kaydı açılır; proje durumu `RenderEdiliyor` yapılır.
   * MassTransit üzerinden RabbitMQ'ya **`RenderRequestedEvent`** (`RenderJobId`, `ProjectId`, `EdlJson`) mesajı fırlatılır ve Frontend'e `202 Accepted` (`RenderStatusDto`) dönülür.
4. **Render Takip Ekranına Yönlendirme (`RenderResultComponent`):**
   * Frontend kullanıcıyı `/project/{projectId}/render/{renderJobId}` (`RenderResultComponent` — `render-result.component.ts`) sayfasına yönlendirir.
   * Bu sayfa hem SignalR `project-{projectId}` odasını dinler hem de 3 saniyede bir (`startPolling()`) `GET /api/projects/{projectId}/render/{renderJobId}` uç noktasını yoklar.
5. **Python Worker 2-Pass FFmpeg Render İşleyişi (`RenderConsumer` -> `VideoRenderer`):**
   * Python Worker'daki `RenderConsumer._on_message` (`render_consumer.py`) mesajı alır:
     * **%10:** Kaynak videoyu MinIO'dan indirir.
     * **%30:** `VideoRenderer.render(...)` (`video_renderer.py`) başlar:
       1. `TemplateApplier.enrich_edl_with_template` ile şablon logosunu ve konuşmacı alt bandını ekler.
       2. `_cut_segments` ile kesilmeyen (`keep_segments`) tüm parçaları 8ms ses mikro-fade ve CFR uygulayarak paralel keser ve `ffprobe` ile gerçek sürelerini (`actual_durations`) ölçer.
       3. `TimelineMapper` ile tüm altyazı ve katman zamanlarını kesilmiş videonun yeni zaman çizgisine kaydırır.
       4. `PillowGraphicsEngine.render_text_badge` ile hap/rozet kutulu metinleri 2x supersampling ile şeffaf PNG'ye çevirir.
       5. `TextOverlay.generate_ass` ile Karaoke kelime vurgulu `.ass` altyazı dosyasını üretir.
       6. **1. Geçiş (`_concat_segments`):** Parçaları birleştirir, yüz takipli kadraj kırpmasını (`crop`) ve `.ass` altyazılarını videoya işler.
       7. **2. Geçiş (`ImageOverlay` + `AudioMixer`):** Görsel katmanlara varsa `BackgroundRemoverService` (`rembg` AI arka plan silme, sticker konturu, dairesel maske, chroma key) uygular, Z-Index (`trackId`) sırasına göre videonun üzerine bindirir ve `AudioMixer.apply_bgm_with_ducking` ile konuşma başladığında sesi kısılan arka plan müziğini miksleyerek nihai `.mp4` dosyasını (`h264_nvenc` GPU hızlandırmasıyla) üretir.
     * **%85:** Üretilen `.mp4` dosyasını `MinioClient.upload_render_output` ile MinIO'daki `renders/{projectId}/{renderJobId}.mp4` yoluna yükler.
     * **%100:** RabbitMQ'ya **`RenderCompletedEvent`** mesajını yayınlar ve yerel geçici dosyaları temizler.
6. **Tamamlanma Bildirimi, Önizleme ve İndirme:**
   * `.NET API`'deki `RenderNotificationConsumer.Consume` olayı yakalar; `RenderManager.CompleteRenderAsync` ile `render_jobs` ve `projects` tablolarında durumu `Tamamlandi` yapar ve SignalR üzerinden `"RenderCompleted"` mesajını yayınlar.
   * `RenderResultComponent` tamamlanma sinyalini alınca `fetchDownloadUrl()` -> `GET /api/projects/{projectId}/render/{renderJobId}/download` (`RenderManager.GetDownloadUrlAsync`) uç noktasını çağırarak MinIO'dan 2 saatlik Presigned MP4 URL'sini alır.
   * Ekranda başarı mesajı belirir, kurgulanmış nihai video `<video controls autoplay>` oynatıcısında otomatik başlar ve kullanıcı **"Nihai Videoyu İndir"** butonuna tıklayarak `.mp4` dosyasını bilgisayarına indirir.

---

## BÖLÜM 10: Tüm Dosyaların, Sınıfların ve Fonksiyonların Tam Teknik Referans Sözlüğü (Ekler)

Yukarıdaki bölümlerde mimariyi, katmanları ve uçtan uca kullanıcı süreçlerini akıcı anlatımla inceledik. Bu bölümde ise projedeki **hiçbir dosya, sınıf, veri modeli, enum veya fonksiyon atlanmadan** her birinin parametreleri, dönüş tipleri ve iç algoritmaları katalog halinde listelenmiştir.

---

# EK A: .NET Backend (OtoEdit.Data, OtoEdit.Business, OtoEdit.API, OtoEdit.UnitTests) ve Altyapı Tam Dosya & Fonksiyon Referansı

# OtoEdit .NET Backend ve Altyapı (Infrastructure) Kapsamlı İnceleme Raporu

Bu rapor, `D:\OtoEdit\OtoEdit` dizininde yer alan tüm **Root/Altyapı**, **`OtoEdit.Data`**, **`OtoEdit.Business`**, **`OtoEdit.API`** ve **`OtoEdit.UnitTests`** dosyalarının eksiksiz, satır satır analizini içerir.

---

## 1. Kök Dizin ve Altyapı (Root & Infrastructure) Dosyaları

### 1.1. `OtoEdit.slnx`
- **Amacı:** .NET 10 XML tabanlı yeni nesil Solution (`slnx`) dosyasıdır.
- **İçeriği:**
  - `/src/` klasörü altında:
    - `src/OtoEdit.API/OtoEdit.API.csproj`
    - `src/OtoEdit.Business/OtoEdit.Business.csproj`
    - `src/OtoEdit.Data/OtoEdit.Data.csproj`
  - `/tests/` klasörü altında:
    - `tests/OtoEdit.UnitTests/OtoEdit.UnitTests.csproj`

### 1.2. `docker-compose.yml`
- **Amacı:** Tüm sistemi (API, Python Worker, PostgreSQL, Redis, RabbitMQ, MinIO, Frontend, Nginx) Production/Container modunda ayağa kaldıran tam orkestrasyon dosyasıdır.
- **Servisler ve Detayları:**
  - `api` (`otoedit-api`): `src/OtoEdit.API/Dockerfile` üzerinden build edilir. `5001:8080` portunu açar. `postgres` (healthy), `redis` (started), `rabbitmq` (healthy), `minio` (started) bağımlılıklarını bekler. `ASPNETCORE_ENVIRONMENT=Production`, `ConnectionStrings__DefaultConnection`, `Redis__ConnectionString`, `RabbitMQ__*`, `Minio__*`, `ApiKey`, `Gemini__*`, `OpenAI__ApiKey` ortam değişkenlerini alır.
  - `python-worker` (`otoedit-worker`): `src/OtoEdit.PythonWorker/Dockerfile` ile build edilir. `NVIDIA_DRIVER_CAPABILITIES=all` ve `deploy.resources.reservations.devices` altında `driver: nvidia`, `count: all`, `capabilities: [gpu]` ile GPU passthrough kullanır.
  - `postgres` (`otoedit-postgres`): `postgres:16-alpine` imajı, `5432:5432` portu, `postgres_data` volume'u ve `pg_isready` healthcheck'i (5s aralık, 5 deneme) içerir.
  - `redis` (`otoedit-redis`): `redis:7-alpine` imajı, `6379:6379` portu.
  - `rabbitmq` (`otoedit-rabbitmq`): `rabbitmq:3-management-alpine` imajı, `5672:5672` (AMQP) ve `15672:15672` (Management UI) portları, `rabbitmq-diagnostics check_running` healthcheck'i.
  - `minio` (`otoedit-minio`): `minio/minio:latest` imajı, `9000:9000` (S3 API) ve `9001:9001` (Console) portları, `server /data --console-address ":9001"` komutu ve `minio_data` volume'u.
  - `frontend` (`otoedit-frontend`): `src/OtoEdit.Frontend/Dockerfile` ile build edilir, `4200:80` portunu açar.
  - `nginx` (`otoedit-nginx`): `nginx:alpine` imajı, `80:80` portu, `./nginx/nginx.conf:/etc/nginx/nginx.conf:ro` mount'u.

### 1.3. `docker-compose.dev.yml`
- **Amacı:** Geliştirme (Development) ortamında altyapı servislerini (`postgres`, `redis`, `rabbitmq`, `minio`) ve `python-worker` servisini Docker üzerinde çalıştırırken, `.NET API` ve `Angular Frontend`'in host makinede (Windows) doğrudan debug/hot-reload ile çalıştırılmasını sağlar.
- **Önemli Farklar ve Detaylar:**
  - Container isimleri `otoedit-dev-*` şeklindedir, volume'lar `dev_postgres_data` ve `dev_minio_data`'dır.
  - `rabbitmq` servisinde `RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS: "-rabbit consumer_timeout 36000000"` (10 saat consumer timeout) tanımlıdır; uzun süren video analizlerinde RabbitMQ'nun kanalı kapatmasını önler.
  - `python-worker` servisi `./src/OtoEdit.PythonWorker:/app` volume mount'u ile canlı kod değişikliklerini görür ve `API_BASE_URL=http://host.docker.internal:5001`, `ANTIGRAVITY_PROXY_URL=http://host.docker.internal:8045/v1`, `STT_ENGINE_ORDER=gemini_transcribe,groq,proxy_gemini,local_whisper`, `JUMPCUT_*` ve `VAD_*` parametrelerini `.env`'den alır.

### 1.4. `baslat.bat`
- **Amacı:** Windows üzerinde tek tıkla geliştirme ortamını başlatan Batch script'idir.
- **Adım Adım İşleyişi:**
  1. `NG_CLI_ANALYTICS=false` ayarlar. Açık olan eski `OtoEdit.API.exe` ve `WINDOWTITLE eq OtoEdit-*` pencerelerini `taskkill` ile temizler.
  2. `.env` dosyası yoksa `.env.example` dosyasından kopyalar; ardından `.env` içindeki tüm `KEY=VALUE` satırlarını `for /f` döngüsüyle mevcut ortam değişkenlerine (`set "%%a=%%b"`) yükler.
  3. `docker-compose -f docker-compose.dev.yml up -d --wait` ile tüm altyapı + worker container'larını başlatıp sağlıklı olmalarını bekler ve `ps` ile durumlarını listeler.
  4. Dosya kilitlenme çakışmalarını önlemek için `dotnet build OtoEdit.slnx -c Debug` çalıştırır.
  5. 3 ayrı konsol penceresi açar:
     - `"OtoEdit-API"`: `cd src\OtoEdit.API && dotnet run --no-build`
     - `"OtoEdit-Worker"`: `docker logs -f otoedit-dev-worker`
     - `"OtoEdit-UI"`: `cd src\OtoEdit.Frontend && npm start`
  6. ~7 saniye bekleyip (`ping 127.0.0.1 -n 7`) varsayılan tarayıcıda `http://localhost:4200` ve `http://localhost:5001/swagger` adreslerini açar.

### 1.5. `durdur.bat`
- **Amacı:** Çalışan geliştirme ortamını temiz şekilde durduran Batch script'idir.
- **Adım Adım İşleyişi:**
  1. `docker-compose -f docker-compose.dev.yml stop` ile Docker servislerini durdurur.
  2. `taskkill` ile `OtoEdit-API*`, `OtoEdit-Worker*`, `OtoEdit-UI*` pencerelerini ve `dotnet.exe`, `node.exe`, `OtoEdit.API.exe` süreçlerini sonlandırır.

### 1.6. `nginx/nginx.conf`
- **Amacı:** Ters vekil (Reverse Proxy) yapılandırmasıdır.
- **Detaylar:**
  - `client_max_body_size 2048M;` (2GB upload limiti) ve `600s` proxy read/connect/send timeout tanımlar.
  - `upstream api_servers { server api:8080; }`
  - `location /api/`: `http://api_servers`'a yönlendirir, HTTP 1.1 ve Upgrade header'larını iletir.
  - `location /pipeline-hub`: SignalR WebSocket bağlantıları için `http://api_servers/pipeline-hub`'a yönlendirir, `86400s` (24 saat) read/send timeout uygular.
  - `location /swagger`: `http://api_servers/swagger`'a yönlendirir.

### 1.7. `.env.example`
- **Amacı:** Veritabanı (`DB_*`), Redis (`REDIS_*`), RabbitMQ (`RABBITMQ_*`), MinIO (`MINIO_*`), `ADMIN_API_KEY`, AI anahtarları (`GEMINI_API_KEY`, `GEMINI_API_KEYS`, `GROQ_API_KEY`, `ANTIGRAVITY_PROXY_*`, `OPENAI_API_KEY`, `PEXELS_API_KEY`), STT motor sırası (`STT_ENGINE_ORDER`) ve JumpCut v2 (`VAD_*`, `JUMPCUT_*`) şablon değişkenlerini tanımlar.

---

## 2. `src/OtoEdit.Data` Katmanı (Veri Erişim Katmanı)

### 2.1. Proje ve Kayıt Dosyaları

#### `src/OtoEdit.Data/OtoEdit.Data.csproj`
- **Amacı:** Veri katmanı proje dosyasıdır (`net10.0`).
- **Paketler:** `Microsoft.EntityFrameworkCore` (10.0.5), `Microsoft.EntityFrameworkCore.Tools` (10.0.5), `Npgsql.EntityFrameworkCore.PostgreSQL` (10.0.1).

#### `src/OtoEdit.Data/ServiceRegistration.cs`
- **Amacı:** Veri katmanı Dependency Injection (DI) kayıtlarını yapar.
- **Sınıf & Metotlar:**
  - `public static class ServiceRegistration`
    - `public static IServiceCollection AddDataLayer(this IServiceCollection services, string connectionString)`:
      1. `AppDbContext`'i `UseNpgsql(connectionString, b => b.MigrationsAssembly("OtoEdit.Data"))` ile kaydeder ve `RelationalEventId.PendingModelChangesWarning` uyarısını bastırır (`Ignore`).
      2. `IRepository<>` -> `GenericRepository<>` (Scoped) kaydeder.
      3. `IProjectRepository` -> `ProjectRepository` (Scoped) kaydeder.
      4. `IVideoRepository` -> `VideoRepository` (Scoped) kaydeder.

#### `src/OtoEdit.Data/Context/AppDbContext.cs`
- **Amacı:** Entity Framework Core ana `DbContext` sınıfıdır.
- **Sınıf & Özellikler (`DbSet<T>`):**
  - `Projects` (`DbSet<Project>`) -> `projects` tablosu
  - `Videos` (`DbSet<Video>`) -> `videos` tablosu
  - `VideoTranscripts` (`DbSet<VideoTranscript>`) -> `video_transcripts` tablosu
  - `EditDecisionLists` (`DbSet<EditDecisionList>`) -> `edit_decision_lists` tablosu
  - `EdlSnapshots` (`DbSet<EdlSnapshot>`) -> `edl_snapshots` tablosu
  - `Templates` (`DbSet<Template>`) -> `templates` tablosu
  - `ChatMessages` (`DbSet<ChatMessage>`) -> `chat_messages` tablosu
  - `RenderJobs` (`DbSet<RenderJob>`) -> `render_jobs` tablosu
  - `EndpointLogs` (`DbSet<EndpointLog>`) -> `endpoint_logs` tablosu
  - `FunctionLogs` (`DbSet<FunctionLog>`) -> `function_logs` tablosu
  - `PipelineLogs` (`DbSet<PipelineLog>`) -> `pipeline_logs` tablosu
  - `ProjectAssets` (`DbSet<ProjectAsset>`) -> `ProjectAssets` tablosu
- **Metotlar:**
  - `protected override void OnModelCreating(ModelBuilder modelBuilder)`: `modelBuilder.ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly())` çağrısıyla derlemedeki tüm `IEntityTypeConfiguration<T>` sınıflarını otomatik uygular.

---

### 2.2. `Enums` Klasörü (`src/OtoEdit.Data/Enums`)

1. **`src/OtoEdit.Data/Enums/LogSeverity.cs`**
   - **Amacı:** Log önem derecesini belirten enum.
   - **Değerler:** `Information = 0`, `Warning = 1`, `Error = 2`, `Critical = 3`.

2. **`src/OtoEdit.Data/Enums/PipelineAsamasi.cs`**
   - **Amacı:** Video analiz ve render pipeline aşamalarını temsil eder. `[JsonConverter(typeof(JsonStringEnumConverter))]` özniteliği sayesinde JSON'da metin olarak serileştirilir.
   - **Değerler:** `SesIyilestirme = 0`, `Stt = 1`, `SessizlikAlgilama = 2`, `KomutAlgilama = 3`, `YuzTakibi = 4`, `Repurposing = 5`, `OneriOlusturma = 6`, `EdlOlusturma = 7`, `Render = 8`, `Tamamlandi = 9`.

3. **`src/OtoEdit.Data/Enums/ProjectDurumu.cs`**
   - **Amacı:** Projenin yaşam döngüsü durumunu belirtir.
   - **Değerler:** `Taslak = 0`, `VideoYuklendi = 1`, `AnalizEdiliyor = 2`, `AnalizTamamlandi = 3`, `RenderEdiliyor = 4`, `Tamamlandi = 5`, `Hata = 99`.

4. **`src/OtoEdit.Data/Enums/RenderDurumu.cs`**
   - **Amacı:** FFmpeg render işinin (`RenderJob`) durumunu belirtir.
   - **Değerler:** `Kuyrukta = 0`, `RenderEdiliyor = 1`, `Tamamlandi = 2`, `Hata = 99`.

5. **`src/OtoEdit.Data/Enums/VideoFormati.cs`**
   - **Amacı:** Hedef video en-boy oranını (aspect ratio) belirtir.
   - **Değerler:** `Yatay_16_9 = 0` (16:9 YouTube/Masaüstü), `Dikey_9_16 = 1` (9:16 Reels/Shorts/TikTok), `Kare_1_1 = 2` (1:1 Post).

6. **`src/OtoEdit.Data/Enums/VideoIslemDurumu.cs`**
   - **Amacı:** Videonun Python Worker analiz pipeline'ındaki alt durumunu belirtir.
   - **Değerler:** `Bekliyor = 0`, `SesIyilestirmeBasladi = 1`, `SttBasladi = 2`, `SttTamamlandi = 3`, `SessizlikAlgilamaBasladi = 4`, `KomutAlgilamaBasladi = 5`, `YuzTakibiBasladi = 6`, `AnalizTamamlandi = 7`, `Hata = 99`.

---

### 2.3. `Entities` Klasörü (`src/OtoEdit.Data/Entities`)

1. **`src/OtoEdit.Data/Entities/Project.cs`**
   - **Amacı:** Video düzenleme projesinin ana varlığıdır.
   - **Alanlar:** `Id` (`Guid`), `Ad` (`string`), `Aciklama` (`string?`), `VideoFormati` (`VideoFormati`, varsayılan `Yatay_16_9`), `TemplateId` (`Guid?`), `GestureCommandsEnabled` (`bool`, varsayılan `true`), `AudioEnhancementEnabled` (`bool`, varsayılan `true`), `Durum` (`ProjectDurumu`, varsayılan `Taslak`), `OlusturmaTarihi` (`DateTime`), `GuncellemeTarihi` (`DateTime?`).
   - **Navigation Properties:** `Video?`, `EditDecisionList?`, `Template?`, `ICollection<ChatMessage> ChatMessages`, `ICollection<RenderJob> RenderJobs`, `ICollection<PipelineLog> PipelineLogs`, `ICollection<ProjectAsset> Assets`.

2. **`src/OtoEdit.Data/Entities/Video.cs`**
   - **Amacı:** Projeye yüklenen ham video varlığıdır (Proje ile 1:1 ilişkilidir).
   - **Alanlar:** `Id` (`Guid`), `ProjectId` (`Guid`), `Baslik` (`string`), `DosyaYolu` (`string` - MinIO key), `TemizSesYolu` (`string?`), `Sure` (`TimeSpan?`), `DosyaBoyutu` (`long`), `IslemDurumu` (`VideoIslemDurumu`, varsayılan `Bekliyor`), `OlusturmaTarihi` (`DateTime`), `IslemTamamlanmaTarihi` (`DateTime?`).
   - **Navigation Properties:** `Project`, `VideoTranscript? Transcript`, `ICollection<PipelineLog> PipelineLogs`.

3. **`src/OtoEdit.Data/Entities/VideoTranscript.cs`**
   - **Amacı:** STT (Whisper/Gemini/Groq) çıktı varlığıdır; ham metni ve kelime bazlı zaman damgalarını (`jsonb`) saklar.
   - **Alanlar:** `Id` (`Guid`), `VideoId` (`Guid`), `HamMetin` (`string`), `ZamanDamgalari` (`string?` - JSONB), `Dil` (`string`, varsayılan `"tr"`), `KelimeSayisi` (`int`), `SttModel` (`string`, varsayılan `"whisper-1"`), `SttSuresiMs` (`int`), `OlusturmaTarihi` (`DateTime`).
   - **Navigation Properties:** `Video`.

4. **`src/OtoEdit.Data/Entities/EditDecisionList.cs`**
   - **Amacı:** Sistemin kalbi olan Edit Decision List (EDL) varlığıdır. Kesim kararları (`cuts`), katmanlar (`overlays`), ayarlar (`settings`) ve öneriler (`suggestions`) `EdlJson` (`jsonb`) sütununda tutulur.
   - **Alanlar:** `Id` (`Guid`), `ProjectId` (`Guid`), `EdlJson` (`string`, varsayılan `"{}"`), `Versiyon` (`int`, varsayılan `1`), `OlusturmaTarihi` (`DateTime`), `GuncellemeTarihi` (`DateTime?`).
   - **Navigation Properties:** `Project`.

5. **`src/OtoEdit.Data/Entities/EdlSnapshot.cs`**
   - **Amacı:** Memento tasarım deseni (Undo/Redo) için her EDL değişikliği öncesinde alınan anlık görüntüleri saklar.
   - **Alanlar:** `Id` (`Guid`), `ProjectId` (`Guid`), `Versiyon` (`int`), `EdlJson` (`string` - JSONB), `Aciklama` (`string?`), `Kaynak` (`string`, varsayılan `"system"` — Undo için `"system"`, Redo için `"system_undo"`), `OlusturmaTarihi` (`DateTime`).
   - **Navigation Properties:** `Project`.

6. **`src/OtoEdit.Data/Entities/ChatMessage.cs`**
   - **Amacı:** AI kurgu asistanı ile yapılan sohbet mesajlarını, üretilen EDL patch'lerini ve Human-in-the-Loop (HitL) onay durumlarını saklar.
   - **Alanlar:** `Id` (`Guid`), `ProjectId` (`Guid`), `Rol` (`string`, `"user"` veya `"assistant"`), `Mesaj` (`string`), `EdlPatch` (`string?` - JSONB; uygulanan patch veya clarification durumunda `formFields` JSON'u), `PendingEdlPatch` (`string?` - JSONB; onay bekleyen patch), `PatchDurumu` (`string`, `"none"`, `"pending"`, `"applied"`, `"rejected"`, `"clarification"`), `OlusturmaTarihi` (`DateTime`).
   - **Navigation Properties:** `Project`.

7. **`src/OtoEdit.Data/Entities/ProjectAsset.cs`**
   - **Amacı:** Projeye yüklenen harici medya dosyalarını (resim, ses, B-roll video, logo) temsil eder.
   - **Alanlar:** `Id` (`Guid`), `ProjectId` (`Guid`), `DosyaAdi` (`string`), `MimeTuru` (`string`), `StorageKey` (`string` - `assets/{projectId}/{assetId}{ext}`), `Url` (`string`), `BoyutByte` (`long`), `YuklemeTarihi` (`DateTime`).
   - **Navigation Properties:** `Project`.

8. **`src/OtoEdit.Data/Entities/RenderJob.cs`**
   - **Amacı:** Nihai video dışa aktarma (FFmpeg render) iş kaydıdır.
   - **Alanlar:** `Id` (`Guid`), `ProjectId` (`Guid`), `EdlSnapshot` (`string` - JSONB), `Durum` (`RenderDurumu`, varsayılan `Kuyrukta`), `CiktiYolu` (`string?` - MinIO yolu), `BaslangicZamani` (`DateTime`), `BitisZamani` (`DateTime?`), `SureMs` (`int?`), `HataMesaji` (`string?`).
   - **Navigation Properties:** `Project`.

9. **`src/OtoEdit.Data/Entities/Template.cs`**
   - **Amacı:** Hazır video kurgu şablonlarını (Yatay, Reels, Kare, logo konumu, altyazı stili) saklar.
   - **Alanlar:** `Id` (`Guid`), `Ad` (`string`), `Tanim` (`string?`), `VideoFormati` (`VideoFormati`), `LogoYolu` (`string?`), `LogoPozisyonu` (`string?` - JSONB), `KonusmaciAdGoster` (`bool`), `AltyaziStili` (`string?`), `AltyaziFont` (`string?`), `AltyaziRenk` (`string?`), `AktifMi` (`bool`, varsayılan `true`), `OlusturmaTarihi` (`DateTime`).
   - **Navigation Properties:** `ICollection<Project> Projects`.

10. **`src/OtoEdit.Data/Entities/EndpointLog.cs`**
    - **Amacı:** HTTP Request/Response loglama varlığıdır (`endpoint_logs` tablosu).
    - **Alanlar:** `Id` (`long`), `TraceId` (`string?`), `Method` (`string`), `Path` (`string`), `Query` (`string?`), `RequestBody` (`string?`), `ResponseBody` (`string?`), `StatusCode` (`int`), `IpAddress` (`string?`), `UserAgent` (`string?`), `DurationMs` (`int`), `CreatedAt` (`DateTime`).

11. **`src/OtoEdit.Data/Entities/FunctionLog.cs`**
    - **Amacı:** Fonksiyon/Metot seviyesinde oluşan istisnaları (`function_logs` tablosu) kaydeder.
    - **Alanlar:** `Id` (`long`), `ErrorCode` (`string`), `ClassName` (`string`), `MethodName` (`string`), `FilePath` (`string?`), `LineNumber` (`int`), `ErrorMessage` (`string?`), `StackTrace` (`string?`), `InputType` (`string?`), `InputValue` (`string?`), `TraceId` (`string?`), `Severity` (`string`, varsayılan `"Error"`), `CreatedAt` (`DateTime`).

12. **`src/OtoEdit.Data/Entities/PipelineLog.cs`**
    - **Amacı:** Python Worker ve Render pipeline aşamalarının başlangıç/bitiş/süre/hata/metadata bilgilerini (`pipeline_logs` tablosu) kaydeder.
    - **Alanlar:** `Id` (`long`), `VideoId` (`Guid?`), `ProjectId` (`Guid?`), `RenderJobId` (`Guid?`), `Asama` (`PipelineAsamasi`), `Durum` (`string`), `BaslangicZamani` (`DateTime`), `BitisZamani` (`DateTime?`), `SureMs` (`int?`), `HataMesaji` (`string?`), `HataDetayi` (`string?`), `GirdiMetadata` (`string?` - JSONB), `CiktiMetadata` (`string?` - JSONB), `TraceId` (`string?`), `CreatedAt` (`DateTime`).
    - **Navigation Properties:** `Video?`, `Project?`.

---

### 2.4. `Configurations` Klasörü (`src/OtoEdit.Data/Configurations`)

1. **`src/OtoEdit.Data/Configurations/ProjectConfiguration.cs`**
   - **Tablo:** `projects` (PK: `id`, `gen_random_uuid()`).
   - **Sütunlar:** `ad` (varchar 200), `aciklama` (varchar 2000), `video_formati`, `template_id`, `gesture_commands_enabled` (default true), `audio_enhancement_enabled` (default true), `durum`, `olusturma_tarihi` (`timestamptz`, default `now()`), `guncelleme_tarihi`.
   - **İndeksler:** `idx_projects_durum`, `idx_projects_olusturma` (DESC).
   - **İlişkiler:** `Template` (1:N, `SetNull`), `Video` (1:1, `Cascade`), `EditDecisionList` (1:1, `Cascade`), `ChatMessages` (1:N, `Cascade`), `RenderJobs` (1:N, `Cascade`).

2. **`src/OtoEdit.Data/Configurations/VideoConfiguration.cs`**
   - **Tablo:** `videos` (PK: `id`).
   - **Sütunlar:** `project_id`, `baslik` (varchar 300), `dosya_yolu` (varchar 500), `temiz_ses_yolu` (varchar 500), `sure` (`interval`), `dosya_boyutu` (`bigint`, default 0), `islem_durumu`, `olusturma_tarihi`, `islem_tamamlanma_tarihi`.
   - **İndeksler:** `idx_videos_project_id` (Unique), `idx_videos_durum`.
   - **İlişkiler:** `Transcript` (`VideoTranscript` ile 1:1, `Cascade`).

3. **`src/OtoEdit.Data/Configurations/VideoTranscriptConfiguration.cs`**
   - **Tablo:** `video_transcripts` (PK: `id`).
   - **Sütunlar:** `video_id`, `ham_metin` (`text`), `zaman_damgalari` (`jsonb`), `dil` (varchar 10, default `"tr"`), `kelime_sayisi` (default 0), `stt_model` (varchar 50), `stt_suresi_ms` (default 0), `olusturma_tarihi`.
   - **İndeksler:** `idx_video_transcripts_video_id` (Unique).

4. **`src/OtoEdit.Data/Configurations/EditDecisionListConfiguration.cs`**
   - **Tablo:** `edit_decision_lists` (PK: `id`).
   - **Sütunlar:** `project_id`, `edl_json` (`jsonb`, default `"{}"`), `versiyon` (default 1), `olusturma_tarihi`, `guncelleme_tarihi`.
   - **İndeksler:** `idx_edl_project_id` (Unique).

5. **`src/OtoEdit.Data/Configurations/EdlSnapshotConfiguration.cs`**
   - **Tablo:** `edl_snapshots` (PK: `id`).
   - **Sütunlar:** `project_id`, `versiyon`, `edl_json` (`jsonb`), `aciklama` (varchar 255), `kaynak` (varchar 50), `olusturma_tarihi`.
   - **İndeksler:** `idx_edl_snapshots_project_id`, `idx_edl_snapshots_project_id_versiyon` (`ProjectId + Versiyon` Unique!).
   - **İlişkiler:** `fk_edl_snapshots_projects` (`Project` ile N:1, `Cascade`).

6. **`src/OtoEdit.Data/Configurations/ChatMessageConfiguration.cs`**
   - **Tablo:** `chat_messages` (PK: `id`).
   - **Sütunlar:** `project_id`, `rol` (varchar 20), `mesaj` (`text`), `edl_patch` (`jsonb`), `pending_edl_patch` (`jsonb`), `patch_durumu` (varchar 20, default `"none"`), `olusturma_tarihi`.
   - **İndeksler:** `idx_chat_messages_project_id`, `idx_chat_messages_olusturma`.

7. **`src/OtoEdit.Data/Configurations/RenderJobConfiguration.cs`**
   - **Tablo:** `render_jobs` (PK: `id`).
   - **Sütunlar:** `project_id`, `edl_snapshot` (`jsonb`), `durum` (default `Kuyrukta`), `cikti_yolu` (varchar 500), `baslangic_zamani`, `bitis_zamani`, `sure_ms`, `hata_mesaji` (`text`).
   - **İndeksler:** `idx_render_jobs_project_id`, `idx_render_jobs_durum`.

8. **`src/OtoEdit.Data/Configurations/TemplateConfiguration.cs`**
   - **Tablo:** `templates` (PK: `id`).
   - **Sütunlar:** `ad` (varchar 200), `tanim` (varchar 1000), `video_formati`, `logo_yolu` (varchar 500), `logo_pozisyonu` (`jsonb`), `konusmaci_ad_goster` (default false), `altyazi_stili` (varchar 50), `altyazi_font` (varchar 100), `altyazi_renk` (varchar 20), `aktif_mi` (default true), `olusturma_tarihi`.

9. **`src/OtoEdit.Data/Configurations/EndpointLogConfiguration.cs`**
   - **Tablo:** `endpoint_logs` (PK: `id`, `UseIdentityAlwaysColumn()`).
   - **Sütunlar:** `trace_id`, `method`, `path`, `query`, `request_body`, `response_body`, `status_code`, `ip_address`, `user_agent`, `duration_ms`, `created_at`.
   - **İndeksler:** `idx_endpoint_logs_created_at` (DESC), `idx_endpoint_logs_status_code`, `idx_endpoint_logs_path`.

10. **`src/OtoEdit.Data/Configurations/FunctionLogConfiguration.cs`**
    - **Tablo:** `function_logs` (PK: `id`, `UseIdentityAlwaysColumn()`).
    - **Sütunlar:** `error_code`, `class_name`, `method_name`, `file_path`, `line_number`, `error_message`, `stack_trace`, `input_type`, `input_value`, `trace_id`, `severity` (default `"Error"`), `created_at`.
    - **İndeksler:** `idx_function_logs_created_at` (DESC), `idx_function_logs_error_code`, `idx_function_logs_severity`.

11. **`src/OtoEdit.Data/Configurations/PipelineLogConfiguration.cs`**
    - **Tablo:** `pipeline_logs` (PK: `id`, `UseIdentityAlwaysColumn()`).
    - **Sütunlar:** `video_id`, `project_id`, `render_job_id`, `asama`, `durum`, `baslangic_zamani`, `bitis_zamani`, `sure_ms`, `hata_mesaji`, `hata_detayi`, `girdi_metadata` (`jsonb`), `cikti_metadata` (`jsonb`), `trace_id`, `created_at`.
    - **İndeksler:** `idx_pipeline_logs_video_id`, `idx_pipeline_logs_project_id`, `idx_pipeline_logs_asama`, `idx_pipeline_logs_created_at` (DESC).
    - **İlişkiler:** `Video` (`Cascade`), `Project` (`Cascade`).
    - **Not:** `ProjectAsset` için ayrı bir `Configuration` sınıfı yazılmamıştır; bu nedenle EF Core varsayılan konvansiyonlarıyla `"ProjectAssets"` (PascalCase) tablosu olarak oluşturulmuştur.

---

### 2.5. `Repositories` Klasörü (`src/OtoEdit.Data/Repositories`)

1. **`src/OtoEdit.Data/Repositories/IRepository.cs`**
   - **Amacı:** Temel Generic Repository arayüzüdür (`where T : class`).
   - **Metotlar:**
     - `Task<T?> GetByIdAsync(Guid id)`
     - `Task<IEnumerable<T>> GetAllAsync(bool asNoTracking = true)`
     - `Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate, bool asNoTracking = true)`
     - `IQueryable<T> Query(bool asNoTracking = true)`
     - `Task<T> AddAsync(T entity)`
     - `void Update(T entity)`
     - `void Delete(T entity)`
     - `Task<int> SaveChangesAsync()`

2. **`src/OtoEdit.Data/Repositories/GenericRepository.cs`**
   - **Amacı:** `IRepository<T>` arayüzünün EF Core `AppDbContext` ve `DbSet<T>` tabanlı implementasyonudur.

3. **`src/OtoEdit.Data/Repositories/IProjectRepository.cs`**
   - **Amacı:** `Project` varlığına özel repository arayüzüdür (`IRepository<Project>`'ten türetilmiştir).
   - **Metotlar:**
     - `Task<Project?> GetProjectWithDetailsAsync(Guid id, bool asNoTracking = true)`
     - `Task<(IEnumerable<Project> Items, int TotalCount)> GetProjectsPagedAsync(int pageNumber, int pageSize, bool asNoTracking = true)`
     - `Task<bool> UpdateStatusAsync(Guid id, ProjectDurumu durum)`

4. **`src/OtoEdit.Data/Repositories/ProjectRepository.cs`**
   - **Amacı:** `IProjectRepository` implementasyonudur.
   - **Metotlar:**
     - `GetProjectWithDetailsAsync(Guid id, bool asNoTracking = true)`: `projects` tablosunu `Video` -> `Transcript`, `Template`, `EditDecisionList` ve `RenderJobs` ilişkileriyle (`Include`/`ThenInclude`) birlikte sorgular ve `FirstOrDefaultAsync` döner.
     - `GetProjectsPagedAsync(int pageNumber, int pageSize, bool asNoTracking = true)`: `Video` ve `Template` dahil edilerek `OlusturmaTarihi` azalan sırada (`OrderByDescending`) sayfalama (`Skip`/`Take`) yapar ve `(Items, TotalCount)` döner.
     - `UpdateStatusAsync(Guid id, ProjectDurumu durum)`: Projeyi `FindAsync` ile bulur, `Durum` ve `GuncellemeTarihi = DateTime.UtcNow` alanlarını güncelleyip `SaveChangesAsync()` çağırır.

5. **`src/OtoEdit.Data/Repositories/IVideoRepository.cs`**
   - **Amacı:** `Video` varlığına özel repository arayüzüdür (`IRepository<Video>`).
   - **Metotlar:**
     - `Task<Video?> GetByProjectIdAsync(Guid projectId, bool asNoTracking = true)`
     - `Task<bool> UpdateStatusAsync(Guid videoId, VideoIslemDurumu status)`

6. **`src/OtoEdit.Data/Repositories/VideoRepository.cs`**
   - **Amacı:** `IVideoRepository` implementasyonudur.
   - **Metotlar:**
     - `GetByProjectIdAsync(Guid projectId, bool asNoTracking = true)`: `videos` tablosunu `Transcript` (`Include`) ile birlikte `ProjectId`'ye göre sorgular.
     - `UpdateStatusAsync(Guid videoId, VideoIslemDurumu status)`: Videonun `IslemDurumu` alanını günceller; eğer durum `AnalizTamamlandi` ise `IslemTamamlanmaTarihi = DateTime.UtcNow` atar ve kaydeder.

---

### 2.6. `Migrations` Klasörü (`src/OtoEdit.Data/Migrations`)

1. **`20260918073553_InitialCreate.cs` & `.Designer.cs`**: İlk 10 tabloyu (`endpoint_logs`, `function_logs`, `templates`, `projects`, `chat_messages`, `edit_decision_lists`, `render_jobs`, `videos`, `pipeline_logs`, `video_transcripts`) ve indekslerini oluşturur.
2. **`20260921081001_AddEdlSnapshots.cs` & `.Designer.cs`**: `chat_messages` tablosuna `patch_durumu` ve `pending_edl_patch` sütunlarını ekler; `edl_snapshots` tablosunu ve `(project_id, versiyon)` unique indeksini oluşturur.
3. **`20260923125746_AddProjectAssets.cs` & `.Designer.cs`**: `ProjectAssets` tablosunu oluşturur.
4. **`AppDbContextModelSnapshot.cs`**: EF Core güncel veritabanı model anlık görüntüsüdür.

---

## 3. `src/OtoEdit.Business` Katmanı (İş Mantığı ve Altyapı Servisleri)

### 3.1. Proje ve DI Yapılandırması

#### `src/OtoEdit.Business/OtoEdit.Business.csproj`
- **Amacı:** İş katmanı proje dosyasıdır (`net10.0`). `Microsoft.AspNetCore.App` framework referansı ve `OtoEdit.Data` proje referansı içerir.
- **Paketler:** `FluentValidation` (12.1.1), `StackExchange.Redis` (3.1.31), `MassTransit` & `MassTransit.RabbitMQ` (8.3.6), `Microsoft.Extensions.Http.Resilience` (10.10.0), `Minio` (7.0.0), `AWSSDK.S3` (3.7.416.1), `Mscc.GenerativeAI` (3.1.0).

#### `src/OtoEdit.Business/DependencyInjection.cs`
- **Amacı:** İş katmanındaki tüm servislerin, doğrulayıcıların, MinIO, Redis, Gemini ve MassTransit/RabbitMQ bileşenlerinin DI kaydını yapar.
- **Metot:** `public static IServiceCollection AddBusinessLayer(this IServiceCollection services, IConfiguration configuration, Action<IBusRegistrationConfigurator>? configureMassTransit = null)`
  1. **FluentValidation:** `services.AddValidatorsFromAssembly(Assembly.GetExecutingAssembly())`
  2. **MinIO S3:** `Minio:Endpoint`, `Minio:AccessKey`, `Minio:SecretKey`, `Minio:UseSSL` ayarlarıyla `AddMinio` kaydeder ve `IFileStorageService` -> `MinioFileStorageService` (Scoped) bağlar.
  3. **Redis:** `Redis:ConnectionString` (`AbortOnConnectFail = false`) ile `IConnectionMultiplexer` (Singleton) ve `ICacheService` -> `RedisCacheService` (Singleton) kaydeder.
  4. **AI Chat Provider:** `IChatProvider` -> `GeminiChatProvider` (Scoped) kaydeder.
  5. **Business Services (Scoped):**
     - `ILogService` -> `LogManager`
     - `IPipelineNotificationService` -> `PipelineNotificationManager`
     - `IProjectService` -> `ProjectManager`
     - `IVideoService` -> `VideoManager`
     - `IEdlService` -> `EdlManager`
     - `IChatService` -> `ChatManager`
     - `IRenderService` -> `RenderManager`
     - `IAssetService` -> `AssetManager`
     - `ITemplateService` -> `TemplateManager`
     - `IPexelsService` -> `PexelsService` (`AddHttpClient` + `AddStandardResilienceHandler()`)
  6. **MassTransit (RabbitMQ):**
     - `configureMassTransit?.Invoke(x)` ile API katmanındaki Consumer'ları alır.
     - RabbitMQ bağlantısını kurar (`RabbitMQ:Host`, `Port`, `Username`, `Password`).
     - Python Worker ile saf JSON uyumluluğu için `cfg.UseRawJsonSerializer()` ve `cfg.UseRawJsonDeserializer()` kullanır (MassTransit zarfını/envelope'unu devre dışı bırakır).
     - `cfg.UseMessageRetry(r => r.Exponential(3, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(2)))` ile 3 kez üstel yeniden deneme uygular.

---

### 3.2. `DTOs` Klasörü (`src/OtoEdit.Business/DTOs`)

1. **`src/OtoEdit.Business/DTOs/Asset/AssetDtos.cs`**
   - `public record ProjectAssetDto`: `Id`, `ProjectId`, `DosyaAdi`, `MimeTuru`, `Url`, `BoyutByte`, `YuklemeTarihi`.

2. **`src/OtoEdit.Business/DTOs/Chat/ChatDtos.cs`**
   - `public record ChatMessageDto`: `Mesaj` (`string`).
   - `public record ChatMessageHistoryDto`: `Id`, `ProjectId`, `Rol`, `Mesaj`, `PatchDurumu`, `OlusturulmaZamani`, `PendingEdlPatch` (`JsonElement?`), `FormFields` (`JsonElement?`).
   - `public record ChatResponseDto`: `Id`, `Rol`, `Mesaj`, `Intent`, `EdlPatch` (`JsonElement?`), `PendingEdlPatch` (`JsonElement?`), `FormFields` (`JsonElement?`), `PatchDurumu`, `EdlVersiyonYeni` (`int?`).
   - `public record ChatHistoryItem`: `Role`, `Message`.
   - `public class ChatResult`: LLM JSON yanıt modeli (`intent`, `mesaj`, `edlPatch`, `formFields`).

3. **`src/OtoEdit.Business/DTOs/Edl/EdlDtos.cs`**
   - `public record EdlDto`: `ProjectId`, `Versiyon`, `Edl` (`JsonElement`), `GuncellemeTarihi`.
   - `public record EdlPatchDto`: `Patch` (`JsonElement`).
   - `public record EdlPatchResponseDto`: `ProjectId`, `Versiyon`, `Mesaj`.

4. **`src/OtoEdit.Business/DTOs/Pipeline/PipelineStatusDto.cs`**
   - `public record PipelineStatusDto`: `VideoId`, `ProjectId`, `Asama` (`PipelineAsamasi`), `Durum`, `Yuzde`, `Mesaj`, `GuncellemeZamani`.

5. **`src/OtoEdit.Business/DTOs/Project/ProjectCreateDto.cs`**
   - `public record ProjectCreateDto`: `Ad`, `Aciklama`, `VideoFormati` (varsayılan `Dikey_9_16`), `TemplateId`, `GestureCommandsEnabled` (`true`), `AudioEnhancementEnabled` (`true`).

6. **`src/OtoEdit.Business/DTOs/Project/ProjectDetailDto.cs`**
   - `public record ProjectDetailDto`: `Id`, `Ad`, `Aciklama`, `VideoFormati`, `TemplateId`, `TemplateAd`, `GestureCommandsEnabled`, `AudioEnhancementEnabled`, `Durum`, `OlusturmaTarihi`, `GuncellemeTarihi`, `Video` (`VideoDetailDto?`), `EdlVersiyon` (`int?`), `ChatMesajSayisi` (`int`), `SonRender` (`RenderStatusDto?`).

7. **`src/OtoEdit.Business/DTOs/Project/ProjectListDto.cs`**
   - `public record ProjectListDto`: `Id`, `Ad`, `VideoFormati`, `Durum`, `OlusturmaTarihi`, `VideoSayisi`, `TemplateAd`.

8. **`src/OtoEdit.Business/DTOs/Project/ProjectUpdateDto.cs`**
   - `public record ProjectUpdateDto`: `Ad`, `Aciklama`, `VideoFormati`, `TemplateId`, `GestureCommandsEnabled`, `AudioEnhancementEnabled`.

9. **`src/OtoEdit.Business/DTOs/Render/RenderStatusDto.cs`**
   - `public record RenderRequestDto`: `CustomOutputName` (`string?`).
   - `public record RenderStatusDto`: `RenderJobId`, `ProjectId`, `Durum` (`RenderDurumu`), `CiktiYolu`, `IndirmeUrl`, `SureMs`, `BaslangicZamani`, `BitisZamani`, `HataMesaji`.

10. **`src/OtoEdit.Business/DTOs/Template/TemplateDto.cs`**
    - `public record TemplateDto`: `Id`, `Ad`, `Tanim`, `VideoFormati`, `LogoYolu`, `LogoPozisyonu`, `KonusmaciAdGoster`, `AltyaziStili`, `AltyaziFont`, `AltyaziRenk`, `AktifMi`.

11. **`src/OtoEdit.Business/DTOs/Video/VideoDetailDto.cs`**
    - `public record VideoDetailDto`: `Id`, `ProjectId`, `Baslik`, `DosyaYolu`, `TemizSesYolu`, `Sure`, `DosyaBoyutu`, `IslemDurumu`, `TranskriptVar` (`bool`), `OlusturmaTarihi`, `IslemTamamlanmaTarihi`.

12. **`src/OtoEdit.Business/DTOs/Video/VideoListDto.cs`**
    - `public record VideoListDto`: `Id`, `ProjectId`, `Baslik`, `DosyaBoyutu`, `IslemDurumu`, `OlusturmaTarihi`.

13. **`src/OtoEdit.Business/DTOs/Video/VideoUploadDto.cs`**
    - `public class VideoUploadDto`: `File` (`IFormFile`), `AutoJumpcut` (`bool = true`), `AutoRetake` (`bool = true`), `AutoBroll` (`bool = true`), `AutoSubtitles` (`bool = false`).

---

### 3.3. `Events` Klasörü (`src/OtoEdit.Business/Events`) — RabbitMQ Mesaj Sözleşmeleri

1. **`src/OtoEdit.Business/Events/VideoUploadedEvent.cs`**
   - **Yön:** .NET API -> Python Worker (RabbitMQ `OtoEdit.Business.Events:VideoUploadedEvent` exchange/kuyruğu).
   - **Alanlar:** `VideoId`, `ProjectId`, `DosyaYolu`, `VideoFormati` (`int`), `GestureCommandsEnabled`, `AudioEnhancementEnabled`, `AutoJumpcutEnabled`, `AutoRetakeEnabled`, `AutoBrollEnabled`, `AutoSubtitlesEnabled`.

2. **`src/OtoEdit.Business/Events/PipelineStageChangedEvent.cs`**
   - **Yön:** Python Worker -> .NET API (`PipelineStageChangedConsumer`).
   - **Alanlar:** `ProjectId`, `VideoId`, `Asama` (`PipelineAsamasi`), `Yuzde` (`int`), `Mesaj` (`string?`).

3. **`src/OtoEdit.Business/Events/AnalysisCompletedEvent.cs`**
   - **Yön:** Python Worker -> .NET API (`AnalysisNotificationConsumer`).
   - **Alanlar:** `ProjectId`, `VideoId`, `EdlJson` (`JsonDocument`).

4. **`src/OtoEdit.Business/Events/RenderRequestedEvent.cs`**
   - **Yön:** .NET API -> Python Worker.
   - **Alanlar:** `RenderJobId`, `ProjectId`, `EdlJson` (`JsonDocument`).

5. **`src/OtoEdit.Business/Events/RenderCompletedEvent.cs`**
   - **Yön:** Python Worker -> .NET API (`RenderNotificationConsumer`).
   - **Alanlar:** `RenderJobId`, `ProjectId`, `IndirmeUrl` (`string`).

6. **`src/OtoEdit.Business/Events/PipelineErrorEvent.cs`**
   - **Yön:** Python Worker -> .NET API (`PipelineErrorConsumer`).
   - **Alanlar:** `ProjectId`, `VideoId` (`Guid?`), `Asama` (`string`), `HataMesaji` (`string`).

---

### 3.4. `Exceptions`, `Helpers` ve `Validators` Klasörleri

1. **`src/OtoEdit.Business/Exceptions/BusinessException.cs`**
   - İş kuralı ihlallerinde fırlatılan (HTTP 400 Bad Request'e dönüşen) temel istisna sınıfı (`ErrorCode` özelliği içerir).

2. **`src/OtoEdit.Business/Exceptions/NotFoundException.cs`**
   - `BusinessException`'dan türetilen, varlık bulunamadığında HTTP 404 Not Found döndüren istisna sınıfı (`EntityName`, `Key`, `ErrorCode = "NOT_FOUND"`).

3. **`src/OtoEdit.Business/Exceptions/PipelineException.cs`**
   - `BusinessException`'dan türetilen pipeline hatası istisnası (`Asama`, `VideoId`, `ErrorCode = "PIPELINE_ERROR"`).

4. **`src/OtoEdit.Business/Helpers/HashHelper.cs`**
   - `ComputeSha256Hash(string rawData)`: Verilen metnin UTF-8 baytları üzerinden 64 karakterlik küçük harf hexadecimal SHA-256 özetini döner.

5. **`src/OtoEdit.Business/Helpers/SensitiveDataMasker.cs`**
   - `Mask(string? input)` ve `MaskJson(string? input)`: Derlenmiş (`RegexOptions.Compiled`) düzenli ifadelerle JSON içindeki `password|token|apiKey|api_key|secret|authorization|access_token` değerlerini `"***"`, Header'daki `X-API-Key|Bearer` değerlerini `***` ve e-posta adreslerini `***@***.***` ile maskeler.

6. **`src/OtoEdit.Business/Validators/ProjectValidators.cs`**
   - `ProjectCreateValidator` & `ProjectUpdateValidator`: `Ad` boş olamaz ve maksimum 200 karakter; `Aciklama` maksimum 2000 karakter kuralını uygular.

7. **`src/OtoEdit.Business/Validators/OtherValidators.cs`**
   - `VideoUploadValidator`: `File` boş olamaz, maksimum 50GB (`53687091200L` byte) olabilir ve uzantısı `.mp4, .mkv, .avi, .mov, .webm` olmalıdır.
   - `ChatMessageValidator`: `Mesaj` boş olamaz ve maksimum 4000 karakter olabilir.

---

### 3.5. `Interfaces` Klasörü (`src/OtoEdit.Business/Interfaces`)

- `IAssetService.cs`: `UploadAssetAsync`, `GetProjectAssetsAsync`, `DeleteAssetAsync`, `GetAssetStreamAsync`, `GetAssetUrlAsync`.
- `ICacheService.cs`: `GetAsync<T>`, `SetAsync<T>`, `RemoveAsync`, `RemoveByPrefixAsync`.
- `IChatService.cs`: `IChatService` (`SendMessageAsync`, `GetHistoryAsync`, `ApplyPendingPatchAsync`, `SubmitFormAsync`) ve `IChatProvider` (`ProcessCommandAsync`).
- `IEdlService.cs`: `GetEdlAsync`, `PatchEdlAsync`, `UndoAsync`, `RedoAsync`, `CreateOrUpdateAsync`.
- `IFileStorageService.cs`: `UploadFileAsync`, `DownloadFileAsync`, `GetPresignedUrlAsync`, `DeleteFileAsync`, `DeleteDirectoryAsync`.
- `ILogService.cs`: `LogEndpointAsync`, `LogPipelineStartAsync`, `LogPipelineEndAsync`, `LogPipelineErrorAsync`, `LogFunctionErrorAsync`.
- `IPexelsService.cs`: `SearchPhotoUrlAsync`, `SearchAndSaveAssetAsync`.
- `IPipelineNotificationService.cs`: `NotifyAnalysisProgressAsync`, `NotifyAnalysisCompletedAsync`, `NotifyRenderProgressAsync`, `NotifyRenderCompletedAsync`, `NotifyPipelineErrorAsync`.
- `IProjectService.cs`: `GetAllAsync`, `GetByIdAsync`, `CreateAsync`, `UpdateAsync`, `DeleteAsync`, `UpdateStatusAsync`.
- `IRenderService.cs`: `RequestRenderAsync`, `GetRenderStatusAsync`, `GetDownloadUrlAsync`, `CompleteRenderAsync`, `FailRenderAsync`.
- `ITemplateService.cs`: `GetAllAsync`, `GetByIdAsync`.
- `IVideoService.cs`: `UploadVideoAsync`, `GetVideoByProjectIdAsync`, `DeleteVideoAsync`, `GetVideoStreamAsync`, `GetVideoUrlAsync`.

---

### 3.6. `Infrastructure` Klasörü (`src/OtoEdit.Business/Infrastructure`)

#### 1. `src/OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs`
- **Amacı:** Yapay zeka destekli video kurgu asistanı motorudur (`IChatProvider`).
- **Metotlar:**
  - `ProcessCommandAsync(string userMessage, string currentEdlJson, string? transcriptText, List<ChatHistoryItem> history, CancellationToken cancellationToken = default) -> Task<ChatResult>`:
    1. Ayrıntılı bir Türkçe `systemPrompt` hazırlar: 4 farklı `intent` (`information`, `suggestion`, `command`, `clarification`) kurallarını, `clarification` durumunda dönecek interaktif `formFields` şemasını (`text`, `position`, `color`, `select` font ve animasyon presetleri) ve transkript dışına çıkmama kuralını tanımlar.
    2. `userPrompt` içine `=== VİDEO TRANSKRİPTİ ===`, `=== GEÇMİŞ SOHBET ===`, `=== MEVCUT EDL ===` ve kullanıcı mesajını yerleştirir.
    3. **4 Kademeli LLM Fallback Zinciri:**
       - **Adım 1 (Antigravity Proxy):** `_proxyUrl` (`http://localhost:8045/v1`) ve `_proxyKey` varsa `CallOpenAiCompatibleAsync` ile `_proxyModel` (`gemini-3.8-flash-tiered`) üzerinden 8 saniye timeout ile çağırır.
       - **Adım 2 (Groq API):** İlk adım başarısızsa ve `_groqApiKey` (`gsk_...`) varsa `https://api.groq.com/openai/v1` adresine `_groqModel` (`openai/gpt-oss-120b`) ile 15 saniye timeout ile istek atar.
       - **Adım 3 (Resmi Google Gemini API):** İlk iki adım başarısızsa ve 39 karakterli `AIza...` anahtarı varsa `Mscc.GenerativeAI.GoogleAI` ile `gemini-2.0-flash` modelini 2 denemeli (503/timeout retry) olarak çağırır.
       - **Adım 4 (JSON Parse & Local Heuristics Fallback):** Gelen yanıttaki markdown ````json` bloklarını temizleyip ilk `{` ile son `}` arasını `ChatResult`'a deserialize eder. Eğer tüm API'ler başarısız olursa veya JSON ayrıştırılamazsa `ParseWithLocalHeuristics` metoduna düşer.
  - `CallOpenAiCompatibleAsync(...) -> Task<string?>`: OpenAI `/chat/completions` formatında `response_format = { type = "json_object" }` ile POST isteği yapar ve `choices[0].message.content` döner.
  - `ParseWithLocalHeuristics(string userMessage, string currentEdlJson, string transcriptText) -> ChatResult`:
    1. Kullanıcı mesajında `[Seçili Aralık: X.Xs - Y.Ys] ...` deseni varsa regex ile başlangıç/bitiş saniyelerini ve yazı metnini ayıklar (`yazılacak buraya`, `ekle`, `koy` eklerini temizler) ve doğrudan `overlays` dizisine `"action": "add"` içeren bir `command` patch'i üretir.
    2. Transkript mevcutsa, kullanıcı sorusundaki Türkçe stop-word'leri filtreleyip kalan kelimelerin ilk 4 harfiyle (Türkçe kök eşleşmesi) transkript satırlarında arama yapar ve eşleşen en fazla 4 satırı zaman damgalarıyla birlikte `information` olarak döner.
    3. Hiçbiri eşleşmezse genel yönlendirici `information` yanıtı döner.

#### 2. `src/OtoEdit.Business/Infrastructure/AI/PexelsService.cs`
- **Amacı:** Pexels API üzerinden stok görsel arayan ve MinIO'ya proje varlığı (asset) olarak kaydeden servistir (`IPexelsService`).
- **Metotlar:**
  - `SearchPhotoUrlAsync(string query, string orientation = "landscape", CancellationToken cancellationToken = default) -> Task<string?>`: `https://api.pexels.com/v1/search?query=...&per_page=1&orientation=...` adresine `Authorization: {_apiKey}` başlığıyla GET isteği atar; `photos[0].src.large` (veya `original`) URL'sini döner.
  - `SearchAndSaveAssetAsync(Guid projectId, string query, string orientation = "landscape", CancellationToken cancellationToken = default) -> Task<string?>`: `SearchPhotoUrlAsync` ile bulduğu görseli indirir ve `IFileStorageService.UploadFileAsync` ile MinIO'ya `assets/{projectId}/{assetId}.jpg` anahtarıyla yükler.

#### 3. `src/OtoEdit.Business/Infrastructure/Cache/RedisCacheService.cs`
- **Amacı:** `StackExchange.Redis` (`IConnectionMultiplexer`) kullanan önbellek servisidir (`ICacheService`). Tüm metotlar `try/catch` ile korunmuştur (Redis hatası ana akışı durdurmaz, `LogWarning` basar).
- **Metotlar:**
  - `GetAsync<T>(string key, ...)`: `db.StringGetAsync(key)` ile okur ve `JsonSerializer.Deserialize<T>` yapar.
  - `SetAsync<T>(string key, T value, TimeSpan? expiry = null, ...)`: `JsonSerializer.Serialize` edip `db.StringSetAsync` ile yazar.
  - `RemoveAsync(string key, ...)`: `db.KeyDeleteAsync(key)` çağırır.
  - `RemoveByPrefixAsync(string prefix, ...)`: Tüm Redis endpoint'lerinde `server.Keys(pattern: $"{prefix}*")` ile eşleşen anahtarları bulup topluca siler.

#### 4. `src/OtoEdit.Business/Infrastructure/Storage/MinioFileStorageService.cs`
- **Amacı:** MinIO S3 nesne depolama servisidir (`IFileStorageService`). Varsayılan bucket adı `"otoedit"`'tir.
- **Metotlar:**
  - `EnsureBucketExistsAsync`: Bucket yoksa `MakeBucketAsync` ile oluşturur.
  - `UploadFileAsync(string objectKey, Stream content, string contentType, ...)`: `PutObjectArgs` ile akışı MinIO'ya yükler.
  - `DownloadFileAsync(string objectKey, ...)`: `GetObjectArgs` ile nesneyi `MemoryStream`'e kopyalar, pozisyonu `0`'a alır ve döner.
  - `GetPresignedUrlAsync(string objectKey, TimeSpan expiry, ...)`: `PresignedGetObjectArgs` ile geçici imzalı URL üretir.
  - `DeleteFileAsync(string objectKey, ...)`: `RemoveObjectArgs` ile nesneyi siler.
  - `DeleteDirectoryAsync(string prefix, ...)`: `ListObjectsEnumAsync` (`Recursive = true`) ile verilen prefix altındaki tüm nesneleri listeler ve tek tek `DeleteFileAsync` ile siler.

#### 5. `src/OtoEdit.Business/Infrastructure/Storage/LocalFileStorageService.cs`
- **Amacı:** Yerel disk (`{ContentRootPath}/App_Data/Storage`) üzerinde çalışan yedek/test `IFileStorageService` implementasyonudur.

---

### 3.7. `Services` Klasörü (`src/OtoEdit.Business/Services`)

#### 1. `src/OtoEdit.Business/Services/ProjectManager.cs` (`IProjectService`)
- **Etkileşimler:** PostgreSQL (`projects`, `videos`, `video_transcripts`, `templates`, `edit_decision_lists`, `render_jobs`), Redis (`project:{id}`), MinIO (`videos/{id}/`, `audio/{id}/`, `renders/{id}/`).
- **Metotlar:**
  - `GetAllAsync`: `IProjectRepository.GetProjectsPagedAsync(1, 100)` çağırır ve `ProjectListDto` listesi döner.
  - `GetByIdAsync(Guid id)`: Önce Redis'te `project:{id}` anahtarına bakar. Yoksa `GetProjectWithDetailsAsync` ile DB'den çeker, en son `RenderJob` kaydını (`OrderByDescending(r => r.BaslangicZamani)`) bulur, `ProjectDetailDto` oluşturup Redis'e **5 dakika** (`TimeSpan.FromMinutes(5)`) TTL ile yazar ve döner.
  - `CreateAsync(ProjectCreateDto dto)`: `_createValidator` ile doğrular, `ProjectDurumu.Taslak` durumunda yeni `Project` kaydeder ve `GetByIdAsync` döner.
  - `UpdateAsync(Guid id, ProjectUpdateDto dto)`: `_updateValidator` ile doğrular, projeyi günceller, Redis `project:{id}` önbelleğini siler ve `GetByIdAsync` döner.
  - `DeleteAsync(Guid id)`:
    1. MinIO'daki `videos/{id}/`, `audio/{id}/`, `renders/{id}/` dizinlerini `DeleteDirectoryAsync` ile temizler.
    2. Projeyi DB'den siler (veritabanı Cascade kurallarıyla bağlı kayıtlar da silinir).
    3. Redis `project:{id}` anahtarını siler.
  - `UpdateStatusAsync(Guid id, ProjectDurumu durum)`: Proje durumunu günceller ve Redis `project:{id}` önbelleğini temizler.

#### 2. `src/OtoEdit.Business/Services/VideoManager.cs` (`IVideoService`)
- **Etkileşimler:** PostgreSQL (`videos`, `projects`), MinIO (`videos/{projectId}/{videoId}{ext}`), RabbitMQ (`VideoUploadedEvent`).
- **Metotlar:**
  - `UploadVideoAsync(Guid projectId, IFormFile file, bool autoJumpcut = true, bool autoRetake = true, bool autoBroll = true, bool autoSubtitles = false, ...)`:
    1. Projeyi kontrol eder (`NotFoundException`).
    2. Dosya boş mu, 50GB'dan büyük mü ve uzantısı `.mp4, .mkv, .avi, .mov, .webm` içinde mi kontrol eder (`BusinessException`).
    3. MinIO'ya `videos/{projectId}/{videoId}{ext}` anahtarıyla stream olarak yükler.
    4. `videos` tablosuna `VideoIslemDurumu.Bekliyor` olarak kaydeder.
    5. Proje durumunu `ProjectDurumu.AnalizEdiliyor` olarak günceller.
    6. RabbitMQ'ya `VideoUploadedEvent` mesajını (`AutoJumpcutEnabled`, `AutoRetakeEnabled`, `AutoBrollEnabled`, `AutoSubtitlesEnabled`, `GestureCommandsEnabled`, `AudioEnhancementEnabled`, `VideoFormati`) publish eder.
  - `GetVideoByProjectIdAsync(Guid projectId)`: Projeye bağlı videoyu ve transkript varlığını (`TranskriptVar`) `VideoDetailDto` olarak döner.
  - `DeleteVideoAsync(Guid projectId)`: MinIO'dan hem ham videoyu (`DosyaYolu`) hem de varsa temiz sesi (`TemizSesYolu`) siler, ardından DB'den `Video` kaydını siler.
  - `GetVideoStreamAsync(Guid videoId)`: MinIO'dan 12 saatlik presigned URL alıp `HttpClient` (`ResponseHeadersRead`) ile stream açarak döner.
  - `GetVideoUrlAsync(Guid videoId)`: MinIO'dan 12 saatlik presigned URL alır; tarayıcının erişebilmesi için URL içindeki `://minio:` ifadesini `://localhost:` olarak değiştirir.

#### 3. `src/OtoEdit.Business/Services/EdlManager.cs` (`IEdlService`)
- **Etkileşimler:** PostgreSQL (`edit_decision_lists`, `edl_snapshots`, `video_transcripts`), Redis (`edl:{projectId}`).
- **Metotlar:**
  - `GetEdlAsync(Guid projectId)`:
    1. Redis'te `edl:{projectId}` varsa döner.
    2. DB'den `EditDecisionList` kaydını okur.
    3. **Otomatik Transkript Besleme:** Eğer `EdlJson` içinde `transcript.segments` dizisi yoksa veya boşsa, `video_transcripts` tablosundan (`ZamanDamgalari`) transkript JSON'unu okuyup `rootNode["transcript"]` içine enjekte eder.
    4. Sonucu Redis'e **2 dakika** (`TimeSpan.FromMinutes(2)`) TTL ile kaydeder ve `EdlDto` döner.
  - `PatchEdlAsync(Guid projectId, JsonElement patch)`:
    1. **Memento Pattern:** Değişiklik öncesi `SaveSnapshotAsync(projectId, edl, "EDL Patch Öncesi", "system")` çağırarak mevcut durumu `edl_snapshots` tablosuna kaydeder.
    2. Gelen `patch` içindeki alanları mevcut `EdlJson` üzerinde akıllıca birleştirir:
       - `cuts`, `overlays`, `suggestions` dizilerinde büyük/küçük harf duyarsız (`StringComparison.OrdinalIgnoreCase`) eşleşme yapar.
       - Elemanın `id` alanı varsa ve `"action": "remove"` ise diziden siler.
       - `"action"` `"remove"` değilse ve aynı `id` mevcutsa, mevcut nesnenin özelliklerini (`action` hariç) yeni değerlerle günceller (kısmi güncelleme / merge).
       - Aynı `id` yoksa veya `id` belirtilmemişse diziye yeni eleman olarak ekler.
       - `settings` nesnesini alt özellik bazında merge eder; diğer üst seviye alanları doğrudan yazar.
    3. `edl.Versiyon += 1` yapar, DB'ye kaydeder ve Redis `edl:{projectId}` önbelleğini siler.
  - `UndoAsync(Guid projectId)`:
    1. `edl_snapshots` tablosundan `Kaynak == "system"` olan en son snapshot'ı bulur (yoksa `InvalidOperationException` fırlatır).
    2. Mevcut EDL durumunu `Kaynak = "system_undo"` olarak yeni bir Redo snapshot'ı şeklinde kaydeder.
    3. EDL'yi bulunan `lastSystemSnapshot.EdlJson` değerine geri döndürür, `Versiyon += 1` yapar (Frontend'in değişikliği algılaması için) ve kullanılan `lastSystemSnapshot` kaydını siler. Redis `edl:{projectId}` anahtarını temizler.
  - `RedoAsync(Guid projectId)`:
    1. `edl_snapshots` tablosundan `Kaynak == "system_undo"` olan en son snapshot'ı bulur.
    2. Mevcut durumu `Kaynak = "system"` olarak kaydeder, EDL'yi `redoSnapshot.EdlJson` değerine alır, `Versiyon += 1` yapar ve kullanılan `redoSnapshot`'ı siler. Redis `edl:{projectId}` anahtarını temizler.
  - `SaveSnapshotAsync(...)`: Yeni bir `"system"` işlemi yapıldığında tüm `"system_undo"` (Redo) geçmişini siler ve proje başına maksimum 50 snapshot sınırını korur (en eski kayıtları temizler).
  - `CreateOrUpdateAsync(Guid projectId, JsonDocument edlJson)`: Python Worker analizi tamamladığında çağrılır; kayıt varsa snapshot alıp günceller (`Versiyon + 1`), yoksa `Versiyon = 1` olarak yeni `EditDecisionList` oluşturur ve Redis `edl:{projectId}` önbelleğini siler.

#### 4. `src/OtoEdit.Business/Services/ChatManager.cs` (`IChatService`)
- **Etkileşimler:** PostgreSQL (`chat_messages`, `edit_decision_lists`, `video_transcripts`, `projects`), Redis (`chat:{projectId}:history`), Pexels API & MinIO (`IPexelsService`), LLM (`IChatProvider`).
- **Metotlar:**
  - `SendMessageAsync(Guid projectId, string message)`:
    1. Projeyi doğrular.
    2. Redis `chat:{projectId}:history` anahtarından son 10 mesajı çeker; Redis'te yoksa `chat_messages` tablosundan son 10 mesajı çekip Redis'e **1 saat** TTL ile yazar.
    3. Mevcut `EditDecisionList` JSON'unu ve `VideoTranscript` metnini okur. Eğer `video_transcripts` tablosu boşsa, EDL JSON içindeki `transcript.segments` dizisinden `[MM:SS (Xs)] metin` formatında zaman damgalı metin üretir.
    4. Kullanıcı mesajını (`Rol = "user"`) `chat_messages` tablosuna ekler.
    5. `_chatProvider.ProcessCommandAsync` ile AI yanıtını (`ChatResult`) alır.
    6. **Human-in-the-Loop (HitL) Akışı:** Eğer AI yanıtında `EdlPatch` varsa ve `Intent` `"information"` değilse (`"command"` veya `"suggestion"`), değişikliği doğrudan EDL'ye uygulamak yerine `EnrichImageOverlaysWithPexelsAsync` ile (varsa görsel overlay'leri Pexels'ten indirip MinIO anahtarıyla zenginleştirerek) `PendingEdlPatch` alanına yazar ve `PatchDurumu = "pending"` yapar. Eğer `Intent == "clarification"` ise `FormFields` JSON'unu `EdlPatch` sütununa yazar ve `PatchDurumu = "clarification"` yapar.
    7. Asistan mesajını kaydeder ve Redis `chat:{projectId}:history` önbelleğini temizler.
  - `ApplyPendingPatchAsync(Guid messageId)`:
    1. Mesajı bulur, `PatchDurumu == "pending"` ve `PendingEdlPatch` dolu mu kontrol eder.
    2. `_edlService.PatchEdlAsync` ile bekleyen patch'i kalıcı olarak EDL'ye uygular.
    3. Mesajın `PatchDurumu = "applied"`, `EdlPatch = PendingEdlPatch`, `PendingEdlPatch = null` olarak günceller ve Redis `chat:{projectId}:history` önbelleğini temizler.
  - `SubmitFormAsync(Guid projectId, Guid messageId, Dictionary<string, string> parameters)`:
    1. Kullanıcının doldurduğu clarification form parametrelerinden (`content`, `source`, `type`, `font`, `color`, `backgroundColor`, `animation`, `timestamp`, `duration`, `fontSize`, `positionX`, `positionY`) yeni bir `overlays` JSON patch'i derler.
    2. Görsel içeriyorsa `EnrichImageOverlaysWithPexelsAsync` ile zenginleştirir ve `_edlService.PatchEdlAsync` ile EDL'ye uygular.
    3. Mesaj durumunu `"applied"` yapar, `"Form onaylandı: ..."` şeklinde bir kullanıcı mesajı ekler ve Redis önbelleğini temizler.
  - `GetHistoryAsync(Guid projectId)`: Kronolojik sırayla tüm sohbet geçmişini döner (`PendingEdlPatch` ve `clarification` durumundaki `FormFields` JSON'larını parse ederek).

#### 5. `src/OtoEdit.Business/Services/AssetManager.cs` (`IAssetService`)
- **Etkileşimler:** PostgreSQL (`ProjectAssets`, `projects`), MinIO (`assets/{projectId}/{assetId}{ext}`).
- **Sabitler:** `MaxFileSize = 52428800` (50MB). İzin verilen uzantılar: `.png, .jpg, .jpeg, .webp, .gif, .svg, .mp3, .wav, .aac, .m4a, .ogg, .mp4, .mov, .webm`.
- **Metotlar:**
  - `UploadAssetAsync(Guid projectId, IFormFile file)`: Boyut ve uzantı kontrolü yapar, MinIO'ya `assets/{projectId}/{assetId}{ext}` olarak yükler, 24 saatlik presigned URL alır (`://minio:` -> `://localhost:` dönüşümüyle), `ProjectAssets` tablosuna kaydeder ve `ProjectAssetDto` döner.
  - `GetProjectAssetsAsync(Guid projectId)`: Projeye ait tüm varlıkları yeni 24 saatlik presigned URL'lerle birlikte döner.
  - `DeleteAssetAsync(Guid projectId, Guid assetId)`: MinIO'dan ve `ProjectAssets` tablosundan siler.
  - `GetAssetStreamAsync` & `GetAssetUrlAsync`: Dosya stream'ini veya 24 saatlik presigned URL'sini döner.

#### 6. `src/OtoEdit.Business/Services/RenderManager.cs` (`IRenderService`)
- **Etkileşimler:** PostgreSQL (`render_jobs`, `projects`, `edit_decision_lists`), MinIO (`renders/...`), RabbitMQ (`RenderRequestedEvent`).
- **Metotlar:**
  - `RequestRenderAsync(Guid projectId, RenderRequestDto? requestDto = null)`:
    1. Projeyi ve `EditDecisionList` varlığını kontrol eder (EDL yoksa `BusinessException` fırlatır).
    2. Mevcut `EdlJson` kopyasıyla `RenderDurumu.Kuyrukta` durumunda yeni bir `RenderJob` oluşturur, proje durumunu `ProjectDurumu.RenderEdiliyor` yapar.
    3. RabbitMQ'ya `RenderRequestedEvent` publish eder.
  - `GetRenderStatusAsync(Guid projectId, Guid renderJobId)`: `RenderJob` durumunu döner.
  - `GetDownloadUrlAsync(Guid projectId, Guid renderJobId)`: `CiktiYolu` doluysa MinIO'dan **2 saatlik** presigned indirme URL'si üretip döner.
  - `CompleteRenderAsync(Guid renderJobId, string indirmeUrl)`: `RenderJob` durumunu `Tamamlandi`, `CiktiYolu = indirmeUrl`, `BitisZamani` ve `SureMs` olarak günceller; projenin durumunu da `ProjectDurumu.Tamamlandi` yapar.
  - `FailRenderAsync(Guid renderJobId, string hataMesaji)`: Eğer render zaten `Tamamlandi` ise işlemi göz ardı eder (idempotency); değilse `RenderDurumu.Hata` ve `HataMesaji` olarak kaydeder.

#### 7. `src/OtoEdit.Business/Services/TemplateManager.cs` (`ITemplateService`)
- **Metotlar:** `GetAllAsync` (`AktifMi == true` olan şablonları döner) ve `GetByIdAsync(Guid id)`.

#### 8. `src/OtoEdit.Business/Services/LogManager.cs` (`ILogService`)
- **Amacı:** 3 katmanlı veritabanı loglama sistemini yönetir; tüm girdileri `SensitiveDataMasker.MaskJson` ile maskeler.
- **Metotlar:**
  - `LogEndpointAsync(EndpointLog log)` -> `endpoint_logs` tablosu.
  - `LogPipelineStartAsync`, `LogPipelineEndAsync`, `LogPipelineErrorAsync` -> `pipeline_logs` tablosu.
  - `LogFunctionErrorAsync` -> `[CallerMemberName]`, `[CallerFilePath]`, `[CallerLineNumber]` öznitelikleriyle hatanın oluştuğu sınıf, metot ve satır numarasını otomatik yakalayıp `function_logs` tablosuna yazar.

#### 9. `src/OtoEdit.Business/Services/PipelineNotificationManager.cs` (`IPipelineNotificationService`)
- **Amacı:** `public static Func<Guid, string, object, Task>? SendSignalRMessageAsync` delegesi üzerinden (`Program.cs`'de `IHubContext<PipelineHub>` ile bağlanır) `project-{projectId}` SignalR grubuna `AnalysisProgress`, `AnalysisCompleted`, `RenderProgress`, `RenderCompleted` ve `PipelineError` mesajlarını yayınlar.

---

## 4. `src/OtoEdit.API` Katmanı (Web API, SignalR, Consumers, Middleware)

### 4.1. Yapılandırma ve Başlangıç Dosyaları

#### `src/OtoEdit.API/OtoEdit.API.csproj`
- **Paketler:** `Microsoft.EntityFrameworkCore.Design` (10.0.5), `Serilog.AspNetCore` (10.0.0), `Serilog.Sinks.Console` (6.1.1), `Serilog.Sinks.File` (7.0.0), `Swashbuckle.AspNetCore` (10.1.7).

#### `src/OtoEdit.API/Program.cs`
- **Adım Adım Uygulama Başlatma Akışı:**
  1. `AppContext.SetSwitch("Npgsql.EnableLegacyTimestampBehavior", true);` ayarlar.
  2. Çalışma dizininden yukarı doğru `.env` dosyasını arar ve bulursa içindeki tüm anahtar-değer çiftlerini hem `Environment.SetEnvironmentVariable` hem de `builder.Configuration` içine yükler.
  3. Controller'ları ve `JsonStringEnumConverter`'ı ekler.
  4. Swagger (`AddSwaggerGen`) ve SignalR (`AddSignalR`) servislerini ekler.
  5. Kestrel `MaxRequestBodySize` ve `FormOptions.MultipartBodyLengthLimit` değerlerini **50 GB** (`53687091200L` byte) olarak yapılandırır.
  6. `AddDataLayer` ve `AddBusinessLayer` çağırır; MassTransit içerisine 4 Consumer'ı (`AnalysisNotificationConsumer`, `RenderNotificationConsumer`, `PipelineStageChangedConsumer`, `PipelineErrorConsumer`) kaydeder.
  7. `"AllowFrontend"` CORS politikasını (tüm origin, method, header ve credentials izinli) ve `"fixed"` Rate Limiter'ı (dakikada 100 istek, 20 kuyruk limiti, HTTP 429) tanımlar.
  8. `PipelineNotificationManager.SendSignalRMessageAsync` delegesini `IHubContext<PipelineHub>` ile `project-{projectId}` grubuna bağlar.
  9. **Middleware Sıralaması:**
     - `ExceptionHandlingMiddleware`
     - `RequestResponseLoggingMiddleware`
     - `Swagger` & `SwaggerUI` (her ortamda açık: `if (app.Environment.IsDevelopment() || true)`)
     - `UseCors("AllowFrontend")`
     - `UseRateLimiter()`
     - `ApiKeyAuthMiddleware`
     - `UseAuthorization()`
     - `MapControllers()` ve `MapHub<PipelineHub>("/pipeline-hub")`
  10. Başlangıçta otomatik `db.Database.Migrate()` çalıştırır.

#### Diğer Yapılandırma Dosyaları
- `src/OtoEdit.API/appsettings.json` & `appsettings.Development.json`: Standart `Logging` (`Information` / `Warning`) ve `AllowedHosts: "*"` ayarları.
- `src/OtoEdit.API/Properties/launchSettings.json`: `http://localhost:5001` üzerinde `Development` ortamında başlatma profili.
- `src/OtoEdit.API/OtoEdit.API.http`: Örnek HTTP test dosyası.

---

### 4.2. `Middleware` Klasörü (`src/OtoEdit.API/Middleware`)

1. **`src/OtoEdit.API/Middleware/ApiKeyAuthMiddleware.cs`**
   - **Amacı:** Tek kullanıcılı Admin `X-API-Key` doğrulaması yapar.
   - **İşleyişi:**
     - `OPTIONS` (CORS preflight) isteklerini ve `/swagger`, `/health`, `/pipeline-hub` ile başlayan yolları doğrulamadan geçirir.
     - Anahtarı önce `X-API-Key` HTTP başlığında, yoksa `?apiKey=` veya `?access_token=` query parametrelerinde arar (video/asset stream yönlendirmeleri için).
     - Yapılandırmadaki `ApiKey` veya `ADMIN_API_KEY` (varsayılan `SUPER_SECRET_OTOEDIT_KEY_123!`) ile eşleşmezse `401 Unauthorized` döner.

2. **`src/OtoEdit.API/Middleware/ExceptionHandlingMiddleware.cs`**
   - **Amacı:** Tüm işlenmemiş hataları yakalar, `ILogService.LogFunctionErrorAsync` ile `function_logs` tablosuna (`API_UNHANDLED_ERR`) kaydeder ve RFC 7231 `application/problem+json` formatında yanıt döner:
     - `ValidationException` -> `400 Bad Request` ("Doğrulama Hatası")
     - `NotFoundException` -> `404 Not Found` ("Kayıt Bulunamadı")
     - `BusinessException` -> `400 Bad Request` ("İş Kuralı İhlali")
     - Diğer tüm istisnalar -> `500 Internal Server Error` ("Sunucu Hatası")

3. **`src/OtoEdit.API/Middleware/RequestResponseLoggingMiddleware.cs`**
   - **Amacı:** `/pipeline-hub` ve `multipart/form-data` (büyük dosya yüklemeleri) dışındaki tüm HTTP istek ve yanıt gövdelerini (maksimum 4000 karaktere kırparak ve `\0` karakterlerini temizleyerek) çalışma süresi (`DurationMs`), IP adresi, User-Agent ve durum koduyla birlikte `endpoint_logs` tablosuna kaydeder.

---

### 4.3. `Hubs` ve `Consumers` Klasörleri (`src/OtoEdit.API/Hubs` & `Consumers`)

1. **`src/OtoEdit.API/Hubs/PipelineHub.cs`** (`/pipeline-hub`)
   - **Metotlar:**
     - `JoinProjectGroup(string projectId)`: İstemci bağlantısını (`Context.ConnectionId`) `project-{projectId}` SignalR grubuna ekler.
     - `LeaveProjectGroup(string projectId)`: İstemciyi `project-{projectId}` grubundan çıkarır.

2. **`src/OtoEdit.API/Consumers/PipelineStageChangedConsumer.cs`** (`IConsumer<PipelineStageChangedEvent>`)
   - Python Worker'dan gelen aşama ilerleme mesajını alır ve `project-{ProjectId}` SignalR grubuna `"AnalysisProgress"` (`{ projectId, asama, yuzde, mesaj }`) event'i olarak yayınlar.

3. **`src/OtoEdit.API/Consumers/AnalysisNotificationConsumer.cs`** (`IConsumer<AnalysisCompletedEvent>`)
   - Python Worker analizi tamamladığında:
     1. `_edlService.CreateOrUpdateAsync` ile üretilen taslak EDL JSON'u veritabanına kaydeder.
     2. `_projectService.UpdateStatusAsync` ile proje durumunu `ProjectDurumu.AnalizTamamlandi` yapar.
     3. `project-{ProjectId}` SignalR grubuna `"AnalysisCompleted"` (`{ projectId, edlVersiyon }`) gönderir.

4. **`src/OtoEdit.API/Consumers/RenderNotificationConsumer.cs`** (`IConsumer<RenderCompletedEvent>`)
   - Python Worker FFmpeg render'ı tamamladığında:
     1. `_renderService.CompleteRenderAsync` ile `RenderJob` ve `Project` durumlarını `Tamamlandi` yapar.
     2. `project-{ProjectId}` SignalR grubuna `"RenderCompleted"` (`{ renderJobId, projectId, indirmeUrl }`) gönderir.

5. **`src/OtoEdit.API/Consumers/PipelineErrorConsumer.cs`** (`IConsumer<PipelineErrorEvent>`)
   - Python Worker'dan hata geldiğinde:
     1. Proje zaten `ProjectDurumu.Tamamlandi` ise hatayı göz ardı eder.
     2. Proje durumunu `ProjectDurumu.Hata` olarak günceller.
     3. Eğer `Asama == "Render"` ve `VideoId.HasValue` ise `_renderService.FailRenderAsync` çağırır.
     4. `project-{ProjectId}` SignalR grubuna `"PipelineError"` (`{ projectId, hataMesaji }`) gönderir.

---

### 4.4. `Controllers` Klasörü (`src/OtoEdit.API/Controllers`) — Tüm Endpoint'ler

1. **`src/OtoEdit.API/Controllers/ProjectsController.cs`** (`Route: api/projects`)
   - `GET /api/projects` (`GetAll`): Tüm projeleri `IEnumerable<ProjectListDto>` olarak döner (200 OK).
   - `GET /api/projects/{id:guid}` (`GetById`): Proje detaylarını `ProjectDetailDto` olarak döner (200 OK / 404 NotFound).
   - `POST /api/projects` (`Create`): `ProjectCreateDto` alır, yeni proje oluşturur (201 Created).
   - `PUT /api/projects/{id:guid}` (`Update`): `ProjectUpdateDto` alır, projeyi günceller (200 OK).
   - `DELETE /api/projects/{id:guid}` (`Delete`): Projeyi ve MinIO dosyalarını siler (204 NoContent).

2. **`src/OtoEdit.API/Controllers/VideosController.cs`**
   - `POST /api/projects/{projectId:guid}/videos` (`UploadVideo`): `[FromForm] VideoUploadDto` alır (50GB limitli), videoyu MinIO'ya yükler ve `VideoUploadedEvent` ile Python analizini başlatır (201 Created).
   - `GET /api/projects/{projectId:guid}/video` (`GetVideo`): Projeye ait video detaylarını döner (200 OK / 404 NotFound).
   - `DELETE /api/projects/{projectId:guid}/video` (`DeleteVideo`): Projeye ait videoyu siler (204 NoContent).
   - `GET /api/videos/{videoId:guid}/stream` (`StreamVideo`): MinIO presigned URL'sine `302 Redirect` döner.

3. **`src/OtoEdit.API/Controllers/EdlController.cs`** (`Route: api/projects/{projectId:guid}/edl`)
   - `GET /api/projects/{projectId:guid}/edl` (`GetEdl`): Güncel EDL JSON verisini (`EdlDto`) döner (200 OK).
   - `PATCH /api/projects/{projectId:guid}/edl` (`PatchEdl`): `[FromBody] JsonElement patch` alır, snapshot kaydedip EDL'yi kısmi günceller (200 OK).
   - `POST /api/projects/{projectId:guid}/edl/undo` (`UndoEdl`): Son EDL değişikliğini geri alır (200 OK).
   - `POST /api/projects/{projectId:guid}/edl/redo` (`RedoEdl`): Geri alınan EDL değişikliğini ileri alır (200 OK).

4. **`src/OtoEdit.API/Controllers/ChatController.cs`** (`Route: api/projects/{projectId:guid}/chat`)
   - `POST /api/projects/{projectId:guid}/chat` (`SendMessage`): `ChatMessageDto` alır, AI kurgu asistanını çalıştırır ve `ChatResponseDto` döner (200 OK).
   - `GET /api/projects/{projectId:guid}/chat` (`GetHistory`): Proje sohbet geçmişini döner (200 OK).
   - `POST /api/projects/{projectId:guid}/chat/{messageId:guid}/apply` (`ApplyPendingPatch`): Onay bekleyen (`pending`) AI EDL patch'ini kalıcı olarak uygular (200 OK).
   - `POST /api/projects/{projectId:guid}/chat/{messageId:guid}/form` (`SubmitForm`): AI Yönetmen (`clarification`) form parametrelerini (`Dictionary<string, string>`) alıp overlay olarak EDL'ye uygular (200 OK).

5. **`src/OtoEdit.API/Controllers/AssetsController.cs`** (`Route: api/projects/{projectId:guid}/assets`)
   - `POST /api/projects/{projectId:guid}/assets` (`UploadAsset`): 50MB limitli medya dosyası (`IFormFile`) yükler (201 Created).
   - `GET /api/projects/{projectId:guid}/assets` (`GetAssets`): Projenin tüm medya varlıklarını listeler (200 OK).
   - `DELETE /api/projects/{projectId:guid}/assets/{assetId:guid}` (`DeleteAsset`): Medya varlığını siler (204 NoContent).
   - `GET /api/projects/{projectId:guid}/assets/{assetId:guid}/stream` (`StreamAsset`): Medya varlığının presigned URL'sine `302 Redirect` döner.

6. **`src/OtoEdit.API/Controllers/RenderController.cs`**
   - `POST /api/projects/{projectId:guid}/render` (`RequestRender`): `RenderRequestDto?` alır, `RenderJob` oluşturup RabbitMQ'ya `RenderRequestedEvent` gönderir (`202 Accepted`).
   - `GET /api/projects/{projectId:guid}/render/{renderJobId:guid}` (`GetRenderStatus`): Render durumunu döner (200 OK).
   - `GET /api/projects/{projectId:guid}/render/{renderJobId:guid}/download` (`Download`): `{ downloadUrl }` presigned linkini döner (200 OK).

7. **`src/OtoEdit.API/Controllers/PipelineController.cs`** (`Route: api/pipeline`)
   - `GET /api/pipeline/project/{projectId:guid}/progress` (`GetProjectProgress`): Projenin durumunu ve `pipeline_logs` tablosundaki tüm aşama kayıtlarını döner (200 OK).
   - `GET /api/pipeline/video/{videoId:guid}/status` (`GetVideoStatus`): Videonun `IslemDurumu` bilgisini döner (200 OK / 404 NotFound).

8. **`src/OtoEdit.API/Controllers/InternalLogsController.cs`** (`Route: api/internal/logs`)
   - `POST /api/internal/logs/pipeline` (`LogPipelineProgress`): Python Worker'dan HTTP üzerinden doğrudan gönderilen `PipelineLogRequestDto` (`ProjectId`, `VideoId`, `Stage`, `ProgressPercentage`, `Status`, `Message`, `DetailsJson`, `ErrorMessage`, `TimestampUtc`) verisini `pipeline_logs` tablosuna kaydeder ve aynı anda SignalR `project-{ProjectId}` grubuna `"AnalysisProgress"` olarak canlı yayınlar (200 OK).

9. **`src/OtoEdit.API/Controllers/TemplatesController.cs`** (`Route: api/templates`)
   - `GET /api/templates` (`GetAll`): Aktif video şablonlarını listeler (200 OK).
   - `GET /api/templates/{id:guid}` (`GetById`): Şablon detayını döner (200 OK / 404 NotFound).

---

## 5. `tests/OtoEdit.UnitTests` Katmanı (Birim Testleri Özeti)

- **`tests/OtoEdit.UnitTests/OtoEdit.UnitTests.csproj`**: `xUnit` (2.9.3), `Moq` (4.20.72), `FluentAssertions` (7.2.0) ve `Microsoft.EntityFrameworkCore.InMemory` (10.0.5) kullanır.
- **`Consumers/AnalysisNotificationConsumerTests.cs`**: `AnalysisCompletedEvent` geldiğinde EDL'nin kaydedildiğini, proje durumunun `AnalizTamamlandi` yapıldığını ve SignalR `AnalysisCompleted` mesajının gönderildiğini doğrular.
- **`Consumers/RenderNotificationConsumerTests.cs`**: `RenderCompletedEvent` geldiğinde `CompleteRenderAsync` çağrıldığını ve SignalR `RenderCompleted` mesajının gönderildiğini doğrular.
- **`Controllers/AssetsControllerTests.cs`**: Boş dosyada 400 BadRequest, geçerli dosyada 201 Created, listelemede 200 OK ve silmede 204 NoContent döndüğünü test eder.
- **`Controllers/ChatControllerTests.cs`**: Boş mesajda 400 BadRequest, geçerli mesajda 200 OK, geçmiş listeleme ve `ApplyPendingPatch` endpoint'lerini test eder.
- **`Controllers/EdlControllerTests.cs`**: `GetEdl`, `PatchEdl`, `UndoEdl` ve `RedoEdl` endpoint'lerinin 200 OK ve beklenen DTO'ları döndürdüğünü test eder.
- **`Events/PipelineEventSerializationTests.cs`**: Python Worker ile .NET API arasındaki `PipelineStageChangedEvent`, `VideoUploadedEvent`, `AnalysisCompletedEvent` ve `PipelineErrorEvent` sınıflarının camelCase JSON serileştirme/ayrıştırma uyumluluğunu test eder.
- **`Helpers/HashHelperTests.cs`**: SHA-256 özet üretiminin boş girdide boş string, geçerli girdide 64 karakter hex ve deterministik sonuç ürettiğini test eder.
- **`Helpers/SensitiveDataMaskerTests.cs`**: JSON içindeki `password`, `apiKey`, `token`, `secret` alanlarının ve metin içindeki e-posta adreslerinin maskelendiğini test eder.
- **`Middleware/ApiKeyAuthMiddlewareTests.cs`**: `OPTIONS` isteklerinin ve `/health`, `/swagger`, `/pipeline-hub` yollarının şartsız geçtiğini; eksik/hatalı `X-API-Key` durumunda 401 Unauthorized, geçerli anahtarda 200 OK döndüğünü test eder.
- **`Middleware/ExceptionHandlingMiddlewareTests.cs`**: `NotFoundException` -> 404, `BusinessException` -> 400, `ValidationException` -> 400, genel `Exception` -> 500 dönüşümlerini ve `LogFunctionErrorAsync` çağrısını test eder.
- **`Services/AssetManagerTests.cs`**: InMemory DB üzerinde proje bulunamama, boş dosya, geçersiz uzantı (`.exe`), geçerli PNG yükleme (`minio` -> `localhost` URL sanitizasyonu), listeleme ve silme senaryolarını test eder.
- **`Services/ChatManagerTests.cs`**: HitL (`pending` patch) akışını, görsel overlay'lerin Pexels ile zenginleştirilmesini (`EnrichImageOverlaysWithPexelsAsync`), `clarification` niyetinde `FormFields` saklanmasını/okunmasını ve `ApplyPendingPatchAsync` metodunu test eder.
- **`Services/EdlManagerPatchTests.cs`**: `PatchEdlAsync` metodunun `cuts` ve `overlays` ekleme/silme/güncelleme, büyük/küçük harf duyarsız (`Cuts`, `OverLAYS`, `ID`, `ACTION`) eşleşme, `trackId` güncelleme, `exitAnimation`/`font` güncelleme ve çoklu kesim birleştirme senaryolarını test eder.
- **`Services/EdlManagerTests.cs`**: Redis cache okuma, `CreateOrUpdateAsync` versiyon artışı, `PatchEdlAsync` ve EDL içinde `transcript` eksik olduğunda `VideoTranscripts` tablosundan otomatik besleme (fallback) davranışını test eder.
- **`Services/PexelsServiceTests.cs`**: `FakeHttpMessageHandler` ile API anahtarı yokken `null` dönmesini, fotoğraf aramayı ve indirip MinIO'ya `assets/{projectId}/{guid}.jpg` olarak kaydetmeyi test eder.
- **`Services/ProjectManagerTests.cs`**: Redis önbellek isabeti (cache hit), DB'den okuma ve önbelleğe yazma, validasyon hatası, proje oluşturma ve silme (MinIO + DB + Cache) akışlarını test eder.
- **`Services/RenderManagerTests.cs`**: EDL yokken render başlatılamamasını, geçerli projede `RenderJob` oluşturulup `RenderRequestedEvent` fırlatılmasını, indirme URL'si üretimini ve `CompleteRenderAsync` akışını test eder.
- **`Services/VideoManagerTests.cs`**: Boş dosya ve geçersiz uzantı (`.pdf`) kontrollerini, geçerli `.mp4` yüklemesinde MinIO upload, DB kaydı, proje durum güncellemesi ve `VideoUploadedEvent` yayınlanmasını test eder.
- **`Validators/OtherValidatorsTests.cs` & `ProjectValidatorsTests.cs`**: `VideoUploadValidator`, `ChatMessageValidator`, `ProjectCreateValidator` ve `ProjectUpdateValidator` kurallarını test eder.

---

# EK B: Python Worker (OtoEdit.PythonWorker ve PythonWorker.Tests) Tam Dosya & Fonksiyon Referansı

# OtoEdit Python Worker ve Testleri — Kapsamlı Teknik İnceleme Raporu

Bu rapor, `OtoEdit/src/OtoEdit.PythonWorker` ve `OtoEdit/tests/PythonWorker.Tests` dizinlerindeki **tüm dosyaların**, sınıfların, veri modellerinin (dataclass / Pydantic), fonksiyonların ve metotların imzalarını, dönüş tiplerini, adım adım algoritmalarını, kullandıkları harici kütüphaneleri ve veri akışlarını eksiksiz olarak içerir.

---

## BÖLÜM 1: KÖK DİZİN DOSYALARI (`src/OtoEdit.PythonWorker/`)

### 1.1. `src/OtoEdit.PythonWorker/main.py`
* **Dosyanın Amacı:** Python Worker mikroservisinin ana giriş noktasıdır (`ENTRYPOINT`). Loglamayı kurar, gerekli geçici/log dizinlerini oluşturur, başlangıçta `janitor` ile eski geçici dosyaları temizler ve `AnalysisConsumer` ile `RenderConsumer` tüketicilerini iki ayrı arka plan (daemon) iş parçacığında (`threading.Thread`) başlatarak ana iş parçacığını canlı tutar.
* **Harici Kütüphaneler:** `sys`, `time`, `threading` (Standart Kütüphane).
* **Fonksiyonlar:**
  1. **`run_analysis_consumer() -> None`**
     * **Algoritma:** `consumers.analysis_consumer.AnalysisConsumer` sınıfını tembel (lazy) import eder, örneğini oluşturur ve `consumer.start()` çağrısıyla RabbitMQ `video-uploaded` kuyruğunu dinleme döngüsüne sokar. Olası istisnaları yakalayıp `logger.error(..., exc_info=True)` ile kaydeder.
  2. **`run_render_consumer() -> None`**
     * **Algoritma:** `consumers.render_consumer.RenderConsumer` sınıfını import eder, örneğini oluşturur ve `consumer.start()` ile RabbitMQ `render-requested` kuyruğunu dinleme döngüsüne sokar. Hataları loglar.
  3. **`main() -> None`**
     * **Algoritma:**
       1. Başlangıç yapılandırma özetini (`Config.TEMP_DIR`, `RABBITMQ_HOST:PORT`, `MINIO_ENDPOINT`, `STT_ENGINE_ORDER`, `JUMPCUT_ENGINE`, `JUMPCUT_MIN_SILENCE_MS`, `JUMPCUT_PAD_MS`) loglar.
       2. `Config.ensure_directories()` ile `temp/` ve `logs/` klasörlerini oluşturur.
       3. `utils.janitor.run_janitor()` çağrısıyla başlangıçta yetim render klasörlerini ve eski temp dosyalarını temizler.
       4. `AnalysisConsumerThread` ve `RenderConsumerThread` adında iki `daemon=True` thread başlatır.
       5. `while t_analysis.is_alive() or t_render.is_alive(): time.sleep(1)` döngüsüyle ana süreci açık tutar; `KeyboardInterrupt` veya beklenmeyen kritik hataları yakalar.

---

### 1.2. `src/OtoEdit.PythonWorker/config.py`
* **Dosyanın Amacı:** Ortam değişkenlerini (`.env` veya işletim sistemi ortam değişkenleri) okuyarak Worker genelinde kullanılan tüm dizin, RabbitMQ, MinIO, AI API anahtarları, STT motor sırası, Silero VAD eşikleri, Jump-Cut v2/v3 parametreleri, Redis önbellek ve .NET Backend API ayarlarını merkezi bir `Config` sınıfında toplar.
* **Harici Kütüphaneler:** `os`, `pathlib.Path`, `python-dotenv` (`dotenv.load_dotenv()`).
* **Sınıflar ve Metotlar:**
  * **`class Config`**
    * **Sabit Özellikler (Class Attributes):**
      * **Dizinler:** `BASE_DIR` (`Path`), `TEMP_DIR` (`BASE_DIR / "temp"`).
      * **RabbitMQ:** `RABBITMQ_HOST` (`"localhost"`), `RABBITMQ_PORT` (`5672`), `RABBITMQ_USERNAME` (`"guest"`), `RABBITMQ_PASSWORD` (`"guest"`), `RABBITMQ_VHOST` (`"/"`).
      * **MinIO S3:** `MINIO_ENDPOINT` (`"localhost:9000"`), `MINIO_ACCESS_KEY` (`"minioadmin"`), `MINIO_SECRET_KEY` (`"minioadmin"`), `MINIO_BUCKET_NAME` (`"otoedit"`), `MINIO_SECURE` (`bool`).
      * **AI & Harici API Anahtarları:** `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GEMINI_API_KEYS` (virgülle ayrılmış çoklu anahtar listesi), `GEMINI_TRANSCRIBE_RPM` (`3`), `GROQ_API_KEY`, `ANTIGRAVITY_PROXY_URL` (`"http://host.docker.internal:8045/v1"`), `ANTIGRAVITY_PROXY_KEY`, `ANTIGRAVITY_PROXY_MODEL` (`"gemini-3.8-flash-tiered"`), `PEXELS_API_KEY`.
      * **STT Motor Zinciri:** `STT_ENGINE_ORDER` (`["gemini_transcribe", "groq", "proxy_gemini", "local_whisper"]`), `STT_CHUNK_MAX_SEC` (`600`), `LOCAL_WHISPER_MODEL` (`"large-v3-turbo"`).
      * **Ses Analizi & VAD:** `VAD_THRESHOLD` (`0.4`), `VAD_MIN_SILENCE_MS` (`500`).
      * **Jump-Cut v2/v3 Parametreleri:** `JUMPCUT_ENGINE` (`"v2"`), `JUMPCUT_MIN_SILENCE_MS` (`700`), `JUMPCUT_PAD_MS` (`200`), `JUMPCUT_PAD_LEAD_MS` (`350`), `JUMPCUT_PAD_TRAILING_MS` (`200`), `JUMPCUT_WORD_GUARD_MS` (`150`), `JUMPCUT_MIN_ISLAND_MS` (`300`), `GEMINI_TRANSCRIBE_MAX_WAIT_SEC` (`180.0`), `TEMP_RETENTION` (`"after_job"`).
      * **Redis:** `REDIS_HOST` (`"redis"`), `REDIS_PORT` (`6379`), `REDIS_PASSWORD` (`""`), `REDIS_DB` (`0`), `ENABLE_ANALYSIS_CACHE` (`False`).
      * **Backend API:** `API_BASE_URL` (`"http://host.docker.internal:5001"`), `INTERNAL_API_KEY`.
      * **Legacy / Gesture:** `GESTURE_FRAME_SKIP` (`8`), `GESTURE_CONFIDENCE` (`0.7`), `SILENCE_MIN_LEN_MS` (`500`), `SILENCE_THRESH_DBFS` (`-40`).
    * **`ensure_directories(cls) -> None` (`@classmethod`)**
      * **Algoritma:** `cls.TEMP_DIR` ve `cls.BASE_DIR / "logs"` dizinlerini `mkdir(parents=True, exist_ok=True)` ile oluşturur.

---

### 1.3. `src/OtoEdit.PythonWorker/requirements.txt`
* **Dosyanın Amacı:** Python Worker'ın çalışması için gerekli tüm Python paket bağımlılıklarını tanımlar:
  * **LLM & STT:** `openai>=1.0.0`, `google-generativeai>=0.3.0`, `faster-whisper>=1.0.0`
  * **Görüntü İşleme & AI:** `mediapipe>=0.10.0`, `opencv-python>=4.8.0`, `Pillow>=10.0.0`, `rembg[cpu]>=2.0.50`
  * **Ses İşleme & Bilimsel Hesaplama:** `pydub>=0.25.0`, `noisereduce>=3.0.0`, `ffmpeg-python>=0.2.0`, `numpy>=1.26.0`, `scipy>=1.10.0`
  * **Altyapı, Mesajlaşma, Depolama ve Önbellek:** `pika>=1.3.0`, `requests>=2.31.0`, `minio>=7.2.0`, `redis>=5.0.0`, `python-dotenv>=1.0.0`, `pydantic>=2.5.0`, `tenacity>=8.2.0`, `pytest>=8.0.0`
  * **NVIDIA CUDA Kütüphaneleri:** `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, `nvidia-cuda-nvrtc-cu12`

---

### 1.4. `src/OtoEdit.PythonWorker/Dockerfile`
* **Dosyanın Amacı:** Python Worker konteyner imajını inşa eder.
* **Adım Adım İnşa Süreci:**
  1. `python:3.11-slim` temel imajını kullanır.
  2. `apt-get` ile `ffmpeg`, `libgl1`, `libglib2.0-0`, `curl`, `unzip`, `fontconfig` sistem paketlerini kurar.
  3. `assets/fonts/*.ttf` içindeki özel Google Fontlarını (`Inter`, `Montserrat`, `Cinzel`, `BebasNeue`, `Anton`, `Poppins-Bold`, `Poppins-Regular`, `Outfit`) `/usr/share/fonts/truetype/custom/` dizinine kopyalar ve `fc-cache -f -v` ile sistem font önbelleğini yeniler (FFmpeg `libass` ve Pillow için).
  4. `/app` çalışma dizininde `requirements.txt` paketlerini kurar, kaynak kodları kopyalar, `/app/temp`, `/app/logs`, `/app/assets/fonts` klasörlerini oluşturur ve `CMD ["python", "main.py"]` ile servisi başlatır.

---

### 1.5. `src/OtoEdit.PythonWorker/.dockerignore`
* **Dosyanın Amacı:** Docker build context'ine yerel `temp/` klasörünün dahil edilmesini engeller.

---

### 1.6. `src/OtoEdit.PythonWorker/test_cut_single_segment.py`
* **Dosyanın Amacı:** Kök dizinde bulunan bağımsız bir test betiğidir; `VideoRenderer` içinde kesim yapılırken FFmpeg `-ss` parametresinin `-i` parametresinden önce (Input Seeking) verildiğini doğrulamak için yazılmıştır (Not: Eski `_execute_ffmpeg_with_concat` metodunu çağırır; güncel `VideoRenderer`'da bu metot `_cut_segments` ve `_concat_segments` olarak ikiye ayrılmıştır).
* **Fonksiyonlar:**
  * **`test_cut() -> None`:** `VideoRenderer(minio_client=MagicMock())` oluşturur, geçici bir `cuts_dummy.txt` yazar, `subprocess.run`'ı mock'layarak çağrı argümanlarında `-ss` indeksinin `-i` indeksinden küçük olduğunu kontrol eder.

---

### 1.7. `src/OtoEdit.PythonWorker/assets/fonts/` ve `src/OtoEdit.PythonWorker/logs/worker.log`
* **`assets/fonts/`:** Altyazı (`.ass`) ve Pillow grafik motoru (`PillowGraphicsEngine`) tarafından kullanılan 8 adet TrueType font dosyasını barındırır: `Anton.ttf`, `BebasNeue.ttf`, `Cinzel.ttf`, `Inter.ttf`, `Montserrat.ttf`, `Outfit.ttf`, `Poppins-Bold.ttf`, `Poppins-Regular.ttf`.
* **`logs/worker.log`:** `utils/logger.py` tarafından çalışma zamanı loglarının yazıldığı yerel log dosyasıdır.

---

## BÖLÜM 2: TÜKETİCİLER (`src/OtoEdit.PythonWorker/consumers/`)

### 2.1. `src/OtoEdit.PythonWorker/consumers/__init__.py`
* **Dosyanın Amacı:** `AnalysisConsumer` ve `RenderConsumer` sınıflarını paket seviyesinde dışa aktarır (`__all__ = ["AnalysisConsumer", "RenderConsumer"]`).

---

### 2.2. `src/OtoEdit.PythonWorker/consumers/heartbeat_manager.py`
* **Dosyanın Amacı:** Uzun süren ağır video/AI analiz ve render işlemleri sırasında RabbitMQ `pika.BlockingConnection` soketinin boşta kalarak kopmasını (`StreamLostError` / `ConnectionResetError`) önlemek amacıyla arka planda periyodik olarak `connection.process_data_events(time_limit=0)` çağıran iş parçacığı yöneticisidir.
* **Harici Kütüphaneler:** `threading`, `time`, `logging`.
* **Sınıflar ve Metotlar:**
  * **`class RabbitHeartbeatKeeper`**
    * **`__init__(self, connection, interval_sec: float = 10.0) -> None`:** RabbitMQ bağlantı nesnesini, nabız aralığını (`10.0` sn) ve durdurma olayını (`threading.Event`) başlatır.
    * **`start(self) -> None`:** Bağlantı açık değilse (`is_open`) uyarı verip çıkar. Aksi halde `_stop_event`'i temizler ve `_run` metodunu `RabbitMQ-HeartbeatKeeper` adlı bir daemon thread olarak başlatır.
    * **`stop(self) -> None`:** `_stop_event.set()` ile döngüyü sonlandırır ve thread'in bitmesini `join(timeout=2.0)` ile bekler.
    * **`_run(self) -> None`:** `_stop_event` set edilene kadar her `_interval` saniyede bir `self._connection.process_data_events(time_limit=0)` çağırarak RabbitMQ soket seviyesinde heartbeat frame'lerini işler.

---

### 2.3. `src/OtoEdit.PythonWorker/consumers/analysis_consumer.py`
* **Dosyanın Amacı:** RabbitMQ'daki `video-uploaded` kuyruğunu dinleyerek yeni yüklenen videolar için uçtan uca yapay zeka analiz pipeline'ını (MinIO indirme -> Redis SHA-256 Idempotency -> Ses iyileştirme -> Silero VAD & RMS analizi -> Paralel Grup 1 [STT + Yüz Takibi] -> Akıllı Retake v3 -> Jump-Cut v3 -> Altyazı segmentlerini kesim sınırlarına göre yeniden üretme -> Paralel Grup 2 [Çoklu-Modal Komutlar + Viral Klip Repurposing + Öneri Motoru + Otomatik B-Roll] -> EDL İnşası -> Redis Kayıt -> RabbitMQ `AnalysisCompletedEvent` yayını -> Temp temizliği) orkestre eder.
* **Harici Kütüphaneler:** `pika` (RabbitMQ), `concurrent.futures` (`ThreadPoolExecutor`), `numpy`, `pydub`.
* **Sınıflar ve Metotlar:**
  * **`class AnalysisConsumer`**
    * **`__init__(self) -> None`**
      * **Veri Akışı / Bileşenler:** `MinioClient`, `RabbitMQPublisher`, `PipelineLogger`, `AnalysisCacheService`, `AudioEnhancer`, `AudioAnalyzer`, `Transcriber`, `SilenceDetector`, `RetakeDetector`, `AutoBrollEngine`, `MultimodalCommandEngine`, `FaceTracker`, `RepurposingEngine`, `SuggestionEngine` ve `EdlBuilder` örneklerini başlatır.
    * **`start(self) -> None`**
      * **Algoritma:**
        1. `pika.PlainCredentials` ve `pika.ConnectionParameters` (`heartbeat=0`, `blocked_connection_timeout=0`) ile `pika.BlockingConnection` açar.
        2. `video-uploaded` (`RabbitMQConstants.QUEUE_VIDEO_UPLOADED`) kuyruğunu `durable=True` olarak tanımlar.
        3. Hem yalın `VideoUploadedEvent` hem de MassTransit命名 uzaylı `OtoEdit.Business.Events:VideoUploadedEvent` fanout exchange'lerini tanımlayıp kuyruğa bağlar (`queue_bind`).
        4. `basic_qos(prefetch_count=1)` ile aynı anda tek bir video analizi yapılmasını sağlar ve `_on_message` callback'i ile dinlemeye başlar.
    * **`_on_message(self, ch, method, properties, body) -> None`**
      * **Adım Adım Algoritma ve Veri Akışı:**
        1. **JSON Çözümleme:** Gelen mesaj gövdesinden `videoId`, `projectId`, `videoFormati` (`0`: 16:9, `1`: 9:16, `2`: 1:1), `dosyaYolu`, `gestureCommandsEnabled`, `audioEnhancementEnabled`, `autoJumpcutEnabled`, `autoRetakeEnabled`, `autoBrollEnabled`, `autoSubtitlesEnabled` bayraklarını okur. JSON bozuksa `basic_nack(requeue=False)` yapar.
        2. **Heartbeat Başlatma:** `RabbitHeartbeatKeeper(self._connection, interval_sec=10.0).start()` ile bağlantı koruyucuyu devreye alır.
        3. **MinIO'dan Video İndirme (%5):** `self.minio.download_video(project_id, video_id, object_key=dosya_yolu)` ile videoyu yerel `temp/` dizinine indirir.
        4. **Redis Idempotency Kontrolü:** `self.cache.compute_video_hash(local_video_path)` ile videonun hızlı SHA-256 özetini hesaplar. `Config.ENABLE_ANALYSIS_CACHE` aktifse ve `self.cache.get_cached_edl(video_hash)` önbellekte bulunursa tüm ağır AI aşamalarını atlar, doğrudan `self.publisher.publish_analysis_completed(project_id, video_id, cached_edl)` çağırır, %100 log basar ve mesajı `basic_ack` ile onaylar.
        5. **Aşama 0 — Ses İyileştirme (%12):** `audio_enhancement` aktifse `self.audio_enhancer.enhance(local_video_path)` ile gürültü temizlenmiş MP3 üretir ve `self.minio.upload_clean_audio(...)` ile MinIO'ya yükler.
        6. **Adım 1 — Tek Kaynak Ses Analizi (%18):** `self.audio_analyzer.analyze(local_video_path)` çağrısıyla 16 kHz mono PCM üzerinden Silero VAD konuşma bölgelerini, 10 ms'lik RMS enerji zarfını ve UI için 1000 noktalı `audio_peaks` dalga formunu çıkarır.
        7. **Faz 3.1 — Paralel Grup 1: STT + Yüz Takibi (%25-%55):** `ThreadPoolExecutor(max_workers=2)` ile iki işi paralel koşturur:
           * `_run_transcribe()`: `self.transcriber.transcribe(clean_audio_path, analysis=analysis, video_id=video_id, on_progress=on_stt_progress)` ile parçalı çoklu-motor STT ve GapFiller çalıştırır.
           * `_run_face()`: Eğer `video_format in (1, 2)` (9:16 veya 1:1) ise `self.face_tracker.track(local_video_path)` ile MediaPipe yüz takibi yapar; 16:9 ise boş liste döner.
        8. **Faz 3.2 — Akıllı Retake Taraması (%65):** `auto_retake` aktifse `self.retake_detector.detect_retakes(clean_audio_path, transcript, analysis=analysis)` ile hatalı tekrar okumaları, yarım başlangıçları ve AI semantik retake'leri tespit eder (`retake_cuts`).
        9. **Jump-Cut v3 (%75):** `auto_jumpcut` aktifse `self.silence_detector.detect_v2(analysis=analysis, transcript_words=transcript.words, existing_cuts=retake_cuts)` çağrısıyla (kelimeler mevcut olduğunda otomatik olarak `detect_v3` motoruna delege edilir) korunan kelimeler arasındaki duraklamaları sıkıştırır (`silence_cuts`).
        10. **Altyazı Segmentlerini Kesim Sınırlarına Göre Güncelleme:** `retake_cuts + silence_cuts` birleştirilir; `self.transcriber.regenerate_segments_with_cuts(words=transcript.words, cuts=all_detected_cuts)` ile kesilen kelimeler altyazıdan çıkarılır ve kesim sınırlarında segmentler bölünür.
        11. **Paralel Grup 2 — Jest Komutları, Viral Klip, Öneriler, B-Roll (%85-%88):** `ThreadPoolExecutor(max_workers=4)` ile dört görevi eşzamanlı yürütür:
            * `_run_commands()`: `gesture_enabled` ise `self.command_engine.detect(local_video_path, transcript)`
            * `_run_repurposing()`: `self.repurposing.analyze(transcript)`
            * `_run_suggestions()`: `self.suggestion_engine.generate_suggestions(transcript)`
            * `_run_broll()`: `auto_broll` ise `self.auto_broll_engine.generate_broll_overlays(transcript, video_format_str=fmt_str)`
        12. **EDL İnşası (%95):** `self.edl_builder.build(...)` ile tüm çıktıları tek bir standart EDL sözlüğünde birleştirir.
        13. **Önbellek & Tamamlanma (%100):** `Config.ENABLE_ANALYSIS_CACHE` aktifse EDL'yi Redis'e yazar (`set_cached_edl`), `self.publisher.publish_analysis_completed(project_id, video_id, edl_dict)` ile .NET Backend'e yayınlar ve `ch.basic_ack` yapar.
        14. **Hata ve Temizlik (`except` / `finally`):** Hata durumunda `PipelineLogger` ile `Failed` bildirir ve `basic_nack(requeue=False)` yapar. `finally` bloğunda `heartbeat.stop()` çağırır ve `TEMP_RETENTION == "after_job"` ise `cleanup_files` ile yerel video/ses dosyalarını siler.
    * **`_extract_audio_peaks(self, audio_path: str, num_peaks: int = 1000) -> list`**
      * **Algoritma:** `AcousticScorer` önbelleğinde ses varsa oradan, yoksa `pydub.AudioSegment.from_file` ile sesi okur, mono float32 dizisine çevirir, `num_peaks` parçaya bölüp her parçanın RMS değerini hesaplar ve `[0, 1]` aralığına normalize edilmiş liste döner.

---

### 2.4. `src/OtoEdit.PythonWorker/consumers/render_consumer.py`
* **Dosyanın Amacı:** RabbitMQ'daki `render-requested` kuyruğunu dinleyerek .NET API'den gelen `RenderRequestedEvent` mesajlarını alır, EDL JSON'a göre `VideoRenderer` ile FFmpeg render işlemini yürütür, üretilen `.mp4` dosyasını MinIO'ya yükler ve `RenderCompletedEvent` yayınlar.
* **Harici Kütüphaneler:** `pika`, `json`, `os`.
* **Sınıflar ve Metotlar:**
  * **`class RenderConsumer`**
    * **`__init__(self) -> None`:** `MinioClient`, `RabbitMQPublisher` ve `VideoRenderer(self.minio)` örneklerini başlatır.
    * **`start(self) -> None`:** RabbitMQ bağlantısını açar, `render-requested` (`RabbitMQConstants.QUEUE_RENDER_REQUESTED`) kuyruğunu tanımlar, `RenderRequestedEvent` ve `OtoEdit.Business.Events:RenderRequestedEvent` fanout exchange'lerine bağlar ve `_on_message` ile dinlemeye başlar.
    * **`_on_message(self, ch, method, properties, body) -> None`**
      * **Adım Adım Algoritma:**
        1. Mesajdan `renderJobId`, `projectId` ve `edlJson` (string ise JSON parse edilir) alanlarını çıkarır.
        2. Teşhis amacıyla `temp/render_{render_job_id}/edl_debug.json` dosyasına EDL'yi kaydeder ve text/image overlay, cut ve segment sayılarını loglar.
        3. `RabbitHeartbeatKeeper` başlatır.
        4. `%10` ilerleme bildirir ve `_resolve_source_video(project_id, video_id, source_url)` ile kaynak videoyu MinIO'dan indirir.
        5. `%30` ilerleme bildirir ve `self.renderer.render(edl_json=edl_json, video_path=local_video_path, output_path=local_output_path, temp_dir=temp_dir)` çağrısıyla FFmpeg render işlemini gerçekleştirir.
        6. `%85` ilerleme bildirir ve `self.minio.upload_render_output(project_id, render_job_id, local_output_path)` ile çıktı videoyu MinIO'ya yükler.
        7. `self.publisher.publish_render_completed(render_job_id, project_id, uploaded_key)` ve `%100` ilerleme mesajını yayınlayıp `ch.basic_ack` yapar.
        8. Hata durumunda `publish_pipeline_error` çağırıp `basic_nack(requeue=False)` yapar; `finally` bloğunda heartbeat'i durdurur ve geçici render klasörünü temizler.
    * **`_resolve_source_video(self, project_id: str, video_id: str, source_url: str) -> str`:** `source_url` yerel diskte mevcutsa doğrudan döner; `s3://` veya bucket yolu içeriyorsa temizleyip `self.minio.download_file(clean_key)` çağırır; boşsa `self.minio.download_video(project_id, video_id)` çağırır.
    * **`_publish_progress(self, render_job_id: str, project_id: str, yuzde: int, mesaj: str) -> None`:** `self.publisher.publish_render_progress(...)` çağrısını güvenli `try/except` bloğunda yapar.

---

## BÖLÜM 3: VERİ MODELLERİ (`src/OtoEdit.PythonWorker/models/`)

### 3.1. `src/OtoEdit.PythonWorker/models/__init__.py`
* **Dosyanın Amacı:** Modeller paketini tanımlar.

---

### 3.2. `src/OtoEdit.PythonWorker/models/command_model.py`
* **Dosyanın Amacı:** Sesli ve el hareketli (multimodal) komutların türlerini ve ayrıştırılmış komut veri yapısını tanımlar.
* **Harici Kütüphaneler:** `enum.Enum`, `dataclasses.dataclass`, `typing.Optional`.
* **Modeller:**
  1. **`class CommandType(str, Enum)`:**
     * `START_MARKER = "start_marker"` (👍 "Başlat")
     * `CUT = "cut"` (👎 "Kes / Durdur")
     * `ADD_TEXT = "add_text"` (✌️ "Buraya {metin} yazısını yaz")
     * `ADD_IMAGE = "add_image"` (🖐️ "Buraya {nesne} resmi koy")
     * `REWIND_CUT = "rewind_cut"` (✊ "{cümle}'ye kadar sil")
  2. **`@dataclass class ParsedCommand`:**
     * Alanlar: `command_type: CommandType`, `timestamp: float`, `start: Optional[float] = None`, `end: Optional[float] = None`, `payload: Optional[str] = None`, `raw_text: Optional[str] = None`.

---

### 3.3. `src/OtoEdit.PythonWorker/models/edl_model.py`
* **Dosyanın Amacı:** .NET Backend ve React Frontend (Timeline Editör) ile Python Worker arasındaki ana veri sözleşmesi olan **EDL (Edit Decision List)** şemasını Pydantic `BaseModel` sınıflarıyla tanımlar (Pydantic yüklü değilse hafif bir fallback `BaseModel` sınıfı içerir).
* **Harici Kütüphaneler:** `pydantic` (`BaseModel`, `Field`).
* **Pydantic Modelleri:**
  1. **`class CutItem(BaseModel)`:**
     * Alanlar: `id: str`, `start: float`, `end: float`, `reason: str` (`"silence"`, `"smart_retake"`, `"gesture_dislike"`, `"command_moment_cut"` vb.), `source: str = "auto"`, `command: Optional[str] = None`.
  2. **`class OverlayItem(BaseModel)`:**
     * Alanlar: `id: str`, `type: str` (`"text"`, `"image"`), `content: Optional[str] = None`, `source: Optional[str] = None`, `font: Optional[str] = "Montserrat-Bold"`, `fontSize: Optional[int] = 48`, `color: Optional[str] = "#FFFFFF"`, `backgroundColor: Optional[str] = "#00000080"`, `timestamp: float`, `duration: float = 5.0`, `animation: Optional[str] = "pop-up"`, `exitAnimation: Optional[str] = "fade"`, `position: List[str] = ["center", "bottom"]`, `positionX: Optional[float] = None`, `positionY: Optional[float] = None`, `scale: Optional[float] = 1.0`, `track_id: Optional[int] = 1`.
     * Tipografi & Rozet Alanları: `strokeColor: Optional[str] = None`, `strokeWidth: Optional[float] = 0.0`, `shadowColor: Optional[str] = None`, `shadowBlur: Optional[float] = None`, `boxStyle: Optional[str] = "none"` (`"none"`, `"pill"`, `"rounded"`, `"badge"`), `boxBgColor: Optional[str] = None`, `boxPadding: Optional[int] = 16`, `borderRadius: Optional[int] = 24`, `allCaps: Optional[bool] = False`, `letterSpacing: Optional[float] = 0.0`.
     * Görsel & AI Arka Plan Alanları: `removeBg: Optional[bool] = False`, `stickerBorder: Optional[bool] = False`, `stickerBorderWidth: Optional[int] = 6`, `stickerBorderColor: Optional[str] = "#FFFFFF"`, `rotation: Optional[float] = 0.0`, `maskShape: Optional[str] = "rect"`, `chromaKeyColor: Optional[str] = None`, `chromaKeySimilarity: Optional[float] = 0.35`.
  3. **`class SuggestionItem(BaseModel)`:**
     * Alanlar: `id: str`, `type: str` (`"text_callout"`, `"image_broll"`), `title: str`, `content: str`, `sourceUrl: Optional[str] = None`, `timestamp: float`, `duration: float = 4.0`, `reason: str`, `status: str = "pending"`.
  4. **`class ViralClipItem(BaseModel)`:**
     * Alanlar: `id: str`, `title: str`, `start: float`, `end: float`, `duration: float`, `targetFormat: str`, `viralityScore: int`, `reason: str`.
  5. **`class RepurposingData(BaseModel)`:**
     * Alanlar: `clips: List[ViralClipItem] = []`, `faceTrackingData: List[Dict[str, Any]] = []`.
  6. **`class SubtitleStyleConfig(BaseModel)`:**
     * Alanlar: `preset: str = "tiktok_yellow"`, `fontFamily: str = "Montserrat-Bold"`, `fontSize: int = 48`, `textColor: str = "#FFFFFF"`, `highlightColor: str = "#FFD700"`, `strokeColor: str = "#000000"`, `strokeWidth: float = 3.0`, `shadowColor: str = "#00000080"`, `shadowDistance: float = 3.0`, `shadowBlur: float = 2.0`, `backgroundColor: Optional[str] = None`, `backgroundPadding: int = 12`, `borderRadius: int = 8`, `verticalPosition: float = 85.0`, `allCaps: bool = False`, `letterSpacing: float = 0.0`.
  7. **`class BackgroundMusicConfig(BaseModel)`:**
     * Alanlar: `url: Optional[str] = None`, `title: Optional[str] = "Arka Plan Müziği"`, `volume: float = 0.25`, `autoDucking: bool = True`, `duckingAmount: float = 0.15`, `fadeIn: float = 1.0`, `fadeOut: float = 2.0`, `loop: bool = True`.
  8. **`class EdlSettings(BaseModel)`:**
     * Alanlar: `targetFormat: str = "16:9"`, `templateId: Optional[str] = None`, `faceTrackingEnabled: bool = True`, `audioEnhancement: bool = True`, `gestureCommandsEnabled: bool = True`, `subtitlesEnabled: bool = True`, `subtitleStyle: Optional[SubtitleStyleConfig] = None`, `backgroundMusic: Optional[BackgroundMusicConfig] = None`.
  9. **`class EdlDocument(BaseModel)`:**
     * Alanlar: `projectId: str`, `videoId: Optional[str] = None`, `sourceVideoUrl: Optional[str] = None`, `duration: float = 0.0`, `settings: EdlSettings`, `transcript: Dict[str, Any]`, `cuts: List[CutItem]`, `overlays: List[OverlayItem]`, `suggestions: List[SuggestionItem]`, `repurposing: RepurposingData`, `template: Dict[str, Any]`, `audioPeaks: Optional[List[float]] = None`.

---

### 3.4. `src/OtoEdit.PythonWorker/models/gesture_model.py`
* **Dosyanın Amacı:** MediaPipe Hands ile algılanan el hareketlerinin (jestlerin) türlerini ve zaman/güven skoru modelini tanımlar.
* **Modeller:**
  1. **`class GestureType(str, Enum)`:** `THUMBS_UP = "thumbs_up"`, `THUMBS_DOWN = "thumbs_down"`, `PEACE_OR_T = "peace_or_t"`, `OPEN_PALM = "open_palm"`, `FIST = "fist"`.
  2. **`@dataclass class GestureResult`:** `gesture_type: GestureType`, `timestamp: float`, `confidence: float = 0.85`.

---

### 3.5. `src/OtoEdit.PythonWorker/models/transcript_model.py`
* **Dosyanın Amacı:** Transkripsiyon çıktısını kelime bazlı zaman damgaları (`WordTimestamp`), altyazı segmentleri (`TranscriptSegment`) ve bütünsel transkript (`TranscriptResult`) olarak temsil eden dataclass modellerini içerir.
* **Modeller:**
  1. **`@dataclass class WordTimestamp`:** `word: str`, `start: float`, `end: float`, `confidence: Optional[float] = 1.0`.
  2. **`@dataclass class TranscriptSegment`:** `start: float`, `end: float`, `text: str`, `words: List[WordTimestamp] = field(default_factory=list)`.
  3. **`@dataclass class TranscriptResult`:** `full_text: str`, `segments: List[TranscriptSegment] = field(default_factory=list)`, `words: List[WordTimestamp] = field(default_factory=list)`, `duration: float = 0.0`.

---

## BÖLÜM 4: ANALİZ PIPELINE MODÜLLERİ (`src/OtoEdit.PythonWorker/pipeline/`)

### 4.1. `src/OtoEdit.PythonWorker/pipeline/__init__.py`
* **Dosyanın Amacı:** Analiz pipeline paketini tanımlar.

---

### 4.2. `src/OtoEdit.PythonWorker/pipeline/acoustic_scorer.py`
* **Dosyanın Amacı:** Ses segmentlerindeki teknik kaliteyi (ses patlaması/clipping, RMS ses seviyesi uygunluğu ve önceki cümleyle enerji sürekliliği) 0-100 arasında puanlayan motordur. In-Memory Caching ile 1 saatlik ses dosyasını RAM'e tek seferde yükleyerek disk I/O darboğazını ortadan kaldırır.
* **Harici Kütüphaneler:** `numpy`, `pydub` (`AudioSegment`).
* **Sınıflar ve Metotlar:**
  1. **`class IAcousticScorer(ABC)`:** `load_audio`, `score_audio_segment` ve `clear_cache` soyut metotlarını tanımlayan arayüz.
  2. **`class AcousticScorer(IAcousticScorer)`:**
     * **`__init__(self, target_sample_rate: int = 16000) -> None`:** Örnekleme hızını ve `_cached_audio`, `_cached_path` alanlarını başlatır.
     * **`load_audio(self, audio_path: str) -> None`:** Dosya zaten `_cached_path` ile aynıysa tekrar yüklemez; değilse uzantısına göre (`from_mp3`, `from_wav`, `from_file`) `AudioSegment` ile belleğe yükler.
     * **`clear_cache(self) -> None`:** `_cached_audio` ve `_cached_path` referanslarını `None` yaparak RAM'i boşaltır.
     * **`score_audio_segment(self, audio_path: str, start_sec: float, end_sec: float, prev_segment_rms: Optional[float] = None) -> Dict[str, float]`:**
       * **Algoritma:**
         1. Süre `<= 0.08` sn ise `_empty_score()` döner. Ses bellekte değilse `load_audio` çağırır.
         2. `self._cached_audio[start_ms:end_ms]` ile RAM üzerinden dilimler, tek kanala (`set_channels(1)`) indirger ve `[-1.0, 1.0]` aralığında `np.float32` örnek dizisine normalize eder.
         3. **Clipping Puanı:** `|samples| >= 0.992` olan örneklerin oranını (`clip_ratio`) hesaplar. `<= 0.0001` ise `100.0`, aksi halde `max(0.0, 100.0 - clip_ratio * 20000.0)`.
         4. **Volume (RMS) Puanı:** `20 * log10(rms)` ile dBFS hesaplar. İdeal aralık olan `[-26.0, -14.0]` dBFS içindeyse `100.0`; `-26`'dan düşükse her dB için `6.25` puan, `-14`'ten yüksekse her dB için `12.5` puan kırar.
         5. **Continuity Puanı:** `prev_segment_rms` verilmişse `max(0.0, 100.0 - abs(current_rms_db - prev_segment_rms) * 8.0)` hesaplar.
         6. **Birleşik Puan:** `0.45 * clipping_score + 0.35 * volume_score + 0.20 * continuity_score` formülüyle hesaplayıp sözlük olarak döner.
     * **`_default_score() -> Dict[str, float]`** ve **`_empty_score() -> Dict[str, float]`:** Statik yardımcı metotlar.

---

### 4.3. `src/OtoEdit.PythonWorker/pipeline/audio_analysis.py`
* **Dosyanın Amacı:** Orijinal videodan FFmpeg borusu (pipe) ile tek seferde 16 kHz mono PCM ses çıkarır, `faster_whisper.vad` (Silero VAD) ile konuşma bölgelerini (`SpeechRegion`), 10 ms pencereli (100 Hz) RMS enerji zarfını ve UI için 1000 noktalı normalize dalga formunu (`peaks`) hesaplar. Hem STT parçalayıcı (`AudioChunker`), hem `WordRefiner`, hem de `SilenceDetector` ve `RetakeDetector` bu tek analiz nesnesinden beslenir.
* **Harici Kütüphaneler:** `subprocess` (`ffmpeg`), `numpy`, `faster_whisper.vad` (`get_speech_timestamps`, `VadOptions`).
* **Veri Yapıları ve Sınıflar:**
  1. **`@dataclass class SpeechRegion`:**
     * Alanlar: `start: float`, `end: float`.
     * Özellik: `duration -> float`: `max(0.0, self.end - self.start)`.
  2. **`@dataclass class AudioAnalysis`:**
     * Alanlar: `duration: float`, `speech_regions: List[SpeechRegion]`, `rms_envelope: np.ndarray`, `peaks: List[float]`, `rms_hop_ms: float = 10.0`, `sample_rate: int = 16000`.
     * **`get_rms_at(self, time_sec: float) -> float`:** Verilen saniyeye karşılık gelen 10 ms indeksindeki RMS değerini döner.
     * **`find_energy_minimum(self, center_sec: float, search_window_sec: float = 0.05, direction: str = "both") -> float`:**
       * **Algoritma:** Kesim noktalarında tık/patlama (click/pop) seslerini önlemek için `center_sec` etrafında RMS enerjisinin en düşük olduğu yerel minimum saniyesini (`np.argmin`) bulur. `direction="backward_only"` ise yalnızca `[center - window, center]` aralığında, `"forward_only"` ise `[center, center + window]` aralığında arama yaparak kesimin konuşma içine taşmasını engeller.
     * **`get_silence_regions(self, min_silence_sec: float = 0.0) -> List[Tuple[float, float]]`:** `speech_regions` arasındaki boşlukları tarayarak `>= min_silence_sec` olan sessizlik aralıklarını `(start, end)` listesi olarak döner.
  3. **`class AudioAnalyzer`:**
     * **`__init__(self, sample_rate: int = 16000) -> None`**
     * **`extract_pcm(self, media_path: str) -> np.ndarray`:** `ffmpeg -v error -i media_path -vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le -` komutunu `subprocess.run` ile çalıştırıp standart çıktıdan (`stdout`) gelen baytları `np.int16`'dan `[-1.0, 1.0]` `np.float32` dizisine dönüştürür.
     * **`analyze(self, media_path: str, vad_threshold: float = None, min_silence_ms: int = None, num_peaks: int = 1000) -> AudioAnalysis`:**
       * **Algoritma:**
         1. `extract_pcm` ile PCM dizisini ve toplam süreyi çıkarır.
         2. `VadOptions(threshold=threshold, min_silence_duration_ms=min_silence, speech_pad_ms=150)` ile Silero VAD çalıştırır ve örnek indekslerini saniyeye çevirerek `SpeechRegion` listesi oluşturur.
         3. PCM dizisini 160 örneklik (10 ms) pencerelere yeniden şekillendirip (`reshape`) her pencerenin karekök ortalamasını (`np.sqrt(np.mean(trimmed ** 2, axis=1))`) alarak `rms_envelope` dizisini üretir.
         4. `rms_envelope`'u `num_peaks` (1000) dilime bölüp her dilimin maksimum değerini alır ve maksimum tepeye bölerek normalize `peaks` listesini oluşturur.

---

### 4.4. `src/OtoEdit.PythonWorker/pipeline/audio_enhancer.py`
* **Dosyanın Amacı:** Videodan sesi ayıklayıp yapay zeka/spektral kapılama (`noisereduce`) veya FFmpeg `afftdn` filtresi ile arka plan gürültüsünü temizleyen motordur.
* **Harici Kütüphaneler:** `subprocess` (`ffmpeg`), `numpy`, `noisereduce`, `pydub` (`AudioSegment`).
* **Sınıflar ve Metotlar:**
  * **`class AudioEnhancer`**
    * **`enhance(self, video_path: str) -> str`**
      * **Algoritma:**
        1. `ffmpeg -i video_path -ac 1 -ar 16000 -vn {stem}_raw.wav -y` ile 16 kHz mono WAV çıkarır.
        2. `pydub.AudioSegment.from_wav` ile okuyup `noisereduce.reduce_noise(y=samples, sr=rate, prop_decrease=0.6)` uygular ve `192k` bitrate ile `{stem}_clean.mp3` olarak dışa aktarır.
        3. Eğer `noisereduce` hata verirse fallback olarak `ffmpeg -i raw_wav -af afftdn=nf=-25 -b:a 192k output_mp3 -y` çalıştırır.
        4. `finally` bloğunda geçici `_raw.wav` dosyasını siler.

---

### 4.5. `src/OtoEdit.PythonWorker/pipeline/auto_broll_engine.py`
* **Dosyanın Amacı:** Transkripti Gemini LLM ile analiz ederek konuşmacının bahsettiği en kritik görsel anları belirler, Pexels API (ve fallback zinciri) üzerinden telifsiz stok fotoğraflar bulur ve bunları doğrudan EDL `OverlayItem` katmanlarına dönüştürür.
* **Harici Kütüphaneler:** `json`, `services.gemini_client.GeminiClient`, `services.pexels_client.PexelsClient`.
* **Sınıflar ve Metotlar:**
  * **`class AutoBrollEngine`**
    * **`__init__(self) -> None`:** `GeminiClient` ve `PexelsClient` başlatır.
    * **`generate_broll_overlays(self, transcript: TranscriptResult, video_format_str: str = "16:9", max_visuals: int = 6) -> List[OverlayItem]`:**
      * **Algoritma:**
        1. Transkript metni boşsa veya süresi `< 5.0` sn ise boş liste döner.
        2. `_extract_visual_moments_with_gemini(transcript)` ile aday B-Roll zamanlarını ve İngilizce arama terimlerini alır.
        3. İki görsel arasında en az `4.0` sn mesafe olmasını zorunlu kılar (`abs(timestamp - ut) < 4.0`).
        4. `self.pexels.search_photo(query=search_query, orientation=orientation)` ile fotoğraf URL'si arar; bulamazsa ilk kelimeyle tekrar dener.
        5. Video formatına göre (`9:16`, `1:1`, `16:9`) konum (`pos_x`, `pos_y`) ve ölçek (`scale`) belirleyerek `track_id=2`, `animation="pop-up"` özellikli `OverlayItem` nesneleri üretir.
    * **`_extract_visual_moments_with_gemini(self, transcript: TranscriptResult) -> List[Dict[str, Any]]`:**
      * **Algoritma:** Gemini'ye ilk 3500 karakterlik transkripti göndererek `[{"timestamp": ..., "duration": ..., "concept": ..., "search_query": ...}]` JSON dizisi ister. Hata durumunda 2 adet güvenli fallback öğesi döner.

---

### 4.6. `src/OtoEdit.PythonWorker/pipeline/edl_builder.py`
* **Dosyanın Amacı:** Tüm analiz motorlarının (Transcriber, SilenceDetector, RetakeDetector, MultimodalCommandEngine, FaceTracker, RepurposingEngine, SuggestionEngine, AutoBrollEngine) çıktılarını birleştirerek nihai `EdlDocument` JSON sözlüğünü inşa eder.
* **Sınıflar ve Metotlar:**
  * **`class EdlBuilder`**
    * **`build(self, project_id: str, video_id: str, transcript: TranscriptResult, silence_cuts: List[CutItem], commands: List[ParsedCommand], face_data: List[Dict[str, Any]], repurposing_data: RepurposingData, suggestions: List[SuggestionItem], video_format: int = 0, extra_cuts: Optional[List[CutItem]] = None, extra_overlays: Optional[List[OverlayItem]] = None, audio_peaks: Optional[List[float]] = None, video_duration: Optional[float] = None) -> Dict[str, Any]`**
      * **Algoritma:**
        1. `silence_cuts` ve `extra_cuts` (`retake_cuts`) listelerini birleştirir; `extra_overlays` (`broll_overlays`) listesini başlatır.
        2. Çoklu-modal `commands` listesindeki her komut için:
           * Komutun söylendiği anı (`cmd.start` -> `cmd.end`) `reason="command_moment_cut"` olarak `cuts` listesine ekler (komut cümlesinin videodan kesilmesi için).
           * `CommandType.CUT` ise `[cmd.timestamp, cmd.timestamp + 5.0]` aralığını `reason="gesture_dislike"` olarak ekler.
           * `CommandType.ADD_TEXT` ise `OverlayItem(type="text", content=cmd.payload, ...)` ekler.
           * `CommandType.ADD_IMAGE` ise `OverlayItem(type="image", content=cmd.payload, ...)` ekler.
        3. `_merge_overlapping_cuts(cuts)` ile çakışan kesimleri türlerini koruyarak düzenler ve tüm kesim ID'lerinin benzersiz olmasını sağlar.
        4. Transkripti JSON uyumlu sözlüğe (`fullText`, `duration`, `segments`) çevirir.
        5. `repurposing_data.faceTrackingData = face_data` atamasını yapar.
        6. `video_duration` parametresi verilmişse (ve `> 0.1` ise) gerçek video süresini korur (transkript fallback modunda `1.0` saniyeye düşse bile video süresinin bozulmasını önler).
        7. `EdlDocument` oluşturup `model_dump()` ile sözlük olarak döner.
    * **`_merge_overlapping_cuts(cuts: List[CutItem]) -> List[CutItem]` (`@staticmethod`)**
      * **Algoritma:**
        1. Kesimleri `silence` (`reason == "silence"`) ve `priority` (`reason != "silence"`, örn. `smart_retake`, `gesture_dislike`, `command_moment_cut`) olarak ikiye ayırır.
        2. Yalnızca **aynı `reason` değerine sahip** çakışan kesimleri kendi içinde birleştirir (`merge_same_reason`).
        3. `silence` kesimlerini `priority` kesimlerinin zaman aralıklarından **çıkarır (kırpar veya böler)**. Böylece kullanıcı Timeline Editör'de bir `smart_retake` kesimini geri aldığında (silip iptal ettiğinde), yanındaki sessizlik kesimi kesik kalmaya devam eder ve retake bloğu sessizliği yutmaz.

---

### 4.7. `src/OtoEdit.PythonWorker/pipeline/face_tracker.py`
* **Dosyanın Amacı:** 9:16 (Dikey) ve 1:1 (Kare) format dönüşümlerinde konuşmacının yüzünü ekranda ortalamak için MediaPipe Face Detection ile yüz koordinatlarını bulan ve kamera titremesini önlemek için **Deadzone + Üstel Hareketli Ortalama (EMA)** filtresi uygulayan motordur.
* **Harici Kütüphaneler:** `cv2` (OpenCV), `mediapipe` (`mp.solutions.face_detection`).
* **Sınıflar ve Metotlar:**
  * **`class FaceTracker`**
    * **`__init__(self, deadzone: float = 0.04, ema_alpha: float = 0.15) -> None`**
    * **`track(self, video_path: str, sample_interval_sec: float = 0.4) -> List[Dict[str, Any]]`**
      * **Algoritma:**
        1. OpenCV `VideoCapture` ile videoyu açar, FPS değerini okur ve her `0.4` saniyede bir kareye (`step_frames = int(fps * sample_interval_sec)`) `cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)` ile atlar.
        2. Kareyi RGB'ye çevirip `FaceDetection(model_selection=1, min_detection_confidence=0.6).process(rgb)` çalıştırır.
        3. Yüz bulunursa ilk tespitin `relative_bounding_box` merkezini (`xmin + width/2`, `ymin + height/2`) alır; bulunamazsa `0.5` varsayar.
        4. `abs(current_face_x - previous_x) > self.deadzone` ise `smoothed_x = current_face_x * ema_alpha + previous_x * (1 - ema_alpha)` uygular; değilse `previous_x`'i korur.
        5. Her örnek için `{"timestamp", "raw_x", "raw_y", "smoothed_crop_x"}` sözlüğü döner.

---

### 4.8. `src/OtoEdit.PythonWorker/pipeline/gesture_detector.py`
* **Dosyanın Amacı:** MediaPipe Hands kullanarak video karelerindeki 21 el eklem noktasını (landmark) analiz eden ve 5 temel el hareketini (`THUMBS_UP`, `THUMBS_DOWN`, `FIST`, `OPEN_PALM`, `PEACE_OR_T`) sınıflandıran motordur. **Smart Windowing** desteği sayesinde tüm videoyu taramak yerine yalnızca sesli komut adaylarının geçtiği zaman pencerelerini OpenCV `seek` ile tarar.
* **Harici Kütüphaneler:** `cv2` (OpenCV), `mediapipe` (`mp.solutions.hands`), `math`.
* **Sınıflar ve Metotlar:**
  * **`class GestureDetector`**
    * **`__init__(self, frame_skip: int = 0, min_confidence: float = 0.0) -> None`**
    * **`detect_gestures(self, video_path: str, target_windows: Optional[List[Tuple[float, float]]] = None) -> List[GestureResult]`:**
      * **Algoritma:** `target_windows` verilmişse her `(win_start, win_end)` penceresi için `cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)` ile doğrudan o kareye atlar ve `frame_skip` (varsayılan 8 karede 1) adımlarla MediaPipe Hands çalıştırır. `target_windows` verilmemişse tüm videoyu `frame_skip` ile tarar.
    * **`classify_landmarks(self, landmarks) -> Optional[GestureType]`:**
      * **Algoritma:** Bilek (`landmarks[0]`) ile işaret parmağı kökü (`landmarks[5]`) arasındaki 3B Öklid mesafesini referans (`ref_dist`) alır:
        * İşaret, orta, yüzük ve serçe parmak uçlarının bileğe uzaklığı `< ref_dist * 1.25` ise `fingers_closed = True`.
        * `thumb_tip.y < index_mcp.y` ve `fingers_closed` -> `GestureType.THUMBS_UP` (👍)
        * `thumb_tip.y > index_mcp.y` ve `fingers_closed` -> `GestureType.THUMBS_DOWN` (👎)
        * Başparmak ucu bileğe `< ref_dist * 0.9` ve `fingers_closed` -> `GestureType.FIST` (✊)
        * Tüm 5 parmak ucu bilekten `> ref_dist * 1.4` uzakta -> `GestureType.OPEN_PALM` (🖐️)
        * İşaret ve orta parmak açık (`> ref_dist * 1.3`), yüzük ve serçe kapalı (`< ref_dist * 1.2`) -> `GestureType.PEACE_OR_T` (✌️)
    * **`_distance(p1, p2) -> float` (`@staticmethod`):** İki landmark arasındaki 3B Öklid mesafesini hesaplar.

---

### 4.9. `src/OtoEdit.PythonWorker/pipeline/multimodal_command_engine.py`
* **Dosyanın Amacı:** Yanlış pozitifleri (konuşmacının doğal el kol hareketlerini veya normal konuşma içi kelimeleri) sıfıra indirmek için **Sesli Komut (`VoiceCommandParser`)** ile **El Hareketini (`GestureDetector`)** `±2.0` saniye (`GESTURE_VOICE_SYNC_TOLERANCE_SECONDS`) tolerans penceresinde eşleştiren çoklu-modal doğrulama motorudur.
* **Sınıflar ve Metotlar:**
  * **`class MultimodalCommandEngine`**
    * **Sabit:** `GESTURE_COMMAND_MAP`: `THUMBS_UP -> START_MARKER`, `THUMBS_DOWN -> CUT`, `PEACE_OR_T -> ADD_TEXT`, `OPEN_PALM -> ADD_IMAGE`, `FIST -> REWIND_CUT`.
    * **`__init__(self, tolerance_seconds: float = GESTURE_VOICE_SYNC_TOLERANCE_SECONDS) -> None`**
    * **`detect(self, video_path: str, transcript: TranscriptResult) -> List[ParsedCommand]`:**
      * **Algoritma:**
        1. Önce metin üzerinden `self.voice_parser.parse_transcript(transcript)` ile sesli komut adaylarını bulur. Hiç sesli komut yoksa MediaPipe'ı hiç çalıştırmadan `[]` döner (%100 görüntü işleme tasarrufu).
        2. Bulunan her sesli komutun `timestamp` değeri etrafında `[ts - tolerance - 0.5, ts + tolerance + 0.5]` hedef pencereleri (`target_windows`) oluşturur.
        3. `self.gesture_detector.detect_gestures(video_path, target_windows=target_windows)` ile yalnızca bu pencerelerde el hareketi arar.
        4. Algılanan jestin beklenen komut türü (`GESTURE_COMMAND_MAP`) ile sesli komutun türü aynıysa ve `abs(g.timestamp - vc.timestamp) <= self.tolerance_seconds` ise komutu onaylar (`Confirmed`).

---

### 4.10. `src/OtoEdit.PythonWorker/pipeline/repurposing_engine.py`
* **Dosyanın Amacı:** Transkripti `GeminiClient.find_viral_clips` ile analiz ederek uzun videodan sosyal medya (Reels / TikTok / YouTube Shorts) için en yüksek etkileşim potansiyeline sahip 30 ve 60-90 saniyelik viral klip adaylarını (`RepurposingData`) çıkaran motordur.
* **Sınıflar ve Metotlar:**
  * **`class RepurposingEngine`**
    * **`__init__(self) -> None`:** `GeminiClient` başlatır.
    * **`analyze(self, transcript: TranscriptResult) -> RepurposingData`:** Gemini'den dönen ham klip sözlüklerini `ViralClipItem` nesnelerine dönüştürür ve `RepurposingData(clips=clip_items)` döner.

---

### 4.11. `src/OtoEdit.PythonWorker/pipeline/retake_detector.py`
* **Dosyanın Amacı:** Akıllı Hatalı Tekrar Eleyici (Smart Retake Detector v3) orkestratörüdür. Deterministik `TakeAligner` motorunu ve LLM tabanlı `TranscriptVerifier` denetçisini birleştirerek tekrar okumaları, cümle içi yeniden başlamaları ve stüdyo outtake'lerini tespit eder, sınırlarını RMS enerji minimumuna yaslar ve `CutItem` listesi üretir.
* **Sınıflar ve Metotlar:**
  * **`class RetakeDetector`**
    * **`ORDINAL_WORDS`:** `{'birinci', 'ikinci', 'üçüncü', 'dördüncü', 'beşinci', 'içinci', 'ilk', 'son'}` (Sıra sayı sıfatı içeren ardışık maddelerin yanlışlıkla retake sanılmasını önler).
    * **`__init__(self, similarity_threshold: float = 0.75, transcript_verifier: Optional[TranscriptVerifier] = None) -> None`:** `TakeAligner`, `AcousticScorer` ve `TranscriptVerifier` başlatır.
    * **`is_meta_speech(self, text: str) -> bool`:** `self.aligner.is_meta_speech(text)` çağrısına delege eder.
    * **`calculate_similarity(self, text1: str, text2: str) -> float`:** İki metni normalize eder; farklı sıra sayı sıfatları (`ORDINAL_WORDS`) içeriyorlarsa `0.0` döner, aksi halde `difflib.SequenceMatcher` oranı döner.
    * **`detect_retakes(self, audio_path: str, transcript: TranscriptResult, silence_cuts: Optional[List[CutItem]] = None, analysis: Optional[AudioAnalysis] = None, enable_ai_verification: bool = True) -> List[CutItem]`:**
      * **Algoritma:**
        1. `transcript.words` listesini alır; boşsa `transcript.segments` içinden kelimeleri toplar veya segment metnini kelime sayısına göre eşit zaman adımlarına böler.
        2. `self.aligner.detect_retakes(words)` ile deterministik `RetakeCut` listesini alır.
        3. Her kesimin başlangıcını `analysis.find_energy_minimum(c_start, search_window_sec=0.025, direction="backward_only")` ve bitişini `direction="forward_only"` ile sessizliğin içine doğru RMS dip noktasına yaslar.
        4. `enable_ai_verification` aktifse `self.transcript_verifier.audit_transcript(...)` ile Gemini kurgu denetçisinden gelen ek semantik kesimleri ekler.
        5. Kesimleri sıralayıp çakışanları birleştirerek `CutItem` listesi döner.

---

### 4.12. `src/OtoEdit.PythonWorker/pipeline/take_aligner.py`
* **Dosyanın Amacı:** Kelime zaman damgaları ve duraklama sınırları üzerinden sağdan sola (Right-Anchored) hizalama yaparak hatalı okumaları (retakes), cümle içi yeniden başlamaları (restarts), yarım başlangıçları (false starts), stüdyo içi meta-konuşmaları ("başa sar", "olmadı" vb.) ve Whisper sessizlik halüsinasyonlarını deterministik olarak tespit eden motordur. Her zaman **son (başarılı) take korunur**, önceki başarısız denemeler kesilir.
* **Harici Kütüphaneler:** `re`, `difflib`, `dataclasses`.
* **Veri Yapıları ve Sınıflar:**
  1. **`@dataclass class WordRef`:** `word: str`, `start: float`, `end: float`, `confidence: float = 1.0`, `index: int = 0`.
  2. **`@dataclass class SpeechChunk`:** `words: List[WordRef]`, `start: float`, `end: float`, `text: str`, `index: int`.
  3. **`@dataclass class RetakeCut`:** `start: float`, `end: float`, `reason: str`, `command: str`, `removed_words: List[str]`.
  4. **`class TakeAligner`:**
     * **Sabitler:** `CONNECTORS` (`{"hatta", "yani", "fakat", ...}`), `META_PATTERNS` (`başa sar`, `baştan al`, `olmadı`, `konuşamadık`, `pardon` vb.), `HALUCINATION_PATTERNS` (`altyazı m.k.`, `abone ol`, `mısır, diber, çay`, `mk`).
     * **`__init__(self, chunk_gap_threshold: float = 0.50, similarity_threshold: float = 0.75, tail_coverage_threshold: float = 0.55, max_lookback_words: int = 30, max_lookback_sec: float = 25.0, max_cut_duration: float = 40.0) -> None`**
     * **`normalize_word(text: str) -> str` (`@staticmethod`):** Türkçe `İ->i`, `I->ı`, `â->a`, `î->i`, `û->u` dönüşümü ve noktalama temizliği yapar.
     * **`is_word_match(self, w1: str, w2: str) -> bool`:**
       * **Algoritma (Türkçe Sondan Eklemeli Dil Koruması):** İki kelimenin normalize halleri aynıysa `True`. Uzunluk farkı `> 3` ise `False`. `SequenceMatcher` oranı `< similarity_threshold` (0.75) ise `False`. Ayrıca kökleri farklı ama ekleri aynı kelimelerin ("hükümlerinin" vs "bölümlerinin") eşleşmesini önlemek için **ilk 3 harfin aynı olması (`prefix_match`) VEYA (`ratio >= 0.80` ve yaklaşık edit mesafesinin `<= 1` olması)** şartını arar.
     * **`is_meta_speech(self, text: str) -> bool`** ve **`is_hallucination(self, text: str) -> bool`:** Regex desenleriyle kontrol yapar.
     * **`split_into_chunks(self, words: List[WordRef]) -> List[SpeechChunk]`:** Ardışık kelimeler arasındaki boşluk `>= chunk_gap_threshold` (`0.50` sn) olduğunda yeni bir `SpeechChunk` konuşma öbeği başlatır.
     * **`detect_retakes(self, raw_words: List[Any]) -> List[RetakeCut]`:**
       * **3 Aşamalı Algoritma:**
         1. **Aşama 1 (Meta Konuşma & Halüsinasyon):** `is_meta_speech` veya `is_hallucination` olan öbekleri doğrudan `RetakeCut` olarak işaretler.
         2. **Aşama 2 (Sağdan Sola Restart/Retake Hizalama):** Her `r_chunk` (başarılı aday okuma) için başındaki 0-2 bağlacı (`CONNECTORS`) es geçerek `r_probe_words` alır. Geriye doğru `max_lookback_words` (30 kelime) ve `max_lookback_sec` (25 sn) içindeki `prior_words` havuzunu toplar. `prior_words` içinde `r_probe_words` başlangıcıyla eşleşen (`k >= 2` kelime veya `k == 1` ve `>= 4` harfli kelime) ve kuyruk kapsaması (`tail_coverage >= 0.55`) sağlayan en yüksek puanlı başlangıcı bulur. Kesim aralığını **yalnızca elenen kelimeleri kapsayacak şekilde** (`match_start_word.start` -> `max(rw.end) + 0.02`) oluşturur; son elenen kelime ile yeni okuma arasındaki duraklamayı Jump-Cut (`silence`) motoruna bırakır. Ayrıca önceki korunan kelimenin kuyruğu kesimle örtüşüyorsa kesim başlangıcını `overlapping_kept_end + 0.01` noktasına iter.
         3. **Aşama 3 (Yarım Başlangıçlar / False Starts):** `<= 3` kelimelik kısa bir öbekten sonra `>= 2.0` sn duraklama varsa, cümle sonu noktalamasıyla bitmiyorsa ve ilk kelimesi sonraki öbeğin ilk/ikinci kelimesiyle eşleşiyorsa (`is_repeat`), bu yarım başlangıcı keser.

---

### 4.13. `src/OtoEdit.PythonWorker/pipeline/transcript_verifier.py`
* **Dosyanın Amacı:** Deterministik `TakeAligner`'ın yakalayamadığı anlamsal tekrarları (`semantic_retake` — aynı düşüncenin farklı kelimelerle yeniden kurulması), yarım bırakılmış cümleleri (`aborted_sentence`) ve yetim kelime kırıntılarını (`orphaned_fragment`) Gemini LLM ile denetleyip `CutItem` listesine dönüştüren motordur.
* **Sınıflar ve Metotlar:**
  * **`class TranscriptVerifier`**
    * **`__init__(self, gemini_client: Optional[GeminiClient] = None) -> None`**
    * **`audit_transcript(self, transcript: TranscriptResult, analysis: Optional[AudioAnalysis] = None, existing_cuts: Optional[List[CutItem]] = None) -> List[CutItem]`:**
      * **Algoritma:**
        1. `existing_cuts` ile `%80`'den fazla örtüşen segmentleri eler.
        2. Kalan aday segmentleri `BATCH_SIZE = 100` (`OVERLAP = 10`) pencereler halinde `self.gemini.audit_transcript_coherence(batch)` metoduna gönderir.
        3. Gemini'nin elenmesini önerdiği her segmenti kelime sınırlarına (`seg.words[0].start` -> `seg.words[-1].end`) ve `analysis.find_energy_minimum(..., search_window_sec=0.06)` ile RMS dip noktalarına oturtarak `source="ai_verifier"` özellikli `CutItem` üretir.

---

### 4.14. `src/OtoEdit.PythonWorker/pipeline/word_refiner.py`
* **Dosyanın Amacı:** Whisper ve Groq gibi STT motorlarının uzun duraklamalarda, nefes alışlarda veya kumanda tıklarında kelime zaman damgalarını aşırı uzatmasını (örneğin 0.5 saniyelik bir kelimeyi 7-8 saniyelik sessizlikle birlikte tek kelime gibi etiketlemesini) önleyerek kelime sınırlarını gerçek ses fonasyonuna (RMS enerji zarfına) kilitleyen iki aşamalı sinyal işleme modülüdür.
* **Harici Kütüphaneler:** `numpy`.
* **Sabitler:** `LONG_WORD_SEC = 0.65`, `CLUSTER_MARGIN_SEC = 0.05`, `MAX_TAIL_EXTEND_SEC = 0.25`, `MAX_HEAD_EXTEND_SEC = 0.15`, `NEIGHBOR_GUARD_SEC = 0.01`.
* **Fonksiyonlar:**
  1. **`compute_thresholds(analysis) -> Optional[Tuple[float, float]]`:**
     * **Algoritma:** VAD konuşma bölgelerindeki medyan RMS enerjisini (`med_speech`) ve tüm sesin 10. yüzdelik gürültü tabanını (`floor_rms`) hesaplar. Konuşma çekirdeği için `high = max(0.012, floor_rms + 0.12 * (med_speech - floor_rms))` ve yumuşak harf kuyrukları için `low = min(max(0.004, floor_rms + 0.04 * (med_speech - floor_rms)), high * 0.6)` eşik çiftini döner.
  2. **`_speech_clusters(w_rms: np.ndarray, thresh: float, hop_sec: float) -> List[Tuple[int, int]]`:**
     * **Algoritma:** Bir kelimenin RMS dilimi içinde `>= thresh` olan kesintisiz enerji kümelerini (60 ms / 6 frame düşüş toleransıyla) bulur, `>= 100 ms` olanları süzer ve kelime içi sessiz ünsüz kapanmalarını (`< 160 ms` boşlukları) tek kümede birleştirir.
  3. **`refine_word_boundaries(spans: List[Tuple[float, float]], analysis, duration: Optional[float] = None, texts: Optional[List[str]] = None) -> List[Tuple[float, float]]`:**
     * **Algoritma:**
       * **Aşama 1 (Küme Kırpması — Yalnızca `> 0.65s` kelimeler):** Kelime aralığındaki konuşma kümelerini (`_speech_clusters`) çıkarır. Birden fazla küme varsa komşu kelimelere olan mesafeye (`dist_prev <= 0.15` ise ilk küme, `dist_next <= 0.15` ise son küme) ve harf sayısına göre beklenen kelime süresine (`expected = max(0.25, 0.06 * harf_sayısı)`) bakarak gerçek konuşma kümesini seçer ve `±0.05s` (`CLUSTER_MARGIN_SEC`) pay bırakarak şişmiş sessizliği kelimeden kesip atar.
       * **Aşama 2 (Histerezis ile Kenar Koruması — Tüm kelimeler):** Kelime sonlarındaki yumuşak ünsüzlerin (`-r, -s, -ş`) kesim tarafından yutulmasını önlemek için kelime sonunu ileri doğru `MAX_TAIL_EXTEND_SEC` (`0.25s`), kelime başını geriye doğru `MAX_HEAD_EXTEND_SEC` (`0.15s`) sınırına kadar (komşu kelimeye `0.01s` mesafe bırakarak) `rms >= low` olduğu sürece genişletir (30 ms / 3 frame üst üste düşüşte durur).

---

### 4.15. `src/OtoEdit.PythonWorker/pipeline/silence_detector.py`
* **Dosyanın Amacı:** Videodaki duraklamaları ve sessizlikleri kesen **Jump-Cut (v3, v2 ve legacy)** motorudur.
* **Harici Kütüphaneler:** `numpy`, `pydub` (yalnızca legacy modda).
* **Sınıflar ve Metotlar:**
  * **`class SilenceDetector`**
    * **`__init__(self, min_silence_len: int = 0, silence_thresh: int = 0, padding_sec: float = 0.0, pad_lead_sec: float = 0.0, pad_trailing_sec: float = 0.0, engine: str = None) -> None`:** Asimetrik nefes paylarını (`pad_lead_sec=0.35s`, `pad_trailing_sec=0.20s`), `word_guard_sec=0.15s` ve `min_island_sec=0.30s` parametrelerini yapılandırır.
    * **`detect(...) -> List[CutItem]`:** `engine == "legacy"` ise `_detect_legacy`, `transcript_words` varsa `detect_v3`, yoksa `detect_v2` çalıştırır.
    * **`detect_v3(self, audio_path: Optional[str] = None, analysis: Optional[AudioAnalysis] = None, transcript_words: Optional[List[Any]] = None, existing_cuts: Optional[List[CutItem]] = None) -> List[CutItem]`:**
      * **Adım Adım Jump-Cut v3 Algoritması:**
        1. `existing_cuts` (`retake_cuts`) içine düşmeyen **korunan kelimeleri (`preserved_words`)** ayıklar.
        2. Video başında ilk korunan kelimedeki boşluk `>= 0.40s` (`MIN_GAP`) ise `(0.0, first_ws - 0.16)` kesimi ekler.
        3. Korunan ardışık kelimeler arasındaki boşluk (`gap = w2_s - run_end`) `>= 0.40s` ise:
           * Cümle sonu olup olmadığını (`w1_txt` noktalama ile bitiyor mu, `gap >= 1.5s` mi veya `w2_txt` büyük harfle mi başlıyor) kontrol eder.
           * Kelime sonu sönümlenme payı (`pad_trail`): cümle sonunda `0.28s`, cümle içinde `0.22s`.
           * Sonraki kelime başı atak payı (`pad_lead`): cümle başında `0.18s`, cümle içinde `0.14s`.
           * `[run_end + pad_trail, w2_s - pad_lead]` aralığı `>= 0.08s` ise aday sessizlik olarak ekler.
        4. Video sonu boşluğu `>= 0.40s` ise `(last_we + 0.28, analysis.duration)` ekler.
        5. **Retake Çıkarma (`_subtract_intervals`):** Retake aralıklarını aday sessizliklerden çıkarır; böylece retake blokları yalnızca elenen kelimeleri, `silence` blokları ise aradaki boşlukları temsil eder.
        6. **Akustik Güvenlik Ağı (`_protect_speech_edges`):** STT kelime zamanı kaymış olsa bile kesim kenarlarının yakınında (`edge_zone=0.45s`) `>= 0.10s` süren sürekli konuşma enerjisi varsa kesim kenarını konuşmanın dışına iter (`pad_after=0.22s`, `pad_before=0.14s`).
        7. **RMS Minimumuna Tek Yönlü Yaslama:** Kesim başlangıcını `direction="forward_only"`, kesim bitişini `direction="backward_only"` ile `±30ms` içinde RMS minimumuna oturtur.
    * **`detect_v2(...) -> List[CutItem]`:** Kelime damgaları varsa doğrudan `detect_v3`'e delege eder. Kelime yoksa yalnızca Silero VAD boşluklarını alır, `< 300ms` (`min_island_sec`) yetim ses adacıklarını birleştirir, `< 700ms` (`min_silence_ms`) doğal nefes aralarını korur, asimetrik padding (`pad_trailing_sec`, `pad_lead_sec`) ve kelime koruma kalkanı (`word_guard_sec`) uygular, ardından RMS minimumuna yaslar.
    * **`_protect_speech_edges(...) -> Tuple[float, float]` (`@staticmethod`):** Kesim aralığındaki RMS zarfını tarayıp kenarlara yakın konuşma kümelerini korur.
    * **`_merge_intervals(...)`** ve **`_subtract_intervals(...)`:** Aralık birleştirme ve fark alma yardımcı metotları.
    * **`_detect_legacy(self, audio_path: str) -> List[CutItem]`:** `pydub.silence.detect_silence` tabanlı eski sessizlik algılayıcı.

---

### 4.16. `src/OtoEdit.PythonWorker/pipeline/suggestion_engine.py`
* **Dosyanın Amacı:** Transkriptten `GeminiClient.generate_content_suggestions` ile B-Roll görsel (`image_broll`) ve vurgu yazısı (`text_callout`) önerileri üreten, görsel önerileri için `PexelsClient.search_photo` ile gerçek fotoğraf URL'si bulan ve kullanıcı onayına sunulmak üzere `status="pending"` durumunda `SuggestionItem` listesi döndüren motordur.
* **Sınıflar ve Metotlar:**
  * **`class SuggestionEngine`:** `__init__(self)` ve `generate_suggestions(self, transcript: TranscriptResult) -> List[SuggestionItem]`.

---

### 4.17. `src/OtoEdit.PythonWorker/pipeline/voice_command_parser.py`
* **Dosyanın Amacı:** Transkript segmentlerini Türkçe düzenli ifadeler (Regex) ile tarayarak 5 komuttan (`START_MARKER`, `CUT`, `ADD_TEXT`, `ADD_IMAGE`, `REWIND_CUT`) birine uyan sesli komut adaylarını ve metin/görsel argümanlarını (`payload`) çıkaran motordur.
* **Sınıflar ve Metotlar:**
  * **`class VoiceCommandParser`:** `PATTERNS` (5 adet derlenmiş regex) ve `parse_transcript(self, transcript: TranscriptResult) -> List[ParsedCommand]`.

---

### 4.18. `src/OtoEdit.PythonWorker/pipeline/transcriber.py`
* **Dosyanın Amacı:** Yüksek doğruluklu çok katmanlı STT (Speech-to-Text) orkestratörüdür. `AudioAnalysis` nesnesinden beslenir, `AudioChunker` ile sesi VAD sessizlik sınırlarından böler, `STTEngineChain` ile motor zincirinde transkribe eder, `GapFiller` ile atlanan kelimeleri kurtarır, `clean_and_trim_words` (`word_refiner`) ile halüsinasyonları temizleyip kelime sınırlarını gerçek fonasyona kilitler ve altyazı mikro-segmentlerini üretir.
* **Sınıflar ve Metotlar:**
  * **`class Transcriber`**
    * **`__init__(self, engine_chain: Optional[STTEngineChain] = None) -> None`:** `STTEngineChain`, `AudioChunker(max_chunk_sec=Config.STT_CHUNK_MAX_SEC)` ve `GapFiller(min_gap_sec=0.40)` başlatır.
    * **`transcribe(self, audio_path: str, analysis: Optional[AudioAnalysis] = None, video_id: str = "", on_progress: Optional[Callable[[int, int, str], None]] = None) -> TranscriptResult`:**
      * **Algoritma:**
        1. `analysis` verilmemişse `AudioAnalyzer().analyze(audio_path)` çalıştırır.
        2. `self.chunker.split(audio_path, analysis)` ile sesi VAD sessizlik noktalarından MP3 parçalarına böler.
        3. Her konuşmalı parçayı `self.chain.transcribe_chunk(chunk)` ile çözümler. Bir parça hata verse bile (`try/except`) önceki parçalardan toplanan kelimeleri korur (parça bazlı hata izolasyonu).
        4. `self.gap_filler.fill_gaps(media_path=audio_path, analysis=analysis, words=all_words, chain=self.chain)` ile kelimesiz kalan VAD konuşma bölgelerini yeniden transkribe ederek kayıp kelimeleri kurtarır.
        5. `self.clean_and_trim_words(all_words, analysis)` ile halüsinasyonları (`"altyazı"`, `"mısır"`, `"diber"`) filtreler ve `refine_word_boundaries` ile kelime sınırlarını RMS zarfına kilitler.
        6. `_words_to_segments(all_words, max_words=6, max_duration=3.0)` ile kelimeleri altyazı segmentlerine böler ve `TranscriptResult` döner. `finally` bloğunda geçici MP3 parçalarını siler.
    * **`clean_and_trim_words(words: List[Word], analysis: Optional[AudioAnalysis] = None) -> List[Word]` (`@staticmethod`):** Halüsinasyon kelimelerini eler ve `refine_word_boundaries` uygular.
    * **`regenerate_segments_with_cuts(words: List[Any], cuts: Optional[List[Any]] = None, max_words: int = 6, max_duration: float = 3.0) -> List[TranscriptSegment]` (`@staticmethod`):**
      * **Algoritma:** Kesim (`cuts`) aralıklarının içine düşen kelimeleri eler; kalan kelimeleri gruplarken iki kelime arasında kesim varsa (`has_cut_between`) veya `gap >= 0.8s` ise veya noktalama/kelime/süre sınırına ulaşıldıysa segmenti bölerek altyazının kesim sınırlarını aşmasını önler.
    * **`_words_to_segments(...)` (`@staticmethod`)** ve **`_generate_fallback_transcript(...)` (`@staticmethod`)**.

---

## BÖLÜM 5: STT MOTOR ZİNCİRİ (`src/OtoEdit.PythonWorker/pipeline/stt/`)

### 5.1. `src/OtoEdit.PythonWorker/pipeline/stt/__init__.py`
* **Dosyanın Amacı:** STT alt paketini tanımlar.

---

### 5.2. `src/OtoEdit.PythonWorker/pipeline/stt/base.py`
* **Dosyanın Amacı:** Tüm STT motorlarının ortak veri modellerini (`Word`, `TranscriptionResult`), zaman ayrıştırıcı yardımcısını (`parse_offset_sec`) ve soyut motor arayüzünü (`BaseSTTEngine`) tanımlar.
* **Veri Yapıları, Fonksiyonlar ve Sınıflar:**
  1. **`@dataclass class Word`:** `word: str`, `start: float`, `end: float`, `confidence: float = 1.0`. Özellik: `duration -> float`, metot: `to_dict() -> dict`.
  2. **`@dataclass class TranscriptionResult`:** `words: List[Word]`, `text: str`, `engine: str`, `duration_sec: float = 0.0`. Metot: `to_dict() -> dict`.
  3. **`parse_offset_sec(val: str | float | int) -> float`:** Gemini API'nin döndürdüğü `"5.600s"` veya `"8s"` gibi offset dizgilerini `float` saniyeye çevirir.
  4. **`class BaseSTTEngine(ABC)`:** `is_available(self) -> bool` ve `transcribe_chunk(self, chunk: AudioChunk) -> List[Word]` soyut metotlarını tanımlar.

---

### 5.3. `src/OtoEdit.PythonWorker/pipeline/stt/chunker.py`
* **Dosyanın Amacı:** Uzun videoları (örn. 1 saat) STT motorlarının zaman aşımı ve token/boyut sınırlarına takılmaması için hedef uzunlukta (`STT_CHUNK_MAX_SEC = 600` sn / 10 dk) parçalara böler. Kelimelerin ortasından kesmemek için parça sınırlarını hedef noktanın `±60` sn içindeki **en uzun VAD sessizliğinin tam ortasına** yerleştirir ve 16 kHz mono 32 kbps MP3 olarak keser.
* **Harici Kütüphaneler:** `subprocess` (`ffmpeg`).
* **Veri Yapıları ve Sınıflar:**
  1. **`@dataclass class AudioChunk`:** `index: int`, `start_sec: float`, `end_sec: float`, `audio_path: str`, `has_speech: bool = True`. Özellik: `duration -> float`.
  2. **`class AudioChunker`:**
     * **`__init__(self, max_chunk_sec: float = None) -> None`**
     * **`calculate_split_points(self, analysis: AudioAnalysis) -> List[float]`:** Toplam süre `<= max_chunk_sec` ise `[duration]` döner. Değilse her `target = current_pos + max_chunk_sec` etrafındaki `[target - 60, target + 60]` penceresinde en uzun VAD sessizliğinin orta noktasını bulur; sessizlik yoksa `analysis.find_energy_minimum(target, search_window_sec=3.0)` seçer.
     * **`split(self, media_path: str, analysis: AudioAnalysis, output_dir: Path = None) -> List[AudioChunk]`:** Her parça aralığında `analysis.speech_regions` kesişimi (`has_speech`) olup olmadığını kontrol eder. Konuşma varsa `ffmpeg -y -ss chunk_start -to chunk_end -i media_path -vn -acodec libmp3lame -ar 16000 -ac 1 -b:a 32k chunk_file` ile MP3 üretir; tamamen sessizse FFmpeg ve STT çalıştırmaz.
     * **`cleanup_chunks(chunks: List[AudioChunk]) -> None` (`@staticmethod`):** Geçici MP3 dosyalarını siler.

---

### 5.4. `src/OtoEdit.PythonWorker/pipeline/stt/rate_limiter.py`
* **Dosyanın Amacı:** Birden fazla Gemini API anahtarı arasında Round-Robin rotasyon yapan, dakika başına istek sınırını (RPM kayan pencere) takip eden ve HTTP 429 kota aşımlarında `retryDelay` süresince ilgili anahtarı soğumaya (cooldown) alan thread-safe hız sınırlayıcıdır.
* **Sınıflar ve Metotlar:**
  1. **`class KeyState`:**
     * `__init__(self, key: str, max_rpm: int = 3)`: Anahtar başına istek zaman damgalarını (`request_timestamps`), soğuma bitiş zamanını (`cool_down_until`) ve `threading.Lock()` tutar.
     * `is_cooling_down(self, now: float) -> bool`
     * `available_in_sec(self, now: float) -> float`: Anahtarın hazır olmasına kalan saniyeyi döner (soğuma süresi veya son 60 saniyedeki en eski isteğin dolma süresi; hazırsa `0.0`).
     * `record_request(self, now: float) -> None`
     * `mark_rate_limited(self, now: float, retry_delay_sec: float = 20.0) -> None`
  2. **`class GeminiKeyRotator`:**
     * `__init__(self, api_keys: List[str], max_rpm: int = 3, max_wait_sec: float = None)`
     * `get_available_key(self, wait_if_needed: bool = True) -> Optional[str]`: Uygun anahtar varsa anında döner. Tüm anahtarlar dolu/soğumada ise ve en yakın hazır olma süresi kalan bekleme bütçesinden (`max_wait_sec - elapsed`) küçükse `min(best_wait + 0.1, 5.0)` sn uyuyarak bekler; bütçeyi aşıyorsa `None` döner (böylece `STTEngineChain` beklemeden bir sonraki motora geçer).
     * `report_429(self, key: str, retry_delay_sec: float = 20.0) -> None`: İlgili anahtarı soğumaya alır.

---

### 5.5. `src/OtoEdit.PythonWorker/pipeline/stt/gemini_transcribe.py`
* **Dosyanın Amacı:** Google'ın `gemini-3.5-transcribe` modelini resmi REST API üzerinden `VERBATIM` ve `word_timestamp=True` modunda çağıran birincil STT motorudur. Arapça/Osmanlıca/yabancı kökenli ifadelerin (ör. "Bismillahirrahmanirrahim") atlanmaması için kasıtlı olarak `language_codes` parametresi göndermez.
* **Harici Kütüphaneler:** `urllib.request`, `base64`, `json`, `re`.
* **Sınıflar ve Metotlar:**
  * **`class GeminiTranscribeEngine(BaseSTTEngine)`**
    * **`__init__(self, api_keys: List[str] = None, rotator: GeminiKeyRotator = None) -> None`**
    * **`is_available(self) -> bool`:** En az bir API anahtarı varsa `True`.
    * **`parse_response(self, data: dict, chunk_offset: float = 0.0) -> List[Word]`:** `candidates[0].content.parts` içindeki `audioTranscription.words` dizisini okur, `startOffset` ve `endOffset` değerlerini `parse_offset_sec` ile saniyeye çevirip `chunk_offset` ekleyerek `Word` listesi döner.
    * **`transcribe_chunk(self, chunk: AudioChunk, max_retries: int = 3) -> List[Word]`:** MP3 dosyasını Base64'e kodlar, `GeminiKeyRotator`'dan anahtar alır ve `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-transcribe:generateContent` adresine POST atar. HTTP 429 alırsa yanıttaki `retryDelay` süresini regex ile okuyup `rotator.report_429` çağırır ve yeniden dener.

---

### 5.6. `src/OtoEdit.PythonWorker/pipeline/stt/groq_engine.py`
* **Dosyanın Amacı:** Groq Cloud API (`https://api.groq.com/openai/v1/audio/transcriptions`) üzerinden `whisper-large-v3-turbo` modelini `verbose_json` ve `timestamp_granularities[]="word"` parametreleriyle çağıran ultra hızlı ikincil STT motorudur.
* **Harici Kütüphaneler:** `urllib.request`, `uuid`, `json`.
* **Sınıflar ve Metotlar:**
  * **`class GroqEngine(BaseSTTEngine)`:** `__init__`, `is_available`, `transcribe_chunk(self, chunk: AudioChunk) -> List[Word]` (Multipart form-data gövdesini `bytearray` ile inşa edip gönderir ve dönen kelimelere `chunk.start_sec` offset'ini ekler).

---

### 5.7. `src/OtoEdit.PythonWorker/pipeline/stt/proxy_gemini.py`
* **Dosyanın Amacı:** Yerel Antigravity Manager Proxy (`http://host.docker.internal:8045/v1/chat/completions`) üzerinden `gemini-3.8-flash-tiered` modeline Base64 `input_audio` gönderen üçüncül yedek STT motorudur.
* **Sınıflar ve Metotlar:**
  * **`class ProxyGeminiEngine(BaseSTTEngine)`:** `__init__`, `is_available`, `transcribe_chunk(self, chunk: AudioChunk) -> List[Word]` (Dönen düz metni kelimelere ayırıp `chunk.duration` süresine orantılı olarak zaman damgası dağıtır).

---

### 5.8. `src/OtoEdit.PythonWorker/pipeline/stt/local_whisper.py`
* **Dosyanın Amacı:** Harici internet bağlantısı veya API kotası gerektirmeyen, `faster-whisper` ve `ctranslate2` kullanarak yerel GPU (`cuda`, `int8_float16`) veya CPU (`int8`, 4 thread) üzerinde çalışan tam çevrimdışı dördüncül yedek STT motorudur.
* **Harici Kütüphaneler:** `ctranslate2`, `faster_whisper` (`WhisperModel`).
* **Sınıflar ve Metotlar:**
  * **`class LocalWhisperEngine(BaseSTTEngine)`:**
    * `__init__(self, model_name: str = None)`
    * `is_available(self) -> bool`: Her zaman `True` döner.
    * `_get_model(self)`: Modeli tembel (lazy) yükler; `large-v3-turbo` yüklenemezse `"base"` modeline düşer.
    * `transcribe_chunk(self, chunk: AudioChunk) -> List[Word]`: `model.transcribe(chunk.audio_path, word_timestamps=True, vad_filter=False, condition_on_previous_text=False)` çalıştırır ve kelime zamanlarına `chunk.start_sec` ekler.

---

### 5.9. `src/OtoEdit.PythonWorker/pipeline/stt/engine_chain.py`
* **Dosyanın Amacı:** `Config.STT_ENGINE_ORDER` (`gemini_transcribe -> groq -> proxy_gemini -> local_whisper`) sırasındaki motorları yöneten Failover (Hata Devretme) zinciridir.
* **Sınıflar ve Metotlar:**
  * **`class STTEngineChain`**
    * **`__init__(self, engine_order: List[str] = None) -> None`:** 4 motoru başlatır ve kotası tükenen motorları izlemek için `self.exhausted_engines: set` tutar.
    * **`_init_engines(self) -> None`**
    * **`transcribe_chunk(self, chunk: AudioChunk) -> Tuple[List[Word], str]`:** Sırayla motorları dener. Bir motor `"quota exceeded"`, `"rate limit"`, `"429"` veya `"kota"` hatası verirse o motoru `self.exhausted_engines` kümesine ekleyerek kalan parçalarda tekrar vakit kaybetmesini önler ve anında sıradaki motora geçer.

---

### 5.10. `src/OtoEdit.PythonWorker/pipeline/stt/gap_filler.py`
* **Dosyanın Amacı:** Silero VAD'ın konuşma tespit ettiği (`>= 0.40s`), ancak birincil STT motorunun hiçbir kelime döndürmediği şüpheli boşlukları tespit edip o küçük aralıkları (`±0.5s` bağlamla) FFmpeg ile keserek `STTEngineChain` üzerinden yeniden transkribe eden ve atlanan kelimeleri kurtaran motordur.
* **Harici Kütüphaneler:** `subprocess` (`ffmpeg`).
* **Sınıflar ve Metotlar:**
  * **`class GapFiller`**
    * **`__init__(self, min_gap_sec: float = 0.40) -> None`**
    * **`find_untranscribed_gaps(self, analysis: AudioAnalysis, words: List[Word]) -> List[Tuple[float, float]]`:** `region.duration >= self.min_gap_sec` olup içinde hiç `Word` bulunmayan `SpeechRegion` aralıklarını döner.
    * **`fill_gaps(self, media_path: str, analysis: AudioAnalysis, words: List[Word], chain: STTEngineChain, temp_dir: Path = None) -> List[Word]`:** En fazla 25 şüpheli boşluğu `[g_start - 0.5, g_end + 0.5]` aralığında MP3 olarak keser, `chain.transcribe_chunk` ile çözümler, üst üste 3 hata alırsa erken çıkar, kurtarılan kelimeleri ana listeyle birleştirip zamana göre sıralar ve `50ms` içindeki mükerrer kelimeleri (`deduped_words`) temizler.

---

## BÖLÜM 6: RENDER MOTORU MODÜLLERİ (`src/OtoEdit.PythonWorker/render/`)

### 6.1. `src/OtoEdit.PythonWorker/render/__init__.py`
* **Dosyanın Amacı:** Render paketini tanımlar.

---

### 6.2. `src/OtoEdit.PythonWorker/render/animation_effects.py`
* **Dosyanın Amacı:** Metin (`.ass`) ve görsel (`ffmpeg overlay`) kaplamaları için giriş/çıkış animasyon etiketlerini ve dinamik FFmpeg koordinat matematik ifadelerini üretir.
* **Sınıflar ve Metotlar:**
  * **`class AnimationEffects`**
    * **`get_ass_tags(animation_type: str, duration_sec: float, pos_x: int = 0, pos_y: int = 0, exit_anim_type: str = "fade") -> str` (`@staticmethod`):**
      * Giriş animasyonları (`fade`, `pop-up`, `slide-left`, `slide-right`, `slide-up`, `slide-down`, `none`) ile çıkış animasyonlarını (`fade`, `scale-out`, `pop-up`, `none`) birleştirerek `\fad(...)`, `\t(0,250,\fscx100\fscy100)`, `\move(x1,y1,x2,y2,0,anim_dur)` gibi ASS kontrol etiketleri üretir.
    * **`get_ffmpeg_overlay_coords(position: Any, base_w: int = 1920, base_h: int = 1080, anim_type: str = "fade", start_time: float = 0.0, duration: float = 5.0) -> Tuple[str, str]` (`@staticmethod`):**
      * FFmpeg `overlay` filtresi için zamana (`t`) bağlı `if(lt(t, ...), ...)` kayma ifadelerini (`slide-left`, `slide-right`, `slide-up`) veya statik koordinatları döner.
    * **`resolve_static_position(position: Any, base_w: int = 1920, base_h: int = 1080) -> Tuple[str, str]` (`@staticmethod`):**
      * `["center", "bottom"]`, `["right", "top"]` gibi konum dizilerini `"40"`, `"main_w-overlay_w-40"`, `"(main_w-overlay_w)/2"` gibi FFmpeg ifadelerine çevirir.

---

### 6.3. `src/OtoEdit.PythonWorker/render/audio_mixer.py`
* **Dosyanın Amacı:** Konuşma ses akışı ile arka plan müziğini (BGM) birleştiren, müzik için sonsuz döngü (`aloop`), giriş/çıkış ses geçişi (`afade`) ve konuşma başladığında müziği otomatik kısan **Sidechain Compression (Auto-Ducking)** filtre grafiğini kuran profesyonel ses mikseridir.
* **Harici Kütüphaneler:** `ffmpeg-python` (`ffmpeg`).
* **Sınıflar ve Metotlar:**
  * **`class AudioMixer`**
    * **`apply_bgm_with_ducking(cls, speech_audio_stream: Any, bgm_file_path: str, total_duration: float, volume: float = 0.25, auto_ducking: bool = True, ducking_amount: float = 0.15, fade_in_sec: float = 1.0, fade_out_sec: float = 2.0) -> Any` (`@classmethod`):**
      * **Algoritma:** BGM dosyasını `aloop(loop=-1, size=2147483647)` ve `volume` filtresinden geçirir, `afade` (in/out) uygular. `auto_ducking=True` ise `ffmpeg.filter([bgm_a, speech_audio_stream], "sidechaincompress", threshold=max(0.02, min(0.25, ducking_amount * 0.6)), ratio=5, attack=150, release=650)` uygular ve ardından `amix(inputs=2, duration="first", dropout_transition=2)` ile konuşma ve müziği birleştirir.

---

### 6.4. `src/OtoEdit.PythonWorker/render/dynamic_subtitle_generator.py`
* **Dosyanın Amacı:** Kelime zaman damgalarından 4'er kelimelik gruplar halinde aktif kelimenin rengini ve boyutunu (`\c&H0000FFFF\fscx110\fscy110`) vurgulayan bağımsız ASS altyazı üreticisidir.
* **Sınıflar ve Metotlar:**
  * **`class DynamicSubtitleGenerator`:** `__init__`, `generate_ass_file(self, transcript: TranscriptResult, output_path: str, video_width: int = 1920, video_height: int = 1080) -> str` ve `_format_ass_time(seconds: float) -> str`.

---

### 6.5. `src/OtoEdit.PythonWorker/render/image_overlay.py`
* **Dosyanın Amacı:** EDL içindeki görsel, B-Roll, sticker ve logo kaplamalarını çözen, gerektiğinde `BackgroundRemoverService` ile AI arka plan silme, chroma key, şekil maskesi ve sticker konturu uygulayan ve bunları Z-Index (`trackId`) sırasına göre FFmpeg `overlay` filtre zincirine bağlayan motordur.
* **Harici Kütüphaneler:** `ffmpeg-python`, `urllib.request`, `urllib.parse`.
* **Sınıflar ve Metotlar:**
  * **`class ImageOverlay`**
    * **`__init__(self, minio_client: Optional[MinioClient] = None) -> None`**
    * **`resolve_image_path(self, source: str, temp_dir: str = "/app/temp") -> Optional[str]`:** Kaynak yerel dosya ise doğrudan döner; MinIO presigned URL (`http` + `"otoedit"`), harici HTTP/HTTPS URL veya `s3://` URI ise yerel `temp_dir` içine indirir.
    * **`apply_image_overlays(self, base_stream: Any, overlays: List[Dict[str, Any]], temp_dir: str = "/app/temp", base_w: int = 1920, base_h: int = 1080) -> Any`:**
      * **Algoritma:**
        1. `type == "image"` olan kaplamaları `trackId` (`track_id`) değerine göre küçükten büyüğe (alttan üste) sıralar.
        2. Her görsel için sırasıyla etkinse: `remove_background`, `apply_chroma_key`, `apply_shape_mask` (`circle` / `rounded`) ve `add_sticker_outline` işlemlerini `BackgroundRemoverService` üzerinden uygular.
        3. Frontend player ile birebir boyut uyumu için `scale_w = int(base_w * (160.0 / 860.0) * scale)` (çift sayıya yuvarlanmış) ile `scale` filtresi ve varsa `rotate` filtresi uygular.
        4. `positionX` / `positionY` (%0-100) verilmişse piksel merkezine, verilmemişse `AnimationEffects.get_ffmpeg_overlay_coords` ifadelerine göre `enable='between(t,start_t,end_t)'` ile `ffmpeg.overlay` düğümünü zincire ekler.

---

### 6.6. `src/OtoEdit.PythonWorker/render/pillow_graphics_engine.py`
* **Dosyanın Amacı:** CapCut ve Premiere Pro tarzı kutucuklu (`pill`, `rounded`, `badge`), konturlu ve yumuşak gölgeli metin rozetlerini **2x süper-örnekleme (supersampling)** ve `LANCZOS` küçültme ile pürüzsüz (antialiased) şeffaf PNG katmanları olarak üreten grafik motorudur.
* **Harici Kütüphaneler:** `PIL` (`Image`, `ImageDraw`, `ImageFont`, `ImageFilter`), `re`.
* **Fonksiyonlar ve Sınıflar:**
  1. **`hex_to_rgba(hex_str: str, default: Tuple[int, int, int, int] = (255, 255, 255, 255)) -> Tuple[int, int, int, int]`:** `#RRGGBB`, `#RRGGBBAA`, `rgb(...)` ve `rgba(...)` renk dizgilerini `(R, G, B, A)` tuple'ına çevirir.
  2. **`class PillowGraphicsEngine`:**
     * **`get_font(cls, font_name: Optional[str] = "Inter", font_size: int = 48) -> ImageFont.FreeTypeFont` (`@classmethod`):** `FONT_PATHS` sözlüğünden sistemdeki `.ttf` font dosyasını bulup yükler; bulunamazsa `DejaVuSans` veya varsayılan fonta düşer.
     * **`render_text_badge(cls, text: str, output_path: str, font_name: str = "Montserrat", font_family: Optional[str] = None, font_size: int = 48, text_color: str = "#FFFFFF", stroke_color: Optional[str] = "#000000", stroke_width: int = 2, shadow_color: Optional[str] = None, box_style: str = "pill", box_bg_color: str = "rgba(0, 0, 0, 0.75)", box_padding: int = 16, border_radius: int = 24, shadow: bool = True, shadow_blur: int = 4, all_caps: bool = False, letter_spacing: int = 0, **kwargs) -> str` (`@classmethod`):**
       * **Algoritma:** Tüm boyutları `ss = 2` (2x supersampling) ile çarpar, satır genişliklerini (`textbbox` ve `letter_spacing`) ölçer, gölge payıyla birlikte RGBA kanvas açar, önce GaussianBlur uygulanmış kutu gölgesini, ardından `rounded_rectangle` ile arka plan kutusunu (`pill` ise yarıçap `box_h // 2`), sonra metin gölgesini ve konturlu metni çizer. Son olarak `getbbox()` ile boşlukları kırpıp `Image.Resampling.LANCZOS` ile 1x hedef boyuta indirgeyerek PNG olarak kaydeder.

---

### 6.7. `src/OtoEdit.PythonWorker/render/template_applier.py`
* **Dosyanın Amacı:** EDL JSON içindeki kurumsal şablon (`template`) ayarlarını (logo ve konuşmacı adı/unvanı alt bandı — Lower Third) okuyarak `overlays` listesine idempotent biçimde (`tpl_logo` ve `tpl_speaker_name` ID'leriyle) ekler.
* **Sınıflar ve Metotlar:**
  * **`class TemplateApplier`:** `enrich_edl_with_template(edl_json: Dict[str, Any]) -> Dict[str, Any]` (`@staticmethod`).

---

### 6.8. `src/OtoEdit.PythonWorker/render/text_overlay.py`
* **Dosyanın Amacı:** EDL içerisindeki metin kaplamalarını (`type == "text"`) ve konuşma altyazılarını (`transcript.segments` + kelime bazlı TikTok/Reels/CapCut karaoke vurgusu) tek bir `.ass` (Advanced SubStation Alpha) dosyasına dönüştüren motordur.
* **Sınıflar ve Metotlar:**
  * **`class TextOverlay`**
    * **`hex_to_ass_color(hex_color: str, default: str = "&H00FFFFFF") -> str` (`@staticmethod`):** `#RRGGBB` veya `#RRGGBBAA` rengini ASS `&HAABBGGRR` (ters BGR sırası) formatına çevirir.
    * **`position_to_ass_alignment(position: Any) -> int` (`@staticmethod`):** Numpad düzeninde (1-9) ASS hizalama kodunu döner (örn. `["center", "bottom"] -> 2`, `["center", "center"] -> 5`, `["right", "top"] -> 9`).
    * **`seconds_to_ass_time(seconds: float) -> str` (`@staticmethod`):** Saniyeyi `H:MM:SS.cs` formatına çevirir.
    * **`generate_ass(cls, overlays: List[Dict[str, Any]], transcript: Optional[Dict[str, Any]] = None, output_path: str = "temp_overlays.ass", play_res_x: int = 1920, play_res_y: int = 1080, subtitle_style: Optional[Dict[str, Any]] = None) -> str` (`@classmethod`):**
      * **Algoritma:**
        1. **Stil Başlığı (`[V4+ Styles]`):** `SubtitleStyleConfig` içindeki `preset` (`tiktok_yellow`, `opaque_banner`, `cinematic_shadow`, `neon_glow`, `custom`), font, renk ve dikey konum (`verticalPosition`) ayarlarına göre `Subtitle` ve `Default` stillerini oluşturur. CSS 96 DPI piksel boyutunu ASS 72 DPI punto boyutuna `96.0 / 72.0` (`4/3`) çarpanıyla birebir ölçekler.
        2. **Metin Overlay'leri:** Her text overlay için `positionX`/`positionY` varsa `\pos(px,py)` (veya kayma animasyonu varsa `\move(...)`), `AnimationEffects.get_ass_tags` etiketleri ve `trackId` katman numarasıyla `Dialogue:` satırı üretir.
        3. **Karaoke / Dinamik Kelime Vurgulu Altyazılar:** Her transkript segmentindeki kelimeler için:
           * İlk kelimeden önce boşluk varsa tüm cümleyi birincil renkte yazar.
           * Her kelimenin okunduğu `[w_start_time, display_end]` aralığında yalnızca o kelimeyi `{\c{highlight_color}\t(0,90,\fscx110\fscy110)}{w_disp}{\c{primary_color}\fscx100\fscy100}` ile renklendirip hafifçe büyüten ayrı bir `Dialogue:` satırı oluşturur. Kelimeler arası `< 0.25s` mikro boşluklarda altyazının titrememesi için `display_end`'i bir sonraki kelimenin başlangıcına uzatır.

---

### 6.9. `src/OtoEdit.PythonWorker/render/timeline_mapper.py`
* **Dosyanın Amacı:** Orijinal videodan kesimler (`cuts`) çıkarıldıktan sonra geriye kalan korunan segmentlere (`keep_segments`) ve FFprobe ile ölçülen gerçek segment sürelerine (`actual_durations`) göre tüm metin/görsel kaplamaların (`overlays`) ve altyazı/karaoke kelime zamanlarının (`transcript`) milisaniye hassasiyetinde yeni video zaman çizgisine haritalanmasını (kaydırılmasını) ve kesilen bölgelerde kalan öğelerin elenmesini sağlar.
* **Sınıflar ve Metotlar:**
  * **`class TimelineMapper`**
    * **`remap_timestamp(t: float, keep_segments: List[Tuple[float, float]], tolerance: float = 0.02, actual_durations: Optional[List[float]] = None) -> Optional[float]` (`@staticmethod`):** Orijinal `t` anı korunan bir segmentin `[start - tolerance, end + tolerance]` aralığındaysa önceki korunan segmentlerin kümülatif süresine (`accumulated_duration`) segment içi `offset = clamped_t - start` ekleyerek yeni zamanı döner; kesilen bölgedeyse `None` döner.
    * **`remap_range(start: float, end: float, keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> Optional[Tuple[float, float]]` (`@staticmethod`):** `[start, end]` aralığının korunan segmentlerle en yüksek kesişimini (`best_overlap > 0.01`) bulup yeni `(new_start, new_end)` aralığına dönüştürür.
    * **`remap_overlays(overlays: List[Dict[str, Any]], keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> List[Dict[str, Any]]` (`@staticmethod`):** Her overlay'in `timestamp` değerini `remap_timestamp` ile yeni zamana taşır; kesilen bölgeye düşenleri (`None`) listeden çıkarır.
    * **`remap_transcript(transcript: Optional[Dict[str, Any]], keep_segments: List[Tuple[float, float]], actual_durations: Optional[List[float]] = None) -> Optional[Dict[str, Any]]` (`@staticmethod`):** Her segmentin içindeki kelimeleri (`words`) `remap_range` ile yeni zaman çizgisine haritalar, segmentin başlangıç ve bitişini korunan ilk ve son kelimenin zamanına günceller.

---

### 6.10. `src/OtoEdit.PythonWorker/render/video_renderer.py`
* **Dosyanın Amacı:** EDL JSON dokümanını okuyarak kare ve ses örneği hassasiyetinde (frame-accurate), sıfır ses-görüntü kayması (zero A/V desync) ve NVIDIA NVENC donanım hızlandırması (başarısız olursa CPU `libx264` fallback) ile nihai videoyu üreten ana render motorudur.
* **Harici Kütüphaneler:** `subprocess` (`ffmpeg`, `ffprobe`, `fc-match`), `concurrent.futures` (`ThreadPoolExecutor`), `ffmpeg-python`.
* **Sınıflar ve Metotlar:**
  * **`class VideoRenderer`**
    * **`__init__(self, minio_client: Optional[MinioClient] = None) -> None`:** `MinioClient` ve `ImageOverlay` başlatır.
    * **`render(self, edl_json: Dict[str, Any], video_path: str, output_path: str, temp_dir: str = "/app/temp") -> str`:**
      * **Adım Adım Render Algoritması:**
        1. `TemplateApplier.enrich_edl_with_template(edl_json)` ile şablon logosu ve alt bandını EDL'ye ekler.
        2. Video süresini EDL'den veya `_probe_video_duration` (`ffprobe`) ile alır; `_get_keep_segments(cuts, total_duration)` ile tutulacak zaman aralıklarını hesaplar.
        3. **1. Aşama — Paralel Frame-Accurate Kesim (`_cut_segments`):** Kesim varsa `_create_concat_file` ile kesim listesini yazar ve `_cut_segments` ile her korunan segmenti ayrı `.mp4` olarak kesip `ffprobe` ile gerçek sürelerini (`actual_durations`) ölçer.
        4. **Zaman Haritalama (`TimelineMapper`):** `actual_durations` kullanarak `remap_transcript` ve `remap_overlays` ile tüm altyazı ve kaplamaları kesilmiş videonun gerçek zaman çizgisine senkronlar.
        5. **Pillow Rozet Dönüşümü (`PillowGraphicsEngine`):** `boxStyle in ("pill", "rounded", "badge")` olan metin kaplamalarını `PillowGraphicsEngine.render_text_badge` ile şeffaf PNG'ye dönüştürüp `mapped_image_overlays` listesine ekler.
        6. **ASS Altyazı Üretimi (`TextOverlay`):** Hedef formata (`16:9` -> `1920x1080`, `9:16` -> `1080x1920`, `1:1` -> `1080x1080`) göre `.ass` altyazı dosyasını üretir (`subtitlesEnabled=False` ise yalnızca kutusuz text overlay'leri yazar).
        7. **Birleştirme + Kadraj + Altyazı (`_concat_segments` veya `_execute_ffmpeg_direct`):** Kesilmiş segmentleri birleştirirken aynı geçişte dikey/kare yüz takipli kırpma (`crop`) ve `.ass` altyazı gömme işlemini uygular.
        8. **2. Geçiş (İkinci Pass — Görsel Overlay'ler ve Auto-Ducking BGM):** Eğer `mapped_image_overlays` veya `backgroundMusic` varsa, ilk geçiş çıktısını `ffmpeg-python` ile açar, `self.image_overlay.apply_image_overlays` ve `AudioMixer.apply_bgm_with_ducking` filtrelerini uygular ve önce `h264_nvenc`, hata verirse `libx264` ile nihai dosyayı üretir.
    * **`_cut_segments(self, concat_txt_path: str, temp_dir: str) -> Tuple[List[str], List[float], str]`:**
      * **Algoritma:** NVENC eşzamanlı oturum sınırını aşmamak için `ThreadPoolExecutor(max_workers=2)` kullanır. Her segment için `-ss {start} -i {video_path} -t {duration}` (Input Seeking), kesim uçlarında tık sesini önleyen **8ms mikro-fade** (`afade=t=in:ss=0:d=0.008,afade=t=out:st=...:d=0.008`), `-fps_mode cfr` ve `-avoid_negative_ts make_zero` ile önce `h264_nvenc`, olmazsa `libx264` çalıştırır. Ardından her segmentin gerçek süresini `ffprobe` ile ölçüp `merge_concat.txt` dosyasını oluşturur.
    * **`_concat_segments(...) -> None`:** `ffmpeg -y -f concat -safe 0 -i merge_concat` ile segmentleri birleştirir, `-vf` (`crop` + `ass`), `-fps_mode cfr`, `-af aresample=async=1000` ve `-shortest` uygular.
    * **`_parse_concat_file(self, concat_path: str) -> List[Tuple[str, float, float]]`**
    * **`_cleanup_segment_files(self, segment_files: List[str], merge_concat: str) -> None`**
    * **`_execute_ffmpeg_direct(...) -> None`:** Kesim olmadığında doğrudan kaynak video üzerinde crop ve ASS filtrelerini çalıştırır.
    * **`_get_crop_str(self, face_data: Optional[List[Dict[str, Any]]], target_format: str) -> str`:** `9:16` için yüz verisinin ortalamasına göre `crop=ih*9/16:ih:...:0`, `1:1` için `crop=ih:ih:(iw-ow)/2:0` döner.
    * **`_get_keep_segments(self, cuts: List[Dict[str, Any]], total_duration: float) -> List[Tuple[float, float]]`:** Çakışan kesimleri birleştirip `[0, total_duration]` aralığından çıkararak korunan segment listesini döner.
    * **`_create_concat_file(...) -> None`** ve **`_probe_video_duration(self, video_path: str) -> float`**.

---

## BÖLÜM 7: DIŞ SERVİSLER (`src/OtoEdit.PythonWorker/services/`)

### 7.1. `src/OtoEdit.PythonWorker/services/__init__.py`
* **Dosyanın Amacı:** Dış servisler paketini tanımlar.

---

### 7.2. `src/OtoEdit.PythonWorker/services/analysis_cache.py`
* **Dosyanın Amacı:** Aynı videonun tekrar yüklenmesi durumunda tüm AI pipeline'ını yeniden çalıştırmak yerine Redis üzerinden saniyeler içinde önceki EDL sonucunu döndüren (Idempotency) fail-safe önbellek servisidir.
* **Harici Kütüphaneler:** `redis`, `hashlib` (`sha256`), `json`, `os`.
* **Sınıflar ve Metotlar:**
  * **`class AnalysisCacheService`**
    * **`__init__(self, host=None, port=None, password=None, db=None) -> None`**
    * **`_get_client(self)`:** Tembel (lazy) olarak `redis.Redis(..., socket_timeout=3.0, decode_responses=True)` bağlantısı kurar ve `ping()` atar. Bağlanamazsa hata fırlatmaz, `_is_available = False` işaretler.
    * **`compute_video_hash(file_path: str, chunk_size: int = 10 * 1024 * 1024) -> str` (`@staticmethod`):**
      * **Algoritma:** Dosya boyutu `<= 30 MB` ise tüm dosyayı, `> 30 MB` ise dosya boyutu + **ilk 10 MB + ortadaki 10 MB + son 10 MB** bloklarını okuyarak çok büyük videolarda bile milisaniyeler içinde deterministik SHA-256 özeti üretir.
    * **`get_cached_edl(self, video_hash: str) -> Optional[Dict[str, Any]]`:** `otoedit:analysis:edl:{video_hash}` anahtarını okur.
    * **`set_cached_edl(self, video_hash: str, edl_data: Dict[str, Any], ttl_seconds: int = 604800) -> bool`:** EDL JSON'u varsayılan 7 gün (`604800` sn) TTL ile Redis'e kaydeder.

---

### 7.3. `src/OtoEdit.PythonWorker/services/bg_remover.py`
* **Dosyanın Amacı:** Görsel kaplamalar için AI destekli arka plan kaldırma (`rembg` `u2netp` + OpenCV `GrabCut` fallback), CapCut tarzı beyaz çıkartma konturu (`add_sticker_outline`), yeşil ekran temizleme (`apply_chroma_key`) ve dairesel/yuvarlatılmış maskeleme (`apply_shape_mask`) işlemlerini yürüten stüdyo servisidir.
* **Harici Kütüphaneler:** `rembg` (`remove`, `new_session`), `cv2` (OpenCV), `numpy`, `PIL` (`Image`, `ImageFilter`, `ImageOps`, `ImageDraw`).
* **Sınıflar ve Metotlar:**
  * **`class BackgroundRemoverService`**
    * **`_get_rembg_session(cls)` (`@classmethod`):** Singleton olarak `new_session("u2netp")` başlatır.
    * **`remove_background(cls, image_path: str, output_path: Optional[str] = None) -> str` (`@classmethod`):** `rembg.remove` ile arka planı şeffaf PNG yapar; `rembg` yüklü değilse veya hata verirse `_fallback_grabcut_remove` metoduna düşer.
    * **`_fallback_grabcut_remove(cls, image_path: str, output_path: str) -> str` (`@classmethod`):** Çerçevenin `%8` içinden `%84` boyutunda merkez dikdörtgen tanımlayıp `cv2.grabCut(..., 4, cv2.GC_INIT_WITH_RECT)` çalıştırır ve alpha kanalını `GaussianBlur(5,5)` ile yumuşatır.
    * **`add_sticker_outline(cls, image_path: str, output_path: Optional[str] = None, outline_width: int = 8, outline_color_hex: str = "#FFFFFF", border_width: Optional[int] = None, border_color: Optional[str] = None, shadow: bool = True, **kwargs) -> str` (`@classmethod`):**
      * **Algoritma:** Görselin alpha kanalına eliptik çekirdekle (`cv2.MORPH_ELLIPSE`) morfolojik genişletme (`cv2.dilate`) uygular, isteğe bağlı derinlik gölgesi (`ImageFilter.GaussianBlur`) ve kontur katmanını `alpha_composite` ile birleştirip `getbbox()` ile kırpar.
    * **`apply_chroma_key(cls, image_path: str, output_path: Optional[str] = None, key_color_hex: str = "#00FF00", similarity: float = 0.35, smoothness: float = 0.1) -> str` (`@classmethod`):** Görseli ve hedef rengi **CIE LAB** renk uzayına (`cv2.COLOR_BGR2LAB`) çevirir, piksel bazlı Öklid renk farkını (`np.linalg.norm`) hesaplayıp `similarity` ve `smoothness` eşikleriyle yumuşak geçişli alpha maskesi üretir.
    * **`apply_shape_mask(cls, image_path: str, output_path: Optional[str] = None, shape: str = "circle", corner_radius: int = 32) -> str` (`@classmethod`):** 4x süper-örnekleme ile elips (`circle`) veya yuvarlatılmış dikdörtgen (`rounded`) maskesi çizer, `LANCZOS` ile küçültüp orijinal alpha kanalıyla çarpar.

---

### 7.4. `src/OtoEdit.PythonWorker/services/gemini_client.py`
* **Dosyanın Amacı:** Antigravity Proxy (`http://host.docker.internal:8045/v1/chat/completions`) veya doğrudan Google Gemini SDK (`google.generativeai`) üzerinden viral klip seçimi, B-Roll/metin önerisi üretimi ve transkript anlamsal kurgu denetimi yapan LLM istemcisidir.
* **Harici Kütüphaneler:** `urllib.request`, `google.generativeai`, `json`, `re`.
* **Sınıflar ve Metotlar:**
  * **`class GeminiClient`**
    * **`__init__(self) -> None`:** `ANTIGRAVITY_PROXY_KEY` varsa proxy modunu (`use_proxy = True`), yoksa `GEMINI_API_KEY` ile resmi SDK modunu başlatır.
    * **`_execute_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]`:** Exponential backoff (`2.0s -> 4.0s -> 8.0s`) ile LLM çağrısını yapar.
    * **`generate_text(self, prompt: str, max_retries: int = 3) -> Optional[str]`**
    * **`find_viral_clips(self, transcript_text: str, duration: float) -> List[Dict[str, Any]]`:** Reels (30s) ve Shorts (60-90s) viral kliplerini JSON olarak ister; hata veya boş yanıt durumunda `_fallback_viral_clips(duration)` döner.
    * **`generate_content_suggestions(self, transcript_text: str, duration: float) -> List[Dict[str, Any]]`:** `image_broll` ve `text_callout` önerilerini JSON olarak ister; hata durumunda `_fallback_suggestions` döner.
    * **`audit_transcript_coherence(self, segments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]`:** Segmentlerdeki `semantic_retake`, `aborted_sentence`, `orphaned_fragment` ve `meta_speech` kusurlarını denetler.
    * **`_safe_parse_json(cls, text: str) -> Any` (`@classmethod`)** ve **`_extract_json(text: str) -> str` (`@staticmethod`):** Markdown ```json kod bloklarını ve trailing comma (`,]`, `,}`) hatalarını temizleyerek güvenli JSON parse işlemi yapar.
    * **`_fallback_viral_clips(duration: float) -> List[Dict[str, Any]]` (`@staticmethod`)** ve **`_fallback_suggestions(duration: float) -> List[Dict[str, Any]]` (`@staticmethod`)**.

---

### 7.5. `src/OtoEdit.PythonWorker/services/minio_client.py`
* **Dosyanın Amacı:** MinIO S3 nesne depolama servisi üzerinden ham video indirme, temizlenmiş ses yükleme, görsel/varlık indirme ve render çıktısı yükleme operasyonlarını yönetir.
* **Harici Kütüphaneler:** `minio` (`Minio`, `S3Error`).
* **Sınıflar ve Metotlar:**
  * **`class MinioClient`**
    * **`__init__(self) -> None`:** `Minio` istemcisini başlatır ve `_ensure_bucket()` çağırır.
    * **`_ensure_bucket(self) -> None`:** Bucket yoksa `make_bucket` ile oluşturur.
    * **`download_file(self, object_key: str, local_path: str | None = None) -> str`:** Dosya yerel diskte zaten mevcutsa ve `> 1 MB` ise tekrar indirmeden yerel yolu döner; değilse `fget_object` ile indirir.
    * **`download_video(self, project_id: str, video_id: str, object_key: str | None = None) -> str`:** Varsayılan `videos/{project_id}/{video_id}.mp4` anahtarını indirir.
    * **`upload_file(self, local_path: str, object_key: str, content_type: str = "application/octet-stream") -> str`:** `fput_object` ile dosyayı yükler.
    * **`upload_clean_audio(self, project_id: str, video_id: str, local_audio_path: str) -> str`:** `audio/{project_id}/{video_id}_clean{ext}` anahtarına yükler.
    * **`upload_render_output(self, project_id: str, render_job_id: str, local_video_path: str) -> str`:** `renders/{project_id}/{render_job_id}.mp4` anahtarına yükler.

---

### 7.6. `src/OtoEdit.PythonWorker/services/pexels_client.py`
* **Dosyanın Amacı:** Pexels REST API (`https://api.pexels.com/v1/search`) üzerinden stok fotoğraf arayan ve yerel diske indiren istemcidir. Anahtar yoksa veya API kota/yetki hatası verirse otomatik olarak `StockMediaFallback` zincirine devreder.
* **Harici Kütüphaneler:** `requests`.
* **Sınıflar ve Metotlar:**
  * **`class PexelsClient`:** `__init__(self)`, `search_photo(self, query: str, orientation: str = "landscape") -> Optional[str]` ve `download_image(self, image_url: str, output_path: Optional[str] = None) -> Optional[str]`.

---

### 7.7. `src/OtoEdit.PythonWorker/services/stock_media_fallback.py`
* **Dosyanın Amacı:** Pexels API anahtarı olmadığında veya hata verdiğinde sırasıyla **Unsplash Public NAPI** ve **Wikimedia Commons API** üzerinden ücretsiz/açık lisanslı stok fotoğraf bulan yedek servisidir.
* **Harici Kütüphaneler:** `requests`, `urllib.parse.quote_plus`.
* **Sınıflar ve Metotlar:**
  * **`class StockMediaFallback`:** `search_unsplash(cls, query: str, orientation: str = "landscape") -> Optional[str]`, `search_wikimedia(cls, query: str) -> Optional[str]` ve `resolve_stock_image(cls, query: str, orientation: str = "landscape") -> Optional[str]`.

---

### 7.8. `src/OtoEdit.PythonWorker/services/pipeline_logger.py`
* **Dosyanın Amacı:** Pipeline ilerleme ve hata durumlarını **3 katmanda** (1: Yerel Konsol/Dosya Logu, 2: RabbitMQ Event Yayını, 3: Doğrudan .NET REST API `/api/internal/logs/pipeline` POST çağrısı) kaydeden ve hiçbir katmanda hata çıksa dahi ana video işleme akışını durdurmayan (Fail-Safe) loglama servisidir.
* **Harici Kütüphaneler:** `requests`, `json`, `datetime`.
* **Sınıflar ve Metotlar:**
  * **`class PipelineLogger`:** `__init__(self, api_base_url=None, api_key=None, publisher=None)` ve `log_progress(self, project_id: str, video_id: str, stage_name: str, progress_pct: int, status: str = "InProgress", message: str = "", details: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None) -> None`.

---

### 7.9. `src/OtoEdit.PythonWorker/services/rabbitmq_publisher.py`
* **Dosyanın Amacı:** Python Worker'dan .NET Backend MassTransit Consumer'larına thread-safe (`threading.Lock`) olarak ham JSON event mesajları (`PipelineStageChangedEvent`, `AnalysisCompletedEvent`, `PipelineErrorEvent`, `RenderCompletedEvent`) yayınlayan servistir.
* **Harici Kütüphaneler:** `pika`, `threading`, `json`.
* **Sınıflar ve Metotlar:**
  * **`class RabbitMQPublisher`**
    * **`__init__(self) -> None`**
    * **`_get_connection(self)`** ve **`_get_channel(self)`:** Bağlantı kapalıysa yeniden açar.
    * **`publish(self, exchange_name: str, message_dict: dict) -> None`:** Hem yalın `exchange_name` hem de `OtoEdit.Business.Events:{exchange_name}` fanout exchange'lerine `delivery_mode=2` (kalıcı/persistent) JSON mesajı basar. Hata durumunda `_close()` ile bağlantıyı sıfırlar.
    * **`publish_stage_changed(self, project_id: str, video_id: str, asama: str, yuzde: int, mesaj: str = "") -> None`**
    * **`publish_analysis_completed(self, project_id: str, video_id: str, edl_json: dict) -> None`**
    * **`publish_pipeline_error(self, project_id: str, video_id: str, asama: str, hata_mesaji: str) -> None`**
    * **`publish_render_completed(self, render_job_id: str, project_id: str, indirme_url: str) -> None`**
    * **`publish_render_progress(self, render_job_id: str, project_id: str, yuzde: int, mesaj: str = "") -> None`**
    * **`_close(self) -> None`**

---

## BÖLÜM 8: YARDIMCI MODÜLLER VE ARAÇLAR (`utils/` ve `tools/`)

### 8.1. `src/OtoEdit.PythonWorker/utils/__init__.py`
* **Dosyanın Amacı:** Yardımcı modüller paketini tanımlar.

---

### 8.2. `src/OtoEdit.PythonWorker/utils/constants.py`
* **Dosyanın Amacı:** Sistem genelindeki sabitleri ve .NET enum/event eşleşmelerini barındırır:
  * **`class VideoFormat`:** `YATAY_16_9 = 0`, `DIKEY_9_16 = 1`, `KARE_1_1 = 2` ve `TO_STRING` sözlüğü.
  * **`class PipelineStage`:** `SES_IYILESTIRME = "SesIyilestirme"`, `STT = "Stt"`, `SESSIZLIK_ALGILAMA = "SessizlikAlgilama"`, `KOMUT_ALGILAMA = "KomutAlgilama"`, `YUZ_TAKIBI = "YuzTakibi"`, `REPURPOSING = "Repurposing"`, `ONERI_OLUSTURMA = "OneriOlusturma"`, `EDL_OLUSTURMA = "EdlOlusturma"`, `RENDER = "Render"`, `TAMAMLANDI = "Tamamlandi"` (ve takma adlar: `RETAKE`, `VIRAL_KLIP`, `BROLL`).
  * **`class RabbitMQConstants`:** Gelen/giden tüm exchange ve kuyruk isimleri.
  * **`GESTURE_VOICE_SYNC_TOLERANCE_SECONDS = 2.0`**.

---

### 8.3. `src/OtoEdit.PythonWorker/utils/janitor.py`
* **Dosyanın Amacı:** Disk dolmasını önlemek için iş bitiminde geçici dosyaları silen (`cleanup_files`) ve başlangıçta `temp/` klasöründeki yetim `render_*` dizinleri ile `2.0` saatten eski medya dosyalarını temizleyen (`run_janitor`) disk temizlik modülüdür.
* **Harici Kütüphaneler:** `os`, `shutil`, `time`, `pathlib.Path`.
* **Fonksiyonlar:**
  * **`cleanup_files(*paths) -> None`:** Verilen dosya/symlink (`unlink`) ve klasörleri (`shutil.rmtree`) güvenli biçimde silip kazanılan MB miktarını loglar.
  * **`run_janitor(temp_dir: Path = None, max_age_hours: float = 2.0) -> None`:** `os.scandir` ile `render_` klasörlerini ve `.mp4, .mp3, .wav, .png, .ass, .json` dosyalarını tarayıp yaşları `> max_age_hours` olanları veya yetim render klasörlerini siler.

---

### 8.4. `src/OtoEdit.PythonWorker/utils/logger.py`
* **Dosyanın Amacı:** Hem standart çıktıya (`sys.stdout`) hem de `logs/worker.log` dosyasına UTF-8 formatında zaman damgalı log yazan ve gürültülü üçüncü parti kütüphaneleri (`pika`, `urllib3`, `mediapipe`) `WARNING` seviyesine çeken merkezi loglama yapılandırmasıdır.
* **Fonksiyonlar:** `setup_logging(log_file: str = "logs/worker.log", level: int = logging.INFO) -> None` ve `get_logger(name: str) -> logging.Logger`.

---

### 8.5. `src/OtoEdit.PythonWorker/tools/cut_benchmark.py`
* **Dosyanın Amacı:** Gerçek veya sentetik ses dosyaları üzerinde `AudioAnalyzer`, `SilenceDetector(engine="v2")` ve `AudioChunker` performansını, kesilen sessizlik yüzdesini ve `< 0.40s` kalan mikro-klip sayısını (Hedef: 0) ölçen CLI benchmark aracıdır.
* **Fonksiyonlar:** `run_benchmark(media_path: str) -> None`.

---

### 8.6. `src/OtoEdit.PythonWorker/tools/eval_edit.py`
* **Dosyanın Amacı:** Bir insan kurgucunun düzenlediği videonun transkripti (`edited_groq.json`) ile ham videonun transkriptini (`orig_groq.json`) `difflib.SequenceMatcher` ile kelime bazında hizalayan, insanın yaptığı kesimleri ve bıraktığı duraklama eğrisini (`human_curve`) çıkaran ve bunu OtoEdit'in otomatik ürettiği EDL (`edl_auto_v1.json`) ile karşılaştırarak True Positive (`tp`), False Positive (`fp` - yanlışlıkla silinen kelime), False Negative (`fn` - kaçırılan retake) ve kırpılan kelime (`clipped_words`) metriklerini `text_compare.json` olarak raporlayan değerlendirme betiğidir.
* **Fonksiyonlar:** `norm(w)`, `load_words(p)`, `speech_sec(a, b)`, `merge(iv)`, `cut_cover(a, b, iv)`, `word_removed_by_auto(j)`, `word_clipped_by_auto(j)`, `pauses_in_run_edited(r)`, `pauses_orig_for_run(r)`, `pct(v, ps)`.

---

## BÖLÜM 9: TEST DOSYALARI (`src/OtoEdit.PythonWorker/tests/` ve `tests/PythonWorker.Tests/`)

### 9.1. `src/OtoEdit.PythonWorker/tests/` İçindeki Test Dosyaları
1. **`src/OtoEdit.PythonWorker/tests/__init__.py`:** Test paketini tanımlar.
2. **`src/OtoEdit.PythonWorker/tests/fixtures/gemini_transcribe_response.json`:** Gerçek bir hukuk dersi videosunun (`"Bismillahirrahmanirrahim. Hukuk, yalnızca kanun maddelerinin..."`) `gemini-3.5-transcribe` API yanıtını ve 400+ kelimelik `startOffset`/`endOffset` zaman damgalarını içeren JSON test verisidir (2145 satır).
3. **`src/OtoEdit.PythonWorker/tests/test_acoustic_scorer.py`:**
   * `test_acoustic_scorer_implements_interface()`: `AcousticScorer`'ın `IAcousticScorer` arayüzünü uyguladığını doğrular.
   * `test_acoustic_scorer_in_memory_caching()`: 50+ kez `score_audio_segment` çağrılsa bile `AudioSegment.from_wav`'ın yalnızca 1 kez çağrıldığını (RAM önbellekleme) ve `clear_cache()` sonrası sıfırlandığını doğrular.
4. **`src/OtoEdit.PythonWorker/tests/test_analysis_cache.py`:**
   * `test_compute_video_hash()`, `test_compute_video_hash_non_existent()`, `test_analysis_cache_set_and_get()`, `test_analysis_cache_redis_unavailable_fail_safe()`: SHA-256 video özetini, Redis okuma/yazmayı ve Redis kapalıyken hata fırlatmadan (`None`/`False`) çalışmayı doğrular.
5. **`src/OtoEdit.PythonWorker/tests/test_analysis_consumer.py`:**
   * `mock_consumer` fixture'ı ile tüm alt servisleri mock'lar.
   * `test_consumer_cache_hit_bypasses_pipeline(mock_consumer)`: Redis cache hit durumunda `transcriber` ve `silence_detector`'ın hiç çağrılmadan doğrudan `publish_analysis_completed` ve `basic_ack` yapıldığını doğrular.
   * `test_consumer_full_parallel_pipeline_execution(mock_consumer)`: Cache miss durumunda tüm paralel aşamaların (STT, FaceTracker, RetakeDetector, SilenceDetector, CommandEngine, Repurposing, Suggestions, AutoBroll, EdlBuilder) eksiksiz çalıştığını doğrular.
6. **`src/OtoEdit.PythonWorker/tests/test_animation_effects.py`:**
   * `test_animation_effects_ass_fade()`, `test_animation_effects_ass_popup()`, `test_animation_effects_ass_slide_left()`, `test_resolve_static_position()`, `test_animation_effects_exit_fade()`, `test_animation_effects_exit_scale_out()`, `test_animation_effects_exit_none()`: Giriş/çıkış ASS etiketlerini ve FFmpeg konum ifadelerini doğrular.
7. **`src/OtoEdit.PythonWorker/tests/test_chunker.py`:**
   * `test_chunker_splits_at_silence()`: 1200 saniyelik bir ses analizinde `595s - 605s` arasındaki sessizliğin tam ortasından (`~600.0s`) bölme yapıldığını doğrular.
8. **`src/OtoEdit.PythonWorker/tests/test_e2e_diagnostics.py`:**
   * `test_font_assets()`: `assets/fonts/` altındaki 8 `.ttf` font dosyasının varlığını, boyutunu (`>10KB`) ve TrueType/OpenType magic byte başlığını (`\x00\x01\x00\x00`, `OTTO`, `true`) denetler.
   * `test_ass_generation_contract()`: `TextOverlay.generate_ass` çıktısında `\fnCinzel`, `\pos(1581,305)` (%82.38, %28.26 -> 1920x1080 piksel dönüşümü) ve kelime vurgu etiketlerini doğrular.
9. **`src/OtoEdit.PythonWorker/tests/test_e2e_render_pipeline.py`:**
   * `main()`: FFmpeg `lavfi` `testsrc` ve `sine` ile 4 saniyelik sentetik test videosu, Pillow ile şeffaf sticker ve BGM WAV dosyası üretip `VideoRenderer.render()` ile rozet, sticker konturu, döndürme ve auto-ducking BGM içeren tam uçtan uca render testini çalıştırır.
10. **`src/OtoEdit.PythonWorker/tests/test_edl_builder.py`:**
    * `test_merge_overlapping_cuts()`: Farklı nedenlere (`silence` vs `gesture_dislike`) sahip kesimlerin birbirini yutmadan ayrı tutulduğunu ve sessizliğin kırpıldığını doğrular.
    * `test_edl_builder_full_assembly()`: Tüm analiz çıktılarının `EdlDocument` içine doğru derlendiğini doğrular.
    * `test_edl_builder_fallback_duration_protection()`: Transkript fallback moduna düşüp `duration=1.0` dönse bile gerçek `video_duration=3145.2` değerinin korunduğunu doğrular.
11. **`src/OtoEdit.PythonWorker/tests/test_gap_filler.py`:**
    * `test_find_untranscribed_gaps()`: `>= 0.40s` olup içinde kelime bulunmayan VAD konuşma bölgelerinin eksiksiz yakalandığını doğrular.
12. **`src/OtoEdit.PythonWorker/tests/test_gemini_client.py`:**
    * `test_gemini_client_extract_json_markdown()`, `test_gemini_client_extract_json_trailing_comma()`, `test_gemini_client_fallback_viral_clips()`: Markdown kod bloklarından ve bozuk virgüllü JSON'lardan veri çıkarımını ve fallback klip üretimini doğrular.
13. **`src/OtoEdit.PythonWorker/tests/test_gemini_parser.py`:**
    * `test_gemini_transcribe_parser_with_fixture()`: `fixtures/gemini_transcribe_response.json` dosyasını `chunk_offset=10.0` ile ayrıştırarak `>= 400` kelime çıktığını ve ilk kelimenin `"Bismillahirrahmanirrahim."` (`12.100s - 13.200s`) olarak korunduğunu doğrular.
14. **`src/OtoEdit.PythonWorker/tests/test_gesture_detector.py`:**
    * `create_landmarks(...)`, `test_classify_thumbs_up()`, `test_classify_thumbs_down()`, `test_classify_open_palm()`: Sentetik 21 eklem noktası ile MediaPipe el hareketi sınıflandırmasını doğrular.
15. **`src/OtoEdit.PythonWorker/tests/test_image_overlay.py`:**
    * `test_resolve_image_path_local_file()`, `test_resolve_image_path_s3()`, `test_apply_image_overlays_skips_non_image()`, `test_apply_image_overlays_sorts_by_track_id()`: Görsel yolu çözümleme ve `trackId` Z-Index sıralamasını doğrular.
16. **`src/OtoEdit.PythonWorker/tests/test_jumpcut_v2.py`:**
    * `create_synthetic_analysis(...)`, `test_jumpcut_v2_padding_and_min_silence()`, `test_jumpcut_v2_word_guard()`, `test_jumpcut_v2_micro_island_merging()`, `test_jumpcut_v2_asymmetric_padding()`, `test_find_energy_minimum_directions()`: Jump-Cut v2 motorunun nefes koruması, kelime koruma kalkanı, mikro-ada birleştirme, asimetrik padding ve tek yönlü RMS enerji minimumu arama özelliklerini doğrular.
17. **`src/OtoEdit.PythonWorker/tests/test_multimodal_command_engine.py`:**
    * `test_multimodal_matching_gesture_and_voice_confirmed()`, `test_multimodal_type_mismatch_not_confirmed()`, `test_multimodal_time_tolerance_exceeded_not_confirmed()`: Jest ve sesli komutun hem tür hem de `±2.0s` zaman farkı açısından eşleşmesini doğrular.
18. **`src/OtoEdit.PythonWorker/tests/test_pipeline_isolated.py`:**
    * Docker konteyneri içinde gerçek video klibi üzerinde 10 izole testi (`test_0_prepare_clip` .. `test_9_concat_overlay_combo`) sırayla çalıştırıp A/V senkron kaymasını (`_check_av_sync`) ölçen ve `test_report.json` üreten kapsamlı entegrasyon test paketidir.
19. **`src/OtoEdit.PythonWorker/tests/test_pipeline_logger.py`:**
    * `test_pipeline_logger_success_flow()`, `test_pipeline_logger_error_flow()`, `test_pipeline_logger_api_failure_fail_safe()`: 3 katmanlı loglamanın ve HTTP API çöktüğünde hata fırlatmama (fail-safe) davranışının doğrulanması.
20. **`src/OtoEdit.PythonWorker/tests/test_repurposing_engine.py`:**
    * `test_repurposing_engine_analyze_with_mock()`, `test_repurposing_engine_fallback_when_empty_clips()`: Viral klip analizini doğrular.
21. **`src/OtoEdit.PythonWorker/tests/test_retake_detector.py`:**
    * `test_meta_speech_detection()`, `test_ordinal_conflict_protection()`, `test_exact_duplicate_detection()`, `test_retake_detector_identifies_meta_and_keeps_clean_speech()`: Stüdyo meta konuşmalarının kesildiğini ve "Birinci öncül..." ile "İkinci öncül..." cümlelerinin birbirini silmediğini doğrular.
22. **`src/OtoEdit.PythonWorker/tests/test_silence_detector.py`:**
    * `test_silence_detector_detects_and_applies_padding()`, `test_silence_detector_handles_exception_gracefully()`: Legacy `pydub` sessizlik algılama modunu doğrular.
23. **`src/OtoEdit.PythonWorker/tests/test_smart_windowing.py`:**
    * `test_smart_windowing_skips_when_no_voice_commands()`, `test_smart_windowing_scans_only_target_windows()`: Sesli komut olmadığında `GestureDetector`'ın hiç çağrılmadığını, sesli komut olduğunda ise yalnızca `target_windows` aralığının tarandığını doğrular.
24. **`src/OtoEdit.PythonWorker/tests/test_stt_resilience.py`:**
    * `test_key_rotator_cooling_down_and_recovery()`: 429 alan anahtarın soğumaya alınıp sıradaki anahtara geçildiğini doğrular.
    * `test_transcriber_chunk_isolation_preserves_words()`: 2. ses parçası 429/RuntimeError ile çökse bile 1. parçadan elde edilen kelimelerin korunduğunu doğrular.
25. **`src/OtoEdit.PythonWorker/tests/test_suggestion_engine.py`:**
    * `test_suggestion_engine_generates_broll_and_text()`: Gemini + Pexels entegrasyonuyla öneri üretimini doğrular.
26. **`src/OtoEdit.PythonWorker/tests/test_take_aligner.py`:**
    * `test_take_aligner_exact_restart()`, `test_take_aligner_turkish_fuzzy_match()`, `test_take_aligner_outtake_and_false_start()`, `test_edl_builder_separate_reasons()`: `TakeAligner` sağdan sola restart tespitini, Türkçe sondan eklemeli kelime kök eşleşmesini ("hükümlerinin" != "bölümlerinin") ve `EdlBuilder`'ın `silence` ile `smart_retake` kesimlerini ayrı tutmasını doğrular.
27. **`src/OtoEdit.PythonWorker/tests/test_template_applier.py`:**
    * `test_enrich_edl_with_template()`, `test_enrich_edl_idempotent()`: Şablon logo ve konuşmacı alt bandının idempotent eklenmesini doğrular.
28. **`src/OtoEdit.PythonWorker/tests/test_text_overlay.py`:**
    * `test_hex_to_ass_color()`, `test_position_to_ass_alignment()`, `test_seconds_to_ass_time()`, `test_generate_ass_file()`, `test_generate_ass_file_with_track_id()`: ASS renk, hizalama, zaman dönüşümü ve `Dialogue:` katman üretimini doğrular.
29. **`src/OtoEdit.PythonWorker/tests/test_timeline_mapper.py`:**
    * `test_remap_timestamp_basic()`, `test_remap_timestamp_empty_segments()`, `test_remap_overlays_filters_cut_content()`, `test_remap_transcript_with_karaoke()`, `test_remap_range_boundary_clamping()`, `test_end_to_end_ass_generation_with_remapping()`: Kesim sonrası zaman çizgisi haritalamasını doğrular.
30. **`src/OtoEdit.PythonWorker/tests/test_transcript_verifier.py`:**
    * `test_transcript_verifier_cuts_semantic_retakes()`, `test_transcript_verifier_skips_when_empty_or_no_findings()`: Gemini destekli `TranscriptVerifier` semantik kesimlerini doğrular.
31. **`src/OtoEdit.PythonWorker/tests/test_video_renderer.py`:**
    * `test_video_renderer_get_keep_segments()`, `test_video_renderer_get_keep_segments_no_cuts()`, `test_video_renderer_create_concat_file()`: `keep_segments` hesaplamasını ve `ffconcat version 1.0` dosya üretimini doğrular.
32. **`src/OtoEdit.PythonWorker/tests/test_visual.py`:**
    * `extract_frame(...)`, `test_font_rendering_visual()`, `test_subtitle_sync_visual()`: FFmpeg ile gerçek siyah/mavi test videoları üzerine ASS altyazı basıp belirli saniyelerdeki kareleri PNG olarak çıkararak piksel parlaklığı (`np.sum(bottom_half > 200)`) üzerinden fontların ve zamanlamanın görsel olarak gerçekten render edildiğini doğrular.
33. **`src/OtoEdit.PythonWorker/tests/test_voice_command_parser.py`:**
    * `test_parse_start_command()`, `test_parse_cut_command()`, `test_parse_add_text_command()`, `test_parse_no_command()`: Türkçe sesli komut regex ayrıştırıcısını doğrular.

---

### 9.2. `tests/PythonWorker.Tests/` İçindeki Test Dosyaları ve Fark Analizi
`OtoEdit/tests/PythonWorker.Tests/` dizininde toplam **14 dosya** yer almaktadır. Bu klasör, `src/OtoEdit.PythonWorker/tests/` içindeki birim testlerinin üst dizindeki merkezi `tests/` klasöründeki karşılığıdır:

1. **`tests/PythonWorker.Tests/__init__.py`:** `src/OtoEdit.PythonWorker/tests/__init__.py` ile birebir aynıdır.
2. **`tests/PythonWorker.Tests/test_animation_effects.py`:** `src/OtoEdit.PythonWorker/tests/test_animation_effects.py` ile birebir aynıdır.
3. **`tests/PythonWorker.Tests/test_gesture_detector.py`:** `src/OtoEdit.PythonWorker/tests/test_gesture_detector.py` ile birebir aynıdır.
4. **`tests/PythonWorker.Tests/test_image_overlay.py`:** `src/OtoEdit.PythonWorker/tests/test_image_overlay.py` ile birebir aynıdır.
5. **`tests/PythonWorker.Tests/test_multimodal_command_engine.py`:** `src/OtoEdit.PythonWorker/tests/test_multimodal_command_engine.py` ile birebir aynıdır.
6. **`tests/PythonWorker.Tests/test_repurposing_engine.py`:** `src/OtoEdit.PythonWorker/tests/test_repurposing_engine.py` ile birebir aynıdır.
7. **`tests/PythonWorker.Tests/test_suggestion_engine.py`:** `src/OtoEdit.PythonWorker/tests/test_suggestion_engine.py` ile birebir aynıdır.
8. **`tests/PythonWorker.Tests/test_template_applier.py`:** `src/OtoEdit.PythonWorker/tests/test_template_applier.py` ile birebir aynıdır.
9. **`tests/PythonWorker.Tests/test_voice_command_parser.py`:** `src/OtoEdit.PythonWorker/tests/test_voice_command_parser.py` ile birebir aynıdır.
10. **`tests/PythonWorker.Tests/test_edl_builder.py`:**
    * *Fark:* Eski sürüm beklentilerini içerir (`test_merge_overlapping_cuts` içinde farklı nedenlere sahip kesimlerin 2 kesime birleşmesini bekler ve `edl["settings"]["targetFormat"]` sözlük erişimi yapar; güncel `src/OtoEdit.PythonWorker/tests/test_edl_builder.py` ise 3 kesim ve `test_edl_builder_fallback_duration_protection` içerir).
11. **`tests/PythonWorker.Tests/test_retake_detector.py`:**
    * *Fark:* `test_retake_detector_identifies_meta_and_keeps_clean_speech` içinde `detector.transcript_verifier` mock'laması bulunmaz; geri kalan 4 test fonksiyonu aynıdır.
12. **`tests/PythonWorker.Tests/test_silence_detector.py`:**
    * *Fark:* `SilenceDetector(...)` çağrısında `engine="legacy"` parametresi açıkça geçilmemiştir (güncel `src/OtoEdit.PythonWorker/tests/test_silence_detector.py` dosyasında varsayılan motor `v2` olduğu için `engine="legacy"` açıkça belirtilmiştir).
13. **`tests/PythonWorker.Tests/test_text_overlay.py`:**
    * *Fark:* `test_generate_ass_file` içinde yalnızca `assert "{\k" in content` kontrolü vardır; güncel `src/OtoEdit.PythonWorker/tests/test_text_overlay.py` içinde ise yeni kelime vurgu formatı olan `assert "\c&H" in content or "{\k" in content` kontrolü yer alır.
14. **`tests/PythonWorker.Tests/test_video_renderer.py`:**
    * *Fark:* `test_video_renderer_create_concat_file` içinde `ffconcat version 1.0
` başlığı olmadan 6 satır beklenmektedir; güncel `src/OtoEdit.PythonWorker/tests/test_video_renderer.py` içinde ise `ffconcat version 1.0
` dahil 7 satır doğrulanmaktadır.

---

# EK C: Angular Frontend (OtoEdit.Frontend) Tam Dosya, Sinyal & Fonksiyon Referansı

# OtoEdit Angular Frontend (`D:\OtoEdit\OtoEdit\src\OtoEdit.Frontend`) Kapsamlı Mimari ve Kod Analiz Raporu

Bu rapor, `OtoEdit.Frontend` dizinindeki tüm yapılandırma dosyalarını, `src/` altındaki her bir kaynak dosyayı (bileşenler, servisler, modeller, sinyaller, borular, metodlar ve parametreleri dahil) ve uçtan uca kullanıcı akışlarını en ince ayrıntısına kadar incelemektedir.

---

## BÖLÜM 1: YAPILANDIRMA DOSYALARI (CONFIGURATION FILES)

### 1.1. `package.json`
- **Amacı:** Projenin NPM bağımlılıklarını, çalışma betiklerini (scripts) ve versiyon bilgilerini tanımlar. Angular 18.2.0 tabanlı standalone mimari kullanılmaktadır.
- **Scriptler:**
  - `ng`: Angular CLI komutu (`ng`).
  - `start`: `ng serve --port 4200 --host 0.0.0.0` (Geliştirme sunucusunu tüm ağ arayüzlerinde 4200 portunda başlatır).
  - `build`: `ng build --configuration production` (Üretim derlemesi alır).
  - `watch`: `ng build --watch --configuration development` (Geliştirme modunda izlemeli derleme).
  - `test`: `ng test` (Birim testlerini çalıştırır).
- **Temel Bağımlılıklar (`dependencies`):**
  - `@angular/animations`, `@angular/common`, `@angular/compiler`, `@angular/core`, `@angular/forms`, `@angular/platform-browser`, `@angular/platform-browser-dynamic`, `@angular/router` (`^18.2.0`)
  - `@microsoft/signalr` (`^8.0.7`): Backend `PipelineHub` ile gerçek zamanlı WebSocket/LongPolling iletişimi için kullanılır.
  - `rxjs` (`^7.8.1`), `tslib` (`^2.6.3`), `zone.js` (`~0.14.10`).
- **Geliştirme Bağımlılıkları (`devDependencies`):**
  - `@angular-devkit/build-angular`, `@angular/cli`, `@angular/compiler-cli` (`^18.2.0`)
  - `tailwindcss` (`^3.4.10`), `postcss` (`^8.4.41`), `autoprefixer` (`^10.4.20`), `typescript` (`~5.5.4`), `@types/node` (`^20.14.12`).

### 1.2. `angular.json`
- **Amacı:** Angular CLI çalışma alanı ve derleme/sunum (architect) yapılandırmasıdır.
- **Detaylar:**
  - Proje adı: `oto-edit-frontend`, kök dizin `""`, kaynak dizini `"src"`, önek `"app"`.
  - Varsayılan stil dili: `"scss"`.
  - **Build (`@angular-devkit/build-angular:application`):**
    - `outputPath`: `"dist/oto-edit-frontend"` (Angular 18 application builder çıktı olarak `dist/oto-edit-frontend/browser` üretir).
    - `index`: `"src/index.html"`, `browser`: `"src/main.ts"`, `polyfills`: `["zone.js"]`, `tsConfig`: `"tsconfig.app.json"`.
    - `assets`: `public` klasöründeki tüm dosyalar (`**/*`).
    - `styles`: `["src/styles.scss"]`.
    - `production` bütçeleri (budgets): `initial` için uyarı 2MB / hata 5MB; `anyComponentStyle` için uyarı 10KB / hata 20KB; `outputHashing`: `"all"`.
    - `development`: Optimizasyon kapalı, lisans çıkarma kapalı, `sourceMap: true`.
  - **Serve (`@angular-devkit/build-angular:dev-server`):**
    - Varsayılan konfigürasyon: `development`.
    - `options.proxyConfig`: `"proxy.conf.json"` (Geliştirme ortamında API ve SignalR isteklerini yönlendirir).

### 1.3. `tailwind.config.js` & `postcss.config.js`
- **`postcss.config.js`:** `tailwindcss` ve `autoprefixer` eklentilerini aktif eder.
- **`tailwind.config.js` Amacı:** Tailwind CSS tema, renk paleti, yazı tipi ve özel animasyon yapılandırmasıdır.
- **Detaylar:**
  - `content`: `["./src/**/*.{html,ts,scss}"]`
  - `darkMode`: `'class'` (`index.html` içinde `<html class="dark">` ile sabit karanlık tema kullanılır).
  - **Özel Renkler (`theme.extend.colors`):**
    - `dark`: `950: '#060913'`, `900: '#0B0F19'`, `800: '#111827'`, `700: '#1F2937'`, `600: '#374151'`, `500: '#4B5563'`
    - `brand`: `blue: '#2563EB'`, `indigo: '#4F46E5'`, `purple: '#7C3AED'`, `cyan: '#06B6D4'`, `accent: '#3B82F6'`
    - `status`: `success: '#10B981'`, `warning: '#F59E0B'`, `error: '#EF4444'`, `info: '#3B82F6'`
  - **Yazı Tipleri (`fontFamily`):** `sans: ['Inter', ...]`, `display: ['Outfit', 'Inter', ...]`
  - **Gölgeler (`boxShadow`):** `'glow-sm'`, `'glow-md'`, `'glow-purple'` (neon parlama efektleri).
  - **Animasyonlar ve Keyframes (`animation` & `keyframes`):**
    - Giriş animasyonları: `'pulse-subtle'`, `'fade-in'`, `'slide-in-right'`, `'scale-in'`, `'slide-up-forwards'`
    - Çıkış animasyonları (Overlay çıkışları için): `'fade-out'`, `'slide-down-out'`, `'slide-up-out'`, `'scale-out'`.

### 1.4. `proxy.conf.json`
- **Amacı:** Geliştirme sunucusunda (`ng serve`) çalışırken `/api` ve `/pipeline-hub` isteklerini yerel backend sunucusuna (`http://localhost:5001`) yönlendirir.
- **Kurallar:**
  - `"/api"`: `target: "http://localhost:5001"`, `secure: false`, `changeOrigin: true`, `timeout: 1800000` (30 dk - büyük video yüklemeleri için), `proxyTimeout: 1800000`.
  - `"/pipeline-hub"`: `target: "http://localhost:5001"`, `secure: false`, `ws: true` (WebSocket desteği), `changeOrigin: true`.

### 1.5. `nginx.conf`
- **Amacı:** Docker konteyneri içinde üretim ortamında Angular SPA dosyalarını sunmak ve ters vekil (reverse proxy) olarak API/SignalR trafiğini `api:8080` servisine iletmek.
- **Kurallar:**
  - Port `80`, kök dizin `/usr/share/nginx/html`, indeks `index.html`.
  - `location /`: `try_files $uri $uri/ /index.html;` (Angular HTML5 History routing desteği).
  - `client_max_body_size 50G;` (50 GB'a kadar ham video yüklemesine izin verir).
  - `location /api/`: `proxy_pass http://api:8080/api/;` (`Host` ve `X-Real-IP` başlıklarını aktarır).
  - `location /pipeline-hub`: `proxy_pass http://api:8080/pipeline-hub;` (`proxy_http_version 1.1`, `Upgrade` ve `Connection "upgrade"` başlıklarıyla WebSocket tünellemesi yapar).

### 1.6. `Dockerfile`
- **Amacı:** Çok aşamalı (multi-stage) Docker imajı oluşturur.
- **Aşamalar:**
  1. `FROM node:20-alpine AS build`: `/app` çalışma dizininde `package*.json` kopyalanır, `npm ci` ile bağımlılıklar kurulur, tüm kaynak kod kopyalanıp `npm run build` çalıştırılır.
  2. `FROM nginx:alpine`: Derlenen `/app/dist/oto-edit-frontend/browser` çıktısını `/usr/share/nginx/html` dizinine, `nginx.conf` dosyasını `/etc/nginx/conf.d/default.conf` yoluna kopyalar. Port 80'i açar ve `nginx -g "daemon off;"` ile başlatır.

### 1.7. `tsconfig.json` & `tsconfig.app.json`
- **`tsconfig.json`:**
  - `strict: true`, `target: "ES2022"`, `module: "ES2022"`, `moduleResolution: "bundler"`, `experimentalDecorators: true`.
  - Yol kısayolları (`paths`): `@core/*` -> `src/app/core/*`, `@shared/*` -> `src/app/shared/*`, `@environments/*` -> `src/environments/*`.
  - Angular derleyici seçenekleri: `strictInjectionParameters: true`, `strictInputAccessModifiers: true`, `strictTemplates: true`.
- **`tsconfig.app.json`:** `tsconfig.json`'ı genişletir, giriş dosyası olarak `src/main.ts` ve `src/**/*.ts` dosyalarını dahil eder.

---

## BÖLÜM 2: `src/` DİZİNİNDEKİ TÜM DOSYALARIN DETAYLI İNCELEMESİ

### 2.1. Kök ve Ortam Dosyaları

#### 1) `src/index.html`
- **Amacı:** Uygulamanın ana HTML şablonudur.
- **İçeriği:**
  - `<html lang="tr" class="dark">` ile Türkçe dil ve karanlık mod tanımlıdır.
  - Başlık: `"OtoEdit — Yapay Zeka Destekli Otomatik Video Kurgu Sistemi"`.
  - Google Fonts bağlantısı: Video kurgu ve altyazı/overlay tipografisinde kullanılan `Anton`, `Bangers`, `Bebas Neue`, `Cinzel`, `Fira Code`, `Inter`, `Montserrat`, `Oswald`, `Outfit`, `Playfair Display`, `Poppins`, `Syne` yazı tiplerini yükler.
  - `<body>` içinde `<app-root></app-root>` bileşenini barındırır.

#### 2) `src/main.ts`
- **Amacı:** Angular uygulamasının tarayıcıda başlatıldığı (bootstrap) giriş noktasıdır.
- **Fonksiyonlar:**
  - `bootstrapApplication(AppComponent, appConfig)`: `AppComponent` kök bileşenini `appConfig` sağlayıcılarıyla başlatır; hata olursa konsola yazar.

#### 3) `src/styles.scss`
- **Amacı:** Global SCSS dosyası ve yardımcı sınıflardır.
- **İçeriği:**
  - `@tailwind base; @tailwind components; @tailwind utilities;` direktifleri.
  - `body`: `#0B0F19` arka plan, `#F3F4F6` metin rengi, `overflow-x: hidden`.
  - Özel kaydırma çubuğu (`::-webkit-scrollbar`): 6px genişlik/yükseklik, `#111827` iz (track), `#374151` tutamaç (thumb).
  - `.glass-panel` ve `.glass-panel-hover`: Bulanık cam (glassmorphism) kart görünümleri (`backdrop-filter: blur(12px)`).
  - `.text-gradient` ve `.text-gradient-cyan`: Gradyan metin efektleri.
  - Çıkış animasyonları (`@keyframes fadeOut`, `slideDownOut`, `slideUpOut`, `scaleOut`) ve bunların yardımcı sınıfları (`.animate-fade-out`, `.animate-slide-down-out`, `.animate-slide-up-out`, `.animate-scale-out`).

#### 4) `src/environments/environment.ts`
- **Amacı:** Geliştirme ortamı yapılandırma sabitlerini tutar.
- **Sabitler:**
  - `production`: `false`
  - `apiUrl`: `'/api'`
  - `hubUrl`: `'/pipeline-hub'`
  - `apiKey`: `'SUPER_SECRET_OTOEDIT_KEY_123!'`

#### 5) `src/environments/environment.prod.ts`
- **Amacı:** Üretim (production) ortamı yapılandırma sabitlerini tutar.
- **Sabitler:**
  - `production`: `true`
  - `apiUrl`: `'/api'`
  - `hubUrl`: `'/pipeline-hub'`
  - `apiKey`: `'SUPER_SECRET_OTOEDIT_KEY_123!'`

---

### 2.2. Uygulama Kök Yapısı (`src/app/`)

#### 6) `src/app/app.component.ts`
- **Amacı:** Uygulamanın en üst düzey kabuk (root shell) bileşenidir.
- **Bileşen:** `AppComponent` (`selector: 'app-root'`, `standalone: true`, `imports: [RouterOutlet]`).
- **Özellikler:**
  - `title = 'OtoEdit Frontend'`
  - Şablonunda yalnızca `<router-outlet></router-outlet>` barındırır.

#### 7) `src/app/app.config.ts`
- **Amacı:** Standalone Angular uygulaması için global Dependency Injection (DI) sağlayıcılarını yapılandırır.
- **Sabit:** `appConfig: ApplicationConfig`
- **Sağlayıcılar (`providers`):**
  - `provideZoneChangeDetection({ eventCoalescing: true })`: Performans için olay birleştirmeli Zone.js değişim tespiti.
  - `provideRouter(routes, withComponentInputBinding())`: Rota parametrelerinin bileşen `@Input()`'larına doğrudan bağlanmasını destekleyen yönlendirici.
  - `provideHttpClient(withFetch(), withInterceptors([apiKeyInterceptor]))`: Fetch API tabanlı `HttpClient` ve her isteğe `X-API-Key` ekleyen interceptor.
  - `provideAnimations()`: Angular animasyon desteği.

#### 8) `src/app/app.routes.ts`
- **Amacı:** Uygulama içi sayfa yönlendirmelerini (lazy-loaded standalone bileşenler olarak) tanımlar.
- **Rotalar (`routes: Routes`):**
  - `''`: `ProjectListComponent` (Ana sayfa - Projeler listesi)
  - `'project/:id'`: `ProjectDetailComponent` (Proje detay, video yükleme, şablon/format seçimi ve canlı analiz takibi)
  - `'project/:id/editor'`: `EditorComponent` (NLE Timeline, Canlı EDL Simülasyonu, AI Kurgu Sohbeti, Altyazı ve Katman Stüdyosu)
  - `'project/:id/render/:renderJobId'`: `RenderResultComponent` (FFmpeg render ilerleme takibi, önizleme ve indirme ekranı)
  - `'**'`: `redirectTo: ''` (Bilinmeyen rotaları ana sayfaya yönlendirir).

---

### 2.3. Core Katmanı - Interceptor ve Modeller (`src/app/core/`)

#### 9) `src/app/core/interceptors/api-key.interceptor.ts`
- **Amacı:** Giden tüm HTTP isteklerine Backend'in `ApiKeyMiddleware` doğrulaması için gerekli olan `X-API-Key` başlığını otomatik ekler.
- **Fonksiyon:** `apiKeyInterceptor: HttpInterceptorFn = (req, next) => ...`
  - **Parametreler:** `req: HttpRequest<unknown>`, `next: HttpHandlerFn`.
  - **İşlevi:** `environment.apiKey` değerini (yoksa `'SUPER_SECRET_OTOEDIT_KEY_123!'`) alır, `req.clone()` ile isteğin `headers` koleksiyonuna `'X-API-Key': apiKey` ekler ve `next(authReq)` ile zinciri devam ettirir.

#### 10) `src/app/core/models/asset.model.ts`
- **Amacı:** Projeye yüklenen medya varlıklarının (görsel, ses, video) veri transfer modelini tanımlar.
- **Arayüzler:**
  - `ProjectAssetDto`:
    - `id: string`
    - `projectId: string`
    - `dosyaAdi: string`
    - `mimeTuru: string`
    - `url: string`
    - `boyutByte: number`
    - `yuklemeTarihi: string`

#### 11) `src/app/core/models/chat.model.ts`
- **Amacı:** Yönetmen AI (AI Kurgu Asistanı) ile yapılan sohbet mesajlarını, dinamik netleştirme (clarification) formlarını ve EDL yama yanıtlarını modeller.
- **Arayüzler:**
  - `FormFieldDto`: AI asistanının kullanıcıdan eksik parametre (metin, renk, konum vb.) istemek için ürettiği dinamik form alanı.
    - `id: string`
    - `type: 'text' | 'color' | 'select' | 'number' | 'position'`
    - `label: string`
    - `options?: ({ label: string; value: string } | string)[]`
    - `defaultValue?: string | number`
    - `required?: boolean`
  - `ChatMessageDto`: Sohbet geçmişindeki veya aktif akıştaki tekil mesaj.
    - `id?: string`, `projectId: string`, `rol: 'user' | 'assistant'`, `mesaj: string`, `intent?: string`, `patchDurumu?: string` (`'pending' | 'applied' | 'rejected' | 'clarification'`), `olusturulmaZamani: string`, `edlPatch?: EdlPatchDto`, `pendingEdlPatch?: EdlPatchDto`, `formFields?: FormFieldDto[]`, `formData?: any` (kullanıcının formda doldurduğu yerel veri).
  - `ChatSendMessageDto`: `{ mesaj: string }`
  - `ChatResponseDto`: `POST /api/projects/{id}/chat` çağrısından dönen yanıt (`id`, `rol`, `mesaj`, `intent`, `patchDurumu`, `edlPatch`, `pendingEdlPatch`, `formFields`, `yeniVersiyon`).

#### 12) `src/app/core/models/edl.model.ts`
- **Amacı:** Uygulamanın kalbi olan **EDL (Edit Decision List - Kurgu Karar Listesi)** veri yapılarını, kesimleri, katmanları, transkripti, altyazı/müzik/renk ayarlarını ve yama (patch) şemalarını tanımlar.
- **Arayüzler:**
  - `CutItem`: Videodan çıkarılacak (atlanan) zaman aralıklarını temsil eder.
    - `id: string`, `start: number`, `end: number`, `reason?: string` (`'silence'`, `'retake'`, `'Manuel kesim'` vb.), `source?: string` (`'auto'`, `'user'`), `command?: string`, `origStart?: number`, `origEnd?: number` (Jump-Cut ince ayarı öncesi orijinal AI sınırları).
  - `OverlayItem`: Video üzerine eklenen metin veya görsel/B-Roll katmanı.
    - Temel: `id: string`, `type: 'text' | 'image'`, `content?: string`, `source?: string`, `timestamp: number`, `duration: number`, `trackId?: number`.
    - Konum & Boyut: `position?: [string, string]`, `positionX?: number` (0-100%), `positionY?: number` (0-100%), `scale?: number`.
    - Animasyon: `animation?: 'fade' | 'pop-up' | 'slide-left' | 'slide-right' | 'slide-up' | 'slide-down' | 'none'`, `exitAnimation?: 'fade' | 'pop-up' | 'slide-down' | 'slide-up' | 'scale-out' | 'none'`.
    - Tipografi & Rozet: `font?: string`, `fontSize?: number`, `color?: string`, `backgroundColor?: string`, `strokeColor?: string`, `strokeWidth?: number`, `shadowColor?: string`, `shadowBlur?: number`, `boxStyle?: 'none' | 'pill' | 'rounded' | 'badge'`, `boxBgColor?: string`, `boxPadding?: number`, `borderRadius?: number`, `allCaps?: boolean`, `letterSpacing?: number`.
    - Görsel & AI Efektleri: `removeBg?: boolean`, `stickerBorder?: boolean`, `stickerBorderWidth?: number`, `stickerBorderColor?: string`, `rotation?: number` (-180..180°), `maskShape?: 'rect' | 'circle' | 'rounded'`, `chromaKeyColor?: string`, `chromaKeySimilarity?: number`.
  - `TranscriptWord`: `{ word: string; start: number; end: number; }` (Karaoke kelime vurgusu için kelime bazlı zaman damgaları).
  - `TranscriptSegment`: `{ start: number; end: number; text: string; words?: TranscriptWord[]; }`.
  - `TranscriptData`: `{ fullText: string; duration?: number; segments: TranscriptSegment[]; }`.
  - `ViralClipItem`: `{ id, title, start, end, duration, targetFormat, viralityScore, reason }`.
  - `SuggestionItem`: `{ id, type: 'image_broll' | 'text_highlight', title, content, sourceUrl?, timestamp, duration, reason?, status: 'pending' | 'accepted' | 'rejected' }`.
  - `SubtitleStyleConfig`: CapCut tarzı altyazı stil yapılandırması (`preset: 'tiktok_yellow' | 'cinematic_shadow' | 'opaque_banner' | 'neon_glow' | 'custom'`, `fontFamily`, `fontSize`, `textColor`, `highlightColor`, `strokeColor`, `strokeWidth`, `shadowColor`, `shadowDistance`, `shadowBlur`, `backgroundColor`, `backgroundPadding`, `borderRadius`, `verticalPosition`, `allCaps`, `letterSpacing`).
  - `BackgroundMusicConfig`: Arka plan müziği ve Sidechain Auto-Ducking ayarları (`url`, `title`, `volume`, `autoDucking`, `duckingAmount`, `fadeIn`, `fadeOut`, `loop`).
  - `ColorGradingConfig`: Video renk düzenleme filtreleri (`brightness`, `contrast`, `saturation`, `temperature`).
  - `EdlSettings`: Genel kurgu ayarları (`targetFormat`, `templateId`, `faceTrackingEnabled`, `audioEnhancement`, `gestureCommandsEnabled`, `subtitlesEnabled`, `subtitleStyle`, `backgroundMusic`, `colorGrading`).
  - `EdlTemplate`: `{ logo?, logoPosition?, speakerName?, speakerTitle? }`.
  - `EdlDto`: Backend'den dönen üst sarmalayıcı (`projectId`, `versiyon`, `edl: EdlContent`, `guncellemeTarihi`).
  - `EdlContent`: Tüm EDL ağacı (`projectId`, `videoId`, `sourceVideoUrl`, `duration`, `settings`, `cuts`, `overlays`, `transcript`, `repurposing`, `suggestions`, `template`, `audioPeaks: number[]`).
  - `EdlPatchDto`: Parçalı güncelleme (Delta Patch) modeli (`cuts?: (CutItem & { action?: 'add' | 'update' | 'remove' })[]`, `overlays?: (OverlayItem & { action?: 'add' | 'update' | 'remove' })[]`, `suggestions?: ...`, `settings?: Partial<EdlSettings>`).

#### 13) `src/app/core/models/project.model.ts`
- **Amacı:** Proje durumlarını, hedef video formatlarını ve proje CRUD DTO'larını tanımlar.
- **Enum ve Arayüzler:**
  - `enum ProjectDurumu`: `'Taslak'`, `'VideoYuklendi'`, `'AnalizEdiliyor'`, `'AnalizTamamlandi'`, `'RenderEdiliyor'`, `'Tamamlandi'`, `'Hata'`.
  - `enum VideoFormati`: `'Yatay_16_9'`, `'Dikey_9_16'`, `'Kare_1_1'`.
  - `ProjectListDto`: Liste görünümü için özet model (`id`, `ad`, `aciklama`, `durum`, `videoFormati`, `videoSayisi`, `olusturulmaTarihi`, `guncellenmeTarihi`).
  - `ProjectDetailDto`: Detay görünümü modeli (`id`, `ad`, `aciklama`, `durum`, `videoFormati`, `templateId`, `templateAdi`, `gestureCommandsEnabled`, `audioEnhancementEnabled`, `olusturulmaTarihi`, `guncellenmeTarihi`, `hasEdl`, `hasVideo`, `hasRenderOutput`).
  - `ProjectCreateDto` & `ProjectUpdateDto`: Oluşturma ve güncelleme istek gövdeleri.

#### 14) `src/app/core/models/render.model.ts`
- **Amacı:** FFmpeg dışa aktarma (render) işlerinin durumunu ve tamamlanma sinyallerini modeller.
- **Enum ve Arayüzler:**
  - `enum RenderDurumu`: `'Kuyrukta'`, `'RenderEdiliyor'`, `'Tamamlandi'`, `'Hata'`.
  - `RenderStatusDto`: `{ renderJobId, projectId, durum, ciktiYolu?, baslangicZamani?, bitisZamani?, sureMs?, hataMesaji? }`.
  - `RenderRequestDto`: `{ targetFormat?: string; templateId?: string; }`.
  - `RenderCompletedSignalDto`: `{ renderJobId, projectId, indirmeUrl }`.

#### 15) `src/app/core/models/template.model.ts`
- **Amacı:** Kurumsal video şablonlarını modeller.
- **Arayüz:** `TemplateDto`: `{ id, ad, aciklama?, videoFormati: number, logoYolu?, logoKonumu?, varsayilanAltyaziStili?, altBantSablonu? }`.

#### 16) `src/app/core/models/video.model.ts`
- **Amacı:** Kaynak video detaylarını ve yükleme yanıtını modeller.
- **Arayüzler:**
  - `VideoDetailDto`: `{ id, projectId, baslik, dosyaYolu, temizSesYolu?, sure?, dosyaBoyutu, islemDurumu, transkriptVar, olusturmaTarihi, islemTamamlanmaTarihi?, streamUrl? }`.
  - `VideoUploadResponseDto`: `{ videoId, projectId, dosyaYolu, durum, mesaj }`.

---

### 2.4. Core Katmanı - Servisler (`src/app/core/services/`)

#### 17) `src/app/core/services/api.service.ts`
- **Amacı:** `HttpClient` üzerinde `environment.apiUrl` (`/api`) önekini otomatik kullanan jenerik HTTP sarmalayıcı (wrapper) servistir.
- **Servis:** `ApiService` (`@Injectable({ providedIn: 'root' })`)
- **Metodlar:**
  - `get<T>(path: string, params?: HttpParams | { ... }): Observable<T>`: `GET /api${path}` çağrısı yapar.
  - `post<T>(path: string, body: any): Observable<T>`: `POST /api${path}` çağrısı yapar.
  - `patch<T>(path: string, body: any): Observable<T>`: `PATCH /api${path}` çağrısı yapar.
  - `put<T>(path: string, body: any): Observable<T>`: `PUT /api${path}` çağrısı yapar.
  - `delete<T>(path: string): Observable<T>`: `DELETE /api${path}` çağrısı yapar.

#### 18) `src/app/core/services/asset.service.ts`
- **Amacı:** Proje medya varlıklarının (görsel, ses, video) listelenmesi, yüklenmesi ve silinmesi işlemlerini yürütür.
- **Servis:** `AssetService` (`providedIn: 'root'`)
- **Metodlar:**
  - `getAssets(projectId: string): Observable<ProjectAssetDto[]>`: `GET /projects/${projectId}/assets` ile varlık listesini getirir.
  - `uploadAsset(projectId: string, file: File): Observable<ProjectAssetDto>`: `FormData` içine `'file'` alanıyla dosyayı ekleyip `POST /projects/${projectId}/assets` uç noktasına gönderir.
  - `deleteAsset(projectId: string, assetId: string): Observable<void>`: `DELETE /projects/${projectId}/assets/${assetId}` ile varlığı siler.

#### 19) `src/app/core/services/chat.service.ts`
- **Amacı:** Yönetmen AI sohbet uç noktalarıyla iletişim kurar.
- **Servis:** `ChatService` (`providedIn: 'root'`)
- **Metodlar:**
  - `sendMessage(projectId: string, mesaj: string): Observable<ChatResponseDto>`: Kullanıcının doğal dil komutunu `{ mesaj }` gövdesiyle `POST /projects/${projectId}/chat` adresine gönderir.
  - `getHistory(projectId: string): Observable<ChatMessageDto[]>`: `GET /projects/${projectId}/chat` ile geçmiş sohbet mesajlarını çeker.
  - `applyPendingPatch(projectId: string, messageId: string): Observable<any>`: Onay bekleyen (`pending`) bir EDL yamasını `POST /projects/${projectId}/chat/${messageId}/apply` ile kalıcı olarak uygular.
  - `submitForm(projectId: string, messageId: string, parameters: { [key: string]: string }): Observable<any>`: AI'ın istediği netleştirme (clarification) formu verilerini `POST /projects/${projectId}/chat/${messageId}/form` adresine gönderir.

#### 20) `src/app/core/services/diagnostics.service.ts`
- **Amacı:** Editör içindeki önemli kullanıcı ve sistem aksiyonlarını (geometri yüklenmesi, inspector değişiklikleri vb.) izlemek ve tarayıcı konsolundan (`window.__OTOEDIT_DIAGNOSTICS__`) hata ayıklama (debugging) yapılmasını sağlamak.
- **Arayüz:** `TraceEvent` (`traceId`, `timestamp`, `stage`, `component`, `action`, `input`, `output?`, `persistedState?`).
- **Servis:** `DiagnosticsService` (`providedIn: 'root'`)
- **Metodlar:**
  - `constructor()`: `window.__OTOEDIT_DIAGNOSTICS__` nesnesini oluşturur ve içine `getTraces`, `clearTraces`, `inspectLast`, `printSummary` yardımcılarını bağlar.
  - `logTrace(stage: string, action: string, input: any, output?: any, persistedState?: any): void`: Benzersiz bir `traceId` üretir, son 500 iz kaydını bellekte tutar ve `console.groupCollapsed` ile girdi/çıktı/durum verilerini konsola yazar.
  - `printSummary(): void`: Tüm iz kayıtlarını `console.table` formatında özetler.

#### 21) `src/app/core/services/edl.service.ts`
- **Amacı:** Projenin EDL (Edit Decision List) belgesini okumak, parçalı yama (`PATCH`) uygulamak ve Geri Al / İleri Al (`Undo / Redo`) işlemlerini tetiklemek.
- **Servis:** `EdlService` (`providedIn: 'root'`)
- **Metodlar:**
  - `getEdl(projectId: string): Observable<EdlDto>`: `GET /projects/${projectId}/edl` ile güncel EDL ve versiyonunu getirir.
  - `patchEdl(projectId: string, patch: EdlPatchDto): Observable<{ versiyon: number }>`: `PATCH /projects/${projectId}/edl` ile kesim, katman, altyazı veya ayar değişikliklerini gönderir.
  - `undoEdl(projectId: string): Observable<EdlDto>`: `POST /projects/${projectId}/edl/undo` ile bir önceki EDL versiyonuna döner.
  - `redoEdl(projectId: string): Observable<EdlDto>`: `POST /projects/${projectId}/edl/redo` ile geri alınan EDL versiyonunu ileri alır.

#### 22) `src/app/core/services/project.service.ts`
- **Amacı:** Proje CRUD işlemlerini yürütür.
- **Servis:** `ProjectService` (`providedIn: 'root'`)
- **Metodlar:**
  - `getAll(): Observable<ProjectListDto[]>`: `GET /projects`
  - `getById(id: string): Observable<ProjectDetailDto>`: `GET /projects/${id}`
  - `create(dto: ProjectCreateDto): Observable<ProjectDetailDto>`: `POST /projects`
  - `update(id: string, dto: ProjectUpdateDto): Observable<ProjectDetailDto>`: `PUT /projects/${id}`
  - `delete(id: string): Observable<void>`: `DELETE /projects/${id}`

#### 23) `src/app/core/services/render.service.ts`
- **Amacı:** Nihai video render (dışa aktarma) talebi oluşturmak, durum sorgulamak ve indirme bağlantısını almak.
- **Servis:** `RenderService` (`providedIn: 'root'`)
- **Metodlar:**
  - `requestRender(projectId: string, dto?: RenderRequestDto): Observable<RenderStatusDto>`: `POST /projects/${projectId}/render` ile yeni bir render işi başlatır.
  - `getRenderStatus(projectId: string, renderJobId: string): Observable<RenderStatusDto>`: `GET /projects/${projectId}/render/${renderJobId}` ile render durumunu sorgular.
  - `getDownloadUrl(projectId: string, renderJobId: string): Observable<{ downloadUrl: string }>`: `GET /projects/${projectId}/render/${renderJobId}/download` ile tamamlanan videonun indirme/stream URL'sini alır.

#### 24) `src/app/core/services/signalr.service.ts`
- **Amacı:** Backend'deki `/pipeline-hub` SignalR Hub'ına bağlanarak yapay zeka analiz ve FFmpeg render ilerlemelerini gerçek zamanlı olarak dinler; bağlantı koptuğunda otomatik yeniden bağlanır ve aktif proje odalarına (`JoinProjectGroup`) tekrar katılır.
- **Arayüzler:**
  - `AnalysisProgressEvent`: `{ projectId: string; asama: string; yuzde: number; mesaj?: string; }`
  - `AnalysisCompletedEvent`: `{ projectId: string; edlVersiyon: number; }`
  - `RenderProgressEvent`: `{ renderJobId: string; projectId: string; yuzde: number; mesaj?: string; }`
  - `RenderCompletedEvent`: `{ renderJobId: string; projectId: string; indirmeUrl: string; }`
  - `PipelineErrorEvent`: `{ projectId: string; videoId?: string; hataMesaji: string; }`
- **Servis:** `SignalrService` (`providedIn: 'root'`)
- **Sinyaller ve RxJS Subject'ler:**
  - `isConnected = signal<boolean>(false)`
  - `currentAnalysisProgress = signal<AnalysisProgressEvent | null>(null)`
  - `currentRenderProgress = signal<RenderProgressEvent | null>(null)`
  - `analysisProgress$ = new Subject<AnalysisProgressEvent>()`
  - `analysisCompleted$ = new Subject<AnalysisCompletedEvent>()`
  - `renderProgress$ = new Subject<RenderProgressEvent>()`
  - `renderCompleted$ = new Subject<RenderCompletedEvent>()`
  - `pipelineError$ = new Subject<PipelineErrorEvent>()`
  - `activeProjectGroups = new Set<string>()`
- **Metodlar:**
  - `constructor()`: `initConnection()` metodunu çağırır.
  - `private initConnection(): void`: `HubConnectionBuilder` ile WebSockets + LongPolling destekli ve `[0, 2000, 5000, 10000, 30000]` ms otomatik yeniden bağlanma politikasına sahip bağlantıyı kurar, `registerHandlers()` ve `startConnection()` çağırır.
  - `private registerHandlers(): void`: Hub üzerindeki `'AnalysisProgress'`, `'AnalysisCompleted'`, `'RenderProgress'`, `'RenderCompleted'`, `'PipelineError'` olaylarını dinleyip ilgili Signal ve Subject'leri tetikler. Ayrıca `onreconnecting`, `onreconnected` (bu durumda `rejoinActiveGroups()` çağrılır) ve `onclose` durumlarını yönetir.
  - `private async startConnection(): Promise<void>`: Bağlantıyı başlatır, hata alırsa 5 saniye sonra tekrar dener.
  - `private async rejoinActiveGroups(): Promise<void>`: Yeniden bağlanma sonrası `activeProjectGroups` kümesindeki tüm `projectId`'ler için Hub üzerinde `'JoinProjectGroup'` metodunu çağırır.
  - `async joinProjectGroup(projectId: string): Promise<void>`: Projeyi `activeProjectGroups` setine ekler ve Hub bağlıysa `'JoinProjectGroup'` invoke eder.
  - `async leaveProjectGroup(projectId: string): Promise<void>`: Projeyi `activeProjectGroups` setinden çıkarır ve Hub bağlıysa `'LeaveProjectGroup'` invoke eder.

#### 25) `src/app/core/services/template.service.ts`
- **Amacı:** Kurumsal video şablonlarını listeler ve detayını getirir.
- **Servis:** `TemplateService` (`providedIn: 'root'`)
- **Metodlar:**
  - `getAll(): Observable<TemplateDto[]>`: `GET /templates`
  - `getById(id: string): Observable<TemplateDto>`: `GET /templates/${id}`

#### 26) `src/app/core/services/video.service.ts`
- **Amacı:** Kaynak videoyu yükleme ilerlemesi (`HttpEventType.UploadProgress`) ile birlikte yüklemek ve projenin video bilgisini çekmek.
- **Servis:** `VideoService` (`providedIn: 'root'`)
- **Metodlar:**
  - `uploadVideo(projectId: string, file: File, options?: { autoJumpcut?: boolean; autoRetake?: boolean; autoBroll?: boolean; autoSubtitles?: boolean }): Observable<HttpEvent<VideoUploadResponseDto>>`:
    - `FormData` oluşturur; `file`, `autoJumpcut` (varsayılan `true`), `autoRetake` (varsayılan `true`), `autoBroll` (varsayılan `true`), `autoSubtitles` (varsayılan `false`) alanlarını ekler.
    - `POST /api/projects/${projectId}/videos` adresine `{ reportProgress: true, observe: 'events' }` seçenekleriyle gönderir.
  - `getVideo(projectId: string): Observable<VideoDetailDto>`: `GET /api/projects/${projectId}/video` ile projenin aktif video detaylarını getirir.

---

### 2.5. Shared Katmanı - Ortak Bileşenler ve Pipe'lar (`src/app/shared/`)

#### 27) `src/app/shared/components/navbar/navbar.component.ts`
- **Amacı:** Tüm ekranların üst kısmında yer alan, marka logosunu, aktif proje adını ve canlı SignalR bağlantı durumunu gösteren üst gezinme çubuğudur.
- **Bileşen:** `NavbarComponent` (`selector: 'app-navbar'`, `standalone: true`)
- **Girdiler ve Özellikler:**
  - `@Input() projectTitle?: string`: Varsa orta kısımda `/ Proje Adı` şeklinde gösterilir.
  - `readonly signalr = inject(SignalrService)`: `signalr.isConnected()` sinyaline göre sağ üstte yeşil (`Canlı Senkron`) veya yanıp sönen kehribar (`Bağlanıyor...`) durumu gösterir.

#### 28) `src/app/shared/components/progress-bar/progress-bar.component.ts`
- **Amacı:** Video yükleme, AI analizi ve FFmpeg render süreçlerinde kullanılan animasyonlu yüzdelik ilerleme çubuğudur.
- **Bileşen:** `ProgressBarComponent` (`selector: 'app-progress-bar'`, `standalone: true`)
- **Girdiler:**
  - `@Input() percentage = 0`: İlerleme yüzdesi (`0-100`).
  - `@Input() label = ''`: Sol üstte gösterilen durum metni (boşsa `'İşlem Sürüyor...'`).

#### 29) `src/app/shared/components/status-badge/status-badge.component.ts`
- **Amacı:** Proje veya Render durumunu renkli bir rozet (badge) ve yanıp sönen nokta ile görselleştirir.
- **Bileşen:** `StatusBadgeComponent` (`selector: 'app-status-badge'`, `standalone: true`)
- **Girdiler ve Getter'lar:**
  - `@Input() status: ProjectDurumu | RenderDurumu | string = ''`
  - `@Input() isRender = false`
  - `get label(): string`: Durum enum değerini Türkçe metne (`'Taslak'`, `'Video Yüklendi'`, `'Analiz Ediliyor'`, `'Analiz Hazır'`, `'Render Ediliyor'`, `'Tamamlandı'`, `'Kuyrukta'`, `'Hata'`) çevirir.
  - `get badgeClass(): string` & `get dotClass(): string`: Duruma göre zümrüt yeşili (`Tamamlandi`), mavi (`AnalizEdiliyor`/`RenderEdiliyor`), mor (`AnalizTamamlandi`), gül kırmızısı (`Hata`) veya arduvaz grisi Tailwind sınıflarını döndürür.

#### 30) `src/app/shared/pipes/duration.pipe.ts`
- **Amacı:** Saniye cinsinden sayısal süreyi `MM:SS` veya `HH:MM:SS` formatına dönüştürür.
- **Pipe:** `DurationPipe` (`name: 'duration'`, `standalone: true`)
- **Metod:** `transform(value: number | null | undefined): string`
  - Değer geçersizse `'00:00'` döner; saat varsa `HH:MM:SS`, yoksa `MM:SS` formatında sıfır dolgulu (zero-padded) metin döner.

#### 31) `src/app/shared/pipes/file-size.pipe.ts`
- **Amacı:** Bayt cinsinden dosya boyutunu okunabilir birime (`B`, `KB`, `MB`, `GB`, `TB`) dönüştürür.
- **Pipe:** `FileSizePipe` (`name: 'fileSize'`, `standalone: true`)
- **Metod:** `transform(bytes: number | null | undefined): string`
  - `1024` tabanında logaritma ile uygun birimi bulur ve virgülden sonra 1 basamakla formatlar.

---

### 2.6. Features Katmanı - Sayfa Bileşenleri (`src/app/features/`)

#### 32) `src/app/features/project-list/project-list.component.ts`
- **Amacı:** Kullanıcının mevcut kurgu projelerini listelediği, silebildiği ve modal pencere üzerinden yeni proje oluşturabildiği ana sayfa bileşenidir.
- **Bileşen:** `ProjectListComponent` (`selector: 'app-project-list'`, `standalone: true`)
- **Sinyaller ve Durumlar:**
  - `projects = signal<ProjectListDto[]>([])`
  - `loading = signal<boolean>(true)`
  - `showCreateModal = signal<boolean>(false)`
  - `creating = signal<boolean>(false)`
  - `newProject`: `{ ad: '', aciklama: '', videoFormati: VideoFormati.Yatay_16_9, gestureCommandsEnabled: true, audioEnhancementEnabled: true }`
- **Metodlar:**
  - `ngOnInit(): void`: `loadProjects()` çağırır.
  - `loadProjects(): void`: `projectService.getAll()` ile projeleri çeker ve `projects` sinyalini günceller.
  - `formatName(format: VideoFormati): string`: Enum değerini `'16:9 Yatay'`, `'9:16 Reels'` veya `'1:1 Kare'` metnine çevirir.
  - `navigateToProject(id: string): void`: `/project/${id}` sayfasına yönlendirir.
  - `deleteProject(e: Event, id: string): void`: Kart tıklamasını durdurur (`e.stopPropagation()`), onay alır ve `projectService.delete(id)` ile projeyi silip listeden çıkarır.
  - `submitCreate(): void`: Yeni proje formunu doğrular, `projectService.create(this.newProject)` çağırır ve başarılı olunca yeni oluşturulan projenin detay sayfasına (`/project/${res.id}`) yönlendirir.

#### 33) `src/app/features/project-detail/project-detail.component.ts`
- **Amacı:** Seçilen projenin detaylarını gösteren, sürükle-bırak (Drag & Drop) ile kaynak video yükleyen, "Akıllı Yönetmen Pipeline Tercihleri"ni (Jump-Cut, Retake, Oto B-Roll, Dinamik Altyazı) belirleyen, çıktı formatı ve şablon seçimi yapan ve SignalR üzerinden canlı analiz ilerlemesini gösteren bileşendir.
- **Bileşen:** `ProjectDetailComponent` (`selector: 'app-project-detail'`, `standalone: true`)
- **Sinyaller ve Özellikler:**
  - `project = signal<ProjectDetailDto | null>(null)`
  - `templates = signal<TemplateDto[]>([])`
  - `uploading = signal<boolean>(false)`
  - `uploadPercentage = signal<number>(0)`
  - `analysisPercentage = signal<number>(0)`
  - `analysisStageMessage = signal<string>('Analiz başlıyor...')`
  - `isAnalyzing = signal<boolean>(false)`
  - Pipeline Tercih Bayrakları: `autoJumpcut = true`, `autoRetake = true`, `autoBroll = true`, `autoSubtitles = false`, `isDragging = false`.
- **Metodlar:**
  - `ngOnInit(): void`: Rota parametresinden `id`'yi alır; `loadProject(id)`, `loadTemplates()` ve `setupSignalR(id)` metodlarını başlatır.
  - `ngOnDestroy(): void`: `signalr.leaveProjectGroup(id)` ile proje odasından ayrılır ve RxJS aboneliklerini temizler.
  - `private loadProject(id: string): void`: `projectService.getById(id)` ile projeyi çeker; eğer durumu `AnalizEdiliyor` ise `isAnalyzing.set(true)` yapar.
  - `private loadTemplates(): void`: `templateService.getAll()` ile kurumsal şablonları yükler.
  - `private setupSignalR(projectId: string): void`:
    - `signalr.joinProjectGroup(projectId)` çağırır.
    - `analysisCompleted$` aboneliği: Analiz bittiğinde `isAnalyzing.set(false)`, `analysisPercentage.set(100)` yapar ve `loadProject(projectId)` ile güncel proje durumunu (`hasEdl: true`, `durum: AnalizTamamlandi`) çeker.
    - `analysisProgress$` aboneliği: `isAnalyzing.set(true)`, `analysisPercentage.set(e.yuzde)` ve `analysisStageMessage.set(e.mesaj || ...)` güncellemelerini yapar.
    - `pipelineError$` aboneliği: Hata durumunda analizi durdurur ve hata mesajını ekrana yazar.
  - `canGoToEditor(): boolean`: Projede `hasEdl` doğruysa veya durum `AnalizTamamlandi`, `RenderEdiliyor` ya da `Tamamlandi` ise `"Editör & Timeline'a Git →"` butonunu aktif eder.
  - `goToEditor(): void`: `/project/${id}/editor` rotasına yönlendirir.
  - `onDragOver(e: DragEvent)`, `onDragLeave(e: DragEvent)`, `onFileDrop(e: DragEvent)`, `onFileSelected(e: Event)`, `reUpload(input: HTMLInputElement)`: Dosya sürükleme ve seçme olaylarını yönetip `uploadFile(file)` metodunu tetikler.
  - `private uploadFile(file: File): void`: `videoService.uploadVideo(p.id, file, { autoJumpcut, autoRetake, autoBroll, autoSubtitles })` çağırır. `HttpEventType.UploadProgress` olaylarında `uploadPercentage` sinyalini günceller; `HttpEventType.Response` geldiğinde yüklemeyi bitirip `isAnalyzing.set(true)` ile AI analiz izleme moduna geçer.
  - `updateFormat(format: VideoFormati): void`: `projectService.update()` ile projenin video formatını (`16:9`, `9:16`, `1:1`) günceller.
  - `selectTemplate(templateId: string): void`: `projectService.update()` ile projeye kurumsal şablon atar.

#### 34) `src/app/features/render-result/render-result.component.ts`
- **Amacı:** Başlatılan FFmpeg dışa aktarma (render) işleminin ilerlemesini hem SignalR hem de periyodik yoklama (polling) ile takip eden, tamamlandığında nihai videoyu `<video>` oynatıcısında önizleten ve MP4 olarak indirme imkanı sunan bileşendir.
- **Bileşen:** `RenderResultComponent` (`selector: 'app-render-result'`, `standalone: true`)
- **Sinyaller ve Özellikler:**
  - `projectId = ''`, `renderJobId = ''`
  - `renderStatus = signal<RenderStatusDto | null>(null)`
  - `renderPercentage = signal<number>(20)`
  - `downloadUrl = signal<string>('')`
- **Metodlar:**
  - `ngOnInit(): void`: URL'den `id` ve `renderJobId` parametrelerini alır; `checkStatus()`, `setupSignalR()` ve `startPolling()` başlatır.
  - `ngOnDestroy(): void`: SignalR proje grubundan çıkar, `pollTimer` zamanlayıcısını ve abonelikleri temizler.
  - `private startPolling(): void`: Her 3 saniyede bir (`setInterval(..., 3000)`) `checkStatus()` çağırır; durum `Tamamlandi` veya `Hata` olduğunda zamanlayıcıyı durdurur (SignalR mesajı kaçırılsa bile kesintisiz durum takibi sağlar).
  - `private checkStatus(): void`: `renderService.getRenderStatus(projectId, renderJobId)` çağırır. Durum `Tamamlandi` ise `renderPercentage.set(100)` yapar ve `fetchDownloadUrl()` tetikler.
  - `private fetchDownloadUrl(): void`: `renderService.getDownloadUrl(projectId, renderJobId)` ile nihai video URL'sini alıp `downloadUrl` sinyaline yazar.
  - `private setupSignalR(): void`: `renderCompleted$` ve `renderProgress$` akışlarını dinleyerek gerçek zamanlı yüzde artışını ve tamamlanma durumunu yakalar.
  - `isRendering(): boolean`, `isCompleted(): boolean`, `isFailed(): boolean`: Şablon görünürlük yardımcıları.
  - `retryRender(): void`: Hata durumunda `renderService.requestRender(this.projectId)` ile yeni bir render işi başlatır.

#### 35) `src/app/features/editor/editor.component.ts` (ve `editor.component.ts.bak`)
- **Not:** `editor.component.ts.bak` dosyası, editör bileşeninin önceki bir geliştirme aşamasından kalan 3034 satırlık yedek dosyasıdır ve uygulama tarafından import edilmez. Aktif kullanılan dosya 6142 satırlık `editor.component.ts` dosyasıdır.
- **Amacı:** CapCut / Premiere Pro tarzı çok kanallı (Multi-Track NLE) zaman çizelgesi, gerçek zamanlı kesim atlamalı EDL video önizleme monitörü, Web Audio API ses dalga formu (waveform) çizimi, AI Kurgu Asistanı (sohbet, önizleme, clarification formu ve 16:9 mini sahne), Karaoke altyazı stüdyosu, serbest metin/görsel katman (overlay) düzenleyicisi, arka plan müziği (Auto-Ducking) ve renk düzenleme (Color Grading) özelliklerinin tamamını barındıran ana kurgu stüdyosudur.
- **Yardımcı Arayüz:**
  - `ContextMenuState`: Sağ tık bağlam menüsü durumu (`visible`, `x`, `y`, `type: 'clip' | 'overlay' | 'timeline'`, `targetClip?`, `targetOverlay?`, `seekTime?`).
- **Sinyaller (Signals) ve Hesaplanmış Sinyaller (Computed Signals):**
  - **Proje, Video & EDL:** `project`, `edl`, `previewEdl`, `previewMessageId`, `activeEdl` (`computed`: `previewEdl() || edl()`), `videoUrl`, `videoAspectRatio` (`'16 / 9'`), `currentTime`, `totalDuration`, `isPlaying`, `playbackSpeed`, `rendering`.
  - **Ses Dalga Formu:** `audioPeaks = signal<number[] | null>(null)`, `isWaveformLoading = signal<boolean>(false)`.
  - **Altyazı & Karaoke Stüdyosu:** `showSubtitles`, `subtitlePreset` (`'tiktok_yellow' | 'cinematic_shadow' | 'opaque_banner' | 'neon_glow' | 'custom'`), `subtitleFont`, `subtitleFontSize`, `subtitleColor`, `subtitleHighlightColor`, `subtitleStrokeColor`, `subtitleStrokeWidth`, `subtitleShadowColor`, `subtitleShadowBlur`, `subtitleBgColor`, `subtitleBgPadding`, `subtitleBorderRadius`, `subtitleAllCaps`, `subtitleLetterSpacing`, `subtitlePositionY`, `currentSubtitleSegment` (`computed`), `vttTrackUrl` (`computed`), `selectedSubtitleId`, `selectedSubtitleIndex`, `selectedSubtitle` (`computed`), `editingSubtitleId`.
  - **Arka Plan Müziği (BGM):** `bgmUrl`, `bgmTitle`, `bgmVolume`, `bgmAutoDucking`, `bgmDuckingAmount`, `isBgmSelectorOpen`.
  - **Renk Düzenleme (Color Grading):** `showColorModal`, `videoBrightness`, `videoContrast`, `videoSaturation`, `videoTemperature`, `isColorGraded` (`computed`), `videoFilterStyle` (`computed`: CSS `brightness() contrast() saturate() hue-rotate()` üretir).
  - **Katmanlar (Overlays) & Çoklu Kanal:** `customTrackCount` (`3`), `overlayTrackNumbers` (`computed`), `hiddenTracks` (`Set<number>`), `lockedTracks` (`Set<number>`), `activeOverlays` (`computed`: gizli olmayan kanallardaki o anki zamana düşen katmanlar), `selectedOverlayId`, `selectedOverlay` (`computed`), `ghostPreview` (`computed`: AI clarification formu açıkken video üzerinde canlı taslak katman gösterir).
  - **Timeline, Ripple & Kesimler:** `timelineZoom`, `audioTrackHeight`, `splitMarkers` (`number[]`), `selectedClipIds` (`string[]`), `selectedHasCuts` (`computed`), `selectedHasKeep` (`computed`), `rippleAi` (`true`), `rippleManual` (`true`), `rippleRetake` (`true`), `clips` (`computed`: `0`, `totalDuration`, `splitMarkers` ve `edl.cuts` sınır noktalarını birleştirip ardışık klip nesneleri üretir), `visibleDuration` (`computed`: görünür kliplerin toplam süresi), `timelineRulerMarks` (`computed`), `retakeCount` (`computed`), `autoCuts` (`computed`), `shortCuts` (`computed`: `< 1.0s`), `longCuts` (`computed`: `>= 1.0s`), `showCutAdjustModal`, `showRestoreDropdown`, `cutAdjustScope`, `cutStartOffsetMs`, `cutEndOffsetMs`, `cutAdjustLoading`.
  - **Sol Panel, Medya, Stok & Chat:** `activeTab` (`'chat' | 'overlays' | 'inspector' | 'media' | 'transcript'`), `assets`, `isUploadingAsset`, `isDragOver`, `selectedStockCategory`, `currentCategoryImages` (`computed`), `transcriptSearchQuery`, `filteredTranscriptSegments` (`computed`), `chatMessages`, `chatLoading`, `contextMenu`.
- **Metodların Tam Listesi ve İşlevleri:**
  1. **Yaşam Döngüsü ve Veri Yükleme:**
     - `ngOnInit()`: `projectId`'yi alır; `loadProject()`, `loadVideo()`, `loadEdl()`, `loadChatHistory()`, `loadAssets()` ve `signalr.joinProjectGroup(projectId)` çağırır.
     - `ngOnDestroy()`: SignalR grubundan çıkar ve abonelikleri sonlandırır.
     - `loadProject()`: `projectService.getById(projectId)` ile proje bilgisini çeker.
     - `loadVideo()`: `videoService.getVideo(projectId)` ile video detayını alır, `/api/videos/${v.id}/stream?apiKey=${apiKey}` akış URL'sini oluşturur, `loadAudioWaveform(streamUrl)` başlatır ve `v.sure` değerinden `totalDuration` hesaplar.
     - `loadEdl()`: `edlService.getEdl(projectId)` ile EDL'i çeker. Çakışan katmanları `autoAssignOverlayTracks()` ile farklı kanallara (`trackId`) dağıtır; altyazı stili, BGM, Color Grading ve `audioPeaks` verilerini sinyallere yükler.
  2. **Scrubbing (İmleç Sürükleme) ve Zaman Dönüşüm Metodları (TimelineMapper Mantığı):**
     - `startScrubbing(clientX: number)`: Video oynuyorsa duraklatır (`wasPlayingBeforeScrub = true`), tıklanan X koordinatındaki zamanı `getTimeAtClientX(clientX)` ile bulup `currentTime` ve `video.currentTime` değerlerini günceller.
     - `handleScrubMouseMove(clientX: number)`: Sürükleme sırasında `requestAnimationFrame` ve varsa `video.fastSeek()` kullanarak donma yapmadan akıcı kare önizlemesi sağlar.
     - `handleScrubMouseUp()`: Sürüklemeyi bitirir; sürükleme öncesi video oynuyorsa kaldığı yerden oynatmaya devam eder.
     - `onPlayheadPointerDown(event)`, `onPlayheadPointerMove(event)`, `onPlayheadPointerUp(event)`, `onPlayheadDragStart(event)`, `onRulerMouseDown(event)`, `onTimelineTrackMouseDown(event)`: Playhead, cetvel ve boş timeline alanı üzerindeki fare/pointer yakalama (`setPointerCapture`) olaylarını yönetir.
     - `isAnyRippleActive(): boolean`: `rippleAi() || rippleManual() || rippleRetake()` durumunu döner.
     - `getRawTimeFromVisTime(visTime: number): number`: Ripple (sıkıştırma) aktifken, sıkıştırılmış (görünür) timeline zamanını (`visTime`) ham video zamanına (`rawTime`) dönüştürür. Görünür kliplerin sürelerini toplayarak hedef zamanın hangi klibin içine düştüğünü bulur.
     - `getVisTimeFromRawTime(rawTime: number): number`: Ham video zamanını (`rawTime`), kesilmiş ve gizlenmiş klipleri hariç tutarak sıkıştırılmış timeline zamanına (`visTime`) dönüştürür.
     - `getTimeAtClientX(clientX: number): number`: Fare X koordinatının timeline genişliğine oranını (`0..1`) hesaplar; Ripple aktifse `percentage * visibleDuration()` üzerinden `getRawTimeFromVisTime()` çağırır, değilse `percentage * totalDuration()` döner.
     - `getPlayheadPosition(): number`: Playhead iğnesinin yüzdelik (`0..100%`) sol konumunu hesaplar.
     - `seekTimeline(event: MouseEvent)`: Timeline'a tek tıklandığında seçimleri temizler ve o noktaya atlar.
  3. **Oynatma, Canlı EDL Simülasyonu ve Ses Dalga Formu (Waveform):**
     - `onTimeUpdate()`: Video oynarken her `timeupdate` olayında `currentTime` sinyalini günceller. O anki zamanın düştüğü klibi bulur; eğer klip kesilmiş ve gizlenmişse (`!this.isVisible(currentClip)`), ardışık gelen tüm kesilmiş klipleri birleştirip sonuna `+ 0.04s` (1 kare tampon) ekleyerek `video.currentTime = finalJumpTime` ile kesimi anında atlar!
     - `onVideoSeeked()`: `isSkippingCut = false` yaparak seek kilidini açar.
     - `onMetadataLoaded()`: Videonun gerçek genişlik/yükseklik oranını (`videoAspectRatio`) ve süresini (`totalDuration`) okur, `DiagnosticsService`'e kaydeder.
     - `loadAudioWaveform(url: string)`: Eğer EDL içinde hazır `audioPeaks` yoksa, video akışını `fetch` ile `ArrayBuffer` olarak indirir, `AudioContext.decodeAudioData` ile çözer, saniyede ~50 örnek (maksimum 10.000 nokta) olacak şekilde RMS + Peak hibrit hesaplamasıyla gerçek ses dalga formunu üretir. Hata olursa `generateFallbackWaveform()` çağırır.
     - `generateFallbackWaveform()`: Transkriptteki konuşma ve kesim bölgelerine göre sentetik dalga formu üretir.
     - `getWaveformPathForClip(clip: any): string`: Her bir klibin başlangıç ve bitiş zamanına karşılık gelen `audioPeaks` dilimini alır ve `viewBox="0 0 100 56"` ölçeğinde SVG `<path d="...">` komutu üretir.
     - `togglePlayPause()`, `skipSeconds(seconds: number)`, `cyclePlaybackSpeed()`, `setPlaybackSpeed(speed: number)`, `toggleFullscreen()`, `seekToTranscript(time: number)`: Oynatma kontrolleri.
  4. **Klip İşlemleri (Bölme, Kesme, Geri Yükleme, Birleştirme, Toplu Milisaniye Trim, Undo/Redo):**
     - `getClipLeft(clip)`, `getClipWidth(clip)`, `isVisible(clip)`, `isRetakeClip(clip)`, `isManualClip(clip)`, `getClipTooltip(clip)`: Klip görünüm ve konum hesaplamaları.
     - `selectClip(clipId: string, event: MouseEvent)`: Tekli seçim, `Ctrl` ile çoklu seçim ve `Shift` ile aralık seçimi yapar.
     - `addSplitMarker()` & `splitClipAtPlayhead(clip)`: `currentTime()` noktasına yerel bir bölme işareti (`splitMarkers`) ekleyerek klibi iki ayrı parçaya böler (`B` kısayolu).
     - `rippleDeleteLeft()`: İmlecin bulunduğu sağlam klibin başlangıcından imlecin olduğu saniyeye kadar olan sol kısmı keser ve `patchEdl` ile kaydeder (`V` kısayolu).
     - `toggleClip(clip, event)`, `deleteClip(clip)`, `deleteSelectedClips()`: Sağlam klibi/klipleri `manual_cut_...` olarak `edl.cuts` listesine ekler (`Del` kısayolu).
     - `restoreClip(clip)`, `restoreSelectedCuts()`: Kesilmiş klipleri `action: 'remove'` yamasıyla `edl.cuts` listesinden kaldırarak sahneyi geri yükler.
     - `mergeSelectedClips()`: Seçili klipler arasındaki tüm kesimleri (`cutsToRemove`) kaldırarak klipleri tek parça halinde birleştirir (`M` kısayolu).
     - `deleteRetakeCuts()`: Sebebi `retake`/`tekrar` olan tüm kesimleri topluca iptal eder.
     - `restoreCutsByScope(scope: 'short' | 'long' | 'all')`: 1 saniyeden kısa, 1 saniyeden uzun veya tüm otomatik kesimleri topluca geri alır.
     - `openCutAdjustModal()`, `resetCutAdjustOffsets()`, `onCutStartInput()`, `onCutEndInput()`, `getTargetCutsCount()`, `applyBatchCutAdjustment()`: Seçilen kapsamdaki (`short`, `long`, `all`) otomatik kesimlerin başlangıç ve bitiş zamanlarını milisaniye bazında (`cutStartOffsetMs`, `cutEndOffsetMs`) kaydırır; süresi 60ms altına düşen kesimleri otomatik siler.
     - `undo()` & `redo()`: `edlService.undoEdl()` ve `edlService.redoEdl()` çağırarak EDL geçmişinde ileri/geri gider (`Ctrl+Z` / `Ctrl+Y`).
  5. **Altyazı (Subtitle) & Karaoke Stüdyosu Metodları:**
     - `getSubtitleLeft(seg)`, `getSubtitleWidth(seg)`, `getSubtitleId(seg)`, `getVisibleSubtitleSegments()`: Altyazıların timeline üzerindeki konumlarını ve görünürlüklerini hesaplar.
     - `selectSubtitle(seg, index?)`, `clearSubtitleSelection()`, `isSelectedSubtitle(seg)`: Altyazıyı seçer, sağ Inspector panelini altyazı moduna geçirir ve videoyu o saniyeye sarar.
     - `startEditSubtitle(seg)`, `cancelSubtitleEdit()`, `saveSubtitleEdit(seg, newText)`: Timeline üzerinde çift tıklanan altyazıyı satır içi (inline `<input>`) düzenler ve `patchEdl` ile kaydeder.
     - `onSubtitleTextChange()`, `onSubtitleStartChange()`, `onSubtitleEndChange()`, `onSubtitleDurationChange()`, `saveSubtitleInspector()`: Sağ Inspector panelinden yapılan metin ve başlangıç/bitiş/süre değişikliklerini yönetir ve kaydeder.
     - `onSubtitleDragStart(event, seg)`, `onSubtitleResizeStart(event, seg, edge)`: Altyazı segmentini timeline üzerinde sürükleyerek zamanını kaydırır veya sağ/sol kenarlarından süresini uzatıp kısaltır.
     - `applySubtitlePreset(preset)`, `persistSubtitleStyle()`, `initSubtitleStyleFromSettings(cfg)`: `'tiktok_yellow'`, `'cinematic_shadow'`, `'opaque_banner'`, `'neon_glow'` hazır şablonlarını veya özel stil ayarlarını (`settings.subtitleStyle`) EDL'e kaydeder.
     - `convertSubtitleToOverlay()`: Seçili altyazı segmentini transkriptten çıkarıp bağımsız hareket edebilen, animasyonlu bir serbest metin katmanına (`OverlayItem`) dönüştürür.
     - `deleteSubtitleSegment()`: Seçili altyazı segmentini transkriptten siler.
     - `isWordActive(word: TranscriptWord): boolean`: Oynatma sırasında `t >= (word.start - 0.05) && t <= (word.end + 0.05)` kontrolüyle aktif kelimeyi Karaoke tarzı vurgular.
     - `toggleSubtitles()`: Altyazıları açıp kapatır ve `settings.subtitlesEnabled` değerini backend'e kaydeder (`C` kısayolu).
     - `formatVttTimestamp(seconds)`: Saniyeyi WebVTT zaman formatına (`HH:MM:SS.mmm`) çevirir.
  6. **Metin ve Görsel/B-Roll Katmanları (Overlays) & Çoklu Kanal Metodları:**
     - `autoAssignOverlayTracks(overlays)`: Zamanları kesişen (çakışan) katmanları tespit edip otomatik olarak bir üst kanala (`T1 -> T2 -> T3...`) yerleştirir.
     - `addTrackLane()`, `removeTrackLane()`, `deleteTrackLane(trackNum)`: Yeni katman kanalı ekler veya mevcut bir kanalı içindeki katmanlarla birlikte silip üst kanalların numaralarını bir aşağı kaydırır.
     - `isTrackHidden(trackNum)`, `isTrackLocked(trackNum)`, `toggleTrackVisibility(trackNum)`, `toggleTrackLock(trackNum)`: Kanal bazlı gizleme (göz ikonu) ve kilitleme (kilit ikonu) kontrolleri.
     - `addTextOverlay()`, `addImageOverlay()`, `addImageOverlayFromUrl(url, contentName)`, `addAssetOverlay(asset)`: İmlecin bulunduğu saniyeye (veya seçili klip aralığına) çakışmayan ilk uygun kanalda yeni metin veya görsel katmanı ekler.
     - `selectOverlay(id)`, `onInspectorChange()`, `saveInspector()`, `cancelInspector()`: Seçilen katmanın tüm özelliklerini (tipografi, hap/rozet kutu, kontur, AI arka plan silme `removeBg`, sticker kenarlığı, döndürme `rotation`, şekil maskesi `maskShape`, giriş/çıkış animasyonu) sağ Inspector paneline bağlar, canlı önizletir ve kaydeder.
     - `duplicateOverlay(overlayId)`: Katmanı 1 saniye sonrasına kopyalar (`Ctrl+D`).
     - `splitOverlayAtPlayhead(ov)`: Katmanı imleç noktasından iki ayrı katmana böler.
     - `bringOverlayForward(overlayId)`, `sendOverlayBackward(overlayId)`, `setOverlayTrack(overlayId, trackId)`, `getOverlaysForTrack(trackNum)`: Katmanın kanal (`trackId`) ve Z-index sırasını değiştirir.
     - `removeOverlay(overlayId)`: Katmanı siler.
     - `onCanvasDragStart(event, overlayId)`, `onCanvasResizeStart(event, overlayId)`: Video önizleme monitörü (Canvas) üzerinde katmanı fareyle sürükleyerek X/Y yüzdesel konumunu değiştirir veya sağ alt tutamaçtan boyutunu (`scale` / `fontSize`) büyütüp küçültür.
     - `onOverlayDragStart(event, overlayId)`, `onOverlayResizeStart(event, overlayId, edge)`: Timeline üzerinde katman kutusunu yatayda (zaman) ve dikeyde (kanal `T1..Tn`) sürükler veya kenarlarından süresini değiştirir.
  7. **Yönetmen AI Sohbet ve Dinamik Form Metodları:**
     - `loadChatHistory()`, `setPrompt(p)`, `sendChatMessage()`: Eğer timeline'da seçili klipler varsa mesajın başına `[Seçili Aralık: Xs - Ys]` bağlamını otomatik ekler ve `chatService.sendMessage()` çağırır.
     - `previewPatch(msg)`, `applyPatch(msg)`, `cancelPatch(msg)`: AI'dan dönen `pending` durumundaki yamayı mevcut EDL üzerine geçici olarak klonlayıp (`previewEdl`) videoyu değişiklikten 2 saniye öncesine sararak canlı önizletir, onaylanırsa kalıcı yapar.
     - `getMarkerPosition(msg, field)`, `onMiniStageClick(event, msg, fieldId)`, `setPresetPosition(msg, fieldId, preset)`, `getPresetCoords(preset)`, `updateFormData(msg, fieldId, val)`, `getOptValue(opt)`, `getOptLabel(opt)`, `submitForm(msg)`: AI `clarification` (netleştirme) formu döndürdüğünde 16:9 mini sahne üzerinden konum seçimi, renk paleti ve metin girişlerini yönetir; video üzerinde canlı `ghostPreview` (taslak katman) gösterir ve onaylandığında `chatService.submitForm()` ile backend'e gönderir.
  8. **BGM, Renk Düzenleme, Klavye Kısayolları ve Export:**
     - `setBgmPreset(url, title)`, `removeBgm()`, `toggleAutoDucking()`, `persistBgmSettings()`, `initBgmFromSettings(cfg)`: Arka plan müziği ve Sidechain Auto-Ducking yönetimi.
     - `resetColorGrading()`, `applyColorPreset(preset)`, `saveColorGrading()`: Doğal, Canlı, Sinematik, Soğuk, S&B renk filtreleri ve parlaklık/kontrast/doygunluk/sıcaklık ayarı.
     - `onGlobalKeyDown(event)`, `onGlobalMouseMove(event)`, `onGlobalMouseUp(event)`: Global klavye kısayolları (`Space`, `B`, `V`, `Del`, `Ctrl+D`, `M`, `C`, `T`, `Ctrl+Z`, `Ctrl+Y`, `Esc`) ve sürükleme/boyutlandırma bırakma olaylarını yönetir (`mouseup` anında yapılan değişiklikleri otomatik `patchEdl` ile backend'e kaydeder).
     - `requestExport()`: Güncel `subtitlesEnabled` ayarını EDL'e yamalar, ardından `renderService.requestRender(this.projectId)` çağırıp `/project/${this.projectId}/render/${res.renderJobId}` sayfasına yönlendirir.

---

## BÖLÜM 3: UÇTAN UCA FRONTEND KULLANICI AKIŞLARI (USER FLOWS)

### Akış 1: Video Yükleme / Proje Oluşturma ve SignalR ile Analiz İlerlemesini İzleme
1. **Proje Oluşturma (`ProjectListComponent`):**
   - Kullanıcı `"Yeni Proje Oluştur"` butonuna tıklar (`showCreateModal.set(true)`).
   - Proje adını, açıklamasını, hedef video formatını (`16:9 Yatay`, `9:16 Dikey`, `1:1 Kare`) ve pipeline özelliklerini (`gestureCommandsEnabled`, `audioEnhancementEnabled`) seçip `"Projeyi Başlat"` butonuna basar.
   - `submitCreate()` -> `ProjectService.create()` -> `POST /api/projects` çağrılır. Dönen `id` ile `/project/:id` (`ProjectDetailComponent`) sayfasına yönlendirilir.
2. **SignalR Odasına Katılma (`ProjectDetailComponent`):**
   - Sayfa açıldığında `setupSignalR(id)` çalışır ve `SignalrService.joinProjectGroup(id)` ile Hub üzerindeki `'JoinProjectGroup'` metodu çağrılarak bu projeye özel canlı bildirim odasına abone olunur.
3. **Ham Videoyu Yükleme:**
   - Kullanıcı `"Akıllı Yönetmen Pipeline Tercihleri"` bölümünden `autoJumpcut`, `autoRetake`, `autoBroll`, `autoSubtitles` kutucuklarını belirler.
   - Videoyu sürükleyip bırakır (`onFileDrop`) veya dosya seçer (`onFileSelected`).
   - `uploadFile(file)` metodu `VideoService.uploadVideo()` üzerinden `POST /api/projects/{id}/videos` isteğini `reportProgress: true` ile başlatır.
   - `HttpEventType.UploadProgress` olayları geldikçe `uploadPercentage` sinyali güncellenir ve `ProgressBarComponent` üzerinde MinIO yükleme yüzdesi gösterilir.
4. **Canlı AI Analiz Takibi:**
   - Yükleme tamamlandığında (`HttpEventType.Response`), `uploading.set(false)` ve `isAnalyzing.set(true)` olur.
   - Backend'deki `VideoProcessingWorker` analiz aşamalarını yürüttükçe SignalR üzerinden `'AnalysisProgress'` mesajları gelir. `SignalrService.analysisProgress$` akışı `analysisPercentage` ve `analysisStageMessage` sinyallerini canlı günceller.
   - Analiz bittiğinde `'AnalysisCompleted'` olayı gelir; `isAnalyzing.set(false)` olur, `loadProject(projectId)` tekrar çağrılır ve `"Editör & Timeline'a Git →"` butonu (`canGoToEditor() === true`) görünür hale gelir.

---

### Akış 2: Timeline Üzerinde Bölme (Splitting), Silme (Deleting), Kırpma (Trimming), Taşıma, Undo/Redo ve EDL & TimelineMapper Çalışma Prensibi
1. **EDL (Edit Decision List) ve Tahribatsız (Non-Destructive) Kurgu Mantığı:**
   - Frontend kaynak videoyu fiziksel olarak kesmez. Tüm kurgu kararları `EdlContent` içindeki `cuts` (kesilen aralıklar) ve `overlays` (katmanlar) dizilerinde tutulur.
   - `clips` computed sinyali; `0`, `totalDuration`, kullanıcının eklediği `splitMarkers` ve `edl.cuts` içindeki her bir kesimin `start` ve `end` noktalarını tek bir sayı doğrusunda birleştirip sıralar. Ardışık her iki nokta arasını bir `clip` nesnesi (`{ id, start, end, duration, isCut, cutObj }`) olarak üretir.
2. **TimelineMapper (Ham Zaman <-> Görünür Zaman Dönüşümü):**
   - Üst araç çubuğundaki `🤖 AI Sıkışık`, `🔄 Retake Sıkışık`, `🖐 Manuel Sıkışık` (`rippleAi`, `rippleRetake`, `rippleManual`) filtreleri aktif olduğunda, kesilen klipler timeline'da gizlenir (`isVisible(clip) === false`) ve kalan klipler sola doğru bitişik (magnetic/ripple) dizilir.
   - Bu durumda videonun ham süresi (`totalDuration`) ile timeline'ın görünür süresi (`visibleDuration`) farklılaşır:
     - `getVisTimeFromRawTime(rawTime)`: Ham video saniyesini, o saniyeye kadar olan görünür kliplerin sürelerini toplayarak timeline üzerindeki sıkıştırılmış konuma çevirir (Playhead iğnesi, altyazı ve overlay kutularının `left` ve `width` yüzdeleri bu metodla hesaplanır).
     - `getRawTimeFromVisTime(visTime)`: Kullanıcının sıkıştırılmış timeline üzerinde tıkladığı veya sürüklediği konumu tekrar gerçek video saniyesine çevirir (`getTimeAtClientX`).
3. **Bölme (Splitting - `B` Tuşu):**
   - `addSplitMarker()` veya sağ tık menüsünden `splitClipAtPlayhead()` çağrıldığında o anki `currentTime()` değeri `splitMarkers` sinyaline eklenir. `clips` computed sinyali anında yeniden hesaplanarak o klibi iki ayrı seçilebilir klibe böler.
4. **Silme / Kesme (Deleting - `Del` Tuşu veya Çift Tık):**
   - Seçili sağlam kliplerde `deleteSelectedClips()` veya `deleteClip()` çağrılır; klibin `start` ve `end` değerleriyle `{ id: 'manual_cut_...', start, end, reason: 'Manuel kesim', action: 'add' }` yaması oluşturulup `PATCH /api/projects/{id}/edl` (`edlService.patchEdl`) ile kaydedilir.
5. **Kırpma (Trimming - `V` Tuşu ve Toplu Milisaniye Trim):**
   - **Soldakini Kırp & Birleştir (`V` tuşu - `rippleDeleteLeft()`):** İmlecin bulunduğu klibin başlangıcından (`targetClip.start`) imlecin bulunduğu saniyeye (`currentTime()`) kadar olan sol parçayı tek tuşla kesip atar.
   - **Toplu Kesim İnce Ayar (`applyBatchCutAdjustment()`):** `"Kesim Payı Ayarla"` modalı üzerinden tüm kısa (`<1s`), uzun (`>=1s`) veya tüm otomatik kesimlerin başlangıç ve bitiş sınırları `-5000ms` ile `+5000ms` arasında kaydırılarak kelime yutulmaları hassas şekilde düzeltilir.
6. **Geri Yükleme ve Birleştirme (`Restore` & `M` Tuşu):**
   - Kesilmiş bir klibe çift tıklamak veya `"Kesimi İptal Et"` demek, ilgili `cut.id` için `action: 'remove'` yaması gönderir.
   - Birden fazla klip seçip `M` tuşuna basmak (`mergeSelectedClips()`), seçili kliplerin arasındaki tüm kesimleri kaldırarak klipleri birleştirir.
7. **Undo / Redo (`Ctrl+Z` / `Ctrl+Y`):**
   - `undo()` -> `POST /api/projects/{id}/edl/undo` ve `redo()` -> `POST /api/projects/{id}/edl/redo` uç noktalarını çağırarak backend'de versiyonlanan EDL geçmişinde geri ve ileri gider.

---

### Akış 3: Altyazı (Subtitle) ve Metin/Görsel/B-Roll Katmanlarını (Overlays) Ekleme, Düzenleme ve Silme
1. **Altyazı (Subtitle) İşlemleri:**
   - **Görüntüleme:** Whisper'dan gelen `edl.transcript.segments` dizisi hem sol paneldeki `"Metin"` sekmesinde, hem timeline'daki `"💬 Altyazı"` kanalında, hem de video monitörü üzerinde (kelime zamanlamaları `seg.words` varsa `isWordActive()` ile aktif kelime parlayarak Karaoke stilinde) gösterilir.
   - **Düzenleme:**
     - Timeline'daki altyazı kutusuna çift tıklanırsa satır içi `<input>` açılır (`startEditSubtitle`), `Enter` veya `blur` ile `saveSubtitleEdit()` çalışır ve güncellenmiş `transcript` `patchEdl` ile kaydedilir.
     - Altyazıya tek tıklanırsa (`selectSubtitle`), sağdaki Inspector paneli `"Altyazı Özellikleri"` moduna geçer. Buradan metin, başlangıç/bitiş/süre, hazır şablonlar (`TikTok Sarı`, `Sinematik`, `Opaque Kutu`, `Neon Glow`), dikey konum (`subtitlePositionY`), font, renk ve kontur değiştirilebilir (`persistSubtitleStyle()`).
     - Timeline üzerinde altyazı kutusu sürüklenerek zamanı kaydırılabilir (`onSubtitleDragStart`) veya sol/sağ tutamaçlarından süresi uzatılıp kısaltılabilir (`onSubtitleResizeStart`). Fare bırakıldığında (`onGlobalMouseUp`) yeni zamanlamalar `patchEdl` ile kaydedilir.
   - **Katmana Dönüştürme & Silme:** `"Serbest Katmana Dönüştür"` (`convertSubtitleToOverlay()`) ile altyazı transkriptten çıkarılıp bağımsız bir `OverlayItem`'a çevrilir. `"Bu Altyazı Segmentini Sil"` (`deleteSubtitleSegment()`) ile segment tamamen silinir.
2. **Metin, Görsel ve B-Roll Katmanı (Overlay) İşlemleri:**
   - **Ekleme:**
     - `T` tuşu veya `"+ Yazı"` butonu (`addTextOverlay()`) ile imleç konumuna yeni metin katmanı eklenir.
     - Sol paneldeki `"Medya"` sekmesinden kullanıcı kendi görsel/video/ses dosyasını yükleyebilir (`uploadFile` -> `POST /api/projects/{id}/assets`) ve `"+ Katman Ekle"` (`addAssetOverlay`) diyebilir; ya da `"B-Roll Stok Kütüphanesi"` kategorilerinden (`Hukuk`, `Teknoloji`, `Doğa`, `Tarih`, `İş`) bir görsel seçip `addImageOverlayFromUrl()` ile ekleyebilir.
     - Ekleme sırasında o saniyede başka bir katman varsa çakışmayı önlemek için otomatik olarak bir üst kanal (`nextTrack = Math.max(...usedTracks) + 1`) atanır.
   - **Taşıma ve Boyutlandırma (Canvas & Timeline):**
     - **Video Monitörü (Canvas) Üzerinde:** Katman fareyle tutulup sürüklenerek (`onCanvasDragStart`) ekran üzerindeki `positionX` ve `positionY` (`0-100%`) koordinatları değiştirilir. Seçili katmanın sağ alt köşesindeki `⤡` tutamacından (`onCanvasResizeStart`) sürüklenerek görselin `scale` değeri veya metnin `fontSize` değeri canlı büyütülüp küçültülür.
     - **Timeline Üzerinde:** Katman kutusu yatayda sürüklenerek `timestamp` değeri, dikeyde sürüklenerek bulunduğu kanal (`T1, T2, T3...`) değiştirilir (`onOverlayDragStart`). Kenarlarından tutularak (`onOverlayResizeStart`) `duration` süresi ayarlanır.
   - **Inspector Düzenleme ve Silme:** Sağ panelden içerik, font, renk, hap/rozet kutu stili (`boxStyle`), AI arka plan kaldırma (`removeBg`), beyaz sticker kenarlığı (`stickerBorder`), döndürme açısı (`rotation`), dairesel/yuvarlak maske (`maskShape`) ve giriş/çıkış animasyonları ayarlanıp kaydedilir (`saveInspector()`). `Del` tuşu veya `removeOverlay()` ile katman silinir (`action: 'remove'`).

---

### Akış 4: AI Chat / Yönetmen AI Asistanı ile Doğal Dilde Video Kurgu Akışı
1. **Komut Gönderme (`sendChatMessage`):**
   - Kullanıcı sol paneldeki `"🤖 AI Kurgu"` sekmesinden doğal dilde bir komut yazar (örn. `"Girişteki sessizlikleri kes"`, `"10. saniyeye Kanala Abone Ol yazısı koy"`).
   - Eğer kullanıcının timeline üzerinde seçtiği klipler varsa (`selectedClipIds().length > 0`), frontend mesajın başına otomatik olarak `[Seçili Aralık: 12.0s - 25.4s] ` bilgisini ekler ve `ChatService.sendMessage()` (`POST /api/projects/{id}/chat`) çağrılır.
2. **Üç Farklı Yanıt Senaryosu (`patchDurumu`):**
   - **Senaryo A - Doğrudan Uygulama (`applied`):** AI komutu doğrudan uyguladıysa `loadEdl()` çağrılır ve yeni kesim/katman anında timeline ve video üzerinde belirir.
   - **Senaryo B - Onay Bekleyen Yama (`pending`):** Mesaj balonunda `"🔍 Önizle"`, `"Onayla"` ve `"İptal"` butonları çıkar.
     - Kullanıcı `"🔍 Önizle"` (`previewPatch(msg)`) butonuna basarsa, mevcut EDL klonlanır, `msg.pendingEdlPatch` içindeki kesim ve katmanlar geçici olarak `previewEdl` sinyaline uygulanır (böylece `activeEdl` computed sinyali simüle edilen EDL'i göstermeye başlar) ve video ilgili değişikliğin 2 saniye öncesine sarılıp otomatik oynatılır.
     - `"Onayla"` (`applyPatch(msg)`) tıklanırsa `POST /api/projects/{id}/chat/{messageId}/apply` çağrılır ve yama kalıcı hale gelir. `"İptal"` (`cancelPatch(msg)`) tıklanırsa önizleme kapatılır ve yama reddedilir.
   - **Senaryo C - Eksik Bilgi / Netleştirme Formu (`clarification`):**
     - Kullanıcı örneğin `"Ekrana yazı ekle"` dediğinde ancak ne yazılacağını veya rengini/konumunu belirtmediğinde, backend `patchDurumu: 'clarification'` ve `formFields: FormFieldDto[]` döndürür.
     - Sohbet balonunun içinde dinamik bir form (`text`, `number`, `color` paleti, `select` ve `16:9 Mini Stage` konum seçici) açılır.
     - Kullanıcı bu formu doldururken ve 16:9 mini sahneye tıklarken (`onMiniStageClick`), ana video monitörü üzerinde `ghostPreview` computed sinyali sayesinde kesikli çerçeveli **`📍 Taslak` (Ghost Layer)** canlı olarak seçilen konumda, renkte ve yazı tipinde gösterilir!
     - Kullanıcı `"✨ Onayla ve Ekle"` (`submitForm(msg)`) butonuna bastığında `POST /api/projects/{id}/chat/{messageId}/form` çağrılır, katman oluşturulur ve `loadEdl()` ile timeline güncellenir.

---

### Akış 5: Şablon Uygulama, Ses Dalga Formu (Waveform) Çizimi ve Önizleme Senkronizasyonu (Kesilen Bölgeleri Atlama)
1. **Şablon Uygulama:**
   - `ProjectDetailComponent` içinde `TemplateService.getAll()` (`GET /api/templates`) ile gelen şablonlardan biri seçildiğinde (`selectTemplate(tpl.id)`), `PUT /api/projects/{id}` ile projeye bağlanır. Ayrıca `EdlContent.template` ve `SubtitleStyleConfig` / `OverlayItem` şablonları editör içinde önizlenir ve render aşamasında FFmpeg filtre grafiğine aktarılır.
2. **Ses Dalga Formu (Waveform) Çizimi:**
   - `loadEdl()` çalıştığında eğer backend analiz aşamasında `edl.audioPeaks` dizisini üretmişse doğrudan bu dizi `audioPeaks` sinyaline atanır (büyük video dosyalarını tarayıcıda tekrar indirmemek için).
   - Eğer `edl.audioPeaks` yoksa `loadAudioWaveform(streamUrl)` devreye girer: Web Audio API (`AudioContext.decodeAudioData`) ile ses kanalını çözer, saniyede 50 örnek (RMS + Peak) çıkarır. O da başarısız olursa `generateFallbackWaveform()` transkriptteki konuşma ve sessizlik aralıklarına göre yüksek yoğunluklu bir dalga formu üretir.
   - Timeline'daki her klip (`V1 Ana Video` kanalı), kendi `clip.start` ve `clip.end` aralığına düşen peak değerlerini `getWaveformPathForClip(clip)` ile alıp kırmızı-kehribar-camgöbeği gradyanlı (`waveGrad_...`) bir SVG `<path>` olarak kendi kutusunun içinde çizer.
3. **Canlı Önizleme Senkronizasyonu (Render Bekletmeden Kesim Atlama):**
   - `<video>` elementi `/api/videos/{videoId}/stream?apiKey=...` kaynağından ham videoyu oynatır.
   - Video oynarken her `timeupdate` olayında `onTimeUpdate()` tetiklenir:
     - O anki `video.currentTime` değerinin içine düştüğü klip (`currentClip`) bulunur.
     - Eğer bu klip kesilmişse ve ilgili kategori için Ripple (sıkıştırma) aktifse (`!this.isVisible(currentClip)`), oynatıcı bu klibi ve hemen peşinden gelen ardışık tüm kesilmiş klipleri tespit eder (`targetJumpTime`).
     - Sonsuz seek döngüsünü (infinite seek-loop) engellemek için hedef zamana `0.04` saniye (1 kare) tampon ekleyip `video.currentTime = finalJumpTime` ataması yapar.
     - Aynı anda `currentSubtitleSegment` (kesim içindeyse altyazıyı gizler), `activeOverlays` (gizli olmayan kanallardaki aktif katmanları gösterir) ve `videoFilterStyle` (canlı CSS Color Grading filtreleri) gerçek zamanlı olarak videonun üzerinde senkronize çalışır.

---

### Akış 6: Nihai Videoyu Dışa Aktarma (Export / Render) ve İndirme
1. **Render Talebi Başlatma (`EditorComponent.requestExport`):**
   - Kullanıcı editörün sağ üst köşesindeki `"Nihai Videoyu Render Et"` butonuna tıklar.
   - `requestExport()` önce o anki altyazı açık/kapalı durumunu (`subtitlesEnabled: this.showSubtitles()`) `edlService.patchEdl()` ile backend'e kaydeder.
   - Ardından `renderService.requestRender(this.projectId)` (`POST /api/projects/{id}/render`) çağrılır.
   - Backend işi kuyruğa alır ve `RenderStatusDto` (`renderJobId` ile birlikte) döner.
   - Uygulama kullanıcıyı `/project/:id/render/:renderJobId` (`RenderResultComponent`) rotasına yönlendirir.
2. **Render İlerlemesini İzleme (`RenderResultComponent`):**
   - Bileşen açıldığında hem `SignalrService.joinProjectGroup(projectId)` ile `'RenderProgress'` ve `'RenderCompleted'` WebSocket olaylarını dinler, hem de `startPolling()` ile her 3 saniyede bir `GET /api/projects/{id}/render/{renderJobId}` uç noktasını yoklar.
   - İlerleme yüzdesi arttıkça `renderPercentage` sinyali ve `ProgressBarComponent` güncellenir.
3. **Önizleme ve İndirme:**
   - Render durumu `RenderDurumu.Tamamlandi` olduğunda `fetchDownloadUrl()` çalışır ve `GET /api/projects/{id}/render/{renderJobId}/download` uç noktasından nihai video URL'sini (`downloadUrl`) alır.
   - Ekranda başarı mesajı belirir, nihai kurgulanmış MP4 videosu `<video controls autoplay>` bileşeninde oynatılır ve kullanıcı `"Nihai Videoyu İndir"` (`<a [href]="downloadUrl()" download="otoedit_render.mp4">`) butonuna tıklayarak videoyu bilgisayarına indirir.
