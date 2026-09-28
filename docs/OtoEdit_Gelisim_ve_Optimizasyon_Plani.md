# 🎬 OtoEdit — Kapsamlı Geliştirme, Mimari Standartlar ve Performans Optimizasyon Master Planı

> **Versiyon:** 2.0 — Performans, Stabilite ve Mimari İyileştirme Planı  
> **Tarih:** 28.09.2026 (Referans Yılı: 2026)  
> **İlgili Belgeler:**  
> - Ana Mimari Kaynağı: `D:\OtoEdit\OtoEdit\docs\gelistirici-dokumani.md`  
> - Kesin Kodlama Kuralları: `D:\OtoEdit\OtoEdit\docs\kurallar.txt`  
> - Sistem Hata Logları: `hata1.txt`, `hata2.txt`, `hata3.txt`, `hata4.txt`

---

## İÇİNDEKİLER

1. [BÖLÜM 1: PROJENİN AMACI VE OPTİMİZASYON KAPSAMI](#bölüm-1-projenin-amacı-ve-optimizasyon-kapsamı)
   - 1.1 Temel Hedef ve Problem Tanımı
   - 1.2 Mevcut Hataların ve Tıkanmaların Kök Nedenleri
   - 1.3 Sistem Ne Hedefliyor, Ne Hedeflemiyor (MVP Sınırları)
   - 1.4 Performans Metrikleri ve Hedeflenen Süreler
2. [BÖLÜM 2: KESİN OLMASI GEREKENLER VE UYULMASI GEREKEN KURALLAR](#bölüm-2-kesin-olması-gerekenler-ve-uyulması-gereken-kurallar)
   - 2.1 Doküman Sadakati ve Tek Gerçek Kaynak (Single Source of Truth)
   - 2.2 Temiz Kod (Clean Code) ve SOLID Prensipleri
   - 2.3 Performans, Caching ve I/O Kuralları
   - 2.4 Hata Yönetimi, Debug Edilebilirlik ve Üç Katmanlı Loglama Sistemi
   - 2.5 Güvenlik, Veri Bütünlüğü ve Veritabanı Standartları
   - 2.6 MVP Odaklılık, Genişletilebilirlik ve Git Sürüm Kontrolü
   - 2.7 Bölümlü Geliştirme ve Doğrulama Kuralı
   - 2.8 Çapraz Dil ve Servisler Arası İletişim Kuralları
3. [BÖLÜM 3: YENİ VE OPTİMİZE EDİLMİŞ DOSYA YAPISI](#bölüm-3-yeni-ve-optimize-edilmiş-dosya-yapısı)
   - 3.1 Solution Genel Dizin Hiyerarşisi
   - 3.2 `OtoEdit.PythonWorker` Modüler Yeni Dizin Ağacı
   - 3.3 `.NET API` ve `Data/Business` Katmanlarındaki Güncellemeler
   - 3.4 Altyapı, Konfigürasyon ve Docker Güncellemeleri
4. [BÖLÜM 4: ÜRETİM STANDARTLARINDA KOD ÖRNEKLERİ](#bölüm-4-üretim-standartlarında-kod-örnekleri)
5. [BÖLÜM 5: NERELERDE, NASIL VE NELER YAPILACAK (MODÜL BAZLI DETAYLAR)](#bölüm-5-nerelerde-nasıl-ve-neler-yapılacak-modül-bazlı-detaylar)
6. [BÖLÜM 6: FAZLARA AYRILMIŞ ADIM ADIM GERÇEKLEŞTİRME PLANI](#bölüm-6-fazlara-ayrılmış-adım-adım-gerçekleştirme-planı)

---

## BÖLÜM 1: PROJENİN AMACI VE OPTİMİZASYON KAPSAMI

### 1.1 Temel Hedef ve Problem Tanımı
OtoEdit sisteminin temel vizyonu, video kaydı bittikten sonra saatler süren manuel kurgu (sessizlikleri kesme, hatalı/tekrar çekimleri ayıklama, kadraj ayarlama, yazı ve görsel yerleştirme) süreçlerini yapay zeka gücüyle **tam otomatik ve sıfır insan müdahalesiyle** gerçekleştirmektir.

Ancak mevcut MVP prototipinde 1 saatlik (veya daha uzun) ham videolar sisteme verildiğinde:
1. **İşlem Süresi Çöküntüsü:** Sistem tek bir videoyu 4-5 saatte tamamlayamamakta veya yarı yolda kalmaktadır.
2. **RabbitMQ Bağlantı Kopmaları (Heartbeat/Timeout):** Analiz döngüsü çok uzun sürdüğü için RabbitMQ soket seviyesinde bağlantıyı koparmakta (`StreamLostError`, `consumer_timeout`) ve tüm emek çöpe gitmektedir.
3. **Bellek ve CPU Boğulması:** CPU %100 yükte kilitlenirken, makinede bulunan NVIDIA GTX 1650 (CUDA) donanımından hiç faydalanılamamaktadır.
4. **Hatalı Mimari Kararlar:** Her segment için devasa video/ses dosyalarının baştan sona tekrar okunması (I/O fırtınası).

**Bu optimizasyon planının ana amacı:**  
Sistemi, **1 saatlik (60 dakika / 108.000 frame) 1080p bir ham videoyu 5 dakikanın altında (< 300 saniye)** analiz edip, EDL JSON'unu üreten ve tek hamlede render alan, kurşun geçirmez (resilient) ve aşırı optimize edilmiş kurumsal bir mimariye kavuşturmaktır.

---

### 1.2 Mevcut Hataların ve Tıkanmaların Kök Nedenleri

Sistem hata dosyalarının (`hata1.txt`, `hata2.txt`, `hata3.txt`, `hata4.txt`) ve kod tabanının derinlemesine incelenmesiyle belirlenen kök nedenler şunlardır:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 KÖK SORUN TABLOSU                                       │
├────────────────────────┬─────────────────────────────┬─────────────────────────────────┤
│ Darboğaz Alanı         │ Hatalı Kod / Davranış       │ Neden Olduğu Felaket            │
├────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 1. acoustic_scorer.py  │ AudioSegment.from_file()    │ 567 kesit için 1 saatlik ses    │
│                        │ döngü içinde 567 kez çağrıldı│ 567 kez baştan okundu (~3.5 saat)│
├────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 2. RabbitMQ Bağlantısı │ consumer_timeout = 30 dk    │ Analiz 30 dk'yı aşınca RabbitMQ │
│                        │ Pika heartbeat işlenmedi    │ kanalı kapattı (Crash)          │
├────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 3. GPU İzolasyonu      │ Docker compose'da NVIDIA    │ Whisper & FFmpeg sadece CPU'da  │
│                        │ runtime tanımlanmamış       │ çalıştı (15x-20x yavaşlama)     │
├────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 4. gesture_detector.py │ Videonun tüm kareleri       │ 108.000 kare MediaPipe ile      │
│                        │ baştan sona tarandı         │ CPU'da tarandı (~45 dakika)     │
├────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 5. gemini_client.py    │ JSON Markdown temizlenmedi  │ Chat ve Repurposing anında      │
│                        │ Exponential backoff yok     │ JSONDecodeError ile patladı     │
└────────────────────────┴─────────────────────────────┴─────────────────────────────────┘
```

---

### 1.3 Sistem Ne Hedefliyor, Ne Hedeflemiyor (MVP Sınırları)

`gelistirici-dokumani.md` Bölüm 1.2 gereğince sistem sınırları kesin çizgilerle belirlenmiştir:

- **Sistem Ne Hedefliyor:**
  - Ham videoyu alıp ses gürültüsünü temizlemeyi,
  - Whisper STT ile kelime zaman damgalarını çıkarmayı,
  - Sessizlikleri (`pydub`) ve tekrar edilen hatalı cümleleri (`acoustic_scorer`) yakalamayı,
  - Çoklu-modal (el hareketi + sesli komut) anlarını tespit edip videodan kesmeyi,
  - Yüz takibi (`face_tracker`) ile 16:9 yatay videodan akıllı 9:16 dikey kadraj üretmeyi,
  - Gemini LLM ile viral klip (Repurposing) ve B-Roll önerileri üretmeyi,
  - Tüm bu kararları tek bir **EDL (Edit Decision List) JSON** dosyasında toplamayı,
  - Kullanıcı onay verdiğinde FFmpeg ile tek seferde nihai videoyu render etmeyi hedefler.

- **Sistem Ne Hedeflemiyor:**
  - Premiere Pro veya DaVinci gibi interaktif, frame-frame video önizleme oynatıcısı değildir.
  - Her küçük AI komutunda videoyu baştan render etmez (Sadece EDL JSON güncellenir).
  - Rastgele tahminlerle kesim yapmaz; kurallara ve transkript semantiğine tam sadıktır.

---

### 1.4 Performans Metrikleri ve Hedeflenen Süreler

| Pipeline Aşaması | Mevcut Durum (1 Saat Video) | Hedeflenen Durum (Optimizasyon Sonrası) | Uygulanan İyileştirme |
|---|---|---|---|
| **1. Audio Extraction & Noise Red.** | 4 - 6 Dakika | **25 - 35 Saniye** | FFmpeg NVDEC + Caching |
| **2. Whisper Speech-to-Text** | 12 - 18 Dakika | **45 - 60 Saniye** | CUDA Batched Inference / Faster-Whisper |
| **3. Silence & Retake Scorer** | **210 Dakika (3.5 saat)** | **15 - 25 Saniye** | In-Memory AudioSegment Cache + Vectorization |
| **4. Multimodal Command Engine** | 40 - 55 Dakika | **30 - 45 Saniye** | Akıllı Pencereleme (Sadece komut adayları) |
| **5. Face Tracking (9:16)** | 35 - 50 Dakika | **20 - 30 Saniye** | Sadece aktif konuşma segmentleri + Keyframe atlama |
| **6. LLM Viral & B-Roll Analysis** | 30 - 60 Saniye | **10 - 15 Saniye** | Async Paralel Prompting + Gemini 1.5/2.0 Flash |
| **7. Final FFmpeg Render** | 45 - 60 Dakika | **60 - 90 Saniye** | NVIDIA NVENC Hardware Encoding (`h264_nvenc`) |
| **TOPLAM İŞLEM SÜRESİ** | **~4.5 - 5.5 Saat (veya çökme)** | **< 4.5 Dakika (270 Saniye)** | **~60 KAT HIZ ARTIŞI** |

---

## BÖLÜM 2: KESİN OLMASI GEREKENLER VE UYULMASI GEREKEN KURALLAR

Bu bölümdeki tüm yönergeler, `D:\OtoEdit\OtoEdit\docs\kurallar.txt` ve `D:\OtoEdit\OtoEdit\docs\gelistirici-dokumani.md` içerisindeki bağlayıcı hükümlerden derlenmiştir. Kod yazan geliştirici veya yapay zeka asistanı bu kurallardan **asla taviz veremez**.

### 2.1 Doküman Sadakati ve Tek Gerçek Kaynak (Single Source of Truth)
1. `D:\OtoEdit\OtoEdit\docs\gelistirici-dokumani.md` ve `D:\OtoEdit\OtoEdit\docs\kurallar.txt` projenin yegane anayasasıdır.
2. Yazılacak her fonksiyon, oluşturulacak her sınıf ve entity, dökümandaki sözleşmeye harfiyen uymalıdır.
3. Mimari veya teknik bir zorunluluk nedeniyle döküman dışına çıkılması gerekirse, geliştirici inisiyatif alamaz; bu durum açıkça raporlanmalı ve kullanıcı onayı alınmalıdır.
4. İnternet veya harici kütüphane araştırmalarında geçerli referans tarihi **Eylül 2026** olarak kabul edilecektir.

---

### 2.2 Temiz Kod (Clean Code) ve SOLID Prensipleri
1. **Single Responsibility (S):** Her sınıf ve fonksiyon tek bir işi mükemmel yapmalıdır. Örneğin, bir sınıf hem ses analizi yapıp hem RabbitMQ mesajı göndermemelidir.
2. **Open/Closed (O):** Sistem yeni bir video filtresi veya AI modeli eklendiğinde mevcut kodları kırmayacak, genişletilebilir soyutlamalarla tasarlanmalıdır.
3. **Liskov Substitution (L) & Interface Segregation (I):** Devasa "God Interface"ler yerine amaca yönelik küçük interfaceler (`IAcousticScorer`, `IFaceTracker`, `ICacheManager`) kullanılmalıdır.
4. **Dependency Inversion (D):** Somut sınıflara doğrudan bağımlılık yasaktır; tüm servisler Dependency Injection (DI) konteynerine kaydedilmelidir (.NET'te `IServiceCollection`, Python'da Dependency Injector veya Constructor Injection).
5. **DRY (Don't Repeat Yourself):** Kod tekrarı kesinlikle yasaktır. Tekrarlanan mantıklar extension metodlara veya ortak utility modüllerine taşınmalıdır.
6. **Yasaklı Kalıplar:**
   - Asla "God Class" (500+ satır) ve "God Method" (50+ satır) yazılmayacaktır.
   - Magic String ve Magic Number kullanımı yasaktır; tüm sabitler `const`, `readonly` veya `Enum` olarak tanımlanacaktır.
   - Boş bırakılmış `catch {}` blokları ("exception swallowing") kesinlikle kabul edilemez; her hata loglanacak ve uygun biçimde fırlatılacaktır.

---

### 2.3 Performans, Caching ve I/O Kuralları
1. **In-Memory Cache Zorunluluğu:** Devasa medya dosyaları (1 saatlik WAV / MP4) diskten defalarca okunamaz! `AudioSegment` veya Video metadata nesneleri işlem süresince RAM'de önbelleğe alınmalıdır.
2. **Redis Idempotency:** Ağır analiz süreçlerinin çıktıları Redis üzerinde hash anahtarlarıyla saklanmalı, aynı dosya için mükerrer analiz engellenmelidir.
3. **Async / Non-Blocking I/O:** Disk, ağ, veritabanı ve RabbitMQ çağrılarının tamamı asenkron (`async/await`) olmak zorundadır. Senkron I/O API thread'lerini kilitlediği için yasaktır.
4. **Veritabanı Okuma Optimizasyonu:** EF Core sorgularında salt-okunur (read-only) veri çekilirken mutlaka `.AsNoTracking()` kullanılmalıdır.
5. **Böl ve Yönet (Chunking):** Uzun işlemler tek bir dev blok halinde değil, yönetilebilir zaman pencerelerinde (windowing) işlenmelidir.

---

### 2.4 Hata Yönetimi, Debug Edilebilirlik ve Üç Katmanlı Loglama Sistemi
Sistemde oluşabilecek herhangi bir hatanın anında izole edilmesi ve debug edilebilmesi için üç katmanlı loglama altyapısı uygulanacaktır:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      ÜÇ KATMANLI LOGLAMA SİSTEMİ                       │
├─────────────────┬──────────────────────────────────────────────────────┤
│ 1. Endpoint Log │ API'ye gelen her HTTP isteği, istek gövdesi (maskeli)│
│                 │ yanıt süresi, durum kodu DB'ye kaydedilir.           │
├─────────────────┼──────────────────────────────────────────────────────┤
│ 2. Function Log │ Business ve Worker katmanındaki her fonksiyonun      │
│                 │ try-catch bloğu; girdi parametreleri, stack-trace.   │
├─────────────────┼──────────────────────────────────────────────────────┤
│ 3. Pipeline Log │ Python Worker'daki 7 ana aşamanın her birinin        │
│                 │ başlangıç, ilerleme yüzdesi (%10-%100), bitiş ve hata│
│                 │ anlarının veritabanında saklanması.                  │
└─────────────────┴──────────────────────────────────────────────────────┘
```

- **Fail-Safe Loglama Kuralı:** Log yazma mekanizmasında meydana gelen herhangi bir hata (DB kesintisi vb.) ana iş akışını veya video analizini **asla durdurmamalıdır**. Log servisi kendi içinde izole hata yakalamaya sahip olmalıdır.
- **Maskeleme:** Loglara API anahtarları, şifreler veya gizli tokenlar asla açık metin olarak yazılamaz (`ApiKey = "AIzaSy..."` yerine `ApiKey = "AIza***"`).

---

### 2.5 Güvenlik, Veri Bütünlüğü ve Veritabanı Standartları
1. **Veri Depolama Disiplini:** Analiz edilen her transkript, tespit edilen her kesim (cut), üretilen her B-Roll önerisi veritabanında ilişkili tablolarına (`video_transcripts`, `edit_decision_lists`, `pipeline_logs`) eksiksiz yazılmalıdır.
2. **SQL Injection Koruması:** Asla ham SQL birleştirmesi yapılmayacak; Entity Framework Core parametrik sorguları ve SQLAlchemy ORM kullanılacaktır.
3. **Environment Güvenliği:** Gizli anahtarlar kod içerisine gömülemez (hardcoded olamaz); `.env` dosyası veya ortam değişkenleri üzerinden okunmalıdır.

---

### 2.6 MVP Odaklılık, Genişletilebilirlik ve Git Sürüm Kontrolü
1. **Yarın Büyüyecekmiş Gibi Tasarla, Bugün Yalnızca MVP'yi Bitir:** Kod mimarisi gelecekte eklenecek filtreleri ve özellikleri kaldıracak esneklikte olmalı, ancak gereksiz aşırı mühendislikten (over-engineering) kaçınılmalıdır.
2. **Git Commit Disiplini:** Her kritik optimizasyon adımı ve her fonksiyonel blok tamamlandığında bağımsız, anlaşılır bir commit mesajı ile Git'e kaydedilmelidir.

---

### 2.7 Bölümlü Geliştirme ve Doğrulama Kuralı (`kurallar.txt` Madde 19 & 26)
1. **Tekte Yazmama Kuralı:** Ne dökümanlar ne de kaynak kodlar tek bir dev hamlede yazılmaya çalışılmayacaktır. Bu durum token aşımına, bağlam kaybına ve derleme hatalarına yol açar.
2. **Adım Adım İlerleme:** Her modül veya bölüm ayrı ayrı yazılacak, doğrulanacak, hata olup olmadığı kontrol edilecek ve ardından bir sonraki bölüme geçilecektir.
3. **Raporlama Zorunluluğu:** Yapılan her işlemden sonra kullanıcıya açık ve net bir rapor sunulacaktır.

---

### 2.8 Çapraz Dil ve Servisler Arası İletişim Kuralları
- **.NET 10 & C#:** API ve iş mantığında tip güvenliği, `record` yapıları, Pattern Matching, Minimal API / Controller standartları ve `MassTransit` kullanılmalıdır.
- **Python 3.10+:** Tip ipuçları (`type hints`), `Pydantic` veri doğrulama modelleri, `dataclass` yapıları ve PEP 8 standartları zorunludur.
- **RabbitMQ Sözleşmesi:** .NET ile Python arasındaki veri alışverişi kesin şemalara sahip JSON payload'ları üzerinden yürütülmelidir. Mesaj boyutunu şişirmemek adına büyük ham veriler (video/ses) RabbitMQ'dan geçirilmeyecek, MinIO S3 URI'leri iletilecektir.

---

## BÖLÜM 3: YENİ VE OPTİMİZE EDİLMİŞ DOSYA YAPISI

Mevcut sistemin performans darboğazlarını ortadan kaldırmak için, modüllerin sorumlulukları kesin sınırlarla ayrılmış ve optimize edilmiş yeni mimari dosya hiyerarşisi aşağıda tanımlanmıştır:

### 3.1 Solution Genel Dizin Hiyerarşisi

```
d:\OtoEdit\OtoEdit\
├── .env.example                               # Ortam değişkenleri şablonu
├── .gitignore                                 # Git hariç tutma kuralları
├── OtoEdit.slnx                               # Solution dosyası
├── docker-compose.yml                         # Canlı ortam orkestrasyonu
├── docker-compose.dev.yml                     # Geliştirme ve GPU tanımlı compose
│
├── docs/                                      # Mimari ve Teknik Belgeler
│   ├── gelistirici-dokumani.md                # Tek gerçek mimari sözleşmesi
│   ├── kurallar.txt                           # Kodlama ve çalışma kuralları
│   └── OtoEdit_Gelisim_ve_Optimizasyon_Plani.md # Bu ana plan dokümanı
│
├── nginx/
│   └── nginx.conf                             # Reverse proxy ve SSE/WebSocket ayarı
│
├── src/
│   ├── OtoEdit.API/                           # ASP.NET Core Web API (.NET 10)
│   ├── OtoEdit.Business/                      # İş Mantığı, Servisler ve DTO'lar
│   ├── OtoEdit.Data/                          # EF Core, PostgreSQL ve Entity'ler
│   └── OtoEdit.PythonWorker/                  # Video & AI Motoru (Ultra Hızlı)
│
└── tests/
    ├── OtoEdit.UnitTests/                     # .NET Birim Testleri
    └── OtoEdit.PythonWorker.Tests/            # Python Pipeline Birim Testleri
```

---

### 3.2 `OtoEdit.PythonWorker` Modüler Yeni Dizin Ağacı

Ağır video ve ses analizini gerçekleştiren Python Worker, sorumluluklarına göre alt paketlere bölünmüştür:

```
src/OtoEdit.PythonWorker/
├── Dockerfile                                 # NVIDIA CUDA 12 destekli Dockerfile
├── requirements.txt                           # Güncel ve GPU uyumlu Python paketleri
├── main.py                                    # Worker başlangıç noktası ve DI
│
├── cache/                                     # [YENİ] Ultra Hızlı Önbellek Katmanı
│   ├── __init__.py
│   ├── memory_cache.py                        # In-Memory singleton nesne deposu
│   ├── audio_cache.py                         # AudioSegment bellekte tutma servisi
│   └── redis_cache.py                         # Dağıtık analiz sonucu idempotency
│
├── consumers/                                 # RabbitMQ Tüketici Katmanı
│   ├── __init__.py
│   ├── analysis_consumer.py                   # Optimize edilmiş asenkron analiz kuyruğu
│   ├── render_consumer.py                     # Donanım hızlandırmalı render kuyruğu
│   └── heartbeat_manager.py                   # [YENİ] Kopmaları önleyen arka plan nabız thread'i
│
├── pipeline/                                  # AI ve Video Analiz Aşamaları
│   ├── __init__.py
│   ├── audio_enhancer.py                      # FFmpeg gürültü ve yankı temizleyici
│   ├── transcriber.py                         # Faster-Whisper GPU batch STT
│   ├── silence_detector.py                    # Vektörize pydub sessizlik tespitçisi
│   ├── acoustic_scorer.py                     # [REFACTORED] Bellekten okuyan hızlı skorlayıcı
│   ├── retake_detector.py                     # Hatalı/tekrar çekim filtreleme motoru
│   ├── gesture_detector.py                    # [REFACTORED] Akıllı pencerelemeli el takipçisi
│   ├── face_tracker.py                        # [REFACTORED] Akıllı pencereli 9:16 yüz takipçisi
│   ├── multimodal_command_engine.py           # Eşzamanlı el + ses komut birleştirici
│   ├── repurposing_engine.py                  # Gemini destekli viral anlar seçicisi
│   ├── suggestion_engine.py                   # Otomatik B-Roll ve yazı öneri motoru
│   └── edl_builder.py                         # Tüm verileri EDL JSON'a derleyen motor
│
├── hardware/                                  # [YENİ] Donanım Hızlandırma Katmanı
│   ├── __init__.py
│   ├── cuda_detector.py                       # GPU ve CUDA varlık kontrolcüsü
│   └── nvenc_ffmpeg.py                        # Donanım hızlandırmalı FFmpeg wrapper'ı
│
├── services/                                  # Yardımcı Servisler ve Dış API'ler
│   ├── __init__.py
│   ├── minio_service.py                       # S3 depolama indirme/yükleme servisi
│   ├── gemini_client.py                       # [REFACTORED] JSON temizleyicili Gemini istemcisi
│   ├── pexels_client.py                       # Stok görsel arama istemcisi
│   └── pipeline_logger.py                     # [YENİ] Veritabanı ve RabbitMQ log ileticisi
│
└── models/                                    # Pydantic Veri Modelleri
    ├── __init__.py
    ├── edl_models.py                          # EDL JSON güçlü tip sözleşmesi
    ├── event_models.py                        # RabbitMQ mesaj yükü modelleri
    └── log_models.py                          # Pipeline log veri modelleri
```

---

### 3.3 `.NET API` ve `Data/Business` Katmanlarındaki Güncellemeler

Backend katmanında uzun süren işlerin durum takibi ve bağlantı kopmalarını yönetmek için yapılan eklemeler:

```
src/OtoEdit.Business/
├── Services/
│   ├── AnalysisOrchestratorService.cs         # Analiz adımlarını yöneten servis
│   ├── PipelineLogService.cs                  # Pipeline loglarını DB'ye basan servis
│   └── VideoOptimizationService.cs            # Video ön işleme optimizasyon kuralları
└── Events/
    ├── VideoAnalysisProgressEvent.cs          # Canlı yüzde (%10..%100) ilerleme eventi
    └── VideoAnalysisFailedEvent.cs            # İzolasyonlu hata bildirim eventi

src/OtoEdit.Data/
├── Entities/
│   └── PipelineLog.cs                         # Pipeline aşamalarının detaylı DB entity'si
└── Migrations/
    └── xxxx_AddPipelineLogsAndOptimizations.cs # Veritabanı migration dosyası
```

---

### 3.4 Altyapı, Konfigürasyon ve Docker Güncellemeleri

Docker altyapısında NVIDIA GTX 1650 kartının konteynere geçirilmesi ve RabbitMQ'nun 10 saatlik analizlere dahi dayanabilmesi için yapılandırma dosyaları güncellenecektir:

```
docker-compose.dev.yml (Güncellenecek Servisler):
├── rabbitmq:
│   └── environment:
│       └── RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS: "-rabbit consumer_timeout 36000000"
└── python-worker:
    └── deploy:
        └── resources:
            └── reservations:
                └── devices:
                    - driver: nvidia
                      count: all
                      capabilities: [gpu, video, compute]
```

## BÖLÜM 4: ÜRETİM STANDARTLARINDA KOD ÖRNEKLERİ

Bu bölümde, sistemdeki kök darboğazları ortadan kaldıracak, `kurallar.txt` ve `gelistirici-dokumani.md` standartlarına tam uyumlu (Interface soyutlamalı, Dependency Injection uyumlu, Fail-Safe loglamalı, Tip güvenli) somut üretim kodları verilmiştir.

---

### 4.1 In-Memory Cache Destekli `AcousticScorer` (Kritik 3.5 Saat Tasarrufu)

**Sorun:** Eski kodda 567 segmentin her biri için `AudioSegment.from_file(audio_path)` çağrılarak 1 saatlik devasa ses dosyası 567 kez diskten okunup çözülüyordu.  
**Çözüm:** `IAcousticScorer` arayüzü tanımlanarak ses dosyası RAM'e yalnızca **1 kez** yüklenir; segment dilimleme mikrosaniyeler içinde bellek referansı üzerinden yürütülür.

```python
"""
src/OtoEdit.PythonWorker/pipeline/acoustic_scorer.py
Ultra Hızlı Akustik Skorlayıcı ve In-Memory Bellek Yöneticisi
"""

from abc import ABC, abstractmethod
import logging
import numpy as np
from pydub import AudioSegment
from typing import Dict, Any, Optional

logger = logging.getLogger("OtoEdit.AcousticScorer")


class IAcousticScorer(ABC):
    """Akustik skorlama servisi soyutlama arayüzü (SOLID - Interface Segregation)."""

    @abstractmethod
    def load_audio(self, audio_path: str) -> None:
        """Ses dosyasını belleğe (RAM) tek seferde yükler."""
        pass

    @abstractmethod
    def score_segment(self, start_sec: float, end_sec: float) -> Dict[str, Any]:
        """Verilen zaman aralığının akustik enerji, rms ve kalite skorunu döner."""
        pass

    @abstractmethod
    def compare_retake(self, seg1_start: float, seg1_end: float,
                       seg2_start: float, seg2_end: float) -> float:
        """İki tekrar cümlesi arasındaki akustik enerji farkını karşılaştırır."""
        pass


class FastAcousticScorer(IAcousticScorer):
    """
    Bellek önbellekli (In-Memory Cached) yüksek başarımlı akustik analiz motoru.
    Disk I/O maliyetini sıfıra indirir.
    """

    def __init__(self, audio_path: Optional[str] = None):
        self._audio: Optional[AudioSegment] = None
        self._current_path: Optional[str] = None
        self._sample_rate: int = 44100
        
        if audio_path:
            self.load_audio(audio_path)

    def load_audio(self, audio_path: str) -> None:
        """Ses dosyasını diskten RAM'e BİR KEZ çeker."""
        if self._current_path == audio_path and self._audio is not None:
            logger.info("Ses dosyası zaten RAM'de önbellekte: %s", audio_path)
            return

        try:
            logger.info("1 Saatlik ses dosyası RAM'e yükleniyor (Tek seferlik): %s", audio_path)
            self._audio = AudioSegment.from_file(audio_path)
            self._current_path = audio_path
            self._sample_rate = self._audio.frame_rate
            logger.info("Ses başarıyla belleğe alındı. Toplam süre: %.2f sn", len(self._audio) / 1000.0)
        except Exception as ex:
            logger.error("Ses dosyası yüklenirken hata oluştu: %s. Hata: %s", audio_path, str(ex), exc_info=True)
            raise RuntimeError(f"Ses yükleme hatası: {str(ex)}")

    def score_segment(self, start_sec: float, end_sec: float) -> Dict[str, Any]:
        """RAM üzerindeki dilimden (slice) anında enerji ve gürültü skoru üretir."""
        if self._audio is None:
            raise ValueError("Önce load_audio() çağrılarak ses yüklenmelidir.")

        # Pydub milisaniye ile çalışır
        start_ms = max(0, int(start_sec * 1000))
        end_ms = min(len(self._audio), int(end_sec * 1000))

        if start_ms >= end_ms:
            return {"rms": 0, "dBFS": -99.0, "pitch_stability": 0.0, "is_valid": False}

        # BELLEKTE DİLİMLEME (MİKROSANİYE SÜRER - DİSK OKUMASI SIFIR)
        clip = self._audio[start_ms:end_ms]

        rms = clip.rms
        dbfs = clip.dBFS

        # Vektörize Numpy ile hızlı enerji ve stabilite hesabı
        raw_samples = np.array(clip.get_array_of_samples(), dtype=np.float32)
        if len(raw_samples) > 0:
            std_dev = float(np.std(raw_samples))
            zero_crossings = int(np.sum(np.diff(np.sign(raw_samples) != 0)))
        else:
            std_dev = 0.0
            zero_crossings = 0

        return {
            "rms": rms,
            "dBFS": round(dbfs, 2),
            "energy_std": round(std_dev, 2),
            "zero_crossings": zero_crossings,
            "is_valid": True
        }

    def compare_retake(self, seg1_start: float, seg1_end: float,
                       seg2_start: float, seg2_end: float) -> float:
        """
        İki ses kesitinin enerji ve RMS değerini karşılaştırarak daha canlı/net
        olanın tespit edilmesini sağlar. Skor 1.0 ise seg2 çok daha enerjik demektir.
        """
        score1 = self.score_segment(seg1_start, seg1_end)
        score2 = self.score_segment(seg2_start, seg2_end)

        if not score1["is_valid"] or not score2["is_valid"]:
            return 0.5

        # Enerji karşılaştırması
        rms1 = max(1.0, float(score1["rms"]))
        rms2 = max(1.0, float(score2["rms"]))

        # 0.0 ile 1.0 arasında bağıl güvenilirlik skoru
        ratio = rms2 / (rms1 + rms2)
        return round(float(ratio), 4)
```

---

### 4.2 RabbitMQ Kopmalarını Önleyen Asenkron `HeartbeatManager` ve Consumer

**Sorun:** `hata2.txt` ve `hata3.txt` içerisinde görülen `pika.exceptions.StreamLostError` ve `ConnectionResetError`. Ağır analizler sırasında RabbitMQ soketi 60 saniye veri almayınca bağlantıyı zorla kapatmaktadır.  
**Çözüm:** Arka planda bağımsız bir thread ile çalışan `HeartbeatManager` ve Pika `connection.process_data_events()` entegrasyonu.

```python
"""
src/OtoEdit.PythonWorker/consumers/heartbeat_manager.py
RabbitMQ Bağlantı Koruyucu Nabız (Heartbeat) Yöneticisi
"""

import threading
import time
import logging
import pika
from typing import Optional

logger = logging.getLogger("OtoEdit.HeartbeatManager")


class RabbitHeartbeatKeeper:
    """
    Uzun süren video/AI işlemlerinde RabbitMQ bağlantısının kopmasını
    engellemek için arka planda düzenli event pompalayan servis.
    """

    def __init__(self, connection: pika.BlockingConnection, interval_sec: float = 10.0):
        self._connection = connection
        self._interval = interval_sec
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Nabız thread'ini başlatır."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="RabbitMQ-Heartbeat")
        self._thread.start()
        logger.info("RabbitMQ Heartbeat koruyucu arka plan thread'i başlatıldı.")

    def stop(self) -> None:
        """Nabız thread'ini durdurur."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("RabbitMQ Heartbeat koruyucu durduruldu.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._connection.is_open:
                    # Soket seviyesinde nabız gönder ve bekleyen frame'leri temizle
                    self._connection.process_data_events(time_limit=0)
            except Exception as ex:
                logger.warning("Heartbeat pompalanırken geçici hata (ihmal edildi): %s", str(ex))
            
            # Belirlenen aralıkla uyu ama stop sinyalini anında dinle
            self._stop_event.wait(self._interval)
```

---

### 4.3 Akıllı Pencerelemeli (Smart Windowing) `GestureDetector` ve `FaceTracker`

**Sorun:** 1 saatlik videonun 108.000 karesini baştan sona tek tek MediaPipe ile CPU'da işlemek 1 saate yakın sürmektedir.  
**Çözüm:** Konuşmanın olmadığı sessiz bölgelerde ve kesilecek hatalı yerlerde yüz ve el takibi **asla çalıştırılmaz**. Sadece transkript aday pencereleri taranır; her 3. kare (FPS/3) taranarak %70 ek tasarruf sağlanır.

```python
"""
src/OtoEdit.PythonWorker/pipeline/smart_windowing.py
Akıllı Pencereleme Motoru — Yalnızca Hedef Zaman Aralıklarını Tarar
"""

import cv2
import logging
from typing import List, Tuple, Generator, Any

logger = logging.getLogger("OtoEdit.SmartWindowing")


class SmartVideoScanner:
    """
    Videonun tamamını taramak yerine sadece verilen zaman aralıklarında (windows)
    OpenCV VideoCapture ile 'seek' yaparak kareleri çeken zeki okuyucu.
    """

    def __init__(self, video_path: str, target_fps_step: int = 3):
        self.video_path = video_path
        self.target_fps_step = target_fps_step  # Her 3. kareyi analiz et

    def iterate_windows(self, active_windows: List[Tuple[float, float]]) -> Generator[Tuple[float, Any], None, None]:
        """
        active_windows: [(start_sec, end_sec), (start_sec, end_sec)]
        Yalnızca bu aralıklara ait kareleri ve o anki saniyeyi döner.
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise IOError(f"Video dosyası açılamadı: {self.video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info("Akıllı Tarama Başladı. Toplam Video Frame: %d, FPS: %.2f", total_frames, fps)

        try:
            for start_sec, end_sec in active_windows:
                start_frame = int(start_sec * fps)
                end_frame = int(end_sec * fps)

                # DOĞRUDAN İLGİLİ KAREYE ATLA (SEEK) — MUAZZAM HIZ KAZANCI
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                current_frame_idx = start_frame

                while current_frame_idx <= end_frame:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Belirlenen kare atlama adımı
                    if current_frame_idx % self.target_fps_step == 0:
                        timestamp = current_frame_idx / fps
                        yield timestamp, frame

                    current_frame_idx += 1
        finally:
            cap.release()
            logger.info("Akıllı Tarama Tamamlandı.")
```

---

### 4.4 Donanım Hızlandırmalı Video Motoru (`CudaFFmpegEngine`)

**Sorun:** Render aşamasında CPU ile `libx264` kodlaması 1 saatlik video için 45 dakika sürmektedir.  
**Çözüm:** NVIDIA GTX 1650 ekran kartının donanımsal kodlayıcısı (`h264_nvenc`) ve kod çözücüsü (`h264_cuvid` / `cuda`) kullanılarak render süresi **1.5 dakikanın altına** indirilir.

```python
"""
src/OtoEdit.PythonWorker/hardware/nvenc_ffmpeg.py
NVIDIA Donanım Hızlandırmalı FFmpeg Yürütücüsü
"""

import subprocess
import logging
import os
from typing import List

logger = logging.getLogger("OtoEdit.CudaFFmpeg")


class CudaFFmpegEngine:
    """NVIDIA NVENC ve NVDEC yeteneklerini kullanan yüksek performanslı video motoru."""

    def __init__(self):
        self.has_cuda = self._check_nvenc_support()

    def _check_nvenc_support(self) -> bool:
        """Sistemde NVIDIA NVENC desteğinin olup olmadığını doğrular."""
        try:
            res = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True, text=True, check=True
            )
            is_supported = "h264_nvenc" in res.stdout
            if is_supported:
                logger.info("✅ NVIDIA NVENC Donanım Hızlandırma Desteği Doğrulandı!")
            else:
                logger.warning("⚠️ NVENC bulunamadı, CPU moduna (libx264) düşülecek.")
            return is_supported
        except Exception as ex:
            logger.error("FFmpeg kontrolünde hata: %s", str(ex))
            return False

    def build_render_command(self, input_video: str, concat_list_file: str,
                             output_video: str, preset: str = "p4") -> List[str]:
        """
        Donanım hızlandırmalı birleştirme ve kodlama komutunu üretir.
        concat demuxer ile birleştirip tek geçişte NVENC ile sıkıştırır.
        """
        cmd = ["ffmpeg", "-y"]

        if self.has_cuda:
            # Donanımsal kod çözme ve kodlama bayrakları
            cmd.extend([
                "-hwaccel", "cuda",
                "-hwaccel_output_format", "cuda"
            ])

        cmd.extend([
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_file
        ])

        if self.has_cuda:
            cmd.extend([
                "-c:v", "h264_nvenc",
                "-preset", preset,        # p1 (en hızlı) - p7 (en kaliteli), p4 optimum
                "-b:v", "6M",             # 6 Mbps 1080p için ideal bitrate
                "-maxrate", "8M",
                "-bufsize", "12M",
                "-c:a", "aac",
                "-b:a", "192k"
            ])
        else:
            # CPU Yedek Modu
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k"
            ])

        cmd.append(output_video)
        return cmd
```

---

### 4.5 Fail-Safe Üç Katmanlı `PipelineLogger` Servisi

**Kural:** `kurallar.txt` ve `gelistirici-dokumani.md` Madde 2.6 gereğince loglama sistemindeki bir aksaklık ana pipeline'ı **kesinlikle durdurmamalıdır**.

```python
"""
src/OtoEdit.PythonWorker/services/pipeline_logger.py
Kopmayan, Hata Fırlatmayan (Fail-Safe) Pipeline Log Servisi
"""

import logging
import requests
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger("OtoEdit.PipelineLogger")


class PipelineLogger:
    """
    Pipeline aşama loglarını hem yerel dosyaya hem de merkezi .NET API / DB'ye
    aktaran, olası bağlantı hatalarında ana sistemi ASLA çökertmeyen servis.
    """

    def __init__(self, api_base_url: str, api_key: str):
        self.api_url = f"{api_base_url.rstrip('/')}/api/internal/logs/pipeline"
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }

    def log_stage_progress(self, project_id: str, stage_name: str,
                           progress_pct: int, status: str = "InProgress",
                           details: Optional[Dict[str, Any]] = None,
                           error_message: Optional[str] = None) -> None:
        """
        Aşama ilerlemesini kaydeder. Hata çıksa dahi try-except ile yutar.
        """
        payload = {
            "projectId": project_id,
            "stage": stage_name,
            "progress": progress_pct,
            "status": status,
            "timestampUtc": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
            "errorMessage": error_message
        }

        # 1. Konsola standart çıktı
        if error_message:
            logger.error("[PIPELINE-LOG][%s][%s] %d%% - HATA: %s", project_id, stage_name, progress_pct, error_message)
        else:
            logger.info("[PIPELINE-LOG][%s][%s] %d%% - Durum: %s", project_id, stage_name, progress_pct, status)

        # 2. API / DB'ye ilet (Fail-Safe)
        try:
            # 2 saniyelik sıkı timeout; ana işi bekletemez
            requests.post(self.api_url, json=payload, headers=self.headers, timeout=2.0)
        except Exception as ex:
            # Kritik: Log servisi patlasa da video analizi DURMAZ!
            logger.warning("Pipeline logu merkezi API'ye iletilemedi (İşlem devam ediyor): %s", str(ex))
```

---

### 4.6 Güvenli JSON Ayrıştırma ve Tenacity Destekli `GeminiClient`

**Sorun:** `hata4.txt` içerisinde görülen LLM JSON markdown temizleme eksikliği ve API oran sınırı (rate limit) çökmeleri.  
**Çözüm:** Markdown \`\`\`json bloklarını otomatik ayıklayan regex ve `tenacity` ile Exponential Backoff Retry.

```python
"""
src/OtoEdit.PythonWorker/services/gemini_client.py
Dayanıklı, JSON Sanitizasyonlu Gemini LLM İstemcisi
"""

import re
import json
import logging
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("OtoEdit.GeminiClient")


class RobustGeminiClient:
    """JSON temizleme ve otomatik tekrar deneme (Retry) mekanizmalı LLM istemcisi."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Gemini model konfigürasyonu burada yapılır

    @staticmethod
    def clean_json_markdown(raw_response: str) -> str:
        """LLM çıktısındaki ```json ... ``` etiketlerini ve kaçış hatalarını temizler."""
        cleaned = raw_response.strip()
        # ```json ve ``` bloklarını kaldır
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        return cleaned

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1.5, min=2, max=15),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def parse_repurposing_and_suggestions(self, transcript_text: str) -> Dict[str, Any]:
        """Transkripti analiz edip viral anları ve B-Roll önerilerini hatasız JSON olarak çeker."""
        logger.info("Gemini LLM analizi başlatılıyor (Uzunluk: %d karakter)...", len(transcript_text))

        # LLM Çağrısı (Mock / Gerçek SDK çağrısı)
        # prompt = f"..."
        raw_output = '```json {"viralClips": [], "suggestions": []} ```'  # Temsili

        cleaned_json_str = self.clean_json_markdown(raw_output)

        try:
            result = json.loads(cleaned_json_str)
            logger.info("Gemini JSON yanıtı başarıyla ayrıştırıldı.")
            return result
        except json.JSONDecodeError as err:
            logger.error("LLM JSON ayrıştırma hatası! Ham Metin: %s, Hata: %s", raw_output, str(err))
            # Güvenli varsayılan veri dönerek sistemin çökmesini engelle
            return {"viralClips": [], "suggestions": []}
```

## BÖLÜM 5: NERELERDE, NASIL VE NELER YAPILACAK (MODÜL BAZLI DETAYLAR)

Bu bölüm, sistemdeki her bir dosyanın mevcut kod durumu, yapılacak somut değişiklikler, uygulanacak teknikler ve beklenen performans kazanımını dosya bazında haritalandırır.

---

### 5.1 Modül: `acoustic_scorer.py` ve `retake_detector.py` (Ses Analizi & Tekrar Çekim)

#### `src/OtoEdit.PythonWorker/pipeline/acoustic_scorer.py`
- **Mevcut Durum:** Fonksiyon tabanlı (`score_segment(audio_path, start, end)`). Her çağrıda `AudioSegment.from_file(audio_path)` çalıştırılıyor.
- **Neler Yapılacak:**
  1. `IAcousticScorer` arayüzü tanımlanacak.
  2. Sınıf tabanlı `FastAcousticScorer` mimarisine geçilecek.
  3. `AudioSegment` nesnesi sınıfın `__init__` veya `load_audio()` metodunda RAM'e yüklenecek ve `self._audio` değişkeninde tutulacak.
  4. Vektörize `numpy` metotları ile RMS, tepe değer (peak) ve sıfır geçiş oranı (zero-crossing rate) hesaplanacak.
- **Nasıl Yapılacak:**
  ```python
  # Eski Kod:
  # audio = AudioSegment.from_file(audio_path) # HER SEFERİNDE DİSKTEN OKUYORDU
  
  # Yeni Kod:
  # clip = self._audio[start_ms:end_ms] # RAM'DEN MİKROSANİYEDE DİLİMLER
  ```
- **Kazanım:** 567 kesit için diskten 567 GB eşdeğeri ses okuma maliyeti **SIFIRA** inecek. Süre 210 dakikadan **15 saniyeye** düşecek.

#### `src/OtoEdit.PythonWorker/pipeline/retake_detector.py`
- **Mevcut Durum:** Döngü içerisinde her iki segment karşılaştırmasında dosya yolunu parametre olarak geçiyor.
- **Neler Yapılacak:**
  1. Analiz döngüsü başlamadan önce `scorer = FastAcousticScorer(audio_path)` bir kez örneklemlenecek.
  2. Döngü içindeki `compare_retakes()` çağrısına hazır scorer nesnesi iletilecek.
  3. Hata toleransı (Fault tolerance): Herhangi bir segmentte akustik analiz patlarsa tüm süreci durdurmak yerine o segmente varsayılan 0.5 skoru atanıp devam edilecek.

---

### 5.2 Modül: `analysis_consumer.py` ve RabbitMQ Altyapısı (Bağlantı & Tüketim)

#### `src/OtoEdit.PythonWorker/consumers/analysis_consumer.py`
- **Mevcut Durum:** Tek bir uzun senkron fonksiyon içinde tüm pipeline çalıştırılıyor. RabbitMQ 30 dakika veri almayınca bağlantıyı kesiyor (`StreamLostError`).
- **Neler Yapılacak:**
  1. `RabbitHeartbeatKeeper` sınıfı ile arka plan nabız thread'i entegre edilecek.
  2. Analiz başlamadan önce `heartbeat.start()` tetiklenecek.
  3. Her pipeline aşaması bittiğinde (Örn: Transkripsiyon bitti, Sessizlik bitti), RabbitMQ kuyruğuna `.NET API`'nin dinleyeceği `VideoAnalysisProgressEvent` mesajı basılacak.
  4. Analiz başarıyla tamamlandığında `channel.basic_ack(delivery_tag)` çağrılacak ve `heartbeat.stop()` ile thread sonlandırılacak.
- **Nasıl Yapılacak:**
  ```python
  heartbeat = RabbitHeartbeatKeeper(connection, interval_sec=10.0)
  heartbeat.start()
  try:
      # Pipeline Aşamaları (Whisper -> Silence -> Retake -> Gestures -> Face -> Suggestions)
      ...
      ch.basic_ack(delivery_tag=method.delivery_tag)
  finally:
      heartbeat.stop()
  ```
- **Kazanım:** 45. dakikada sistemin çökmesi, RabbitMQ kanalının kapanması tamamen engellenecek; %10-%100 arası canlı ilerleme verisi üretilecek.

---

### 5.3 Modül: `docker-compose.dev.yml` ve `Dockerfile` (NVIDIA CUDA & Donanım)

#### `docker-compose.dev.yml`
- **Mevcut Durum:** Konteynerler standart bridge network'te CPU ile çalışıyor. RabbitMQ consumer_timeout varsayılan 30 dakikada.
- **Neler Yapılacak:**
  1. `rabbitmq` servisine `RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS: "-rabbit consumer_timeout 36000000"` (10 saat) eklenecek.
  2. `python-worker` servisine NVIDIA GPU rezervasyonu eklenecek.
- **Nasıl Yapılacak:**
  ```yaml
  python-worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu, video, compute]
  ```

#### `src/OtoEdit.PythonWorker/Dockerfile`
- **Mevcut Durum:** Standart `python:3.10-slim` imajı kullanılıyor. CUDA kütüphaneleri ve NVENC derlemeleri eksik.
- **Neler Yapılacak:**
  1. Base imaj `nvidia/cuda:12.1.0-runtime-ubuntu22.04` veya FFmpeg NVENC destekli optimize imaja geçirilecek.
  2. `torch` ve `torchaudio` kütüphaneleri `cu121` tekerlekleri (wheels) ile kurulacak.
  3. Sistem ayağa kalkarken `torch.cuda.is_available()` doğrulaması yapılarak log basılacak.
- **Kazanım:** Whisper transkripsiyonu ve FFmpeg render işlemi doğrudan GPU çekirdeklerine aktarılarak **20x hızlanacak**.

---

### 5.4 Modül: `gesture_detector.py` ve `face_tracker.py` (Görüntü İşleme AI)

#### `src/OtoEdit.PythonWorker/pipeline/gesture_detector.py`
- **Mevcut Durum:** 1 saatlik videodaki 108.000 frame'in tamamı `cv2.VideoCapture` ile okunup MediaPipe Hands modeline sokuluyor.
- **Neler Yapılacak:**
  1. **Akıllı Pencereleme (Smart Windowing):** El hareketleri ve sesli komutlar yalnızca bir konuşma olduğunda anlamlıdır. Transkriptten elde edilen konuşma başlangıç/bitiş saniyeleri alınacak.
  2. OpenCV `cap.set(cv2.CAP_PROP_POS_FRAMES)` kullanılarak konuşma olmayan sessiz bölgeler taranmadan doğrudan atlanacak.
  3. Her kare değil, her 3. kare (FPS/3) taranacak (El işaretleri en az 1-2 saniye sürdüğü için hiçbir hareket kaçırılmaz).
- **Kazanım:** Taranacak kare sayısı 108.000'den ~15.000 kareye düşecek. Süre 50 dakikadan **45 saniyeye** inecek.

#### `src/OtoEdit.PythonWorker/pipeline/face_tracker.py`
- **Mevcut Durum:** Sadece yatay (16:9) videodan dikey (9:16) veya kare (1:1) video üretilecekken çalışması gerekirken, gereksiz yere her formatta çalışıyor ve tüm videoyu tarıyor.
- **Neler Yapılacak:**
  1. Video formatı `16:9` ise bu modül tamamen pas geçilecek (Bypass).
  2. Format `9:16` ise sadece kesilmeyecek (EDL'de kalacak) aktif sahnelerde yüz aranacak.
  3. Yüz tespit kutuları için Kalman Filtresi / Üstel Hareketli Ortalama (EMA) ve Deadzone uygulanarak kameranın titreşmesi engellenecek.
- **Kazanım:** Yatay videolarda süre sıfıra inecek; dikey videolarda işlem süresi 40 dakikadan **30 saniyeye** düşecek.

---

### 5.5 Modül: `gemini_client.py` ve `repurposing_engine.py` (LLM & Öneriler)

#### `src/OtoEdit.PythonWorker/services/gemini_client.py`
- **Mevcut Durum:** Ham metin dönüşü `json.loads()` ile parse ediliyor. Model yanıtında markdown \`\`\`json etiketleri olduğunda sistem patlıyor (`hata4.txt`).
- **Neler Yapılacak:**
  1. `clean_json_markdown()` static metodu eklenecek.
  2. `tenacity` kütüphanesi ile ağ kesintilerine ve Google API Rate Limit (429) durumlarına karşı Exponential Backoff uygulanacak.
  3. JSON parse hatası alınırsa boş liste dönülerek pipeline'ın durması engellenecek (Fail-Safe).

---

### 5.6 Modül: `.NET API` ve `Data` Katmanı (Durum Takibi & Loglar)

#### `src/OtoEdit.Data/Entities/PipelineLog.cs` ve `AppDbContext.cs`
- **Neler Yapılacak:**
  1. `PipelineLog` entity'si eklenecek (Id, ProjectId, Stage, ProgressPct, Status, DetailsJson, ErrorMessage, TimestampUtc).
  2. EF Core Migration oluşturulacak ve PostgreSQL'e yansıtılacak.
- **Nasıl Yapılacak:**
  ```csharp
  public class PipelineLog
  {
      public Guid Id { get; set; } = Guid.NewGuid();
      public Guid ProjectId { get; set; }
      public string Stage { get; set; } = string.Empty;
      public int ProgressPercentage { get; set; }
      public string Status { get; set; } = "InProgress";
      public string? DetailsJson { get; set; }
      public string? ErrorMessage { get; set; }
      public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
  }
  ```

#### `src/OtoEdit.API/Controllers/InternalLogsController.cs`
- **Neler Yapılacak:**
  1. Python Worker'ın fail-safe log gönderebilmesi için `POST /api/internal/logs/pipeline` endpoint'i açılacak.
  2. Gelen ilerleme durumu anında SignalR Hub üzerinden Angular ön yüzüne push edilecek.

## BÖLÜM 6: FAZLARA AYRILMIŞ ADIM ADIM GERÇEKLEŞTİRME PLANI

`kurallar.txt` kuralları doğrultusunda sistem bir kerede değil, **üç bağımsız ve test edilebilir faza** ayrılarak geliştirilecektir. Her fazın sonunda tam doğrulama yapılacak ve Git commit atılacaktır.

---

### 6.1 FAZ 1: Çökmeyi Önleme ve Acil Hızlandırma (Öncelik: Kritik / 1. Gün)

Bu fazın temel amacı, 1 saatlik videonun ortasında yaşanan RabbitMQ çökmesini (`StreamLostError`) engellemek ve `acoustic_scorer`'daki disk okuma felaketini ortadan kaldırmaktır.

#### Adım 1.1: In-Memory Ses Önbellekleme (`acoustic_scorer.py` Refactoring)
- **Yapılacak İş:**
  - `src/OtoEdit.PythonWorker/pipeline/acoustic_scorer.py` içerisine `FastAcousticScorer` sınıfı entegre edilecek.
  - `AudioSegment.from_file()` sınıf yüklemesinde tek sefer çalıştırılacak şekilde yapılandırılacak.
  - `src/OtoEdit.PythonWorker/pipeline/retake_detector.py` bu yeni sınıfa bağlanacak.
- **Doğrulama / Test:**
  - 1 saatlik ses dosyası üzerinde 500 segmentlik yapay döngü çalıştırılacak.
  - Test süresinin 3.5 saatten **15-20 saniyeye indiği** doğrulanacak.
- **Git Commit:** `perf(pipeline): implement in-memory audio caching in acoustic_scorer`

#### Adım 1.2: RabbitMQ Bağlantı ve Nabız Koruması (`heartbeat_manager.py`)
- **Yapılacak İş:**
  - `src/OtoEdit.PythonWorker/consumers/heartbeat_manager.py` oluşturulacak.
  - `analysis_consumer.py` döngüsüne `RabbitHeartbeatKeeper` dahil edilecek.
  - `docker-compose.dev.yml` içinde RabbitMQ sunucu parametresine `consumer_timeout = 36000000` (10 saat) tanımlanacak.
- **Doğrulama / Test:**
  - RabbitMQ kuyruğu açıkken Python tarafında kasıtlı 40 dakikalık işlem simüle edilecek; bağlantının kopmadığı (`connection.is_open == True`) teyit edilecek.
- **Git Commit:** `fix(rabbitmq): add heartbeat keeper thread and extend consumer timeout`

#### Adım 1.3: LLM JSON Temizleme ve Hata Toleransı (`gemini_client.py`)
- **Yapılacak İş:**
  - `gemini_client.py` içine `clean_json_markdown()` ve `tenacity` retry dekoratörleri eklenecek.
  - Markdown etiketleri içeren yapay LLM yanıtları üzerinde test edilecek.
- **Doğrulama / Test:**
  - `hata4.txt`'de patlayan JSON formatı fonksiyona verilerek geçerli Python sözlüğü döndüğü doğrulanacak.
- **Git Commit:** `fix(llm): sanitize markdown json responses and add exponential backoff`

---

### 6.2 FAZ 2: Donanım Hızlandırma ve Akıllı Pencereleme (Öncelik: Yüksek / 2-3. Gün)

Bu fazın amacı, CPU yükünü GPU'ya devretmek ve taranması gerekmeyen video karelerini atlayarak işlem süresini 15 dakikanın altına çekmektir.

#### Adım 2.1: Docker NVIDIA CUDA Entegrasyonu (GTX 1650 Passthrough)
- **Yapılacak İş:**
  - `docker-compose.dev.yml` içerisindeki `python-worker` servisine NVIDIA runtime rezervasyonu eklenecek.
  - `Dockerfile` CUDA destekli kütüphaneler ile donatılacak.
  - `cuda_detector.py` modülü yazılarak sistem açılışında `torch.cuda.is_available()` ve GPU ismi loglanacak.
- **Doğrulama / Test:**
  - Konteyner içinde `nvidia-smi` komutu çalıştırılacak ve GTX 1650'nin VRAM kullanımı doğrulanacak.
- **Git Commit:** `feat(docker): enable nvidia cuda gpu passthrough for python worker`

#### Adım 2.2: Akıllı Pencerelemeli Görüntü Analizi (`smart_windowing.py`)
- **Yapılacak İş:**
  - `pipeline/smart_windowing.py` oluşturulacak.
  - `gesture_detector.py` ve `face_tracker.py`, tüm videoyu taramak yerine sadece konuşma aralıklarını `seek` yaparak tarayacak şekilde güncellenecek.
  - Kare tarama frekansı her 3. kareye (FPS/3) çekilecek.
- **Doğrulama / Test:**
  - 1 saatlik videonun el ve yüz analizi çalıştırılacak; taranan kare sayısının 108.000'den 15.000'e düştüğü ve sürenin **1 dakikanın altına indiği** ölçülecek.
- **Git Commit:** `perf(vision): implement smart windowing and frame skipping for gestures and faces`

#### Adım 2.3: Donanım Hızlandırmalı Video Kodlama (`nvenc_ffmpeg.py`)
- **Yapılacak İş:**
  - `hardware/nvenc_ffmpeg.py` motoru entegre edilecek.
  - FFmpeg render çağrılarına `-hwaccel cuda` ve `-c:v h264_nvenc` eklenecek.
- **Doğrulama / Test:**
  - 1 saatlik videonun EDL kesim listesi donanım hızlandırmayla birleştirilecek; GPU Video Encode motorunun çalıştığı doğrulanacak.
- **Git Commit:** `feat(render): integrate nvidia nvenc hardware encoding for ffmpeg`

---

### 6.3 FAZ 3: Çoklu İşlem (Paralelizasyon) ve Kurumsal Dayanıklılık (Öncelik: Orta / 4-5. Gün)

Bu fazın amacı, mimariyi dağıtık ve asenkron standartlara eriştirerek toplam işlem süresini **< 5 dakika** hedefinin altına sabitlemektir.

#### Adım 3.1: Asenkron Paralel Pipeline Yürütme (`concurrent.futures`)
- **Yapılacak İş:**
  - Bağımsız adımlar (Örn: Ses gürültü temizleme ile Transkripsiyon; veya Yüz takibi ile LLM Repurposing analizi) eşzamanlı (paralel thread/process) çalıştırılacak.
- **Doğrulama / Test:**
  - İşlemci çekirdeklerinin dengeli dağıldığı ve adımların birbirini bloklamadan bittiği doğrulanacak.
- **Git Commit:** `perf(pipeline): parallelize independent analysis stages using concurrent futures`

#### Adım 3.2: Üç Katmanlı Fail-Safe `PipelineLogger` ve SignalR Entegrasyonu
- **Yapılacak İş:**
  - `src/OtoEdit.PythonWorker/services/pipeline_logger.py` tamamlanacak.
  - `.NET Data` katmanında `PipelineLog` tablosu oluşturulacak (`dotnet ef migrations add AddPipelineLogs`).
  - `.NET API`'deki `POST /api/internal/logs/pipeline` endpoint'i SignalR hub'ına bağlanarak canlı ilerleme arayüze aktarılacak.
- **Doğrulama / Test:**
  - Analiz sürerken DB'de aşama kayıtlarının oluştuğu ve SignalR istemcilerine anlık bildirim gittiği test edilecek.
- **Git Commit:** `feat(logging): add resilient 3-layer pipeline logging and signalr progress push`

#### Adım 3.3: Redis Idempotency ve Analiz Sonuçlarının Önbelleğe Alınması
- **Yapılacak İş:**
  - Video dosyasının SHA256 hash'i çıkarılacak; daha önce analiz edilmiş bir dosya yeniden yüklendiğinde Redis'ten anında EDL dönecek.
- **Git Commit:** `feat(cache): implement sha256 video analysis idempotency with redis`

---

### 6.4 Kabul Kriterleri ve Doğrulama Matrisi (Definition of Done)

Projenin başarıyla tamamlandığı aşağıdaki kriterlerin tümü sağlandığında onaylanacaktır:

| No | Kriter | Başarı Şartı | Doğrulama Yöntemi |
|---|---|---|---|
| **K-1** | **Toplam Süre** | 1 Saatlik Video < 5 Dakika | Stop-watch / PipelineLog süresi |
| **K-2** | **Sıfır Çökme** | RabbitMQ kopması / timeout olmamalı | RabbitMQ logları ve worker uptime |
| **K-3** | **GPU Kullanımı** | NVIDIA GTX 1650 aktif çalışmalı | `nvidia-smi` GPU Load > %60 |
| **K-4** | **EDL Bütünlüğü** | Tüm kesimler ve overlay'ler eksiksiz olmalı | EDL JSON Schema validasyonu |
| **K-5** | **Doküman Uyumu** | `kurallar.txt` ve `gelistirici-dokumani.md` tam uyumlu | Kod incelemesi (Code Review) |

---

### 6.5 Geri Alma (Rollback) ve Kurtarma Stratejisi
Herhangi bir optimizasyon adımında beklenmeyen bir kütüphane uyumsuzluğu yaşanması durumunda:
1. `git revert` veya ilgili commit'e `git checkout` yapılarak sistem anında bir önceki stabil faza döndürülecektir.
2. GPU sürücüsü veya CUDA konteyner uyumsuzluğunda, `CudaFFmpegEngine` ve `transcriber.py` otomatik olarak CPU yedekleme moduna (`fallback to CPU`) düşecek ve video işlemeyi asla durdurmayacaktır.

---

## BÖLÜM 7: SONUÇ VE İCRAAT TAAHHÜDÜ

Bu master plan, OtoEdit sisteminin 1 saatlik uzun videolarda yaşadığı darboğazların üzerini örtmek için değil; **kök nedenleri cerrahi bir titizlikle kesip atmak** için hazırlanmıştır.

- `kurallar.txt` hükümlerine %100 sadık kalınarak,
- `gelistirici-dokumani.md` mimari sözleşmesinden zerre sapmadan,
- Kod tekrarı yapılmadan (DRY),
- Her fonksiyon loglanabilir ve debug edilebilir kılınarak,
- Bölüm bölüm, adım adım ilerlenerek sistem dönüştürülecektir.

**Plan tamamlanmıştır. Artık söz mühendisliğe ve koda geçmiştir.**



