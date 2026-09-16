# 🎬 OtoEdit — Yapay Zeka Destekli Otomatik Video Kurgu Sistemi — Geliştirici Dökümanı

> **Versiyon:** 1.0 — MVP (Müstakil & Nihai Uygulama Sözleşmesi)  
> **Tarih:** 15.09.2026  
> **Kapsam:** Bu döküman, projenin tek ve bağımsız gerçek kaynağıdır (Single Source of Truth). Başka bir harici mimari dokümana veya internet kaynağına bağımlı değildir; tüm mimari kararlar, veri modelleri, endpoint sözleşmeleri ve kod standartları eksiksiz olarak bu metin içerisinde tanımlanmıştır.

---

## İçindekiler

1. [Projenin Amacı ve MVP Kapsamı](#1-projenin-amacı-ve-mvp-kapsamı)
2. [Kesin Uyulması Gereken Kurallar](#2-kesin-uyulması-gereken-kurallar)
3. [Teknoloji Ağacı](#3-teknoloji-ağacı)
4. [Dosya Yapısı (Tüm Projeler ve İçerikleri)](#4-dosya-yapısı)
5. [Veritabanı Tabloları ve İlişkiler](#5-veritabanı-tabloları-ve-ilişkiler)
6. [Temel Fonksiyonlar ve API Endpoint'leri](#6-temel-fonksiyonlar-ve-api-endpointleri)
7. [Kod Yazım Örnekleri ve Entegrasyonlar](#7-kod-yazım-örnekleri-ve-entegrasyonlar)
8. [Log Sistemi](#8-log-sistemi)
9. [Frontend (Angular) Mimarisi ve Arayüz Akışları](#9-frontend-angular-mimarisi-ve-arayüz-akışları)
10. [Geliştirme Fazları (Roadmap)](#10-geliştirme-fazları-roadmap)

---

## 1. Projenin Amacı ve MVP Kapsamı

### 1.1 Projenin Amacı

OtoEdit, video çekimi sonrasında yapılan manuel ve tekrarlayan kurgu işlerini (sessizlik kesme, dolgu sesleri temizleme, format dönüştürme, yazı/görsel ekleme) **yapay zeka ile otomatize eden**, aynı zamanda kullanıcıya **doğal dilde sohbet ederek** videosuna müdahale etme imkânı tanıyan yeni nesil bir video düzenleme sistemidir.

**Kullanıcının elle yaptığı iş sadece şu noktalarda var:**
1. **Video yükleme** — Ham videoyu arayüzden sürükleyip bırakma ve çıktı formatını (16:9, 9:16, 1:1) seçme
2. **Şablon seçme** — Hangi video şablonunun uygulanacağını belirleme (Yatay Anlatım, Reels/Shorts vb.)
3. **AI ile sohbet** — "Videonun 2. dakikasına 'Abone Ol' yazısı koy" gibi doğal dil komutları yazma
4. **Dışa aktarma** — Sonuçtan memnun olunca "Render Et" deyip nihai videoyu alma

Aradaki her şey (sessizlik algılama, el hareketi komutları, ses iyileştirme, yüz takibi, repurposing, altyazı oluşturma) arka planda **tam otomatik** çalışır.

### 1.2 Sistem Ne Değildir

- Geleneksel bir video editörü (Premiere Pro, DaVinci Resolve) **değildir**: Timeline üzerinde frame-frame kesim yapılmaz. Tüm kararlar yapay zeka tarafından alınır ve JSON (EDL) üzerinden temsil edilir.
- Sadece bir jump-cutter aracı **değildir**: Sessizlik kesmenin ötesinde; el hareketleri, sesli komutlar, repurposing (uzun→ kısa), yazı/görsel ekleme ve AI sohbet tabanlı kurgu gibi gelişmiş özellikler sunar.
- Tek seferlik bir script **değildir**: Bugün 1 video, yarın 100 video olsa bile mimaride hiçbir değişiklik gerekmez — sadece veri hacmi artar.

### 1.3 Sistemin Kalbi: EDL (Edit Decision List) Mantığı

OtoEdit videoyu her komutta yeniden render etmez. Her proje için bir **EDL (Edit Decision List)** JSON dosyası tutulur. Tüm AI kararları (kesimler, overlay'ler, format ayarları) bu JSON'u günceller. Angular arayüzü bu JSON'u okuyarak videonun önizlemesini gösterir. Kullanıcı "Dışa Aktar" dediğinde sistem **sadece 1 kere** FFmpeg ile gerçek render işlemi yapar.

**Örnek EDL JSON:**
```json
{
  "projectId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sourceVideoUrl": "s3://otoedit/videos/raw_v1.mp4",
  "settings": {
    "targetFormat": "9:16",
    "templateId": "reels_kursu_tv",
    "faceTrackingEnabled": true,
    "audioEnhancement": true,
    "gestureCommandsEnabled": true
  },
  "transcript": {
    "fullText": "Bismillahirrahmanirrahim...",
    "segments": [
      {"start": 0.0, "end": 3.5, "text": "Bismillahirrahmanirrahim"},
      {"start": 3.5, "end": 8.2, "text": "Bugünkü konumuz tevekkül"}
    ]
  },
  "cuts": [
    {"id": "cut_1", "start": 12.5, "end": 15.0, "reason": "silence", "source": "auto"},
    {"id": "cut_2", "start": 45.0, "end": 52.0, "reason": "gesture_dislike", "source": "auto"},
    {"id": "cut_3", "start": 120.0, "end": 135.0, "reason": "user_command", "source": "chat", "command": "Girişteki boş konuşmayı kes"}
  ],
  "overlays": [
    {
      "id": "text_1",
      "type": "text",
      "content": "Kanala Abone Ol!",
      "font": "Montserrat-Bold",
      "fontSize": 48,
      "color": "#FFFFFF",
      "backgroundColor": "#00000080",
      "timestamp": 60.0,
      "duration": 5.0,
      "animation": "pop-up",
      "position": ["center", "bottom"]
    },
    {
      "id": "img_1",
      "type": "image",
      "source": "s3://otoedit/assets/cat_pexels_123.jpg",
      "timestamp": 25.0,
      "duration": 4.0,
      "animation": "slide-left",
      "position": ["center", "center"],
      "scale": 0.3
    }
  ],
  "template": {
    "logo": "s3://otoedit/templates/kursu_tv_logo.png",
    "logoPosition": ["center", "bottom"],
    "speakerName": "Prof. Dr. Hasan Herken",
    "speakerTitle": "Psikiyatrist/Psikoterapist",
    "subtitleStyle": "karaoke",
    "subtitleFont": "Montserrat-Bold",
    "subtitleColor": "#FFFFFF"
  },
  "repurposing": {
    "enabled": true,
    "clips": [
      {"start": 180.0, "end": 210.0, "viralScore": 0.92, "reason": "En ilgi çekici 30 saniyelik bölüm"},
      {"start": 450.0, "end": 540.0, "viralScore": 0.87, "reason": "En bilgilendirici 90 saniyelik bölüm"}
    ],
    "faceTrackingData": [
      {"timestamp": 0.0, "faceBox": {"x": 320, "y": 100, "w": 280, "h": 350}},
      {"timestamp": 0.5, "faceBox": {"x": 325, "y": 102, "w": 280, "h": 350}}
    ]
  },
  "suggestions": [
    {
      "id": "sug_1",
      "type": "image",
      "keyword": "beyin ve sinir hücreleri",
      "source": "s3://otoedit/assets/brain_neurons.jpg",
      "previewUrl": "https://images.pexels.com/photos/123/brain.jpg",
      "timestamp": 45.2,
      "duration": 3.5,
      "reason": "Konuşmacı 'zihinsel odaklanma ve nöronlar' konusundan bahsediyor",
      "status": "pending"
    },
    {
      "id": "sug_2",
      "type": "text",
      "content": "Önemli İpucu: Günde 7 Saat Uyku",
      "timestamp": 110.0,
      "duration": 4.0,
      "animation": "pop-up",
      "reason": "Tavsiye cümlesi için dikkat çekici vurgu alt başlığı",
      "status": "pending"
    }
  ]
}
```

> **Akıllı Öneri ve Onay Mekanizması (`suggestions`):**
> Sistem sadece kullanıcının el hareketi yaptığı anlarda değil; konuşmanın tamamını NLP ile tarayarak görsel/B-roll veya dikkat çekici metin yerleştirmeye uygun anları **otomatik tespit eder**. Bu öneriler başlangıçta `"status": "pending"` (onay bekliyor) durumundadır. Kullanıcı editör arayüzündeki öneri kartlarından veya AI Chat üzerinden onay verirse (`status: "accepted"`), öneri aktif `overlays` listesine taşınır ve render'a dahil edilir. Kullanıcı onaylamadan hiçbir içerik videoya zorla eklenmez.

> **Akıllı Öneri ve Onay Mekanizması (`suggestions`):**
> Sistem sadece kullanıcının el hareketi yaptığı anlarda değil; konuşmanın tamamını NLP ile tarayarak görsel/B-roll veya dikkat çekici metin yerleştirmeye uygun anları **otomatik tespit eder**. Bu öneriler başlangıçta `"status": "pending"` (onay bekliyor) durumundadır. Kullanıcı editör arayüzündeki öneri kartlarından veya AI Chat üzerinden onay verirse (`status: "accepted"`), öneri aktif `overlays` listesine taşınır ve render'a dahil edilir. Kullanıcı onaylamadan hiçbir içerik videoya zorla eklenmez.

### 1.4 MVP'de Olması Gereken Her Şey (Checklist)

MVP (Minimum Viable Product) kapsamında aşağıdaki tüm özellikler **çalışır durumda** olmalıdır:

#### Backend (.NET API)
- [ ] **Proje (Project) CRUD** — Video projesi oluşturma, listeleme, güncelleme, silme
- [ ] **Admin Kimlik Doğrulama (Auth)** — Tek kullanıcılı Admin `X-API-Key` koruması
- [ ] **Video Yükleme** — Projeye video dosyası yükleme (MinIO S3)
- [ ] **Format ve Şablon Seçimi** — Kullanıcının çıktı formatını (16:9, 9:16, 1:1) ve şablonu belirlemesi
- [ ] **EDL Yönetimi** — EDL JSON oluşturma, okuma, güncelleme (veritabanı JSONB)
- [ ] **AI Chat Endpoint** — Kullanıcı mesajını alıp LLM'e gönderme, EDL güncelleme komutu alma
- [ ] **Render Talebi** — Kullanıcı onayladığında render işlemini Python Worker'a gönderme
- [ ] **SignalR Bildirimleri** — Analiz ilerlemesi ve render tamamlanma bildirimi
- [ ] **Redis Cache** — Analiz sonucu idempotency + render cache
- [ ] **RabbitMQ Kuyrukları** — Tüm ağır işlemlerin (analiz, render) asenkron işlenmesi
- [ ] **Dayanıklılık ve Retry (Polly)** — Dış AI servisleri için Exponential Backoff retry

#### Python Worker (Video & AI Motoru)
- [ ] **Ses İyileştirme (Audio Enhancement)** — Gürültü engelleme, yankı azaltma (FFmpeg `afftdn` / `noisereduce`)
- [ ] **STT (Speech-to-Text)** — Whisper ile transkript + kelime bazlı zaman damgası çıkarma
- [ ] **Sessizlik Algılama** — `pydub` ile sessiz aralıkları tespit
- [ ] **Çoklu-Modal Komut Algılama** — MediaPipe Hands (el işaretleri) + Whisper (ses) eşzamanlı analizi
  - [ ] 👍  Thumbs Up + "Başlat" = Kayda başla/devam et
  - [ ] 👎 Thumbs Down + "Kes" = Buradan itibaren kes
  - [ ] ✌️  T İşareti + "Buraya {metin} yaz" = O anki saniyeye metin overlay ekle
  - [ ] 🖐️  P İşareti (Avuç açık) + "Buraya {nesne} resmi koy" = O anki saniyeye görsel ekle
  - [ ] ✊ G İşareti (Yumruk) + "{cümle}'ye kadar sil" = Geriye dönük bağlamsal silme
- [ ] **Komut Anı Silme** — Sesli ve görsel komut verilen anların videodan otomatik kesilmesi
- [ ] **Yüz Takibi (Face Tracking)** — MediaPipe Face Detection ile konuşan yüzün bounding box koordinatlarını çıkarma (9:16 auto-framing için)
- [ ] **Repurposing (Viral Anları Bulma)** — LLM'e transkript verip en ilgi çekici 30sn (Reels) veya 90sn (Shorts) bölümlerini seçtirme (her zaman otomatik çalışır)
- [ ] **Akıllı B-Roll & Metin Öneri Motoru** — Konuşma metnini analiz edip görsel veya yazı konulabilecek yerleri otomatik tespit etme ve kullanıcı onayına sunma
- [ ] **Stok Görsel İndirme** — Pexels/Unsplash API ile anahtar kelimeye göre görsel arama ve indirme
- [ ] **EDL Oluşturma** — Tüm analiz sonuçlarını birleştirip taslak EDL JSON üretme
- [ ] **Render Motoru** — EDL JSON'u okuyup FFmpeg (filter_complex / concat demuxer) ile nihai videoyu render etme
  - [ ] Kesim (Cut) uygulama
  - [ ] Yazı ekleme (FFmpeg drawtext / .ass altyazı)
  - [ ] Görsel ekleme (FFmpeg overlay filtresi)
  - [ ] Format dönüştürme (16:9 →  9:16 crop + face tracking)
  - [ ] Şablon uygulama (logo, isim, altyazı)
  - [ ] Animasyon uygulama (fade-in, pop-up, slide)

#### Frontend (Angular)
- [ ] **Proje Listesi Sayfası** — Tüm projeleri listeleme
- [ ] **Proje Detay Sayfası** — Video yükleme, format/şablon seçimi, analiz durumu
- [ ] **Video Yükleme Bileşeni** — Drag & drop ile video yükleme
- [ ] **Timeline Önizleme** — EDL JSON'a göre videonun kesim noktaları ve overlay'lerinin timeline gösterimi
- [ ] **AI Chat Paneli** — Yapay zeka ile sohbet ederek videoya müdahale
- [ ] **Şablon Seçim Ekranı** — Reels, Shorts, Yatay Video şablonlarından seçim
- [ ] **Render İlerleme** — SignalR ile canlı render ilerlemesi
- [ ] **Sonuç & İndirme** — Render tamamlanınca videonun önizlemesi ve indirme linki

#### Altyapı
- [ ] **Docker Compose** — Tüm servislerin (PostgreSQL, Redis, RabbitMQ, MinIO, Python Worker) tek komutla ayağa kalkması
- [ ] **MinIO S3 Depolama** — Ham video, temizlenmiş ses, render çıktısı ve asset (logo, font, görsel) depolama
- [ ] **Veritabanı Migration'ları** — Tüm entity'ler için EF Core migration
- [ ] **Log Sistemi** — Veritabanına kaydedilen kapsamlı log (Endpoint, Function, Pipeline)

### 1.5 Uçtan Uca Çalışma Akışı (Adım Adım)

| # | Adım | Kim Yapıyor | Ne Oluyor | Teknik Detay |
|---|------|-------------|-----------|--------------|
| 1 | **Videoyu Yükle & Ayarla** | 👤 Kullanıcı | Ham videoyu yükler, çıktı formatını (9:16 Reels) ve şablonu (Kürsü TV Reels) seçer. | `POST /api/projects/{id}/videos` →  MinIO'ya kaydet →  `VideoUploadedEvent` publish |
| 2 | **Ses İyileştirme** | ⚙️  Otomatik (Python) | Gürültü engelleme ve yankı azaltma. | FFmpeg `afftdn` filtresi veya Python `noisereduce` kütüphanesi |
| 3 | **STT (Ses →  Metin)** | ⚙️  Otomatik (Python) | Video sesini metne çevirir, kelime bazlı zaman damgaları çıkarır. | OpenAI Whisper API (word-level timestamps) |
| 4 | **Sessizlik & Dolgu Algılama** | ⚙️  Otomatik (Python) | 0.5 saniyeden uzun sessizlikleri ve "ıı/şey" dolgu seslerini bulur. | `pydub.silence.detect_silence()` + Whisper transkript NLP |
| 5 | **El & Ses Komut Algılama** | ⚙️  Otomatik (Python) | Videodaki el hareketlerini (👍 👎✌️ 🖐️ ✊) ve eşzamanlı sesli komutları algılar. Komut anları otomatik kesilir. | MediaPipe Hands 21 landmark + Whisper transcript eşleştirme |
| 6 | **Yüz Takibi** | ⚙️  Otomatik (Python) | 9:16 formatı seçildiyse konuşan yüzün her frame'deki bounding box koordinatları çıkarılır. | MediaPipe Face Detection |
| 7 | **Repurposing (Viral Anları Bulma)** | ⚙️  Otomatik (Python) | Gemini ile videonun en viral 30sn ve 90sn kısımları otomatik tespit edilir. | Gemini API →  `repurposing.clips` |
| 8 | **Akıllı Görsel & Metin Önerileri** | ⚙️  Otomatik (Python) | Gemini transkripti tarayıp görsel/B-roll veya vurgu yazısı konulabilecek anları öneri olarak üretir. | Gemini API + Pexels API →  `suggestions` |
| 9 | **Taslak EDL Oluşturma** | ⚙️  Otomatik (Python) | Tüm analiz sonuçları ve öneriler birleştirilip ilk taslak EDL JSON üretilir. | Python →  RabbitMQ →  .NET API'ye gönderilir |
| 10 | **Timeline İnceleme, AI Chat & Öneri Onayı** | 👤 Kullanıcı | Angular arayüzünde taslak timeline'ı görür. AI öneri kartlarını tek tıkla onaylar/reddeder veya Chat panelinden komutlar yazar ("Tüm görsel önerilerini ekle", "Vurgu yazılarını onaylama" vb.). | Angular Timeline & Öneri Kartları + `POST /api/projects/{id}/chat` →  LLM →  EDL güncelleme |
| 11 | **Repurposing Uygulama** | 👤 Kullanıcı | Arka planda Pipeline (Aşama 5) zaten viral anları seçmiştir. Kullanıcı UI'dan "Viral Klipleri Uygula (Reels/Shorts)" seçtiğinde EDL güncellenir ve video 9:16'ya göre kırpılır. | Önceden hesaplanmış EDL verisi + UI format değişimi |
| 12 | **Render** | ⚙️  Otomatik (Python) | Kullanıcı "Dışa Aktar" deyince Python Worker EDL JSON'u okur, kaynak videoyu FFmpeg donanım hızlandırması ile keser, yazıları ekler ve yeni videoyu MinIO'ya yükler. | `RenderVideoEvent` →  Python Worker →  FFmpeg →  MinIO'ya sonuç |
| 13 | **İndirme** | 👤 Kullanıcı | SignalR ile "Render tamamlandı" bildirimi gelir, video indirme linki gösterilir. | SignalR push →  Angular sonuç ekranı |

**İki tür bekleme vardır:**
- **Orta bekleme (video yüklendiğinde, bir kere):** Adım 2-8 — Videonun uzunluğuna göre dakikalar sürebilir, arka planda çalışır.
- **Kısa bekleme (chat'te her komutta):** Adım 9 — Saniyeler, çünkü sadece LLM bir JSON patch üretiyor.
- **Uzun bekleme (render, bir kere):** Adım 11 — Videonun uzunluğuna ve karmaşıklığına göre dakikalar sürebilir.

### 1.6 Çoklu-Modal Komut Sistemi Detay Tablosu

| El İşareti | MediaPipe Algılama | Eşzamanlı Sesli Komut Örneği | Sistem Aksiyonu | EDL JSON Sonucu |
|---|---|---|---|---|
| 👍  Thumbs Up | Landmark 4 (başparmak ucu) Y < Landmark 5 (işaret parmağı kökü) Y, diğer parmaklar kapalı | "Başlat" / "Devam" / "Videoyu başlat" | Kayıt aktif bölgesini başlatır. Bu andan itibaren gelen içerik korunur. | `{"type": "marker", "action": "start", "timestamp": X}` |
| 👎 Thumbs Down | Landmark 4 Y > Landmark 5 Y, diğer parmaklar kapalı | "Kes" / "Durdur" / "Burayı kes" | Aktif bölgeyi sonlandırır. Aradaki içerik cut olarak işaretlenir. | `{"type": "cut", "start": X, "end": Y, "reason": "gesture_dislike"}` |
| ✌️  T İşareti | İki elin işaret parmakları çapraz (landmark 8 koordinatları kesişir) | "Buraya {metin} yazısını yaz" | Belirtilen metni o anki saniyeye text overlay olarak ekler. Komut anı kesilir. | `{"type": "text", "content": "{metin}", "timestamp": X}` |
| 🖐️  P İşareti (Avuç açık) | Tüm parmak uçları (4,8,12,16,20) birbirinden uzak, avuç kameraya dönük | "Buraya {nesne} resmi koy" | Pexels/Unsplash API'den `{nesne}` araması yapılır, bulunan görsel o anki saniyeye eklenir. Komut anı kesilir. | `{"type": "image", "source": "pexels://...", "timestamp": X}` |
| ✊ G İşareti (Yumruk) | Tüm parmak uçları avuç içine yakın (kapalı yumruk) | "{cümle}'ye kadar sil" / "Geriye {cümle}'ye kadar sar" | Whisper transkriptinde geriye doğru `{cümle}` aranır, bulunduğu saniyeden şu ana kadar olan aralık silinir. | `{"type": "cut", "start": cümle_sn, "end": şu_an_sn, "reason": "gesture_rewind"}` |

> **Kritik Kural:** El hareketi ve sesli komut **eşzamanlı** olmalıdır (±2 saniye tolerans). Sadece el hareketi yapılıp sesli komut verilmezse veya tam tersi durumda sistem komut olarak **algılamaz**. Bu, yanlışlıkla komut vermeyi önler.

> **Açılıp Kapatılabilir:** Bu özellik proje ayarlarında `gestureCommandsEnabled: true/false` olarak kontrol edilir. Kapalıyken sistem sadece sessizlik algılama ve jump-cut yapar.

### 1.7 Şablon (Template) Sistemi

Kullanıcı video yüklerken hangi formatı ve şablonu istediğini seçer. Sistem bu şablona göre EDL JSON'u otomatik doldurur ve render aşamasında uygular.

#### Şablon 1 — Yatay Anlatım Videosu (16:9)
```
┌──────────────────────────────────────┐ 
│                              [LOGO]  │  →   Sağ üst köşe
│                                      │
│         [VIDEO İÇERİĞİ]             │
│                                      │
│                                      │
│  [ALT YAZI - opsiyonel]              │  →   Alt kısım, yarı saydam arka plan
└──────────────────────────────────────┘
```
- Logo: Kanal logosu, sağ üst veya sol üst
- Alt yazı: Opsiyonel, karaoke tarzı veya statik

#### Şablon 2 — Reels/Shorts Dikey Video (9:16)
```
┌────────────────┐ 
│                │
│   [KONUŞMACI]  │  →   Yüz takibi ile ortada
│    (yüz)       │
│                │
│ [Ad Soyad]     │  →   Konuşmacı adı ve unvanı
│ [Unvan]        │
│                │
│   [LOGO]       │  →   Kanal logosu, alt orta
│ [ALT YAZI]     │  →   Dinamik karaoke altyazı
└────────────────┘
```
- Konuşmacının yüzü: MediaPipe Face Tracking ile 9:16 kadrajın ortasında
- Ad/Unvan: Beyaz yazı, yarı saydam koyu arka plan
- Logo: Kanal logosu, alt ortada
- Altyazı: Dinamik karaoke tarzı (konuşulan kelime highlight'lanır)

#### Şablon 3 — Kare Video (1:1)
- Instagram Post / Facebook formatı (1080x1080). Üstte kalın başlık, ortada video, altta dinamik altyazı.

#### Şablon 4 — Özel Şablon
- Esnek kullanım: Sadece kullanıcının EDL JSON üzerinden belirlediği özel konumlar.

### 1.8 Pipeline'ın Aşamaları (Teknik Detay)

#### Aşama 0 — Ses İyileştirme (Audio Enhancement)
- Video yüklenince ffmpeg ile ses ayrıştırılır
- `noisereduce` (Python) veya ffmpeg `afftdn` filtresi ile gürültü engelleme uygulanır
- Yankı azaltma (echo cancellation) uygulanır
- Çıktı: Temizlenmiş `audio_clean.wav` →  MinIO'ya kaydedilir
- **Bu özellik açılıp kapatılabilir** (proje ayarlarından)

#### Aşama 1 — Speech-to-Text (STT)
- Temizlenmiş ses OpenAI Whisper API'ye gönderilir
- Word-level timestamp'ler ile kelime bazlı metin çıkarılır
- Çıktı: Transkript metni + `[{"word": "Merhaba", "start": 0.0, "end": 0.5}]` formatında zaman damgaları
- Çıktı veritabanına (`video_transcripts`) kaydedilir

#### Aşama 2 — Sessizlik & Dolgu Algılama (Jump-Cut Motoru)
- `pydub.silence.detect_silence(audio, min_silence_len=500, silence_thresh=-40)` ile sessiz anlar bulunur
- Whisper transkriptinden "ıı", "şey", "hmm" gibi dolgu sesleri NLP ile algılanır
- Bulunan anlar EDL JSON'u `{"type": "cut", "reason": "silence"}` veya `{"type": "cut", "reason": "filler_word"}` olarak eklenir

#### Aşama 3 — Çoklu-Modal Komut Algılama (Gesture + Voice)
- **Bu özellik açılıp kapatılabilir** (proje ayarlarından `gestureCommandsEnabled: true/false`)
- MediaPipe Hands ile video frame-by-frame taranır (her 3. frame yeterli, FPS/3)
- 21 el eklem noktasının (landmark) X,Y,Z koordinatları çıkarılır
- El hareketi tespit algoritması:
  - **Thumbs Up (👍 ):** Landmark 4 (başparmak ucu) Y < Landmark 5 (işaret parmağı kökü) Y ve diğer parmaklar kapalı (landmark 8,12,16,20 avuç içine yakın)
  - **Thumbs Down (👎):** Tam tersi — Landmark 4 Y > Landmark 5 Y
  - **T İşareti (✌️ ):** İki elin işaret parmakları (landmark 8) çapraz kesişimi
  - **P İşareti (🖐️ ):** Avuç tamamen açık, tüm parmak uçları (4,8,12,16,20) birbirinden uzak
  - **G İşareti (✊):** Yumruk — tüm parmak uçları avuç içine yakın
- El hareketi tespit edildiğinde, **aynı zaman aralığındaki sesli komut** Whisper transkriptinden eşleştirilir
- **İkisi birlikte olmadan komut geçerli sayılmaz** (yanlışlıkla komut vermayı önler)
- Komut verilen anlar (el hareketi + konuşma süresi) videodan otomatik olarak **kesilir** (EDL'ye cut olarak eklenir)

#### Aşama 4 — Yüz Takibi (Face Tracking)
- Sadece 9:16 veya 1:1 formatı seçildiğinde çalışır
- MediaPipe Face Detection ile her frame'de konuşan yüzün bounding box (x,y,w,h) koordinatları çıkarılır
- 16:9 →  9:16 dönüşümde yüz kutusu merkez alınarak X ekseni dinamik kaydırılır (kişi nereye hareket ederse kamera onu takip eder)
- Koordinatlar EDL JSON'a `repurposing.faceTrackingData` olarak yazılır

#### Aşama 5 — Repurposing (Viral Klip Çıkarma)
- Videonun tam transkripti Gemini API'ye gönderilir (her zaman otomatik çalışır)
- LLM'den "En ilgi çekici, duygusal veya bilgilendirici ardışık 30 saniyelik bölüm" istenir (Reels için)
- LLM'den "En ilgi çekici ardışık 90 saniyelik bölüm" istenir (Shorts için)
- LLM başlangıç ve bitiş saniyelerini + seçim gerekçesini döner
- Çıktı EDL JSON'a `repurposing.clips` olarak yazılır

#### Aşama 6 — Akıllı B-Roll ve Görsel/Metin Öneri Motoru (AI Suggestions)
- Kullanıcı herhangi bir el hareketi yapmamış olsa dahi, yapay zeka transkripti baştan sona tarar:
  - **Görsel/B-Roll Tespiti:** Konuşmacının bahsettiği somut nesneler, metaforlar veya kavramlar (örn: "yapay zeka", "beyin nöronları", "stres", "kitap") tespit edilir. Pexels API'den ilgili stok görsel aranıp URL'si ve saniyesi belirlenir.
  - **Metin/Vurgu (Callout) Tespiti:** Konuşmadaki kilit cümleler, tavsiyeler veya başlıklar için dikkat çekici yazı overlay'leri hazırlanır.
- Üretilen tüm öneriler EDL JSON'da `"suggestions": [...]` dizisine `"status": "pending"` olarak eklenir.
- **Onay Prensibi:** Öneriler doğrudan videoya zorla eklenmez; editör arayüzünde `[Kabul Et]` / `[Reddet]` kartları veya AI Chat ("Tüm görsel önerilerini ekle") aracılığıyla kullanıcının onayına sunulur. Onaylananlar aktif `overlays` dizisine taşınır.

#### Aşama 7 — Render (Nihai Video Üretimi)
- Python Worker EDL JSON'u okur
- **Kesimler:** Kesilmeyecek olan zaman aralıkları için bir `concat.txt` oluşturulup FFmpeg `concat demuxer` kullanılarak tek hamlede birleştirilir (RAM tüketimi minimumda kalır).
- **Format dönüştürme:** 16:9 →  9:16 ise yüz takibi koordinatlarına göre FFmpeg `crop` filtresi (EMA ve Deadzone ile yumuşak geçişli) uygulanır.
- **Yazılar:** Zamanlanmış yazılar, FFmpeg `drawtext` filtresi veya geçici bir `.ass` (Advanced SubStation Alpha) altyazı dosyası üretilerek render edilir.
- **Görseller:** FFmpeg `overlay` filtresi ile (örneğin `enable='between(t,5,9)'`) eklenir.
- **Şablon:** Logo, konuşmacı adı, unvan ve altyazı şablona göre otomatik yerleştirilir
- **Animasyonlar:** FFmpeg filtreleri ile (`fade`, zoompan vb.) donanım seviyesinde uygulanır.
- **Ses:** İyileştirilmiş ses dosyası nihai videoya monte edilir
- Çıktı: Renderlanmış `output.mp4` →  MinIO'ya kaydedilir

---

## 2. Kesin Uyulması Gereken Kurallar

Bu bölümdeki kurallar **mutlak** olup, hiçbir koşulda ihlal edilmemelidir. Kurallar `D:\OtoEdit\OtoEdit\docs\kurallar.txt` dosyasından referans alınarak genişletilmiştir.

### 2.1 Doküman Sadakati ve Müstakil Mimari Sözleşme
- **Bu döküman (`gelistirici-dokumani.md`) projenin tek ve nihai gerçek kaynağıdır (Single Source of Truth).**
- Geliştirici veya yapay zekâ asistanı, doğrudan bu dökümandaki teknik sözleşmeye harfiyen uyarak sistemi kuracaktır.
- Projede kodlar yazılırken **kesinlikle bu dökümanın dışına çıkılmaz**. Her bir şey yapmadan önce "bu dökümana uygun mu?" diye kontrol edilmelidir.
- Sözleşme dışına çıkılması gerekiyorsa önce açıkça raporlanmalı ve onay alınmalıdır.

### 2.2 Temiz Kod ve SOLID Prensipleri
- **S** — Single Responsibility: Her sınıf/fonksiyon tek bir iş yapmalı
- **O** — Open/Closed: Yeni özellik eklemek için mevcut kodu değiştirmemeli, genişletmeli
- **L** — Liskov Substitution: Alt sınıflar, üst sınıfların yerine kullanılabilmeli
- **I** — Interface Segregation: Büyük interface'ler yerine küçük, odaklı interface'ler
- **D** — Dependency Inversion: Somut sınıflara değil, soyutlamalara (interface) bağımlılık

### 2.3 Kod Kalitesi Standartları
```
✅ YAPILMASI GEREKENLER:
├── Interface kullanarak soyutlama (her servis bir interface'e sahip olmalı)
├── Dependency Injection ile bağımlılık yönetimi
├── Async/await pattern'ı tutarlı kullanım
├── Anlamlı isimlendirme (değişken, metod, sınıf)
├── XML dokümantasyon yorumları (public metodlar için)
├── try-catch ile hata yönetimi + loglama
├── Null safety (nullable reference types aktif)
├── Kod tekrarı yerine ortak utility/extension metodları
├── Her fonksiyonun loglanabilir olması
├── Kullanılan dilin (C#, Python, TypeScript) özelliklerini sonuna kadar kullanma
├── Modern altyapıları ve güncel best-practice'leri kullanma
└── Okunabilir ve debug edilebilir kod yazma

❌ YAPILMAMASI GEREKENLER:
├── Magic string/number kullanımı (constant veya enum kullan)
├── God class / God method (500+ satır sınıf, 50+ satır metod)
├── Catch-all exception yutma (catch {} boş bırakma — en azından logla)
├── Hardcoded connection string veya API key
├── Senkron I/O çağrısı (her zaman async kullan)
├── Console.WriteLine (ILogger kullan)
├── Kod tekrarı (DRY prensibi)
└── Bir şeyi tek seferde yazmaya çalışmak (bölümlere ayırarak yaz, her bölümden sonra dur ve kontrol et)
```

### 2.4 Performans Kuralları
- **Cache kullanımı zorunlu**: Redis ile analiz sonucu idempotency + render cache
- Veritabanı sorgularında **AsNoTracking()** kullanımı (readonly sorgular için)
- Büyük liste sorguları için **sayfalama (pagination)** zorunlu
- Ağır işlemler (video analizi, render) **asenkron kuyruk** ile işlenmeli, API thread'ini bloklamamalı
- Kod olabildiğince hızlı çalışacağı yöntemler kullanmalı (cache, paralel işlem, lazy loading vb.)
- Gereken her şey veritabanına kaydedilmeli ve en hızlı yöntem ile veri çekme işlemleri yapılmalı

### 2.5 Güvenlik Kuralları
- Hassas veriler (API key, connection string) **environment variable** veya **user-secrets** ile
- API endpoint'leri **authorization** ile korunmalı (Admin API Key)
- Input validation **FluentValidation** ile (.NET) / validator fonksiyonları ile (Python)
- Dosya yükleme boyut ve tip kontrolü
- SQL injection koruması (EF Core parameterized queries, SQLAlchemy)
- Log'larda hassas veri **maskelenmeli** (API key, token, şifre)
- Veri güvenliğine öncelik verilmeli

### 2.6 Loglama Kuralları (Kritik)
- **Her fonksiyon ve API çağrısı loglanmalıdır**
- Log'lar veritabanı tablosuna kaydedilmelidir
- Üç katmanlı log sistemi:
  1. **Endpoint Log** — Her HTTP isteği/yanıtı (middleware ile otomatik)
  2. **Function Log** — Her business/worker fonksiyonundaki hatalar (try-catch ile)
  3. **Pipeline Log** — Her pipeline aşamasının başlangıç/bitiş/hata durumu (bu projeye özel)
- Log yazma hatası uygulamayı **asla çökertmemeli**
- Hassas veriler loglanmadan önce **maskelenmeli**
- Debug edilebilirlik: Loglar sayesinde herhangi bir bug kolayca tespit edilebilmeli

### 2.7 MVP Odaklı Geliştirme
- Kod "şu haliyle kalacakmış gibi" yazılmamalı — ileride geliştirilecek ve farklı özellikler eklenecek
- Ancak şu an **sadece MVP** yapılıyor
- Her önemli eklentide **Git commit** atılmalı — olabildiğince yedekli çalışılacak
- Interface'ler ve soyutlamalar kullanarak ilerideki genişlemeye zemin hazırlanmalı

### 2.8 Bölümlü Geliştirme
- Hiçbir şey tek seferde yazılmaya çalışılmamalı (token sınırı sorunları yaşanır)
- Her bölüm yazıldıktan sonra durup, ne yapıldığına bakılmalı
- Hata alındığında, hatanın kaynağı analiz edilmeli (o dosyadan mı, başka bir bağımlılıktan mı)
- Her tamamlanan iş sonrası **rapor** verilmeli
- Eğer dökümanın dışına çıkılması gerekirse **kesinlikle haber verilmeli**

### 2.9 Çapraz Dil (Multi-Language) Kuralları
Bu projede .NET (C#), Python ve TypeScript (Angular) olmak üzere 3 dil kullanılmaktadır. Her dil için:

| Kural | .NET (C#) | Python | TypeScript (Angular) |
|-------|-----------|--------|---------------------|
| **Interface kullanımı** | `IService` interface'leri | ABC (Abstract Base Class) veya Protocol | Angular Service interface'leri |
| **Loglama** | `ILogger<T>` + veritabanı | Python `logging` modülü + RabbitMQ ile .NET'e gönderme | `console.error` + HTTP error interceptor |
| **Hata yönetimi** | try-catch + custom exception | try-except + custom exception | RxJS `catchError` + error interceptor |
| **DI (Bağımlılık Enjeksiyonu)** | Built-in Microsoft DI | Constructor injection veya Python dependency-injector | Angular built-in DI (`@Injectable`) |
| **Async** | `async/await` (Task) | `async/await` (asyncio) veya Celery task | `Observable` (RxJS) + `async/await` |

---

## 3. Teknoloji Ağacı

### 3.0 MVP Standart Teknoloji Sözleşmesi

| Alan | MVP Tercihi | Paket / İmaj | Gerekçe |
|------|-------------|--------------|---------|
| **Kimlik Doğrulama** | `X-API-Key` Middleware | `Microsoft.AspNetCore.App` | 🔑 Admin |
| **Dosya Depolama** | `MinIO (S3 API)` | `AWSSDK.S3` | Container izolasyonu |
| **STT** | `OpenAI Whisper API` | `openai` (Python) | Word-level timestamp (25MB sınırı için MP3 sıkıştırma) |
| **Ses İyileştirme** | `FFmpeg afftdn` + `noisereduce` | `noisereduce` (Python) | Gürültü/yankı temizleme |
| **El Hareketi** | `MediaPipe Hands` | `mediapipe` (Python) | 21 eklem noktası |
| **Yüz Takibi** | `MediaPipe Face Detection` | `mediapipe` (Python) | Auto-framing (Smoothing/Deadzone destekli) |
| **Video İşleme** | `FFmpeg (filter_complex)` | `ffmpeg-python` | RAM dostu, donanım hızlandırmalı, 10x hızlı |
| **Stok Görseller** | `Pexels API` | `requests` (Python) | Ücretsiz stok fotoğraf |
| **LLM** | `Google Gemini API` | `HttpClient` veya `Microsoft.Extensions.AI` | Resmi/standart çözüm, function calling |
| **Mesaj Broker** | `RabbitMQ` | `MassTransit.RabbitMQ` / `pika` | .NET → Python iletişim |
| **Veritabanı** | `PostgreSQL 16` | `Npgsql.EntityFrameworkCore.PostgreSQL` | JSONB desteği |
| **Cache** | `Redis 7` | `StackExchange.Redis` | Idempotency + cache |
| **Bildirim** | `SignalR` | `Microsoft.AspNetCore.SignalR` | Anlık bildirim |
| **Fontlar** | Gömülü `.ttf` / `.ass` altyazı | `assets/fonts/` | Hızlı ve sorunsuz render |
| **Animasyonlar** | `FFmpeg` filtreleri | — | Fade, Zoom, Crop (donanım seviyesi) |

### 3.1 Genel Mimari Görünüm

```
┌─────────────────────────────────────────────────────────────────┐ 
│                        FRONTEND                                  │
│                    Angular 18+ (SPA)                              │
│         SignalR Client · HttpClient · RxJS · Video.js            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐ 
│                      API GATEWAY                                 │
│              ASP.NET Core Web API (.NET 10)                       │
│     Controllers · Middleware · SignalR Hub · FluentValidation     │
└─────┬──────────────┬──────────────┬───────────────────────────┘
        │              │              │
        ▼              ▼              ▼
┌───────────┐   ┌───────────┐   ┌──────────────────────────────────┐ 
│  Business  │  │   Data    │  │      PYTHON WORKER               │
│   Layer    │  │   Layer   │  │  (Video & AI Motoru)             │
│ Services · │  │ EF Core · │  │                                  │
│ Interfaces │  │ Entities ·│  │  MediaPipe · Whisper · FFmpeg    │
│ DTOs ·     │  │ Repos ·   │  │  Pydub · noisereduce · Pexels    │
│ Validators │  │ Configs   │  │  Gemini API · RabbitMQ (pika)    │
└─────┬──────┘  └─────┬─────┘  └──────────┬──────────────────────┘
      │               │                   │
      ▼               ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐ 
│                     INFRASTRUCTURE                               │
│  PostgreSQL · Redis · RabbitMQ · MinIO · FFmpeg (filter_complex)     │
│  OpenAI Whisper API · Gemini API · Pexels API                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Backend Teknolojileri (.NET)

| Teknoloji | Versiyon | NuGet Paketi | Kullanım Yeri |
|-----------|----------|-------------|---------------|
| .NET | 10 | — | Tüm backend projeleri |
| ASP.NET Core Web API | 10 | `Microsoft.AspNetCore.App` | API projesi |
| Entity Framework Core | 10.x | `Microsoft.EntityFrameworkCore` | Data katmanı |
| EF Core PostgreSQL | 10.x | `Npgsql.EntityFrameworkCore.PostgreSQL` | Data katmanı |
| MassTransit | 8.x | `MassTransit.RabbitMQ` | Event publish/consume |
| Redis | 7 | `StackExchange.Redis` | Cache servisi |
| SignalR | built-in | `Microsoft.AspNetCore.SignalR` | Gerçek zamanlı bildirim |
| FluentValidation | 11.x | `FluentValidation.DependencyInjectionExtensions` | DTO validasyonu |
| Polly | 8.x | `Microsoft.Extensions.Http.Resilience` | AI API retry |
| Serilog | — | `Serilog.Sinks.PostgreSQL` | Loglama |

### 3.3 Python Worker Teknolojileri

**Neden YOLO değil de MediaPipe?**
YOLO nesne tespiti (araba, insan) için mükemmeldir ancak **parmak eklem noktalarını** çıkaramaz. MediaPipe Hands eldeki **21 eklem noktasının X,Y,Z** koordinatlarını döner — Thumbs Up/Down tespiti için bu şarttır. MediaPipe hafiftir ve GPU gerektirmez.

| Teknoloji | pip Paketi | Kullanım Yeri |
|-----------|-----------|---------------|
| MediaPipe | `mediapipe` | El/yüz algılama |
| OpenCV | `opencv-python` | Frame okuma |
| FFmpeg | `ffmpeg-python` | Kesim, overlay, render ve ses işlemleri |
| pydub | `pydub` | Sessizlik algılama |
| noisereduce | `noisereduce` | Ses gürültü temizleme |
| OpenAI Whisper API | `openai` | STT (25MB limiti için MP3 32kbps sıkıştırma) |
| Gemini API | `google-generativeai` | LLM komut çözümleme |
| Pexels API | `requests` | Stok görsel |
| pika | `pika` | RabbitMQ bağlantısı |

### 3.4 Frontend Teknolojileri

| Teknoloji | npm Paketi | Kullanım Yeri |
|-----------|-----------|---------------|
| Angular 18+ | `@angular/core` | SPA framework |
| RxJS 7.x | `rxjs` | Reactive programlama |
| SignalR Client | `@microsoft/signalr` | Gerçek zamanlı bildirim |
| Tailwind CSS | `tailwindcss` | UI stillendirme |

### 3.5 Docker Compose Servis Haritası

```yaml
services:
  api:            # ASP.NET Core API         →  localhost:5001
  python-worker:  # Python Worker (Video+AI) →  (port yok, sadece RabbitMQ consumer)
  frontend:       # Angular SPA              →  localhost:4200
  postgres:       # PostgreSQL 16            →  localhost:5432
  redis:          # Redis 7                  →  localhost:6379
  rabbitmq:       # RabbitMQ 3 Management    →  localhost:5672 (AMQP), localhost:15672 (UI)
  minio:          # MinIO S3                 →  localhost:9000 (API), localhost:9001 (Console)
  nginx:          # Nginx reverse proxy      →  localhost:80
```

### 3.6 Tam Paket Listeleri

#### OtoEdit.API (.NET)
```xml
<PackageReference Include="Microsoft.AspNetCore.SignalR" />
<PackageReference Include="Swashbuckle.AspNetCore" />
<PackageReference Include="Serilog.AspNetCore" />
<PackageReference Include="MassTransit" />
<PackageReference Include="MassTransit.RabbitMQ" />
```

#### OtoEdit.Business (.NET)
```xml
<PackageReference Include="FluentValidation.DependencyInjectionExtensions" />
<PackageReference Include="StackExchange.Redis" />
<PackageReference Include="MassTransit" />
<PackageReference Include="Microsoft.Extensions.Http" />
<PackageReference Include="AWSSDK.S3" />
```

#### OtoEdit.Data (.NET)
```xml
<PackageReference Include="Microsoft.EntityFrameworkCore" />
<PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" />
<PackageReference Include="Microsoft.EntityFrameworkCore.Design" />
```

#### Python Worker (requirements.txt)
```
openai>=1.0.0
google-generativeai>=0.3.0
mediapipe>=0.10.0
opencv-python>=4.8.0
pydub>=0.25.0
noisereduce>=3.0.0
ffmpeg-python>=0.2.0
pika>=1.3.0
requests>=2.31.0
numpy>=1.26.0
Pillow>=10.0.0
```

---

## 4. Dosya Yapısı (Tüm Projeler ve İçerikleri)

Bu bölüm, projenin **tam dosya ağacını** gösterir. OtoEdit projesindeki Clean Architecture yapısı temel alınmıştır.

### 4.1 Solution Root (Kök Dizin)

```
OtoEdit/
├── .env.example                          # Environment variable şablonu
├── .gitignore                            # Git ignore kuralları
├── OtoEdit.slnx                          # Solution dosyası
├── docker-compose.yml                    # Production docker compose
├── docker-compose.dev.yml                # Development docker compose (override)
├── nginx/
│   └── nginx.conf                        # Nginx reverse proxy yapılandırması
├── docs/
│   ├── gelistirici-dokumani.md           # Bu döküman
│   └── kurallar.txt                      # Kodlama kuralları
├── src/
│   ├── OtoEdit.API/                      # ASP.NET Core Web API projesi
│   ├── OtoEdit.Business/                 # Business Logic katmanı
│   ├── OtoEdit.Data/                     # Data Access katmanı
│   └── OtoEdit.PythonWorker/             # Python Worker projesi (Video & AI Motoru)
└── tests/
    └── OtoEdit.UnitTests/                # Unit testler
```

### 4.2 OtoEdit.Data — Data Access Katmanı

```
OtoEdit.Data/
├── OtoEdit.Data.csproj
├── ServiceRegistration.cs                    # EF Core ve Repository DI kaydı
│
├── Context/
│   └── AppDbContext.cs                       # Ana DbContext — tüm DbSet tanımları
│
├── Entities/
│   ├── Project.cs                            # Video projesi entity
│   ├── Video.cs                              # Projeye bağlı video entity
│   ├── VideoTranscript.cs                    # STT çıktısı entity
│   ├── EditDecisionList.cs                   # EDL JSON entity (JSONB)
│   ├── Template.cs                           # Video şablon entity
│   ├── ChatMessage.cs                        # AI sohbet mesajı entity
│   ├── RenderJob.cs                          # Render iş kaydı entity
│   ├── EndpointLog.cs                        # HTTP istek/yanıt log entity
│   ├── FunctionLog.cs                        # Fonksiyon hata log entity
│   └── PipelineLog.cs                        # Pipeline aşama log entity
│
├── Enums/
│   ├── ProjectDurumu.cs                      # Proje genel durumu enum
│   ├── VideoIslemDurumu.cs                   # Video analiz pipeline durumu enum
│   ├── RenderDurumu.cs                       # Render iş durumu enum
│   ├── VideoFormati.cs                       # 16:9, 9:16, 1:1 enum
│   ├── PipelineAsamasi.cs                    # Pipeline aşama enum
│   └── LogSeverity.cs                        # Log severity enum
│
├── Configurations/                           # EF Core Fluent API yapılandırmaları
│   ├── ProjectConfiguration.cs
│   ├── VideoConfiguration.cs
│   ├── VideoTranscriptConfiguration.cs
│   ├── EditDecisionListConfiguration.cs
│   ├── TemplateConfiguration.cs
│   ├── ChatMessageConfiguration.cs
│   ├── RenderJobConfiguration.cs
│   ├── EndpointLogConfiguration.cs
│   ├── FunctionLogConfiguration.cs
│   └── PipelineLogConfiguration.cs
│
├── Repositories/
│   ├── IRepository.cs                        # Generic repository interface
│   ├── GenericRepository.cs                  # Generic repository implementasyon
│   ├── IProjectRepository.cs                 # Proje özel repository interface
│   ├── ProjectRepository.cs                  # Proje özel repository implementasyon
│   ├── IVideoRepository.cs                   # Video özel repository interface
│   └── VideoRepository.cs                    # Video özel repository implementasyon
│
└── Migrations/                               # EF Core migration dosyaları (otomatik üretilir)
```

#### Entity Dosyaları — İçerik Detayı

**`Project.cs`** — Birinci sınıf varlık (ana entity)
```
Alanlar:
  - Id (Guid, PK)
  - Ad (string, zorunlu, maks 200 karakter)
  - Aciklama (string?, opsiyonel, maks 2000 karakter)
  - VideoFormati (VideoFormati enum) — 16:9, 9:16, 1:1
  - TemplateId (Guid?, FK →  Template, nullable)
  - GestureCommandsEnabled (bool, default: true)
  - AudioEnhancementEnabled (bool, default: true)
  - Durum (ProjectDurumu enum)
  - OlusturmaTarihi (DateTime, default: UtcNow)
  - GuncellemeTarihi (DateTime?, nullable)

Navigation Properties:
  - Videos (ICollection<Video>) — 1-N ilişki
  - EditDecisionList (EditDecisionList?) — 1-1 ilişki
  - Template (Template?) — N-1 ilişki
  - ChatMessages (ICollection<ChatMessage>) — 1-N ilişki
  - RenderJobs (ICollection<RenderJob>) — 1-N ilişki
```

**`Video.cs`** — Projeye bağlı video dosyası
```
Alanlar:
  - Id (Guid, PK)
  - ProjectId (Guid, FK →  Project)
  - Baslik (string, zorunlu, maks 300 karakter)
  - DosyaYolu (string, zorunlu) — MinIO S3 path
  - TemizSesYolu (string?, nullable) — İyileştirilmiş ses path
  - Sure (TimeSpan?, nullable) — video süresi
  - DosyaBoyutu (long)
  - IslemDurumu (VideoIslemDurumu enum)
  - OlusturmaTarihi (DateTime)
  - IslemTamamlanmaTarihi (DateTime?, nullable)

Navigation Properties:
  - Project (Project) — N-1 ilişki
  - Transcript (VideoTranscript?) — 1-1 ilişki
```

**`VideoTranscript.cs`** — STT çıktısı
```
Alanlar:
  - Id (Guid, PK)
  - VideoId (Guid, FK →  Video, unique)
  - HamMetin (string, zorunlu) — tam transkript
  - ZamanDamgalari (string?, JSON) — [{"word": "merhaba", "start": 0.0, "end": 0.5}]
  - Dil (string, default: "tr")
  - KelimeSayisi (int)
  - SttModel (string) — ör: "whisper-1"
  - SttSuresiMs (int)
  - OlusturmaTarihi (DateTime)
```

**`EditDecisionList.cs`** — Kurgu karar listesi (sistemin kalbi)
```
Alanlar:
  - Id (Guid, PK)
  - ProjectId (Guid, FK →  Project, unique)
  - EdlJson (string, JSONB) — tam EDL JSON (Bölüm 1.3'teki yapı)
  - Versiyon (int, default: 1) — her güncelleme versiyonu artırır
  - OlusturmaTarihi (DateTime)
  - GuncellemeTarihi (DateTime?)
```

**`Template.cs`** — Video şablonu
```
Alanlar:
  - Id (Guid, PK)
  - Ad (string, zorunlu) — "Kürsü TV Reels", "Yatay Anlatım" vb.
  - Tanim (string?, opsiyonel)
  - VideoFormati (VideoFormati enum) — 16:9, 9:16 veya 1:1
  - LogoYolu (string?, nullable) — MinIO path
  - LogoPozisyonu (string?, JSON) — ["center", "bottom"]
  - KonusmacıAdGoster (bool, default: false)
  - AltyaziStili (string?, nullable) — "karaoke", "static", "none"
  - AltyaziFont (string?, nullable) — "Montserrat-Bold"
  - AltyaziRenk (string?, nullable) — "#FFFFFF"
  - AktifMi (bool, default: true)
  - OlusturmaTarihi (DateTime)
```

**`ChatMessage.cs`** — AI sohbet mesajı
```
Alanlar:
  - Id (Guid, PK)
  - ProjectId (Guid, FK →  Project)
  - Rol (string, zorunlu) — "user" veya "assistant"
  - Mesaj (string, zorunlu) — kullanıcı veya AI mesajı
  - EdlPatch (string?, JSON, nullable) — AI'ın ürettiği EDL değişikliği
  - OlusturmaTarihi (DateTime)
```

**`RenderJob.cs`** — Render iş kaydı
```
Alanlar:
  - Id (Guid, PK)
  - ProjectId (Guid, FK →  Project)
  - EdlSnapshot (string, JSONB) — render anındaki EDL kopyası
  - Durum (RenderDurumu enum)
  - CiktiYolu (string?, nullable) — MinIO path (render sonucu)
  - BaslangicZamani (DateTime)
  - BitisZamani (DateTime?, nullable)
  - SureMs (int?, nullable)
  - HataMesaji (string?, nullable)
```

#### Enum Dosyaları — İçerik Detayı

**`ProjectDurumu.cs`**
```csharp
public enum ProjectDurumu
{
    Taslak = 0,           // Video yüklenmemiş
    VideoYuklendi = 1,    // Video yüklendi, analiz başlamadı
    AnalizEdiliyor = 2,   // Python Worker analiz ediyor
    AnalizTamamlandi = 3, // Taslak EDL hazır, kullanıcı inceleyebilir
    RenderEdiliyor = 4,   // Render işlemi devam ediyor
    Tamamlandi = 5,       // Render tamamlandı, indirmeye hazır
    Hata = 99             // Herhangi bir aşamada hata
}
```

**`VideoIslemDurumu.cs`**
```csharp
public enum VideoIslemDurumu
{
    Bekliyor = 0,
    SesIyilestirmeBasladi = 1,
    SttBasladi = 2,
    SttTamamlandi = 3,
    SessizlikAlgilamaBasladi = 4,
    KomutAlgilamaBasladi = 5,
    YuzTakibiBasladi = 6,
    AnalizTamamlandi = 7,
    Hata = 99
}
```

**`VideoFormati.cs`**
```csharp
public enum VideoFormati
{
    Yatay_16_9 = 0,   // 16:9 — YouTube, standart yatay video
    Dikey_9_16 = 1,   // 9:16 — Reels, Shorts, TikTok
    Kare_1_1 = 2      // 1:1 — Instagram post
}
```

**`PipelineAsamasi.cs`**
```csharp
using System.Text.Json.Serialization;

[JsonConverter(typeof(JsonStringEnumConverter))]
public enum PipelineAsamasi
{
    SesIyilestirme = 0,
    Stt = 1,
    SessizlikAlgilama = 2,
    KomutAlgilama = 3,
    YuzTakibi = 4,
    Repurposing = 5,
    OneriOlusturma = 6,
    EdlOlusturma = 7,
    Render = 8
}
```

### 4.3 OtoEdit.Business — Business Logic Katmanı

```
OtoEdit.Business/
├── OtoEdit.Business.csproj
├── DependencyInjection.cs                    # Tüm servis DI kayıtları
│
├── Interfaces/
│   ├── IProjectService.cs                    # Proje CRUD
│   ├── IVideoService.cs                      # Video yükleme ve yönetim
│   ├── IEdlService.cs                        # EDL oluşturma, okuma, güncelleme
│   ├── IChatService.cs                       # AI sohbet servisi
│   ├── IRenderService.cs                     # Render talep yönetimi
│   ├── ITemplateService.cs                   # Şablon yönetimi
│   ├── ICacheService.cs                      # Redis cache interface
│   ├── ILogService.cs                        # Log servis interface
│   ├── IFileStorageService.cs                # Dosya depolama interface
│   └── IPipelineNotificationService.cs       # SignalR bildirim interface
│
├── DTOs/
│   ├── Project/
│   │   ├── ProjectCreateDto.cs
│   │   ├── ProjectUpdateDto.cs
│   │   ├── ProjectListDto.cs
│   │   └── ProjectDetailDto.cs
│   ├── Video/
│   │   ├── VideoUploadDto.cs
│   │   ├── VideoListDto.cs
│   │   └── VideoDetailDto.cs
│   ├── Chat/
│   │   ├── ChatMessageDto.cs
│   │   └── ChatResponseDto.cs
│   ├── Edl/
│   │   └── EdlDto.cs
│   ├── Render/
│   │   ├── RenderRequestDto.cs
│   │   └── RenderStatusDto.cs
│   └── Pipeline/
│       └── PipelineStatusDto.cs
│
├── Events/                                   # MassTransit event mesajları (.NET → Python)
│   ├── VideoUploadedEvent.cs                 # Video yüklendi →  Python analize başlasın
│   ├── AnalysisCompletedEvent.cs             # Python analiz tamamlandı →  EDL hazır
│   ├── RenderRequestedEvent.cs               # Kullanıcı render istedi →  Python render başlasın
│   ├── RenderCompletedEvent.cs               # Python render tamamlandı
│   ├── PipelineStageChangedEvent.cs          # Pipeline aşama değişti →  SignalR bildirimi
│   └── PipelineErrorEvent.cs                 # Pipeline hatası →  SignalR bildirimi
│
├── Exceptions/
│   ├── BusinessException.cs
│   ├── NotFoundException.cs
│   └── PipelineException.cs
│
├── Validators/
│   ├── ProjectCreateValidator.cs
│   ├── ProjectUpdateValidator.cs
│   ├── VideoUploadValidator.cs
│   └── ChatMessageValidator.cs
│
├── Helpers/
│   ├── SensitiveDataMasker.cs                # Log'larda hassas veri maskeleme
│   └── HashHelper.cs                         # Cache key hash üretimi
│
├── Services/
│   ├── ProjectManager.cs                     # IProjectService implementasyonu
│   ├── VideoManager.cs                       # IVideoService implementasyonu
│   ├── EdlManager.cs                         # IEdlService implementasyonu
│   ├── ChatManager.cs                        # IChatService implementasyonu
│   ├── RenderManager.cs                      # IRenderService implementasyonu
│   ├── TemplateManager.cs                    # ITemplateService implementasyonu
│   ├── LogManager.cs                         # ILogService implementasyonu
│   └── PipelineNotificationManager.cs        # IPipelineNotificationService implementasyonu
│
└── Infrastructure/
    ├── Cache/
    │   └── RedisCacheService.cs              # ICacheService implementasyonu
    ├── Storage/
    │   ├── MinioFileStorageService.cs        # MinIO S3 implementasyonu
    │   └── LocalFileStorageService.cs        # Yerel fallback (test için)
    └── AI/
        └── GeminiChatProvider.cs             # Gemini API ile chat komut çözümleme (.NET tarafı)
```

### 4.4 OtoEdit.API — Web API Katmanı

```
OtoEdit.API/
├── OtoEdit.API.csproj
├── Program.cs
├── Dockerfile
├── appsettings.json
├── appsettings.Development.json
│
├── Controllers/
│   ├── ProjectsController.cs                 # Proje CRUD endpoint'leri
│   ├── VideosController.cs                   # Video yükleme endpoint'leri
│   ├── EdlController.cs                      # EDL okuma/güncelleme endpoint'leri
│   ├── ChatController.cs                     # AI sohbet endpoint'leri
│   ├── RenderController.cs                   # Render talep endpoint'leri
│   ├── TemplatesController.cs                # Şablon listeleme endpoint'leri
│   └── PipelineController.cs                 # Pipeline durumu endpoint'leri
│
├── Middleware/
│   ├── ExceptionHandlingMiddleware.cs
│   ├── RequestResponseLoggingMiddleware.cs
│   └── ApiKeyAuthMiddleware.cs               # X-API-Key doğrulama
│
├── Hubs/
│   └── PipelineHub.cs                        # SignalR hub — analiz ve render ilerlemesi
│
├── Consumers/
│   ├── AnalysisNotificationConsumer.cs       # Python'dan gelen analiz event'lerini SignalR'a iletir
│   └── RenderNotificationConsumer.cs         # Python'dan gelen render event'lerini SignalR'a iletir
│
└── Helpers/
    └── ApiKeyValidator.cs
```

### 4.5 OtoEdit.PythonWorker — Python Video & AI Motoru

```
OtoEdit.PythonWorker/
├── Dockerfile                                # Python + ffmpeg kurulumu
├── requirements.txt                          # pip bağımlılıkları
├── main.py                                   # Giriş noktası — RabbitMQ bağlantısı ve consumer başlatma
├── config.py                                 # Environment variable okuma (MinIO, RabbitMQ, API keys)
│
├── consumers/                                # RabbitMQ event dinleyicileri
│   ├── __init__.py
│   ├── analysis_consumer.py                  # VideoUploadedEvent →  tam analiz pipeline
│   └── render_consumer.py                    # RenderRequestedEvent →  FFmpeg render
│
├── pipeline/                                 # Analiz pipeline aşamaları
│   ├── __init__.py
│   ├── audio_enhancer.py                     # Ses iyileştirme (noisereduce + ffmpeg afftdn)
│   ├── transcriber.py                        # Whisper STT (word-level timestamps)
│   ├── silence_detector.py                   # pydub ile sessizlik algılama
│   ├── gesture_detector.py                   # MediaPipe Hands — el hareketi algılama
│   ├── voice_command_parser.py               # Sesli komut çözümleme (NLP + Whisper eşleştirme)
│   ├── multimodal_command_engine.py          # Hareket + Ses eşzamanlı komut motoru
│   ├── face_tracker.py                       # MediaPipe Face Detection — yüz takibi
│   ├── repurposing_engine.py                 # LLM ile viral bölüm seçimi
│   ├── suggestion_engine.py                  # Akıllı B-Roll ve görsel/metin öneri motoru
│   └── edl_builder.py                        # Tüm analiz sonuçlarını EDL JSON'a birleştirme
│
├── render/                                   # Render motoru
│   ├── __init__.py
│   ├── video_renderer.py                     # FFmpeg (filter_complex) ile EDL →  video render
│   ├── text_overlay.py                       # .ass dosyası veya drawtext ile yazı ekleme
│   ├── image_overlay.py                      # FFmpeg overlay ile görsel ekleme
│   ├── template_applier.py                   # Şablon uygulama (logo, isim, altyazı)
│   └── animation_effects.py                  # Hazır animasyonlar (fade, pop-up, slide)
│
├── services/                                 # Dış servis entegrasyonları
│   ├── __init__.py
│   ├── minio_client.py                       # MinIO S3 dosya indirme/yükleme
│   ├── pexels_client.py                      # Pexels API görsel arama/indirme
│   ├── gemini_client.py                      # Gemini API (viral bölüm seçimi, komut çözümleme)
│   └── rabbitmq_publisher.py                 # RabbitMQ event publish (.NET'e geri bildirim)
│
├── models/                                   # Veri modelleri (dataclass / Pydantic)
│   ├── __init__.py
│   ├── edl_model.py                          # EDL JSON Python modeli
│   ├── gesture_model.py                      # El hareketi algılama sonucu
│   ├── transcript_model.py                   # Transkript ve zaman damgası modeli
│   └── command_model.py                      # Çoklu-modal komut modeli
│
├── utils/                                    # Yardımcı fonksiyonlar
│   ├── __init__.py
│   ├── logger.py                             # Python logging yapılandırması
│   └── constants.py                          # Sabit değerler (gesture thresholds vb.)
│
└── assets/                                   # Statik dosyalar
    └── fonts/                                # Gömülü font dosyaları (.ttf)
        ├── Montserrat-Bold.ttf
        ├── Montserrat-Regular.ttf
        ├── Roboto-Bold.ttf
        ├── Roboto-Regular.ttf
        ├── BebasNeue-Regular.ttf
        ├── Poppins-Bold.ttf
        ├── Poppins-Regular.ttf
        └── Impact.ttf
```

### 4.6 Frontend — Angular Projesi

```
OtoEdit.Frontend/
├── angular.json
├── package.json
├── tsconfig.json
├── Dockerfile
│
└── src/
    ├── index.html
    ├── main.ts
    ├── styles.scss
    │
    ├── environments/
    │   ├── environment.ts
    │   └── environment.prod.ts
    │
    └── app/
        ├── app.component.ts
        ├── app.component.html
        ├── app.routes.ts
        ├── app.config.ts
        │
        ├── core/
        │   ├── services/
        │   │   ├── api.service.ts             # Base HTTP client wrapper
        │   │   ├── project.service.ts         # Proje API çağrıları
        │   │   ├── video.service.ts           # Video API çağrıları
        │   │   ├── edl.service.ts             # EDL API çağrıları
        │   │   ├── chat.service.ts            # Chat API çağrıları
        │   │   ├── render.service.ts          # Render API çağrıları
        │   │   ├── template.service.ts        # Şablon API çağrıları
        │   │   └── signalr.service.ts         # SignalR bağlantı yönetimi
        │   ├── interceptors/
        │   │   ├── error.interceptor.ts
        │   │   └── loading.interceptor.ts
        │   └── models/
        │       ├── project.model.ts
        │       ├── video.model.ts
        │       ├── edl.model.ts
        │       ├── chat.model.ts
        │       └── render.model.ts
        │
        ├── shared/
        │   ├── components/
        │   │   ├── loading-spinner/
        │   │   ├── progress-bar/
        │   │   ├── status-badge/
        │   │   └── file-upload/
        │   └── pipes/
        │       ├── duration.pipe.ts
        │       └── file-size.pipe.ts
        │
        └── features/
            ├── project-list/                  # Proje listesi sayfası
            ├── project-detail/                # Proje detay — video yükleme, format seçimi
            │   └── components/
            │       ├── video-upload/
            │       ├── format-selector/
            │       └── template-selector/
            ├── editor/                        # Ana editör sayfası — timeline + chat
            │   └── components/
            │       ├── timeline-viewer/        # EDL tabanlı timeline görünümü
            │       ├── chat-panel/             # AI sohbet paneli
            │       └── overlay-inspector/      # Overlay (yazı/görsel) yönetim paneli
            └── render-result/                 # Render sonucu — indirme sayfası
```

---

## 5. Veritabanı Tabloları ve İlişkiler

### 5.1 Entity-Relationship Diyagramı (ER)

```mermaid
erDiagram
    Project ||--o| Video : "1-1"
    Project ||--o| EditDecisionList : "1-1"
    Project ||--o{ ChatMessage : "1-N"
    Project ||--o{ RenderJob : "1-N"
    Project }o--o| Template : "N-1"
    Video ||--o| VideoTranscript : "1-1"

    Project {
        uuid Id PK
        string Ad
        string Aciklama
        int VideoFormati
        uuid TemplateId FK
        bool GestureCommandsEnabled
        bool AudioEnhancementEnabled
        int Durum
        datetime OlusturmaTarihi
        datetime GuncellemeTarihi
    }

    Video {
        uuid Id PK
        uuid ProjectId FK_UK
        string Baslik
        string DosyaYolu
        string TemizSesYolu
        interval Sure
        bigint DosyaBoyutu
        int IslemDurumu
        datetime OlusturmaTarihi
        datetime IslemTamamlanmaTarihi
    }

    VideoTranscript {
        uuid Id PK
        uuid VideoId FK_UK
        text HamMetin
        jsonb ZamanDamgalari
        string Dil
        int KelimeSayisi
        string SttModel
        int SttSuresiMs
        datetime OlusturmaTarihi
    }

    EditDecisionList {
        uuid Id PK
        uuid ProjectId FK_UK
        jsonb EdlJson
        int Versiyon
        datetime OlusturmaTarihi
        datetime GuncellemeTarihi
    }

    Template {
        uuid Id PK
        string Ad
        int VideoFormati
        string LogoYolu
        string LogoPozisyonu
        bool KonusmacıAdGoster
        string AltyaziStili
        bool AktifMi
        datetime OlusturmaTarihi
    }

    ChatMessage {
        uuid Id PK
        uuid ProjectId FK_UK
        string Rol
        text Mesaj
        jsonb EdlPatch
        datetime OlusturmaTarihi
    }

    RenderJob {
        uuid Id PK
        uuid ProjectId FK_UK
        jsonb EdlSnapshot
        int Durum
        string CiktiYolu
        datetime BaslangicZamani
        datetime BitisZamani
        int SureMs
        string HataMesaji
    }
```

### 5.2 Tablo Detayları

#### 5.2.1 `projects` Tablosu

**Açıklama:** Birinci sınıf varlık. Tüm verinin filtre anahtarı `ProjectId` bu tablodan başlar.

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `ad` | `varchar(200)` | `string` | NOT NULL | — | Proje adı |
| `aciklama` | `varchar(2000)` | `string?` | NULL | — | Proje açıklaması |
| `video_formati` | `integer` | `VideoFormati` | NOT NULL | `0` | 16:9, 9:16, 1:1 enum |
| `template_id` | `uuid` | `Guid?` | FK →  `templates(id)`, NULL | — | Seçili şablon |
| `gesture_commands_enabled` | `boolean` | `bool` | NOT NULL | `true` | El hareketi + ses komutu açık/kapalı |
| `audio_enhancement_enabled` | `boolean` | `bool` | NOT NULL | `true` | Ses iyileştirme açık/kapalı |
| `durum` | `integer` | `ProjectDurumu` | NOT NULL | `0` | Proje genel durumu enum |
| `olusturma_tarihi` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Oluşturma zamanı (UTC) |
| `guncelleme_tarihi` | `timestamptz` | `DateTime?` | NULL | — | Son güncelleme zamanı |

**Index'ler:**
```sql
CREATE INDEX idx_projects_durum ON projects (durum);
CREATE INDEX idx_projects_olusturma ON projects (olusturma_tarihi DESC);
```

---

#### 5.2.2 `videos` Tablosu

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `project_id` | `uuid` | `Guid` | FK →  `projects(id)`, NOT NULL | — | Ait olduğu proje |
| `baslik` | `varchar(300)` | `string` | NOT NULL | — | Video başlığı |
| `dosya_yolu` | `varchar(500)` | `string` | NOT NULL | — | MinIO S3 path (`videos/{projectId}/{videoId}.mp4`) |
| `temiz_ses_yolu` | `varchar(500)` | `string?` | NULL | — | İyileştirilmiş ses path (`audio/{projectId}/{videoId}_clean.wav`) |
| `sure` | `interval` | `TimeSpan?` | NULL | — | Video süresi |
| `dosya_boyutu` | `bigint` | `long` | NOT NULL | `0` | Dosya boyutu (byte) |
| `islem_durumu` | `integer` | `VideoIslemDurumu` | NOT NULL | `0` | Pipeline durumu enum |
| `olusturma_tarihi` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Yükleme zamanı |
| `islem_tamamlanma_tarihi` | `timestamptz` | `DateTime?` | NULL | — | Analiz tamamlanma zamanı |

**Index'ler:**
```sql
CREATE INDEX idx_videos_project_id ON videos (project_id);
CREATE INDEX idx_videos_durum ON videos (islem_durumu);
```

**Foreign Key:**
```sql
ALTER TABLE videos ADD CONSTRAINT fk_videos_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
```

---

#### 5.2.3 `video_transcripts` Tablosu

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `video_id` | `uuid` | `Guid` | FK →  `videos(id)`, UNIQUE, NOT NULL | — | Ait olduğu video |
| `ham_metin` | `text` | `string` | NOT NULL | — | Tam transkript metni |
| `zaman_damgalari` | `jsonb` | `string?` | NULL | — | `[{"word": "merhaba", "start": 0.0, "end": 0.5}]` |
| `dil` | `varchar(10)` | `string` | NOT NULL | `'tr'` | Tespit edilen dil |
| `kelime_sayisi` | `integer` | `int` | NOT NULL | `0` | Toplam kelime sayısı |
| `stt_model` | `varchar(50)` | `string` | NOT NULL | — | Kullanılan model (`whisper-1`) |
| `stt_suresi_ms` | `integer` | `int` | NOT NULL | `0` | STT API çağrı süresi (ms) |
| `olusturma_tarihi` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Oluşturma zamanı |

**Index'ler ve FK:**
```sql
CREATE UNIQUE INDEX idx_video_transcripts_video_id ON video_transcripts (video_id);
ALTER TABLE video_transcripts ADD CONSTRAINT fk_transcripts_video
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE;
```

---

#### 5.2.4 `edit_decision_lists` Tablosu

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `project_id` | `uuid` | `Guid` | FK →  `projects(id)`, UNIQUE, NOT NULL | — | Ait olduğu proje |
| `edl_json` | `jsonb` | `string` | NOT NULL | `'{}'` | Tam EDL JSON (Bölüm 1.3 yapısı) |
| `versiyon` | `integer` | `int` | NOT NULL | `1` | Her güncelleme versiyonu artırır |
| `olusturma_tarihi` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Oluşturma zamanı |
| `guncelleme_tarihi` | `timestamptz` | `DateTime?` | NULL | — | Son güncelleme zamanı |

**Index'ler ve FK:**
```sql
CREATE UNIQUE INDEX idx_edl_project_id ON edit_decision_lists (project_id);
ALTER TABLE edit_decision_lists ADD CONSTRAINT fk_edl_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
```

---

#### 5.2.5 `templates` Tablosu

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `ad` | `varchar(200)` | `string` | NOT NULL | — | Şablon adı |
| `tanim` | `varchar(1000)` | `string?` | NULL | — | Şablon açıklaması |
| `video_formati` | `integer` | `VideoFormati` | NOT NULL | — | 16:9, 9:16 veya 1:1 enum |
| `logo_yolu` | `varchar(500)` | `string?` | NULL | — | MinIO S3 logo path |
| `logo_pozisyonu` | `jsonb` | `string?` | NULL | — | `["center", "bottom"]` |
| `konusmaci_ad_goster` | `boolean` | `bool` | NOT NULL | `false` | Konuşmacı adı göster |
| `altyazi_stili` | `varchar(50)` | `string?` | NULL | — | `karaoke`, `static`, `none` |
| `altyazi_font` | `varchar(100)` | `string?` | NULL | — | Font adı |
| `altyazi_renk` | `varchar(20)` | `string?` | NULL | — | Hex renk kodu |
| `aktif_mi` | `boolean` | `bool` | NOT NULL | `true` | Aktif/pasif durumu |
| `olusturma_tarihi` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Oluşturma zamanı |

---

#### 5.2.6 `chat_messages` Tablosu

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `project_id` | `uuid` | `Guid` | FK →  `projects(id)`, NOT NULL | — | Ait olduğu proje |
| `rol` | `varchar(20)` | `string` | NOT NULL | — | `user` veya `assistant` |
| `mesaj` | `text` | `string` | NOT NULL | — | Mesaj içeriği |
| `edl_patch` | `jsonb` | `string?` | NULL | — | AI'ın önerdiği EDL değişikliği JSON |
| `olusturma_tarihi` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Mesaj zamanı |

**Index'ler ve FK:**
```sql
CREATE INDEX idx_chat_messages_project_id ON chat_messages (project_id);
CREATE INDEX idx_chat_messages_olusturma ON chat_messages (olusturma_tarihi);
ALTER TABLE chat_messages ADD CONSTRAINT fk_chat_messages_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
```

---

#### 5.2.7 `render_jobs` Tablosu

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `uuid` | `Guid` | PK | `gen_random_uuid()` | Benzersiz tanımlayıcı |
| `project_id` | `uuid` | `Guid` | FK →  `projects(id)`, NOT NULL | — | Ait olduğu proje |
| `edl_snapshot` | `jsonb` | `string` | NOT NULL | — | Render anındaki EDL kopyası |
| `durum` | `integer` | `RenderDurumu` | NOT NULL | `0` | Render durumu enum |
| `cikti_yolu` | `varchar(500)` | `string?` | NULL | — | MinIO path (sonuç video) |
| `baslangic_zamani` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Render başlangıcı |
| `bitis_zamani` | `timestamptz` | `DateTime?` | NULL | — | Render bitişi |
| `sure_ms` | `integer` | `int?` | NULL | — | Render süresi (ms) |
| `hata_mesaji` | `text` | `string?` | NULL | — | Hata mesajı (varsa) |

**Index'ler ve FK:**
```sql
CREATE INDEX idx_render_jobs_project_id ON render_jobs (project_id);
CREATE INDEX idx_render_jobs_durum ON render_jobs (durum);
ALTER TABLE render_jobs ADD CONSTRAINT fk_render_jobs_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
```

---

#### 5.2.8 `endpoint_logs` Tablosu — [MEVCUT PATTERN]

OtoEdit projesindeki `EndpointLog` tablosu **aynen** kullanılır. Her HTTP isteği/yanıtı burada saklanır.

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `bigserial` | `long` | PK, auto-increment | — | Benzersiz ID |
| `trace_id` | `varchar(50)` | `string?` | NULL | — | HTTP trace identifier |
| `method` | `varchar(10)` | `string` | NOT NULL | — | `GET`, `POST`, `PUT`, `DELETE` |
| `path` | `varchar(500)` | `string` | NOT NULL | — | İstek yolu |
| `query` | `varchar(1000)` | `string?` | NULL | — | Query string |
| `request_body` | `text` | `string?` | NULL | — | İstek gövdesi (hassas veriler maskelenmiş) |
| `response_body` | `text` | `string?` | NULL | — | Yanıt gövdesi (5000 char'da truncate) |
| `status_code` | `integer` | `int` | NOT NULL | — | HTTP durum kodu |
| `ip_address` | `varchar(45)` | `string?` | NULL | — | İstemci IP adresi |
| `user_agent` | `varchar(500)` | `string?` | NULL | — | Tarayıcı/client bilgisi |
| `duration_ms` | `integer` | `int` | NOT NULL | — | İstek süresi (ms) |
| `created_at` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Kayıt zamanı |

---

#### 5.2.9 `function_logs` Tablosu — [MEVCUT PATTERN]

OtoEdit projesindeki `FunctionLog` tablosu **aynen** kullanılır.

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `bigserial` | `long` | PK, auto-increment | — | Benzersiz ID |
| `error_code` | `varchar(50)` | `string` | NOT NULL | — | Hata kodu (ör: `STT_001`) |
| `class_name` | `varchar(200)` | `string` | NOT NULL | — | Hatanın oluştuğu sınıf |
| `method_name` | `varchar(200)` | `string` | NOT NULL | — | Hatanın oluştuğu metod |
| `error_message` | `text` | `string?` | NULL | — | Hata mesajı |
| `stack_trace` | `text` | `string?` | NULL | — | Stack trace |
| `input_value` | `text` | `string?` | NULL | — | Giriş verisi (JSON) |
| `trace_id` | `varchar(50)` | `string?` | NULL | — | İstek trace ID'si |
| `severity` | `varchar(20)` | `string` | NOT NULL | `'Error'` | `Error`, `Critical` |
| `created_at` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Kayıt zamanı |

---

#### 5.2.10 `pipeline_logs` Tablosu — [YENİ]

| Sütun | PostgreSQL Tipi | .NET Tipi | Constraint | Varsayılan | Açıklama |
|-------|----------------|-----------|------------|-----------|----------|
| `id` | `bigserial` | `long` | PK, auto-increment | — | Benzersiz ID |
| `video_id` | `uuid` | `Guid?` | NULL | — | İşlenen video |
| `project_id` | `uuid` | `Guid?` | NULL | — | İlgili proje |
| `render_job_id` | `uuid` | `Guid?` | NULL | — | İlgili render (render aşaması için) |
| `asama` | `integer` | `PipelineAsamasi` | NOT NULL | — | Pipeline aşama enum |
| `durum` | `varchar(20)` | `string` | NOT NULL | — | `Basladi`, `Tamamlandi`, `Hata` |
| `baslangic_zamani` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Aşama başlangıcı |
| `bitis_zamani` | `timestamptz` | `DateTime?` | NULL | — | Aşama bitişi |
| `sure_ms` | `integer` | `int?` | NULL | — | Aşama süresi (ms) |
| `hata_mesaji` | `text` | `string?` | NULL | — | Hata mesajı |
| `hata_detayi` | `text` | `string?` | NULL | — | Stack trace |
| `girdi_metadata` | `jsonb` | `string?` | NULL | — | `{"dosyaBoyutu": 1024}` |
| `cikti_metadata` | `jsonb` | `string?` | NULL | — | `{"kelimeSayisi": 5000}` |
| `trace_id` | `varchar(50)` | `string?` | NULL | — | İstek izleme ID'si |
| `created_at` | `timestamptz` | `DateTime` | NOT NULL | `now()` | Kayıt zamanı |
**Constraint'ler:**
- `video_id`: FK →  `videos.id` (ON DELETE CASCADE)
- `project_id`: FK →  `projects.id` (ON DELETE CASCADE)

**Index'ler:**
```sql
CREATE INDEX idx_pipeline_logs_video_id ON pipeline_logs (video_id);
CREATE INDEX idx_pipeline_logs_project_id ON pipeline_logs (project_id);
CREATE INDEX idx_pipeline_logs_asama ON pipeline_logs (asama);
CREATE INDEX idx_pipeline_logs_created_at ON pipeline_logs (created_at DESC);
```

### 5.3 İlişki Özet Tablosu

| Ana Tablo | Bağlı Tablo | İlişki Tipi | FK Sütunu | ON DELETE |
|-----------|-------------|-------------|-----------|-----------|
| `projects` | `videos` | 1-1 | `videos.project_id` (UNIQUE) | CASCADE |
| `projects` | `edit_decision_lists` | 1-1 | `edit_decision_lists.project_id` (UNIQUE) | CASCADE |
| `projects` | `chat_messages` | 1-N | `chat_messages.project_id` | CASCADE |
| `projects` | `render_jobs` | 1-N | `render_jobs.project_id` | CASCADE |
| `templates` | `projects` | 1-N | `projects.template_id` | SET NULL |
| `videos` | `video_transcripts` | 1-1 | `video_transcripts.video_id` (UNIQUE) | CASCADE |

**Cascade silme zinciri:**
```
Proje silinirse (IProjectService.DeleteAsync):
  1. Aşama — MinIO S3 Temizliği (Uygulama Seviyesi):
     → s3://otoedit/videos/{projectId}/ klasöründeki ham video
     → s3://otoedit/audio/{projectId}/ klasöründeki temizlenmiş ses dosyaları
     → s3://otoedit/renders/{projectId}/ klasöründeki render çıktıları
     MinIO API (RemoveObjects) ile diskten fiziksel olarak silinir (orphan/yetim dosya kalmaz).
  2. Aşama — PostgreSQL DB CASCADE:
     → projects kaydı silinir
       → video kaydı silinir (1-1)
         → video_transcripts kaydı silinir (1-1)
       → edit_decision_lists kaydı silinir (1-1)
       → chat_messages kayıtları silinir (1-N)
       → render_jobs kayıtları silinir (1-N)
```

### 5.4 Veritabanı Genel Kuralları

1. **Tüm tarihler UTC** — `DateTime.UtcNow`, `timestamptz`
2. **Tüm ID'ler UUID (Guid)** — dağıtık ortam uyumlu
3. **Log tabloları `bigserial`** — yüksek hacimli, performans için
4. **JSON verileri `jsonb`** — sorgulama ve indeksleme mümkün (`json` değil)
5. **Soft delete kullanılmaz** — CASCADE ile fiziksel silme (MVP'de yeterli)
6. **Her tablo `created_at` / `olusturma_tarihi`** — audit trail
7. **1-1 ilişkiler UNIQUE constraint** — FK + UNIQUE = birebir garanti
8. **EF Core Configuration ile tüm constraint'ler tanımlanır** — convention yerine explicit

---

## 6. Temel Fonksiyonlar ve API Endpoint'leri

### 6.1 API Endpoint Özet Tablosu

| # | Metod | Route | Açıklama | Auth |
|---|-------|-------|----------|------|
| 1 | `POST` | `/api/projects` | Yeni proje oluştur | 🔑 Admin |
| 2 | `GET` | `/api/projects` | Tüm projeleri listele | 🔑 Admin |
| 3 | `GET` | `/api/projects/{id}` | Proje detayı | 🔑 Admin |
| 4 | `PUT` | `/api/projects/{id}` | Proje güncelle | 🔑 Admin |
| 5 | `DELETE` | `/api/projects/{id}` | Proje sil (cascade) | 🔑 Admin |
| 6 | `POST` | `/api/projects/{id}/videos` | Video yükle | 🔑 Admin |
| 7 | `GET` | `/api/projects/{id}/video` | Projeye ait videoyu getir | 🔑 Admin |
| 8 | `DELETE` | `/api/projects/{id}/video` | Projeye ait videoyu sil | 🔑 Admin |
| 9 | `GET` | `/api/projects/{id}/edl` | EDL JSON oku | 🔑 Admin |
| 10 | `PATCH` | `/api/projects/{id}/edl` | EDL JSON güncelle (partial) | 🔑 Admin |
| 11 | `POST` | `/api/projects/{id}/chat` | AI sohbet mesajı gönder | 🔑 Admin |
| 12 | `GET` | `/api/projects/{id}/chat` | Chat geçmişi | 🔑 Admin |
| 13 | `POST` | `/api/projects/{id}/render` | Render talebi oluştur | 🔑 Admin |
| 14 | `GET` | `/api/projects/{id}/render/{renderJobId}` | Render durumu | 🔑 Admin |
| 15 | `GET` | `/api/projects/{id}/render/{renderJobId}/download` | Render sonucu indirme | 🔑 Admin |
| 16 | `GET` | `/api/templates` | Tüm şablonları listele | 🔑 Admin |
| 17 | `GET` | `/api/pipeline/project/{id}/progress` | Proje analiz ilerlemesi | 🔑 Admin |
| 18 | `GET` | `/api/pipeline/video/{videoId}/status` | Video analiz durumu | 🔑 Admin |
| 19 | `POST` | `/api/pipeline/video/{videoId}/retry` | Başarısız adımı tekrar dene | 🔑 Admin |

### 6.2 Proje Endpoint'leri

#### 6.2.1 `POST /api/projects` — Yeni Proje Oluştur

**Request:**
```json
{
  "ad": "Kürsü TV - Psikoloji Dersleri",
  "aciklama": "Prof. Dr. Hasan Herken'in psikoloji ders serisi",
  "videoFormati": 1,
  "templateId": "tmpl-uuid-reels",
  "gestureCommandsEnabled": true,
  "audioEnhancementEnabled": true
}
```

**Response (201 Created):**
```json
{
  "id": "proj-uuid-1234",
  "ad": "Kürsü TV - Psikoloji Dersleri",
  "aciklama": "Prof. Dr. Hasan Herken'in psikoloji ders serisi",
  "videoFormati": "Dikey_9_16",
  "templateAd": "Kürsü TV Reels",
  "gestureCommandsEnabled": true,
  "audioEnhancementEnabled": true,
  "durum": "Taslak",
  "olusturmaTarihi": "2026-09-15T07:00:00Z",
  "video": null
}
```

#### 6.2.2 `GET /api/projects/{id}` — Proje Detayı

**Response (200 OK):**
```json
{
  "id": "proj-uuid-1234",
  "ad": "Kürsü TV - Psikoloji Dersleri",
  "durum": "AnalizTamamlandi",
  "videoFormati": "Dikey_9_16",
  "video": {
    "id": "v1-uuid",
    "baslik": "Ders 1 - Depresyon",
    "sure": "01:15:30",
    "dosyaBoyutu": 1073741824,
    "islemDurumu": "AnalizTamamlandi",
    "transkriptVar": true
  },
  "edlVersiyon": 3,
  "chatMesajSayisi": 5,
  "sonRender": null
}
```

### 6.3 Video Endpoint'leri

#### 6.3.1 `POST /api/projects/{id}/videos` — Video Yükle

**Request:** `multipart/form-data`
```
Content-Type: multipart/form-data
file: video.mp4 (IFormFile)
```

**Response (201 Created):**
```json
{
  "id": "v1-uuid",
  "projectId": "proj-uuid-1234",
  "baslik": "Ders_1_Depresyon",
  "dosyaBoyutu": 1073741824,
  "islemDurumu": "Bekliyor",
  "olusturmaTarihi": "2026-09-15T07:05:00Z"
}
```

**Validasyon:**
- Dosya boyutu: Maksimum 2GB
- Dosya formatı: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`
- Proje mevcut olmalı (404)

**İş Akışı (pipeline tetikleme noktası):**
```
1. Proje var mı kontrol et →  404
2. VideoUploadValidator ile validasyon
3. Dosyayı MinIO'ya stream et: videos/{projectId}/{videoId}.mp4
4. Video entity oluştur (IslemDurumu = Bekliyor)
5. DB'ye kaydet
6. VideoUploadedEvent publish →  RabbitMQ →  Python Worker
7. Proje durumunu güncelle (AnalizEdiliyor)
8. VideoListDto olarak dön
```

### 6.4 EDL Endpoint'leri

#### 6.4.1 `GET /api/projects/{id}/edl` — EDL JSON Oku

**Response (200 OK):**
```json
{
  "projectId": "proj-uuid-1234",
  "versiyon": 3,
  "edl": {
    "cuts": [...],
    "overlays": [...],
    "template": {...},
    "repurposing": {...}
  },
  "guncellemeTarihi": "2026-09-15T08:30:00Z"
}
```

#### 6.4.2 `PATCH /api/projects/{id}/edl` — Kısmi Güncelleme (EDL Patch)

**Request (Kısmi Güncelleme / JSON Patch benzeri):**
```json
{
  "cuts": [
    {"id": "cut_1", "action": "remove"},
    {"id": "cut_new", "start": 60.0, "end": 65.0, "reason": "user_manual"}
  ],
  "overlays": [
    {
      "id": "text_new",
      "type": "text",
      "content": "Abone Ol!",
      "timestamp": 120.0,
      "duration": 5.0
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "projectId": "proj-uuid-1234",
  "versiyon": 4,
  "mesaj": "EDL güncellendi"
}
```

### 6.5 AI Chat Endpoint'leri

#### 6.5.1 `POST /api/projects/{id}/chat` — AI Sohbet Mesajı

**Request:**
```json
{
  "mesaj": "Videonun 2. dakikasına 'Abone Ol!' yazısı koy ve girişteki ilk 10 saniyeyi kes"
}
```

**Response (200 OK):**
```json
{
  "id": "chat-uuid-1",
  "rol": "assistant",
  "mesaj": "Tamam! 2. dakikaya (120. saniye) 'Abone Ol!' yazısı ekledim ve ilk 10 saniyeyi kestim. Timeline'da değişiklikleri görebilirsiniz.",
  "edlPatch": {
    "cuts": [
      {"id": "cut_ai_1", "start": 0.0, "end": 10.0, "reason": "user_command", "source": "chat"}
    ],
    "overlays": [
      {
        "id": "text_ai_1",
        "type": "text",
        "content": "Abone Ol!",
        "font": "Montserrat-Bold",
        "fontSize": 48,
        "color": "#FFFFFF",
        "timestamp": 120.0,
        "duration": 5.0,
        "animation": "pop-up",
        "position": ["center", "bottom"]
      }
    ]
  },
  "edlVersiyonYeni": 5
}
```

**İş Akışı:**
```
1. Kullanıcı mesajını al
2. Son 10 chat mesajını DB'den çek (bağlam)
3. Mevcut EDL JSON'u oku
4. Gemini API'ye gönder:
   - System prompt: "Sen bir video editörüsün. Kullanıcı komutunu EDL JSON patch'ine çevir. Kullanıcı isteğine göre formatı (targetFormat) 16:9, 9:16 veya 1:1 yapabilirsin. Kullanıcı videonun sadece viral kısımlarını veya Reels istiyorsa repurposing kliplerine dokunabilirsin. Sadece 'cuts', 'overlays' ve 'settings' dizilerini modify et, diğer alanları bozma."
   - Context: mevcut EDL özeti + chat geçmişi
   - User message: kullanıcının mesajı
5. Gemini'den dönen JSON patch'i parse et
6. EDL'yi güncelle (versiyon artır)
7. Chat mesajlarını DB'ye kaydet (user + assistant)
8. Response dön
```

### 6.6 Render Endpoint'leri

#### 6.6.1 `POST /api/projects/{id}/render` — Render Talebi

**Response (202 Accepted):**
```json
{
  "renderJobId": "rj-uuid-1",
  "projectId": "proj-uuid-1234",
  "durum": "Kuyrukta",
  "mesaj": "Render işlemi başlatıldı. SignalR ile ilerlemeden haberdar olacaksınız."
}
```

**İş Akışı:**
```
1. Proje durumu AnalizTamamlandi mi kontrol et
2. Mevcut EDL'nin snapshot'ını al
3. RenderJob entity oluştur (durum: Kuyrukta)
4. DB'ye kaydet
5. RenderRequestedEvent publish →  RabbitMQ →  Python Worker
6. Proje durumunu güncelle (RenderEdiliyor)
7. 202 Accepted döndür
```

#### 6.6.2 `GET /api/projects/{id}/render/{renderJobId}/download` — Render İndirme

**Response:** MinIO'dan presigned URL ile yönlendirme veya stream

### 6.7 SignalR Hub Mesajları

#### Hub Route: `/pipeline-hub`

**Client →  Server (invoke):**

| Metod | Parametre | Açıklama |
|-------|-----------|----------|
| `JoinProjectGroup` | `projectId: string` | Proje grubuna katıl |
| `LeaveProjectGroup` | `projectId: string` | Proje grubundan ayrıl |

**Server →  Client (on):**

| Mesaj | Payload | Tetikleyen |
|-------|---------|------------|
| `AnalysisProgress` | `{ projectId, asama, yuzde, mesaj }` | Her analiz aşaması ilerlemesi |
| `AnalysisCompleted` | `{ projectId, edlVersiyon }` | Analiz tamamlandı, EDL hazır |
| `RenderProgress` | `{ renderJobId, projectId, yuzde }` | Render ilerlemesi |
| `RenderCompleted` | `{ renderJobId, projectId, indirmeUrl }` | Render tamamlandı |
| `PipelineError` | `{ projectId, videoId, asama, hataMesaji }` | Herhangi bir hata |

### 6.8 Event Akışı (.NET → Python)

#### Video Analiz Pipeline (Event Chain)

```
VideoUploadedEvent (.NET →  Python)
  │
  Python Worker analiz pipeline:
  ├── Aşama 0: Ses İyileştirme (ffmpeg afftdn + noisereduce)
  ├── Aşama 1: STT (Whisper API →  word-level timestamps)
  ├── Aşama 2: Sessizlik Algılama (pydub)
  ├── Aşama 3: El Hareketi + Ses Komut Algılama (MediaPipe + Whisper eşleştirme)
  ├── Aşama 4: Yüz Takibi (MediaPipe Face Detection) [9:16 veya 1:1 ise]
  ├── Aşama 5: Repurposing (Gemini ile viral bölüm seçimi - her zaman çalışır)
  ├── Aşama 6: Akıllı Öneri Motoru (Görsel ve Metin B-Roll önerileri)
  └── Aşama 7: EDL Oluşturma (tüm sonuçları ve önerileri birleştir)
  │
  ├── Her aşamada: PipelineStageChangedEvent (Python →  .NET →  SignalR)
  └── Son: AnalysisCompletedEvent (Python →  .NET)
       ├── EDL JSON →  DB'ye kaydet
       ├── Proje durumu →  AnalizTamamlandi
       └── SignalR: AnalysisCompleted
```

#### Render Pipeline

```
RenderRequestedEvent (.NET →  Python)
  │
  Python Worker render:
  ├── MinIO'dan ham video indir
  ├── EDL JSON'u oku
  ├── FFmpeg (filter_complex) ile render:
  │   ├── Cuts uygula
  │   ├── Format dönüştür (face tracking ile crop)
  │   ├── Text overlay ekle
  │   ├── Image overlay ekle
  │   ├── Şablon uygula (logo, isim, altyazı)
  │   └── Animasyonlar uygula
  ├── Sonuç video →  MinIO'ya yükle
  └── RenderCompletedEvent (Python →  .NET)
       ├── RenderJob durumu →  Tamamlandi
       ├── Proje durumu →  Tamamlandi
       └── SignalR: RenderCompleted
```

### 6.9 Redis Cache Stratejisi

| Key Pattern | Değer | TTL | Kullanım |
|-------------|-------|-----|----------|
| `analysis:video:{videoId}` | `"done"` | 7 gün | Analiz idempotency kilidi |
| `render:{projectId}:{edlHash}` | MinIO path | 24 saat | Aynı EDL'den tekrar render önleme |
| `chat:{projectId}:history` | JSON (son 10 mesaj) | 1 saat | AI sohbet bağlamı hızlı yükleme |
| `pipeline:progress:{projectId}` | JSON (durum) | 5 dakika | Pipeline ilerleme — DB yükü azaltma |

### 6.10 Dayanıklılık ve Retry (Polly & MassTransit)

| Hata Türü | Davranış | Retry | Bildirim |
|-----------|----------|-------|----------|
| AI Rate Limit (429) | Exponential backoff | 3 deneme + `Retry-After` | SignalR: "Yoğunluk bekleniyor" |
| Dış API Timeout | Tekrar dene | 3 deneme (5s, 15s, 30s) | SignalR: "AI yanıtı bekleniyor" |
| Auth Hatası (401/403) | Durdur, logla | Retry yok | PipelineError |
| ffmpeg Hata | Durdur, logla | Retry yok (bozuk dosya) | PipelineError |
| DB Bağlantı | Exponential retry | 5 deneme | "DB bağlantısı kuruluyor" |

---

## 7. Kod Yazım Örnekleri ve Entegrasyonlar

Bu bölüm, projenin kullanılan kritik teknolojilerin **gerçek kod** ile nasıl entegre edileceğini gösterir.

### 7.1 Python Worker — Analiz Consumer (RabbitMQ)

```python
"""analysis_consumer.py — VideoUploadedEvent'i dinler ve tam analiz pipeline'ını çalıştırır."""
import json
import logging
import pika
from pipeline.audio_enhancer import AudioEnhancer
from pipeline.transcriber import Transcriber
from pipeline.silence_detector import SilenceDetector
from pipeline.multimodal_command_engine import MultimodalCommandEngine
from pipeline.face_tracker import FaceTracker
from pipeline.repurposing_engine import RepurposingEngine
from pipeline.suggestion_engine import SuggestionEngine
from pipeline.edl_builder import EdlBuilder
from services.minio_client import MinioClient
from services.rabbitmq_publisher import RabbitMQPublisher
from config import Config

logger = logging.getLogger(__name__)


class AnalysisConsumer:
    """RabbitMQ'dan VideoUploadedEvent dinler ve analiz pipeline'ını çalıştırır."""

    def __init__(self):
        self.minio = MinioClient()
        self.publisher = RabbitMQPublisher()
        self.audio_enhancer = AudioEnhancer()
        self.transcriber = Transcriber()
        self.silence_detector = SilenceDetector()
        self.command_engine = MultimodalCommandEngine()
        self.face_tracker = FaceTracker()
        self.repurposing = RepurposingEngine()
        self.suggestion_engine = SuggestionEngine()
        self.edl_builder = EdlBuilder()

    def start(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=Config.RABBITMQ_HOST))
        channel = connection.channel()
        
        # MassTransit Exchange Binding
        # MassTransit Publish<VideoUploadedEvent> bir fanout exchange üretir.
        # Python Worker'ın mesajı alabilmesi için kuyruk bu exchange'e bağlanmalıdır.
        channel.exchange_declare(exchange='VideoUploadedEvent', exchange_type='fanout', durable=True)
        channel.queue_declare(queue='video-uploaded', durable=True)
        channel.queue_bind(queue='video-uploaded', exchange='VideoUploadedEvent')
        
        channel.basic_consume(
            queue='video-uploaded',
            on_message_callback=self._on_message,
            auto_ack=False)
        logger.info("AnalysisConsumer başlatıldı, kuyruk dinleniyor...")
        channel.start_consuming()

    def _on_message(self, ch, method, properties, body):
        msg = json.loads(body)
        video_id = msg["videoId"]
        project_id = msg["projectId"]
        video_format = msg.get("videoFormati", 0)
        gesture_enabled = msg.get("gestureCommandsEnabled", True)
        audio_enhancement = msg.get("audioEnhancementEnabled", True)

        logger.info(f"Analiz başlıyor: video={video_id}, proje={project_id}")

        try:
            # 1. Video dosyasını MinIO'dan indir
            local_path = self.minio.download_video(project_id, video_id)
            self._publish_progress(project_id, "SesIyilestirme", 0)

            # 2. Ses İyileştirme (opsiyonel)
            if audio_enhancement:
                clean_audio = self.audio_enhancer.enhance(local_path)
                self.minio.upload_clean_audio(project_id, video_id, clean_audio)
            else:
                clean_audio = None
            self._publish_progress(project_id, "Stt", 15)

            # 3. STT (Whisper)
            transcript = self.transcriber.transcribe(
                clean_audio or local_path, video_id)
            self._publish_progress(project_id, "SessizlikAlgilama", 35)

            # 4. Sessizlik Algılama
            silence_cuts = self.silence_detector.detect(
                clean_audio or local_path)
            self._publish_progress(project_id, "KomutAlgilama", 50)

            # 5. Çoklu-Modal Komut Algılama (opsiyonel)
            commands = []
            if gesture_enabled:
                commands = self.command_engine.detect(
                    local_path, transcript)
            self._publish_progress(project_id, "YuzTakibi", 65)

            # 6. Yüz Takibi (9:16 ise)
            face_data = []
            if video_format in [1, 2]:  # Dikey_9_16
                face_data = self.face_tracker.track(local_path)
            self._publish_progress(project_id, "YuzTakibi", 75)

            # 7. Repurposing (Viral Klip Tespiti)
            repurposing_data = self.repurposing.analyze(transcript)
            self._publish_progress(project_id, "Repurposing", 80)

            # 8. Akıllı B-Roll & Görsel/Metin Öneri Motoru
            suggestions = self.suggestion_engine.generate_suggestions(transcript)
            self._publish_progress(project_id, "OneriOlusturma", 90)

            # 9. EDL Oluşturma (Öneriler dahil)
            edl_json = self.edl_builder.build(
                project_id=project_id,
                video_id=video_id,
                transcript=transcript,
                silence_cuts=silence_cuts,
                commands=commands,
                face_data=face_data,
                repurposing_data=repurposing_data,
                suggestions=suggestions,
                video_format=video_format)

            # 8. Tamamlandı event'i gönder
            self.publisher.publish("analysis-completed", {
                "projectId": project_id,
                "videoId": video_id,
                "edlJson": edl_json
            })
            self._publish_progress(project_id, "Tamamlandi", 100)
            logger.info(f"Analiz tamamlandı: video={video_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Analiz hatası: video={video_id}, hata={e}", exc_info=True)
            self.publisher.publish("pipeline-error", {
                "projectId": project_id,
                "videoId": video_id,
                "asama": "Analiz",
                "hataMesaji": str(e)
            })
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _publish_progress(self, project_id, asama, yuzde):
        self.publisher.publish("pipeline-stage-changed", {
            "projectId": project_id,
            "asama": asama,
            "yuzde": yuzde
        })
```

### 7.2 Python — Gesture Detector (MediaPipe Hands)

```python
"""gesture_detector.py — MediaPipe Hands ile el hareketlerini algılar."""
import cv2
import mediapipe as mp
import logging
from models.gesture_model import GestureResult, GestureType

logger = logging.getLogger(__name__)

mp_hands = mp.solutions.hands


class GestureDetector:
    """Video frame'lerinde el hareketlerini algılar."""

    FRAME_SKIP = 8  # Her 8. frame'i analiz et (Performans optimizasyonu)

    def detect_gestures(self, video_path: str) -> list[GestureResult]:
        """Video'daki tüm el hareketlerini algılar."""
        results = []
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_idx = 0

        with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7
        ) as hands:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % self.FRAME_SKIP != 0:
                    frame_idx += 1
                    continue

                timestamp = frame_idx / fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                detection = hands.process(rgb)

                if detection.multi_hand_landmarks:
                    for hand_landmarks in detection.multi_hand_landmarks:
                        gesture = self._classify_gesture(hand_landmarks)
                        if gesture:
                            results.append(GestureResult(
                                gesture_type=gesture,
                                timestamp=timestamp,
                                confidence=0.85
                            ))
                frame_idx += 1

        cap.release()
        logger.info(f"Gesture algılama tamamlandı: {len(results)} hareket bulundu")
        return results

    def _classify_gesture(self, landmarks) -> GestureType | None:
        """21 landmark noktasından el pozunu sınıflandırır."""
        lm = landmarks.landmark

        # Landmark 4: başparmak ucu, Landmark 5: işaret parmağı kökü
        thumb_tip = lm[4]
        index_mcp = lm[5]
        index_tip = lm[8]
        middle_tip = lm[12]
        ring_tip = lm[16]
        pinky_tip = lm[20]

        # Diğer parmaklar kapalı mı? (uçlar avuç merkezine yakın)
        wrist = lm[0]
        fingers_closed = all(
            self._distance(tip, wrist) < self._distance(index_mcp, wrist) * 1.2
            for tip in [index_tip, middle_tip, ring_tip, pinky_tip]
        )

        # Thumbs Up: başparmak yukarıda, diğerleri kapalı
        if thumb_tip.y < index_mcp.y and fingers_closed:
            return GestureType.THUMBS_UP

        # Thumbs Down: başparmak aşağıda, diğerleri kapalı
        if thumb_tip.y > index_mcp.y and fingers_closed:
            return GestureType.THUMBS_DOWN

        # Yumruk (G): tüm parmak uçları kapalı
        all_closed = self._distance(thumb_tip, wrist) < self._distance(index_mcp, wrist) * 0.8
        if all_closed and fingers_closed:
            return GestureType.FIST

        # Avuç açık (P): tüm parmak uçları birbirinden uzak
        all_open = all(
            self._distance(tip, wrist) > self._distance(index_mcp, wrist) * 1.5
            for tip in [thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip]
        )
        if all_open:
            return GestureType.OPEN_PALM

        return None

    @staticmethod
    def _distance(a, b) -> float:
        return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5
```

### 7.3 Python — Ses İyileştirme (noisereduce + FFmpeg)

```python
"""audio_enhancer.py — Gürültü engelleme ve yankı azaltma."""
import subprocess
import numpy as np
import noisereduce as nr
from pydub import AudioSegment
import logging

logger = logging.getLogger(__name__)


class AudioEnhancer:
    """Video sesinden gürültü ve yankı temizler."""

    def enhance(self, video_path: str) -> str:
        """Video'dan sesi çıkarır, temizler ve WAV olarak döner."""
        output_path = video_path.replace(".mp4", "_clean.wav")

        # 1. FFmpeg ile sesi çıkar (WAV, mono, 16kHz)
        raw_audio = video_path.replace(".mp4", "_raw.wav")
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-ac", "1", "-ar", "16000",
            "-vn", raw_audio, "-y"
        ], check=True, capture_output=True)

        # 2. noisereduce ile AI tabanlı gürültü temizleme
        audio = AudioSegment.from_wav(raw_audio)
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        rate = audio.frame_rate

        cleaned = nr.reduce_noise(y=samples, sr=rate, prop_decrease=0.8)

        # 3. FFmpeg afftdn filtresi ile ek yankı azaltma
        # Whisper API 25MB limitini aşmamak için 32kbps MP3 olarak export edilir
        cleaned_segment = AudioSegment(
            cleaned.astype(np.int16).tobytes(),
            frame_rate=rate, sample_width=2, channels=1)
        cleaned_segment.export(output_path.replace('.wav', '.mp3'), format="mp3", bitrate="32k")

        logger.info(f"Ses iyileştirme tamamlandı: {output_path.replace('.wav', '.mp3')}")
        return output_path.replace('.wav', '.mp3')
```

### 7.4 Python — Render Motoru (FFmpeg filter_complex)

```python
"""video_renderer.py — EDL JSON'u okuyup ffmpeg-python ile videoyu render eder."""
import ffmpeg
import json
import logging
from services.minio_client import MinioClient

logger = logging.getLogger(__name__)


class VideoRenderer:
    """EDL JSON'u okuyarak FFmpeg filter_complex ile donanım hızlandırmalı render eder."""

    def __init__(self):
        self.minio = MinioClient()

    def render(self, edl_json: dict, video_path: str, output_path: str):
        """EDL JSON'a göre video render et."""
        logger.info(f"Render başlıyor: {output_path}")

        # 1. Cuts uygula (Concat Demuxer ile)
        # Yüzlerce cut işlemi filter_complex'te limitlere takılabileceği için concat.txt üretilir
        cuts = edl_json.get("cuts", [])
        concat_file_path = "concat.txt"
        
        if cuts:
            keep_segments = self._get_keep_segments(cuts, edl_json.get("duration", 0))
            self._create_concat_file(keep_segments, video_path, concat_file_path)
            # Girdi olarak concat dosyasını veriyoruz
            inp = ffmpeg.input(concat_file_path, format='concat', safe=0)
        else:
            inp = ffmpeg.input(video_path)

        v = inp.video
        a = inp.audio

        # 2. Format dönüştürme (9:16 Crop - EMA & Deadzone)
        target_format = edl_json.get("settings", {}).get("targetFormat", "16:9")
        if target_format in ["9:16", "1:1"]:
            face_data = edl_json.get("repurposing", {}).get("faceTrackingData", [])
            v = self._apply_smooth_crop(v, face_data, target_format)

        # 3. Text ve Image Overlay (.ass dosyası ile)
        ass_path = self._generate_ass_file(edl_json.get("overlays", []))
        if ass_path:
            v = v.filter('ass', ass_path)

        # 4. FFmpeg komutunu çalıştır (NVENC Donanım hızlandırma ile)
        try:
            out = ffmpeg.output(v, a, output_path, 
                                vcodec='h264_nvenc', preset='p4', 
                                acodec='aac', audio_bitrate='192k')
            out.run(overwrite_output=True, quiet=True)
            logger.info(f"Render tamamlandı: {output_path}")
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg Hatası: {e.stderr.decode()}")
            raise

    def _create_concat_file(self, segments, video_path, out_file):
        """FFmpeg concat demuxer için txt dosyası üretir."""
        with open(out_file, 'w', encoding='utf-8') as f:
            for start, end in segments:
                f.write(f"file '{video_path}'\n")
                f.write(f"inpoint {start}\n")
                f.write(f"outpoint {end}\n")

    def _get_keep_segments(self, cuts, total_duration):
        """Kesilecek kısımları çıkarıp tutulacak kısımları döner."""
        cut_ranges = sorted([(c["start"], c["end"]) for c in cuts], key=lambda x: x[0])
        segments = []
        current = 0.0
        
        for start, end in cut_ranges:
            if current < start:
                segments.append((current, start))
            current = end
            
        if total_duration > 0 and current < total_duration:
            segments.append((current, total_duration))
        return segments

    def _apply_smooth_crop(self, video_stream, face_data):
        """9:16 Crop için Jitter önleyici (EMA + Deadzone) pürüzsüz crop."""
        # FFmpeg filter_complex içinde dinamik crop için matematiksel ifade (sendcmd veya crop=...) gerekir.
        # Bu örnekte basitleştirilmiş statik merkez veya sendcmd ile zaman bağımlı crop temsil edilmiştir.
        # İdeal senaryoda face_data üzerinden smooth X koordinatları hesaplanıp FFmpeg 'sendcmd' ile uygulanır.
        
        # Deadzone & EMA mantığı (örnek hesaplama)
        # smoothed_x = previous_x
        # if abs(current_x - previous_x) > DEADZONE:
        #     smoothed_x = (current_x * 0.1) + (previous_x * 0.9)
        
        target_w = "ih*9/16"
        return video_stream.filter('crop', w=target_w, h='ih', x='(iw-ow)/2', y=0)

    def _generate_ass_file(self, overlays):
        """Overlay objelerinden geçici bir .ass (karaoke dahil) dosyası üretir."""
        # ... .ass dosyası oluşturma mantığı ...
        return None
```

### 7.5 .NET — MassTransit Yapılandırması ve Consumer'lar

#### 7.5.1 MassTransit ve Raw JSON Konfigürasyonu (Program.cs / ServiceRegistration.cs)

Python Worker saf (raw) JSON mesajları ürettiğinden ve tükettiğinden, .NET tarafında MassTransit'e `UseRawJsonSerializer` ve `UseRawJsonDeserializer` eklenmelidir:

```csharp
builder.Services.AddMassTransit(x =>
{
    x.AddConsumer<AnalysisNotificationConsumer>();

    x.UsingRabbitMq((context, cfg) =>
    {
        cfg.Host(builder.Configuration["RabbitMQ:Host"] ?? "localhost", "/", h =>
        {
            h.Username(builder.Configuration["RabbitMQ:Username"] ?? "guest");
            h.Password(builder.Configuration["RabbitMQ:Password"] ?? "guest");
        });

        // Python Worker ile saf JSON entegrasyonu (MassTransit zarf hatasını önler)
        cfg.UseRawJsonSerializer();
        cfg.UseRawJsonDeserializer();

        cfg.ConfigureEndpoints(context);
    });
});
```

#### 7.5.2 Event DTO Tanımları (OtoEdit.Business.Events)

```csharp
namespace OtoEdit.Business.Events;

public record VideoUploadedEvent
{
    public Guid VideoId { get; init; }
    public Guid ProjectId { get; init; }
    public string DosyaYolu { get; init; } = string.Empty;
    public int VideoFormati { get; init; }
    public bool GestureCommandsEnabled { get; init; }
    public bool AudioEnhancementEnabled { get; init; }
}

public record PipelineStageChangedEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
    public PipelineAsamasi Asama { get; init; } // [JsonConverter(typeof(JsonStringEnumConverter))] ile string deserialize edilir
    public int Yuzde { get; init; }
    public string? Mesaj { get; init; }
}

public record AnalysisCompletedEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
    public System.Text.Json.JsonDocument EdlJson { get; init; } = default!;
}

public record RenderRequestedEvent
{
    public Guid RenderJobId { get; init; }
    public Guid ProjectId { get; init; }
    public System.Text.Json.JsonDocument EdlJson { get; init; } = default!;
}

public record RenderCompletedEvent
{
    public Guid RenderJobId { get; init; }
    public Guid ProjectId { get; init; }
    public string IndirmeUrl { get; init; } = string.Empty;
}
```

#### 7.5.3 Python'dan Gelen Event Consumer'ı

```csharp
using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen analiz tamamlanma event'ini dinler.
/// EDL JSON'u veritabanına kaydeder ve SignalR ile bildirir.
/// </summary>
public class AnalysisNotificationConsumer : IConsumer<AnalysisCompletedEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly IEdlService _edlService;
    private readonly IProjectService _projectService;
    private readonly ILogger<AnalysisNotificationConsumer> _logger;

    public AnalysisNotificationConsumer(
        IHubContext<PipelineHub> hubContext,
        IEdlService edlService,
        IProjectService projectService,
        ILogger<AnalysisNotificationConsumer> logger)
    {
        _hubContext = hubContext;
        _edlService = edlService;
        _projectService = projectService;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<AnalysisCompletedEvent> context)
    {
        var msg = context.Message;
        _logger.LogInformation(
            "AnalysisCompleted alındı: ProjectId={ProjectId}", msg.ProjectId);

        // 1. EDL JSON'u veritabanına kaydet
        var edl = await _edlService.CreateOrUpdateAsync(msg.ProjectId, msg.EdlJson);

        // 2. Proje durumunu güncelle
        await _projectService.UpdateStatusAsync(
            msg.ProjectId, Data.Enums.ProjectDurumu.AnalizTamamlandi);

        // 3. SignalR ile bildir
        await _hubContext.Clients
            .Group($"project-{msg.ProjectId}")
            .SendAsync("AnalysisCompleted", new
            {
                projectId = msg.ProjectId,
                edlVersiyon = edl.Versiyon
            });

        _logger.LogInformation(
            "Analiz tamamlandı, EDL kaydedildi: ProjectId={ProjectId}", msg.ProjectId);
    }
}
```

### 7.6 .NET — Redis Cache Kullanımı

OtoEdit projesindeki `RedisCacheService` pattern'ı **aynen** kullanılır (Bölüm 7.2'deki OtoEdit dökümanı referans).

### 7.7 .NET — AI Chat Provider (Gemini Function Calling)

```csharp
using Microsoft.Extensions.AI;
using OtoEdit.Business.Interfaces;
using System.Text.Json;

namespace OtoEdit.Business.Infrastructure.AI;

public class GeminiChatProvider : IChatProvider
{
    private readonly GenerativeModel _model;
    private readonly ILogger<GeminiChatProvider> _logger;

    public GeminiChatProvider(IConfiguration config, ILogger<GeminiChatProvider> logger)
    {
        var apiKey = config["Gemini:ApiKey"];
        var modelName = config["Gemini:Model"] ?? "gemini-2.0-flash";
        var googleAi = new GoogleAI(apiKey);
        _model = googleAi.GenerativeModel(modelName);
        _logger = logger;
    }

    public async Task<ChatResult> ProcessCommandAsync(
        string userMessage, string currentEdlJson, List<ChatHistoryItem> history)
    {
        var systemPrompt = """
            Sen bir video editörü asistanısın. Kullanıcının doğal dil komutunu alıp,
            mevcut EDL JSON üzerinde yapılacak değişiklikleri JSON patch olarak döndürüyorsun.

            Kurallar:
            - Sadece "cuts" ve "overlays" alanlarını değiştirebilirsin
            - Her cut'a benzersiz id ver (cut_ai_{index})
            - Her overlay'e benzersiz id ver (text_ai_{index} veya img_ai_{index})
            - Yanıtını JSON formatında ver: {"mesaj": "...", "edlPatch": {...}}
            - "mesaj" kullanıcıya gösterilecek, Türkçe ve samimi ol
            """;

        var prompt = $"{systemPrompt}\n\nMevcut EDL:\n{currentEdlJson}\n\nKullanıcı: {userMessage}";

        var response = await _model.GenerateContent(prompt);
        var resultText = response.Text?.Replace("```json", "").Replace("```", "").Trim();

        var parsed = JsonSerializer.Deserialize<ChatResult>(resultText);
        return parsed ?? new ChatResult { Mesaj = "Komutu anlayamadım, tekrar dener misiniz?" };
    }
}
```

---

## 8. Log Sistemi

### 8.1 Üç Katmanlı Log Mimarisi

| Katman | Tablo | Kim Yazıyor | Ne Loglanıyor |
|--------|-------|-------------|---------------|
| **Endpoint Log** | `endpoint_logs` | API Middleware (otomatik) | Her HTTP istek/yanıtı (method, path, status code, süre) |
| **Function Log** | `function_logs` | try-catch blokları (business + worker) | Fonksiyon seviyesinde hatalar (sınıf, metod, stack trace) |
| **Pipeline Log** | `pipeline_logs` | Consumer'lar (analiz + render) | Her pipeline aşamasının başlangıç/bitiş/hata kaydı |

### 8.2 Serilog Konfigürasyonu

```json
{
  "Serilog": {
    "Using": ["Serilog.Sinks.PostgreSQL", "Serilog.Sinks.Console"],
    "MinimumLevel": {
      "Default": "Information",
      "Override": {
        "Microsoft": "Warning",
        "Microsoft.Hosting.Lifetime": "Information",
        "MassTransit": "Warning",
        "Microsoft.EntityFrameworkCore.Database.Command": "Warning"
      }
    },
    "WriteTo": [
      { "Name": "Console" },
      {
        "Name": "PostgreSQL",
        "Args": {
          "connectionString": "@ConnectionStrings:DefaultConnection",
          "tableName": "function_logs",
          "autoCreateSqlTable": false
        }
      }
    ]
  }
}
```

### 8.3 Hassas Veri Maskeleme

OtoEdit projesindeki `SensitiveDataMasker` pattern'ı **aynen** kullanılır. Tüm request body'ler ve parametreler loglanmadan önce bu servisten geçer.

**Maskelenen veriler:**
- Email adresleri →  `***@***.***`
- API key'ler →  `***`
- Token'lar →  `***`
- Şifreler →  `***`

### 8.4 Log Servisi Interface

```csharp
public interface ILogService
{
    // Pipeline log
    Task<long> LogPipelineStartAsync(Guid? videoId, Guid? projectId,
        PipelineAsamasi asama, string? traceId = null);
    Task LogPipelineEndAsync(long logId, string? ciktiMetadata = null);
    Task LogPipelineErrorAsync(long logId, Exception ex);

    // Function log
    Task LogFunctionErrorAsync(string errorCode, Exception ex,
        object? input = null, string? traceId = null,
        [CallerMemberName] string methodName = "",
        [CallerFilePath] string filePath = "",
        [CallerLineNumber] int lineNumber = 0);
}
```

### 8.5 Python Worker Log Stratejisi

Python Worker kendi loglarını Python `logging` modülü ile yazar. **Kritik hatalar** RabbitMQ üzerinden .NET API'ye `PipelineErrorEvent` olarak gönderilir ve `function_logs` tablosuna kaydedilir.

```python
# utils/logger.py
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("/app/logs/worker.log")
        ]
    )
```

---

## 9. Frontend (Angular) Mimarisi ve Arayüz Akışları

### 9.1 Sayfa ve Rota Yapısı

| Rota | Component | Açıklama |
|------|-----------|----------|
| `/` | `project-list` | Tüm projeleri kart veya tablo olarak listele |
| `/project/:id` | `project-detail` | Proje detayı — video yükleme, format/şablon seçimi |
| `/project/:id/editor` | `editor` | Ana editör — timeline + AI chat panel |
| `/project/:id/render/:renderJobId` | `render-result` | Render sonucu — indirme sayfası |

### 9.2 Core Services — İçerik Detayı

**`signalr.service.ts`** — [Kritik]
```typescript
// SignalR bağlantı yönetimi
İçerik:
  - HubConnection oluşturma ve yönetme
  - Otomatik yeniden bağlanma (retry policy)
  - Grup katılma/ayrılma (joinProjectGroup / leaveProjectGroup)

Signals (Angular 18+):
  - analysisProgress() — { projectId, asama, yuzde, mesaj }
  - analysisCompleted$ — { projectId, edlVersiyon }
  - renderProgress() — { renderJobId, projectId, yuzde }
  - renderCompleted$ — { renderJobId, projectId, indirmeUrl }
  - pipelineError$ — { projectId, videoId, hataMesaji }

Kullanım:
  - project-detail component →  analiz ilerlemesi
  - editor component →  EDL güncelleme bildirimi
  - render-result component →  render tamamlanma
```

**`project.service.ts`**
```typescript
Metodlar:
  - getAll(): Observable<ProjectListDto[]>
  - getById(id: string): Observable<ProjectDetailDto>
  - create(dto: ProjectCreateDto): Observable<ProjectDetailDto>
  - update(id: string, dto: ProjectUpdateDto): Observable<ProjectDetailDto>
  - delete(id: string): Observable<void>
```

**`edl.service.ts`**
```typescript
Metodlar:
  - getEdl(projectId: string): Observable<EdlDto>
  - patchEdl(projectId: string, patch: EdlPatchDto): Observable<{ versiyon: number }>
```

**`chat.service.ts`**
```typescript
Metodlar:
  - sendMessage(projectId: string, mesaj: string): Observable<ChatResponseDto>
  - getHistory(projectId: string): Observable<ChatMessageDto[]>
```

### 9.3 Feature Components — İçerik Detayı

**`project-list`** — Proje Listesi
```
- Tüm projeleri kart olarak gösterir
- Her kartta: ad, format (16:9/9:16), video sayısı, durum, oluşturma tarihi
- "Yeni Proje" butonu →  dialog ile oluşturma
- Kart tıklanınca →  project-detail sayfasına yönlendirme
```

**`project-detail`** — Proje Detay
```
- Proje bilgileri ve ayarlar
- Video yükleme alanı (drag & drop)
- Format seçici (16:9, 9:16, 1:1 butonları)
- Şablon seçici (grid ile şablon kartları)
- Analiz ilerleme çubuğu (SignalR ile canlı)
- "Editöre Git" butonu (analiz tamamlanınca aktif)
```

**`editor`** — Ana Editör Sayfası (en karmaşık sayfa)
```
Layout:
┌─────────────────────────────────────────────┐
│                 [VIDEO PLAYER]               │
│           (kaynak video + EDL önizleme)       │
├─────────────────────────────────────────────┤
│              [TIMELINE VIEWER]               │
│    ████░░░██████░░████████░░░██████       │
│    ^cuts^    ^overlay^    ^overlay^           │
├───────────────────────┬─────────────────────┤
│   [OVERLAY INSPECTOR] │    [AI CHAT PANEL]   │
│   Yazı/Görsel listesi │    Sohbet geçmişi    │
│   + düzenleme form    │    + mesaj kutusu     │
└───────────────────────┴─────────────────────┘

Alt Bileşenler:
  - timeline-viewer: EDL JSON'daki cuts ve overlays'i yatay timeline olarak gösterir
    - Yeşil bölgeler: korunan kısımlar
    - Kırmızı bölgeler: kesilen kısımlar
    - Mavi işaretler: text overlay
    - Mor işaretler: image overlay
    - Tıklama ile seçim ve düzenleme

  - chat-panel: AI ile sohbet
    - Mesaj kutusu (Enter ile gönder)
    - Mesaj balonları (user: sağ, assistant: sol)
    - AI yanıtındaki EDL patch otomatik uygulanır
    - Timeline anında güncellenir

  - overlay-inspector: Mevcut overlay'lerin listesi ve düzenleme
    - Yazı overlay: metin, font, boyut, renk, süre, animasyon
    - Görsel overlay: kaynak, boyut, konum, süre

Aksiyonlar:
  - **Canlı EDL Simülasyonu**: Video oynatılırken `timeupdate` event'i dinlenir. Oynatma imleci kesilen (cut) bir bölgeye girerse anında `video.currentTime = cut.end` yapılarak render beklemeden akıcı atlama (skip) sağlanır.
  - "Dışa Aktar" butonu →  POST /api/projects/{id}/render →  render-result'a yönlendir
```

**`render-result`** — Render Sonucu
```
- Render ilerlemesi (SignalR ile canlı yüzde çubuğu)
- Tamamlandığında: video player ile önizleme
- İndirme butonu (presigned MinIO URL)
```

### 9.4 Angular SignalR Kullanım Örneği

```typescript
// editor.component.ts
export class EditorComponent implements OnInit, OnDestroy {
  private signalr = inject(SignalrService);
  private edlService = inject(EdlService);

  ngOnInit() {
    this.signalr.joinProjectGroup(this.projectId);

    // EDL güncelleme bildirimi
    this.signalr.analysisCompleted$
      .pipe(filter(e => e.projectId === this.projectId))
      .subscribe(() => {
        this.edlService.getEdl(this.projectId).subscribe(edl => {
          this.timeline.updateEdl(edl);
        });
      });
  }

  ngOnDestroy() {
    this.signalr.leaveProjectGroup(this.projectId);
  }

  async sendChatMessage(mesaj: string) {
    const response = await firstValueFrom(
      this.chatService.sendMessage(this.projectId, mesaj));

    // AI'ın EDL patch'i otomatik uygulandı, timeline güncelle
    if (response.edlPatch) {
      this.timeline.applyPatch(response.edlPatch);
    }
  }
}
```

---

## 10. Geliştirme Fazları (Roadmap)

### Faz 1 — Temel Altyapı (1-2 hafta)

**Hedef:** Projenin iskeletini kurmak, Docker Compose ile tüm servislerin ayağa kalkması.

| Görev | Detay |
|-------|-------|
| Solution ve projeleri oluştur | OtoEdit.API, OtoEdit.Business, OtoEdit.Data, OtoEdit.PythonWorker |
| Docker Compose hazırla | PostgreSQL, Redis, RabbitMQ, MinIO, API, Python Worker |
| Entity ve DbContext | Tüm entity'ler, enum'lar, konfigürasyonlar |
| EF Core Migration | İlk migration, tablo oluşturma |
| Repository pattern | Generic + özelleşmiş repository'ler |
| Log sistemi | Endpoint, Function, Pipeline log middleware ve servisleri |
| MinIO entegrasyonu | `IFileStorageService` →  `MinioFileStorageService` |
| Redis entegrasyonu | `ICacheService` →  `RedisCacheService` |
| API Key middleware | `ApiKeyAuthMiddleware` |
| Proje CRUD | ProjectsController + ProjectManager |

### Faz 2 — Python Worker & Analiz Pipeline (2-3 hafta)

**Hedef:** Video yüklendiğinde Python Worker'ın otomatik analiz yapması.

| Görev | Detay |
|-------|-------|
| RabbitMQ bağlantısı | pika consumer + MassTransit event |
| Ses İyileştirme | `audio_enhancer.py` — noisereduce + ffmpeg |
| STT | `transcriber.py` — Whisper API word-level timestamps |
| Sessizlik Algılama | `silence_detector.py` — pydub |
| El Hareketi Algılama | `gesture_detector.py` — MediaPipe Hands |
| Ses Komut Çözümleme | `voice_command_parser.py` — Whisper transcript eşleştirme |
| Çoklu-Modal Motor | `multimodal_command_engine.py` — hareket + ses birleştirme |
| Yüz Takibi | `face_tracker.py` — MediaPipe Face Detection |
| EDL Oluşturucu | `edl_builder.py` — tüm sonuçları birleştir |
| .NET Consumer | AnalysisNotificationConsumer →  EDL kaydet + SignalR |

### Faz 3 — AI Chat & EDL Yönetimi (1-2 hafta)

**Hedef:** Kullanıcının AI ile sohbet ederek videoya müdahale etmesi.

| Görev | Detay |
|-------|-------|
| AI Chat Provider | `GeminiChatProvider` — doğal dil →  EDL patch |
| Chat Controller | `POST /api/projects/{id}/chat` — mesaj al, LLM'e gönder, EDL güncelle |
| EDL Controller | `GET/PATCH /api/projects/{id}/edl` |
| Chat geçmişi | DB'de saklama ve Redis cache |
| Pexels entegrasyonu | `pexels_client.py` — stok görsel arama ve indirme |
| Asset yönetimi | Kullanıcının istediği görselleri MinIO'ya kaydetme |

### Faz 4 — Render Motoru (1-2 hafta)

**Hedef:** EDL JSON'dan nihai videoyu üretme.

| Görev | Detay |
|-------|-------|
| Render motoru | `video_renderer.py` — FFmpeg (filter_complex) ile render |
| Text overlay | `text_overlay.py` — FFmpeg drawtext veya .ass dosyası |
| Image overlay | `image_overlay.py` — FFmpeg overlay |
| Template sistemi | `template_applier.py` — logo, isim, altyazı |
| Animasyonlar | `animation_effects.py` — fade, pop-up, slide |
| Format dönüştürme | 16:9 →  9:16 crop + face tracking |
| Render consumer | `render_consumer.py` + .NET `RenderNotificationConsumer` |

### Faz 5 — Frontend & Son Dokunuşlar (2-3 hafta)

**Hedef:** Angular arayüzünü tamamlamak ve sistemi uçtan uca test etmek.

| Görev | Detay |
|-------|-------|
| Angular proje kurulumu | Angular 18, Tailwind CSS, SignalR Client |
| Proje listesi sayfası | Kartlar, yeni proje oluşturma |
| Proje detay sayfası | Video yükleme, format/şablon seçimi |
| Editör sayfası | Timeline viewer + AI chat panel + overlay inspector |
| Render sonuç sayfası | İndirme + önizleme |
| SignalR entegrasyonu | Canlı analiz/render ilerlemesi |
| Repurposing | `repurposing_engine.py` + frontend gösterimi |
| Uçtan uca test | Tam akış testi (yükle →  analiz →  chat →  render →  indir) |
| Polly retry | AI API'leri için dayanıklılık |
| Rate limiting | API koruması |

### Toplam Tahmini Süre

| Faz | Süre | Kümülatif |
|-----|------|-----------|
| Faz 1 — Temel Altyapı | 1-2 hafta | 1-2 hafta |
| Faz 2 — Analiz Pipeline | 2-3 hafta | 3-5 hafta |
| Faz 3 — AI Chat | 1-2 hafta | 4-7 hafta |
| Faz 4 — Render | 1-2 hafta | 5-9 hafta |
| Faz 5 — Frontend | 2-3 hafta | 7-12 hafta |
| **TOPLAM** | **7-12 hafta** | — |

---

> **Bu dökümanın sonu.** Tüm teknik kararlar, veri modelleri, API sözleşmeleri ve kod örnekleri yukarıda tanımlanmıştır. Geliştirme sürecinde bu döküman güncel tutulmalı ve her büyük değişiklikte versiyonu artırılmalıdır.






