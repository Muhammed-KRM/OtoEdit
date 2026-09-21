# 🔴 OtoEdit — Kapsamlı Mimari Sorun Analizi ve 2026 Çözüm Planı

> **Tarih:** 21.09.2026  
> **Kapsam:** AI sohbet sisteminin halüsinasyonları, onay mekanizması eksikliği, geri alma (undo/redo) altyapısının yokluğu ve manuel düzenleme (timeline) araçlarının eksikliği.  
> **Durum:** ⚠️ Mimari düzeyde acil müdahale gerektirir. Bu belge, mevcut sistemin kod düzeyinde detaylı analizini ve 2026 endüstri standartlarına (HitL, Memento Pattern, Structured Outputs) dayalı derinlemesine çözüm mimarisini içerir.

---

## İçindekiler

1. [Tespit Edilen Sorunlar (Özet)](#1-tespit-edilen-sorunlar-özet)
2. [Sorun 1 — AI Videoyu İzlemiyor, Uydurma Cevaplar Veriyor](#2-sorun-1--ai-videoyu-i̇zlemiyor-uydurma-cevaplar-veriyor)
3. [Sorun 2 — AI Onay Almadan Doğrudan Edit Yapıyor](#3-sorun-2--ai-onay-almadan-doğrudan-edit-yapıyor)
4. [Sorun 3 — Geri Alma (Undo/Redo) Mekanizması Yok](#4-sorun-3--geri-alma-undoredo-mekanizması-yok)
5. [Sorun 4 — Manuel Düzenleme Araçları Yok](#5-sorun-4--manuel-düzenleme-araçları-yok)
6. [Kapsamlı Çözüm Mimarisi (2026 Standartları)](#6-kapsamlı-çözüm-mimarisi-2026-standartları)
7. [Adım Adım Uygulama Planı ve Kod Örnekleri](#7-adım-adım-uygulama-planı-ve-kod-örnekleri)
8. [Etkilenen Dosyalar ve Değişiklik Haritası](#8-etkilenen-dosyalar-ve-değişiklik-haritası)

---

## 1. Tespit Edilen Sorunlar (Özet)

| # | Sorun | Tip | Önem | İlgili Dosya(lar) |
|---|-------|-----|------|------------|
| 1 | AI videoyu analiz etmiyor, saçma/uydurma cevaplar veriyor | **MİMARİ** | 🔴 Kritik | `GeminiChatProvider.cs`, `transcriber.py` |
| 2 | AI soru sorulduğunda bile onay almadan EDL'yi değiştiriyor | **MİMARİ** | 🔴 Kritik | `ChatManager.cs`, `GeminiChatProvider.cs` |
| 3 | Yapılan değişiklikleri geri almanın (Undo) hiçbir yolu yok | **MİMARİ** | 🔴 Kritik | `EdlManager.cs`, `EditDecisionList.cs` |
| 4 | Yanlış kesilen yeri düzeltmek, sahneyi manuel silmek için araçlar yok | **EKSİK ÖZELLİK** | 🟠 Yüksek | Frontend `editor.component.ts` |

---

## 2. Sorun 1 — AI Videoyu İzlemiyor, Uydurma Cevaplar Veriyor

### 2.1 Sorunun Belirtileri ve Kullanıcı Deneyimi
Kullanıcı AI asistanına "bu videonun neresine ne ekleyebiliriz?" diye bir soru yönelttiğinde, AI videoda hiç geçmeyen cümlelere dayanarak "Videonun sonundaki abone ol dediğin yere abone ol işareti ekleyeceğim" şeklinde yanıt vermektedir. Videoda böyle bir ifade bulunmamasına rağmen AI bu halüsinasyonu (uydurma veriyi) gerçek kabul etmektedir.

### 2.2 Kod Seviyesinde Kök Neden Analizi (Root Cause)

**A. Sahte Fallback Verisi (En Büyük Etken):**
Python pipeline'ı içindeki `transcriber.py` dosyasında (Satır 97-129), Whisper API anahtarı bulunmadığında geliştirme ortamı çökmesin diye uydurma bir transkript üretilmektedir:
```python
sample_words = [
    ("Merhaba", 0.5, 1.2), ("değerli", 1.3, 1.8), ...
    ("kanalımıza", 15.0, 15.8), ("abone", 15.9, 16.4),
    ("olmayı", 16.5, 17.0), ("unutmayın", 17.1, 18.0)
]
```
AI'ın "abone ol" referansı vermesinin birincil sebebi, veritabanına kaydedilen ve ardından EDL JSON içerisine gömülen bu sahte metindir. 

**B. Context Grounding (Bağlama Oturtma) Eksikliği:**
`GeminiChatProvider.cs` dosyasındaki prompt yapısı (Satır 47-64) incelendiğinde, transkriptin modele özel olarak sunulmadığı görülmektedir. Transkript, yalnızca çok büyük bir yapı olan EDL JSON'unun içinde küçük bir düğüm (node) olarak yer almaktadır. LLM'ler büyük JSON yığınları içinde spesifik metinlere odaklanmakta (attention mekanizması) zorlanırlar.

**C. Guardrails (Sınırlandırıcı Kurallar) Eksikliği:**
Sistem promptunda *"Yalnızca sana verilen transkripte göre yanıt ver, bilmiyorsan uydurma"* gibi LLM halüsinasyonlarını engelleyecek katı kurallar bulunmamaktadır. Ayrıca API çağrısında `temperature` (yaratıcılık) ayarı yapılmadığı için model varsayılan yüksek yaratıcılık seviyesinde çalışmaktadır.

---

## 3. Sorun 2 — AI Onay Almadan Doğrudan Edit Yapıyor

### 3.1 Sorunun Belirtileri
Kullanıcı yalnızca tavsiye veya bilgi almak amacıyla soru sorduğunda, AI asistanı soruyu yanıtlamakla kalmayıp videoyu doğrudan kesmekte veya üzerine katman (overlay) eklemektedir.

### 3.2 Kod Seviyesinde Kök Neden Analizi

`ChatManager.cs` (Satır 95-107) içindeki akış şu şekildedir:
```csharp
var chatResult = await _chatProvider.ProcessCommandAsync(message, edlJson, historyItems, cancellationToken);

if (chatResult.EdlPatch.HasValue)
{
    // HİÇBİR ONAY MEKANİZMASI YOK! DOĞRUDAN VERİTABANINA YAZILIYOR.
    var patchedElement = await EnrichImageOverlaysWithPexelsAsync(projectId, chatResult.EdlPatch.Value, cancellationToken);
    var patchResponse = await _edlService.PatchEdlAsync(projectId, patchedElement, cancellationToken);
}
```

Sistemde **Niyet (Intent) Sınıflandırması** yapılmamaktadır. Gelen mesajın bir "soru" mu yoksa "kesin bir komut" mu olduğu ayırt edilmemektedir. Gemini modeli varsayılan prompt nedeniyle her zaman bir `EdlPatch` (değişiklik yaması) üretmeye eğilimlidir. ChatManager ise içinde `EdlPatch` olan her yanıtı doğrudan ve kalıcı olarak `EdlManager`'a göndererek uygular. Kullanıcıya "Bu değişiklikleri yapayım mı?" diye soran bir ara katman (Human-in-the-loop) yoktur.

---

## 4. Sorun 3 — Geri Alma (Undo/Redo) Mekanizması Yok

### 4.1 Sorunun Belirtileri
Gerek AI'ın hatalı kesimleri, gerekse ileride eklenecek manuel kesim işlemleri sonrasında kullanıcının önceki duruma dönme (Ctrl+Z) şansı yoktur.

### 4.2 Kod Seviyesinde Kök Neden Analizi
`EdlManager.cs` içerisindeki `PatchEdlAsync` metodu (Satır 143-148) durumu açıklamaktadır:
```csharp
edl.EdlJson = rootNode.ToJsonString();
edl.Versiyon += 1;
edl.GuncellemeTarihi = DateTime.UtcNow;
await _context.SaveChangesAsync(cancellationToken);
```
Mevcut mimaride `EditDecisionList` entity'si yalnızca "en son" durumu tutmaktadır. Yeni bir patch geldiğinde, eski JSON verisinin tamamen üzerine yazılmaktadır. Versiyon numarası artırılsa bile geçmiş versiyonların verisi hiçbir tabloda loglanmamakta veya saklanmamaktadır.

---

## 5. Sorun 4 — Manuel Düzenleme Araçları Yok

### 5.1 Sorunun Belirtileri
Aynı sahne birden fazla kez çekildiğinde bunlardan birini seçip diğerlerini manuel silmek, yanlış otomatik kesimleri düzeltmek veya eklenen metinlerin süresini değiştirmek için UI araçları eksiktir.

### 5.2 Kod Seviyesinde Kök Neden Analizi
Frontend klasöründeki `editor.component.ts` incelendiğinde, uygulamanın yalnızca bir **Viewer (Görüntüleyici)** işlevine sahip olduğu görülmektedir.
- Timeline üzerinde kesimler ve metinler gösterilmektedir (Read).
- Overlay silme butonu eklenmiştir (Delete).
Ancak:
- Bir kesimin başlangıç/bitiş saniyesini değiştirecek (Update) bir form yoktur.
- Timeline üzerinde belirli bir alanı seçip "Burayı Kes" (Create Cut) diyecek interaktif araçlar yazılmamıştır.
- Overlay'lerin metin içeriğini, rengini, ekranda duracağı süreyi değiştirecek bir inspector (denetçi) paneli bulunmamaktadır.

---
---

## 6. Kapsamlı Çözüm Mimarisi (2026 Standartları)

Mevcut sorunları çözmek için mimariyi 2026 endüstri standartlarına (Best Practices) uygun hale getireceğiz.

### 6.1 Context Grounding ve Structured Output (Halüsinasyon Çözümü)
Gemini gibi modern LLM'lerin halüsinasyonlarını engellemek için üç ayaklı bir yapı kurulacaktır:
1. **Veri İzolasyonu:** Transkript, EDL JSON'dan ayrılarak prompta özel ve yapısal bir bağlam (context) olarak eklenecektir.
2. **Structured Outputs (Yapısal Çıktı):** `Google.GenAI` SDK kullanılarak API seviyesinde `response_mime_type = "application/json"` ve `response_schema` (JSON şema validasyonu) dayatılacaktır. Modelin formata uymama ihtimali teknik olarak ortadan kaldırılacaktır.
3. **Guardrails (Korkuluklar):** System prompt güncellenerek "Transkript dışına çıkma, emin değilsen 'bilmiyorum' de" kuralları eklenecek ve `Temperature: 0.1` ayarlanarak yaratıcılık kısıtlanacaktır.

### 6.2 Human-in-the-Loop (HitL) ve "Suggest then Apply" Deseni (Onay Çözümü)
Enterprise AI sistemlerinde kritik işlemler onaysız yapılmaz. Chat sistemi şu yapıya evrilecektir:
- **Intent (Niyet) Tespiti:** Gemini'den dönen JSON şemasına `intent` alanı eklenecektir (`information`, `suggestion`, `command`).
- **Approval Envelope (Onay Zarfı):** `intent == suggestion` olduğunda `ChatManager`, patch'i EDL'ye uygulamaz. `ChatMessage` entity'sinde `PendingPatch` alanına yazar.
- **Kullanıcı Kararı:** Frontend'de mesajın altında `[Uygula] [Reddet]` butonları çıkar. Kullanıcı Uygula derse ayrı bir API endpoint'i üzerinden işlem kalıcı hale getirilir.

### 6.3 Memento Pattern ile Snapshot Yönetimi (Undo/Redo Çözümü)
JSON tabanlı karmaşık dokümanların versiyon kontrolü için en güvenilir mimari olan **Memento (Hatıra) Deseni** uygulanacaktır.
- **Originator (EdlManager):** EDL üzerinde her değişiklik yapıldığında (ister manuel ister AI ile), işlemin hemen öncesindeki `EdlJson` durumu kopyalanır.
- **Memento (EdlSnapshot Entity):** Bu kopya, veritabanındaki yeni `EdlSnapshots` tablosuna (Tarih, Versiyon, Açıklama ile birlikte) eklenir.
- **Caretaker (Tarihçe Servisi):** Kullanıcı "Geri Al" dediğinde, sondan bir önceki Snapshot alınır ve aktif EDL'nin üzerine yazılır. Veritabanı şişmesini önlemek için proje başına maksimum 50 snapshot tutulur.

### 6.4 Reactive Timeline State ve UX Desenleri (Manuel Düzenleme Çözümü)
Angular tarafında Canvas veya kompleks state gerektiren timeline işlemleri için:
- **Split & Merge (Böl ve Birleştir):** Kullanıcının timeline üzerinde aralık (range) seçimi yapabilmesi sağlanacaktır. Seçilen aralık `cuts` (kesimler) dizisine yeni bir obje olarak eklenecek, silinmesi durumunda "Merge" (birleştirme) işlemi ile video eski haline dönecektir.
- **Inspector Paneli:** Seçili katmanın (Overlay) veya kesimin özelliklerini sağ menüde form olarak gösteren ve değişiklikleri anında (Debounce ile) API'ye Patch eden bir mimari kurulacaktır.

---

## 7. Adım Adım Uygulama Planı ve Kod Örnekleri

### FAZ A: Mimari Düzeltmeler ve Güvenlik Altyapısı (Öncelik: Kritik / P0)

#### Adım 1: Sahte Veri Kaynağının Kurutulması
- **Dosya:** `OtoEdit.PythonWorker/pipeline/transcriber.py`
- **İşlem:** `_generate_fallback_transcript` metodu uydurma sözcükler üretmek yerine boş bir liste veya hata fırlatmalıdır ki AI hayali metinler üzerinden çıkarım yapmasın.

#### Adım 2: Snapshot Altyapısının Kurulması (Memento Pattern)
- **Dosya:** `OtoEdit.Data/Entities/EdlSnapshot.cs` (YENİ)
- **Açıklama:** EF Core için yeni bir entity yaratılacak.
```csharp
public class EdlSnapshot {
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public int Versiyon { get; set; }
    public string EdlJson { get; set; } = string.Empty; // Memento (Durum)
    public string Kaynak { get; set; } = "system"; // 'ai_chat', 'manual'
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;
    public Project Project { get; set; } = null!;
}
```
- **İşlem:** `AppDbContext`'e eklenecek, EF Core Migration çalıştırılacak. `EdlManager.PatchEdlAsync` içinde ana entity güncellenmeden önce `EdlSnapshot` tablosuna INSERT işlemi eklenecek. `UndoAsync` metodu yazılacak.

#### Adım 3: AI Grounding & Structured Output Entegrasyonu
- **Dosya:** `OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs`
- **Açıklama:** Google.GenAI SDK'sı ile şema dayatması yapılacak.
```csharp
var config = new GenerationConfig {
    Temperature = 0.1f, // Halüsinasyon önleyici düşük ısı
    ResponseMimeType = "application/json",
    ResponseSchema = new Schema {
        Type = Type.Object,
        Properties = {
            { "intent", new Schema { Type = Type.String, Enum = ["information", "suggestion"] } },
            { "mesaj", new Schema { Type = Type.String } },
            { "edlPatch", new Schema { Type = Type.Object } }
        },
        Required = { "intent", "mesaj" }
    }
};
// Prompt güncellenerek transkript harici bilgi uydurmaması emredilecek.
```

#### Adım 4: "Suggest Then Apply" Onay Mekanizması
- **Dosya:** `OtoEdit.Business/Services/ChatManager.cs`
- **Açıklama:** Gelen intent "suggestion" ise EDL'yi doğrudan patchlemek yerine, `ChatMessage` tablosuna `PendingEdlPatch` olarak kaydedilecek.
- **Dosya:** Frontend `editor.component.ts`
- **Açıklama:** Eğer mesajın `PendingEdlPatch` değeri doluysa, mesaj balonunun altına yeşil bir **"✅ Bu Değişiklikleri Uygula"** butonu eklenecek. Bu butona basıldığında yeni yazılacak `POST /api/projects/{id}/chat/{messageId}/apply` endpoint'i tetiklenecek.

---

### FAZ B: Manuel Düzenleme UX Uygulaması (Öncelik: Yüksek / P1)

#### Adım 5: Kesim (Cut) Yönetim Formu
- **Dosya:** Frontend `editor.component.ts`
- **Açıklama:** Uygulamanın sağ paneline `activeTab() === 'cuts'` isimli yeni bir sekme eklenecek.
- Tüm `edl.cuts` array'i kartlar halinde listelenecek. Her kesim için "Başlangıç Saniyesi" ve "Bitiş Saniyesi" için `<input type="number">` (veya custom slider) eklenecek.
- Kartın sağ üst köşesine eklenecek "Sil / Geri Yükle" butonu, ilgili cut'ı listeden çıkartıp backend'e Patch isteği atacak (Bu da beraberinde bir Snapshot oluşturarak Undo geçmişine girecek).

#### Adım 6: Timeline Üzerinden İnteraktif Kesim (Sürükle-Bırak)
- **Dosya:** Frontend `editor.component.ts`
- **Açıklama:** Timeline şeridi üzerinde fare ile tıkla-sürükle yapıldığında (mouse down -> mouse move -> mouse up), seçili olan aralık hesaplanıp kırmızı bir kutu olarak belirecek.
- Seçimin üzerinde "✂️ Burayı Kes" tooltip butonu çıkacak. Butona tıklandığında `{ start: x, end: y, reason: "manual_user_cut" }` objesi oluşturulup backend'e iletilecek.

#### Adım 7: Overlay (Katman) Denetçisi (Inspector)
- **Dosya:** Frontend `editor.component.ts`
- **Açıklama:** Mevcut Katmanlar listesindeki her objeye "✏️ Düzenle" butonu konulacak.
- Tıklandığında; İçerik (Textarea), Süre (Number Input), Konum (Dropdown: Sol, Sağ, Merkez), Animasyon tipi gibi özellikleri değiştiren reaktif bir Angular Form açılacak. Değişiklikler kaydedildiğinde API'ye Patch olarak yansıtılacak.

---

## 8. Etkilenen Dosyalar ve Değişiklik Haritası

```text
📁 OtoEdit.Data
├── Entities/EdlSnapshot.cs                   [YENİ] Undo/Redo için Snapshot model
├── Configurations/EdlSnapshotConfig.cs       [YENİ] EF Core Fluent API ayarları
├── Context/AppDbContext.cs                   [GÜNCELLE] DbSet<EdlSnapshot> tanımı
└── Entities/ChatMessage.cs                   [GÜNCELLE] PendingPatch (string/JSON) alanı ekle

📁 OtoEdit.Business
├── DTOs/Chat/ChatDtos.cs                     [GÜNCELLE] Intent enum veya string alanı
├── Infrastructure/AI/GeminiChatProvider.cs   [GÜNCELLE] GenerationConfig (Şema), Prompt revizyonu
├── Services/ChatManager.cs                   [GÜNCELLE] Onaysız PatchEdlAsync çağrısının koşullandırılması
└── Services/EdlManager.cs                    [GÜNCELLE] UndoAsync, RedoAsync metodları ve Snapshot mantığı

📁 OtoEdit.API
├── Controllers/EdlController.cs              [GÜNCELLE] /undo ve /redo endpoint'leri
└── Controllers/ChatController.cs             [GÜNCELLE] /{messageId}/apply endpoint'i

📁 OtoEdit.PythonWorker
└── pipeline/transcriber.py                   [GÜNCELLE] _generate_fallback_transcript içindeki uydurma metinlerin temizlenmesi

📁 OtoEdit.Frontend
└── src/app/
    ├── core/services/edl.service.ts          [GÜNCELLE] undo() ve redo() HTTP istekleri
    └── features/editor/editor.component.ts   [GÜNCELLE] Undo UI, Onay (HitL) UI, Cuts ve Overlays CRUD UI formları
```

Bu çözüm mimarisi ile uygulamanın omurgası güvence altına alınmış, kullanıcıların güvenle ve hata korkusu olmadan yapay zeka ile etkileşime girebileceği, gerektiğinde manuel kontrolü eline alabileceği 2026 standartlarında bir ürün yapısına geçilmiş olacaktır.
