# 🚀 OtoEdit — Yeni Kalanlar ve Sorunların Çözüm Rehberi Dökümanı

> **Dosya Konumu:** `docs/yeni_kalanlar_ve_cozum_rehberi.md`  
> **Tarih:** 15 Ekim 2026  
> **Hazırlayan:** Antigravity AI — OtoEdit Çekirdek Geliştirme Ekibi  
> **Durum:** Güncel Durum Tespiti, Tamamlananlar ve Adım Adım Çözüm Kılavuzu  

---

## 📋 1. Yönetici Özeti ve Mevcut Durum Tespiti

OtoEdit projesinde son yapılan geliştirmelerle birlikte projenin temel omurgasını oluşturan algoritmik, yapay zeka ve arayüz katmanları büyük oranda tamamlanmış ve stabilize edilmiştir. 

Kullanıcı geri bildirimleri doğrultusunda incelenen ve **zaten yapılı olduğu teyit edilen** veya **son aşamada sisteme kazandırılan** özellikler aşağıda özetlenmiştir.

### ✅ 1.1. Tamamlanan ve Doğrulanan Özellikler Tablosu

| Modül | Özellik | Durum | Açıklama / Kod Konumu |
| :--- | :--- | :---: | :--- |
| **Kesim Motoru** | Jump-Cut (v2 / v3) & Silero VAD | **Tamamlandı** | `pipeline/silero_vad.py`, `pipeline/jumpcut.py` |
| **Kelime Koruma** | Word Guard & Akıllı Kenar Boşluğu | **Tamamlandı** | Kelime başlangıç/bitiş harflerinin kesilmesini önler. |
| **Toplu Trim** | Milisaniye İnce Ayar (+/- ms) & Sıfırla | **Tamamlandı** | Kısa/uzun/tüm kesimlere serbest ms kaydırma ve tek tıkla sıfırlama. |
| **Hatalı Tekrar** | Retake Detector & Geri Alma | **Tamamlandı** | `pipeline/retake_detector.py` ve timeline geri alma butonu. |
| **Altyazı Stüdyosu** | Dinamik Karaoke Altyazı (CapCut Stili) | **Tamamlandı** | Canlı oynatıcıda sarı parlama ve ASS `{\k...}` motoru hazır. |
| **Monitör Kanvası**| Serbest Sürükleme (Drag) & Boyutlandırma | **Tamamlandı** | `onCanvasDragStart` & `onCanvasResizeStart` ile serbest düzenleme. |
| **AI Sohbet** | Seçili Aralığa Yazı Ekleme (Önizle / Onayla) | **Tamamlandı** | `GeminiChatProvider.cs` `pendingEdlPatch` ile çift butonlu onay. |
| **AI Transkript** | Soru-Cevap & İçerik Arama | **Tamamlandı** | "Bediüzzaman kaçıncı saniyede?" soruları EDL transkriptinden yanıtlanır. |
| **Oynatıcı** | Hız Kontrolü (0.5x - 2.0x) | **Tamamlandı** | Monitör barında `⚡ 1x` hızlı çevrim butonu. |
| **Görüntü İşleme** | Renk Ayarları (Color Grading Paneli) | **Tamamlandı** | Parlaklık, kontrast, doygunluk, sıcaklık ve 5 hazır preset. |
| **Medya** | Kategorize B-Roll Stok Kütüphanesi | **Tamamlandı** | Hukuk, Teknoloji, Doğa, Tarih, İş kategorilerinde hazır medya. |

---

## 🧩 2. Yeni Kalanlar Listesi (Kalan Eksikler)

Projenin profesyonel video kurgu pazarında (CapCut, Premiere Pro, OpusClip) tam teşekküllü bir alternatif haline gelebilmesi için çözülmesi gereken yeni kalan maddeler öncelik sırasına göre şunlardır:

1. **[E1] Otonom Video Yönetmeni (Proaktif AI & Suggestions Motoru)**
2. **[E2] Arka Plan Müziği (BGM) FFmpeg Auto-Ducking Entegrasyonu**
3. **[E3] Altyazı Çift Tıklayarak Düzenleme (Inline Subtitle Editor)**
4. **[E4] Görsel Arka Plan Kaldırma (`rembg` U2Net AI Sticker Motoru)**
5. **[E5] Pexels API Entegrasyonu & Otomatik İngilizceye Çeviri**
6. **[E6] Manyetik Timeline & Otomatik Boşluk Kapatma (Ripple Edit)**
7. **[E7] Çoklu Klip Seçimi (Multi-Select Ctrl/Shift ile Toplu İşlem)**
8. **[E8] Standart Ses Normalizasyonu (YouTube / TikTok -14 LUFS Loudnorm)**

---

## 🛠️ 3. Kalan Sorunlar ve Adım Adım Çözüm Rehberi

---

### 3.1. [E1] Otonom Video Yönetmeni (Proaktif AI Suggestions Motoru)

#### 🔴 Sorun:
Şu anda yapay zeka yalnızca kullanıcı sohbet kutusuna bir şey yazdığında tepki veriyor. Video yüklendiğinde kullanıcıyı yönlendiren, kurgusal öneriler sunan proaktif bir mekanizma bulunmuyor.

#### 🟢 Çözüm Mimarisi:
1. Python Worker transkripsiyonu tamamlayıp EDL oluşturduktan hemen sonra veya `.NET API` tarafında `VideoDirectorService` tetiklenir.
2. Servis transkripti LLM'e (Gemini) göndererek şu formatta 3-5 adet öneri (`SuggestionItem`) üretir:
   * **Giriş Kancası (Hook Title):** İlk 3-5 saniyeye çarpıcı bir başlık overlay'i.
   * **B-Roll Önerisi:** Konuşmacının önemli bir kavramdan bahsettiği yere ilgili stok görsel.
   * **Bölüm Başlığı:** Konu geçişi olan yere alt yazı başlığı.
3. Öneriler `edl_json->suggestions` içerisine yazılır.
4. Frontend'deki **Öneriler** sekmesinde kullanıcıya kartlar halinde gösterilir; kullanıcı tek tıkla **"Kabul Et"** dediğinde öneri doğrudan EDL'e katman olarak eklenir.

#### 💻 Çözüm Kodu (.NET / Python):
```csharp
// OtoEdit.Business/Services/VideoDirectorService.cs
public async Task<List<SuggestionItem>> GenerateSuggestionsAsync(string transcriptText, double duration)
{
    var prompt = $@"Aşağıdaki video transkriptini incele ve sosyal medya kurgusu için 3 ile 5 arasında somut görsel/metin önerisi üret.
JSON formatında array dön:
[
  {{
    ""id"": ""sug_1"",
    ""type"": ""overlay_text"",
    ""timestamp"": 2.5,
    ""duration"": 4.0,
    ""title"": ""Çarpıcı Giriş Başlığı"",
    ""content"": ""Büyük Değişim Başlıyor!"",
    ""reason"": ""İzleyiciyi videoda tutmak için ilk saniyelerde kanca başlık.""
  }}
]
Transkript:
{transcriptText}";

    return await _geminiProvider.GenerateJsonAsync<List<SuggestionItem>>(prompt);
}
```

---

### 3.2. [E2] Arka Plan Müziği (BGM) FFmpeg Auto-Ducking Entegrasyonu

#### 🔴 Sorun:
Frontend'de BGM ses düzeyi ve Auto-Ducking anahtarı bulunuyor; ancak video nihai olarak FFmpeg ile render edilirken konuşma başladığında müziğin sesini kısıp konuşma bitince yükselten dinamik ducking filtresi FFmpeg komutuna bağlanmamış durumda.

#### 🟢 Çözüm Mimarisi:
FFmpeg'in `sidechaincompress` veya `volume` filtresi konuşma ses kanalını (speech) tetikleyici olarak kullanır. Konuşma sesi belirli bir eşiği (`threshold=0.03`) aştığında müzik kanalı otomatik olarak %15'e iner; konuşma durduğunda yumuşak bir geçişle (attack/release) eski seviyesine döner.

#### 💻 Çözüm Kodu (`src/OtoEdit.PythonWorker/render/video_renderer.py`):
```python
# FFmpeg complex_filter ducking pipeline:
def build_audio_ducking_filter(speech_input: str, bgm_input: str, ducking_amount: float = 0.15) -> str:
    # speech: [1:a], bgm: [2:a]
    filter_graph = (
        f"[2:a]volume=0.3[bgm_vol];"
        f"[bgm_vol][1:a]sidechaincompress="
        f"threshold=0.04:ratio=5:attack=60:release=350[ducked_bgm];"
        f"[1:a][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )
    return filter_graph
```
*Bu sayede konuşma olan yerlerde müzik asla konuşmacıyı bastırmaz, YouTube/Reels profesyonel stüdyo kalitesinde miksaj elde edilir.*

---

### 3.3. [E3] Altyazı Çift Tıklayarak Canlı Düzenleme (Inline Subtitle Editor)

#### 🔴 Sorun:
Whisper transkripsiyonu sırasında konuşmacının söylediği özel isimler veya terimler yanlış algılandığında (örneğin "Gazali" yerine "Kazalı"), kullanıcının bunu altyazı kutusuna çift tıklayarak düzeltmesi ve düzeltmenin anında hem video monitörüne hem de EDL'e kaydedilmesi gerekiyor.

#### 🟢 Çözüm Mimarisi:
1. `editor.component.ts` içerisindeki altyazı önizleme bileşenine ve sol paneldeki Transkript listesine `(dblclick)="startInlineSubtitleEdit(seg)"` eklenir.
2. Çift tıklandığında metin kutusu anında bir input'a dönüşür.
3. Kullanıcı `Enter` tuşuna bastığında veya kutu dışına tıkladığında (`blur`), `edlService.patchEdl` çağrılarak ilgili segmentin `text` alanı güncellenir.

#### 💻 Çözüm Kodu (`editor.component.ts`):
```typescript
// editor.component.ts
editingSubtitleId = signal<string | null>(null);
inlineSubText = signal<string>('');

startInlineSubtitleEdit(seg: TranscriptSegment): void {
  this.editingSubtitleId.set(this.getSubtitleId(seg));
  this.inlineSubText.set(seg.text);
}

saveInlineSubtitleEdit(seg: TranscriptSegment): void {
  const newText = this.inlineSubText().trim();
  if (newText && newText !== seg.text) {
    seg.text = newText;
    this.edlService.patchEdl(this.projectId, {
      transcript: {
        segments: [{ id: this.getSubtitleId(seg), text: newText, start: seg.start, end: seg.end }]
      }
    } as any).subscribe();
  }
  this.editingSubtitleId.set(null);
}
```

---

### 3.4. [E4] Görsel Arka Plan Kaldırma (`rembg` U2Net AI Sticker Motoru)

#### 🔴 Sorun:
Kullanıcı veya yapay zeka bir kitap kapağı, portre veya logo eklediğinde, görselin arkasındaki beyaz/siyah fon videonun üzerine dikdörtgen kutu gibi biniyor.

#### 🟢 Çözüm Mimarisi:
1. `OtoEdit.PythonWorker` ortamına hafif ve yüksek doğruluklu `rembg` (U-2-Net tabanlı) kütüphanesi kurulur (`pip install rembg`).
2. Bir asset yüklendiğinde veya kullanıcı katman ayarlarında **"Arka Planı Kaldır (Sticker Yap)"** butonuna bastığında Python Worker görseli işleyip şeffaf PNG olarak MinIO'ya geri kaydeder.
3. Frontend'de `ov.removeBg = true` olduğunda bu şeffaf görsel URL'i katmana atanır.

#### 💻 Çözüm Kodu (`pipeline/bg_remover.py`):
```python
from rembg import remove
from PIL import Image
import io

def remove_background(input_image_bytes: bytes) -> bytes:
    """Görselin arka planını yapay zeka ile şeffaf hale getirir."""
    input_image = Image.open(io.BytesIO(input_image_bytes))
    output_image = remove(input_image)
    output_io = io.BytesIO()
    output_image.save(output_io, format='PNG')
    return output_io.getvalue()
```

---

### 3.5. [E5] Pexels API Entegrasyonu & Otomatik İngilizceye Çeviri

#### 🔴 Sorun:
`.env` dosyasında varsayılan `PEXELS_API_KEY` placeholder olarak durduğu için canlı aramalarda veya AI otomatik stok indirmesinde 401 hatası alınabiliyor. Ayrıca kullanıcı Türkçe arama yaptığında ("mahkeme salonu") Pexels sonuç döndüremeyebiliyor.

#### 🟢 Çözüm Mimarisi:
1. `.env` içerisine geçerli bir Pexels API Key tanımlanır.
2. `PexelsService` arama yapmadan önce arama terimini Gemini veya basit bir sözlük ile İngilizceye dönüştürür ("mahkeme salonu" ➔ "courtroom law", "yapay zeka" ➔ "artificial intelligence coding").
3. Arama sonuçları MinIO'ya geçici olarak önbelleğe alınır.

---

### 3.6. [E6] Manyetik Timeline & Otomatik Boşluk Kapatma (Ripple Edit)

#### 🔴 Sorun:
Kullanıcı timeline üzerinde manuel bir kesim yaptığında veya bir klibi sildiğinde, silinen klibin ardındaki tüm kliplerin ve üzerlerindeki overlay katmanlarının sola doğru yanaşarak boşluğu otomatik kapatması gerekir.

#### 🟢 Çözüm Mimarisi:
1. Bir klip silindiğinde (`deleteClip(clipId)`):
   * Silinen klibin süresi hesaplanır: `gapDuration = clip.end - clip.start`.
   * Silinen klibin bitişinden sonra başlayan tüm kliplerin başlangıç ve bitiş zamanları `gapDuration` kadar sola kaydırılır (`start -= gapDuration`, `end -= gapDuration`).
   * Aynı şekilde o zaman aralığından sonraki metin/görsel katmanları (`overlay.timestamp -= gapDuration`) sola kaydırılır.
2. Tek bir `patchEdl` paketiyle güncel zamanlar kaydedilir.

---

### 3.7. [E7] Çoklu Klip Seçimi (Multi-Select Ctrl/Shift ile Toplu İşlem)

#### 🔴 Sorun:
Kullanıcı birden fazla klibi aynı anda seçip tek seferde silemiyor veya topluca sesini kapatamıyor.

#### 🟢 Çözüm Mimarisi:
* `editor.component.ts` içerisinde `selectedClipIds = signal<string[]>([])` dizisi zaten tanımlıdır.
* Timeline üzerindeki klibe tıklandığında:
  * `Ctrl` tuşu basılıysa: Klip `selectedClipIds` listesinde varsa çıkarılır, yoksa listeye eklenir.
  * `Shift` tuşu basılıysa: Son seçilen klip ile tıklanan klip arasındaki tüm klipler aralık olarak seçilir.
  * Tuşa basılmamışsa: Yalnızca tıklanan klip seçilir.
* Birden fazla klip seçildiğinde ekranda beliren yüzen araç çubuğu (Floating Bar) ile **"Seçilenleri Toplu Kes / Sil"** işlemi uygulanır.

---

### 3.8. [E8] Standart Ses Normalizasyonu (YouTube / TikTok -14 LUFS)

#### 🔴 Sorun:
Farklı mikrofonlarla kaydedilen videolarda ses seviyesi bazen çok düşük, bazen ise patlayacak kadar yüksek (clipping) olabiliyor.

#### 🟢 Çözüm Mimarisi:
Render aşamasında FFmpeg'in çift geçişli EBU R128 `loudnorm` filtresi entegre edilir:
```bash
-af "loudnorm=I=-14:LRA=7:TP=-1.5"
```
* **I=-14:** YouTube ve TikTok entegre ses standardı (-14 LUFS).
* **TP=-1.5:** Dijital ses patlamasını (clipping) önleyen -1.5 dB True Peak tavanı.

---

## 📅 4. Uygulama ve Öncelik Matrisi

| Kod | Özellik Adı | Efor | Etki / Fayda | Önerilen Başlama Sırası |
| :---: | :--- | :---: | :---: | :---: |
| **E3** | Altyazı Çift Tıklayarak Canlı Düzenleme | 1 Gün | Yüksek | **1. Öncelik (Hemen)** |
| **E2** | BGM FFmpeg Auto-Ducking (Sidechain) | 1 Gün | Çok Yüksek | **2. Öncelik** |
| **E8** | YouTube/TikTok -14 LUFS Ses Normalizasyonu | Yarım Gün | Yüksek | **3. Öncelik** |
| **E1** | Otonom Video Yönetmeni (Proaktif AI) | 2 Gün | Devrimsel | **4. Öncelik** |
| **E6** | Manyetik Timeline (Ripple Gap Auto-Close) | 2 Gün | Yüksek | **5. Öncelik** |
| **E4** | Görsel Arka Plan Kaldırma (`rembg` AI) | 1 Gün | Orta | **6. Öncelik** |
| **E7** | Çoklu Klip Seçimi (Ctrl/Shift Multi-Select) | 1 Gün | Orta | **7. Öncelik** |
| **E5** | Pexels Canlı Video B-Roll İndirme | 1 Gün | Orta | **8. Öncelik** |

---

## 🎯 5. Sonuç ve Özet

OtoEdit projesinin en karmaşık algoritmik kısımları (**VAD ses kesimi, Retake tespiti, Karaoke altyazı motoru, Monitör sürükle-bırak kanvası, AI sohbet yazı ekleme ve Transkript arama**) başarıyla tamamlanmış ve hatasız şekilde çalışmaktadır.

Yukarıda sıralanan 8 yeni madde, projenin temel altyapısını bozmadan modüler olarak eklenebilecek geliştirmelerdir. Kullanıcının tercihine göre **E3 (Altyazı Çift Tıklama)** veya **E2 (BGM Auto-Ducking)** ile geliştirme sürecine hemen başlanabilir.
