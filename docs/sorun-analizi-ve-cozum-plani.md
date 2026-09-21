# 🔴 OtoEdit — Kritik Sorun Analizi ve Çözüm Planı

> **Tarih:** 21.09.2026  
> **Kapsam:** AI sohbet sisteminin yanlış çalışması, onay mekanizması eksikliği, geri alma (undo/redo) yokluğu ve manuel düzenleme araçlarının eksikliği  
> **Durum:** ⚠️ Mimari düzeyde acil müdahale gerektirir

---

## İçindekiler

1. [Tespit Edilen Sorunlar (Özet)](#1-tespit-edilen-sorunlar-özet)
2. [Sorun 1 — AI Videoyu "İzlemiyor", Uydurma Cevaplar Veriyor (MİMARİ)](#2-sorun-1--ai-videoyu-izlemiyor-uydurma-cevaplar-veriyor-mimari)
3. [Sorun 2 — AI Onay Almadan Doğrudan Edit Yapıyor (MİMARİ)](#3-sorun-2--ai-onay-almadan-doğrudan-edit-yapıyor-mimari)
4. [Sorun 3 — Geri Alma (Undo/Redo) Mekanizması Yok (MİMARİ)](#4-sorun-3--geri-alma-undoredo-mekanizması-yok-mimari)
5. [Sorun 4 — Manuel Düzenleme Araçları Yok (EKSİK ÖZELLİK)](#5-sorun-4--manuel-düzenleme-araçları-yok-eksik-özellik)
6. [Kök Neden Analizi (Root Cause)](#6-kök-neden-analizi-root-cause)
7. [Çözüm Planı](#7-çözüm-planı)
8. [Etkilenen Dosyalar ve Değişiklik Haritası](#8-etkilenen-dosyalar-ve-değişiklik-haritası)
9. [Uygulama Öncelikleri](#9-uygulama-öncelikleri)

---

## 1. Tespit Edilen Sorunlar (Özet)

| # | Sorun | Tip | Önem | Dosya(lar) |
|---|-------|-----|------|------------|
| 1 | AI videoyu analiz etmiyor, saçma/uydurma cevaplar veriyor | **MİMARİ** | 🔴 Kritik | `GeminiChatProvider.cs`, `ChatManager.cs` |
| 2 | AI soru sorulduğunda bile onay almadan EDL'yi değiştiriyor | **MİMARİ** | 🔴 Kritik | `GeminiChatProvider.cs`, `ChatManager.cs` |
| 3 | Yapılan değişiklikleri geri almanın hiçbir yolu yok | **MİMARİ** | 🔴 Kritik | `EdlManager.cs`, `EditDecisionList.cs` |
| 4 | Yanlış kesilen yeri düzeltmek, sahneyi manuel silmek için araçlar yok | **EKSİK ÖZELLİK** | 🟠 Yüksek | Frontend `editor.component.ts` |

---

## 2. Sorun 1 — AI Videoyu "İzlemiyor", Uydurma Cevaplar Veriyor (MİMARİ)

### 2.1 Sorunun Belirtileri
- Kullanıcı "bu videonun neresine ne ekleyebiliriz" diye soruyor
- AI "abone ol" yazısı ekleyeceğini söylüyor ama videoda böyle bir şey söylenmemiş
- AI videonun gerçek içeriğinden habersiz, hayal ürünü yanıtlar veriyor

### 2.2 Kök Neden — GeminiChatProvider'ın Çalışma Şekli

AI chat sistemi şu anda **videonun gerçek içeriğini neredeyse hiç bilmiyor**. İşte tam akış:

```
Kullanıcı Mesajı → ChatManager → GeminiChatProvider.ProcessCommandAsync()
```

`GeminiChatProvider.cs` (Satır 47-64) incelendiğinde:

```csharp
var systemPrompt = """
    Sen bir video editörü asistanısın. Kullanıcının doğal dildeki kurgu komutunu alıp,
    mevcut EDL JSON üzerinde yapılacak değişiklikleri JSON patch olarak döndürüyorsun.
    ...
    """;

var historyText = string.Join("\n", history.Select(h => $"{h.Role}: {h.Message}"));
var prompt = $"{systemPrompt}\n\nGeçmiş Sohbet:\n{historyText}\n\nMevcut EDL:\n{currentEdlJson}\n\nKullanıcı: {userMessage}";
```

**Sorunlar:**

#### A. Transkript EDL JSON'un İçinde Gömülü Ama Yetersiz Kullanılıyor
EDL JSON'un içinde `transcript.fullText` ve `transcript.segments` alanları var (`edl_builder.py` satır 87-98). Bu veri Gemini'ye gönderiliyor ama:

1. **Yapısal olarak gömülü:** Transkript, devasa bir EDL JSON'un küçük bir parçası. Gemini modeli bu JSON'u bir "bağlam" olarak okuyor ama transkripti özel olarak vurgulamıyor.
2. **Sistem promptu transkripte yönlendirmiyor:** System prompt'ta "transkripte göre cevap ver" gibi bir talimat yok. Model sadece "EDL JSON üzerinde değişiklik yap" talimatı alıyor.
3. **Token sınırı riski:** EDL JSON büyüdükçe (çok kesim, overlay, yüz takibi verisi vb.) transkript kısmı truncate olabilir veya modelin dikkatini çekemez.
4. **Temperature/yaratıcılık parametresi ayarlanmamış:** Model varsayılan yaratıcılık seviyesiyle çalışıyor, bu da halüsinasyonlara zemin hazırlıyor.

#### B. Fallback Transkripti Tamamen Uydurma
`transcriber.py` satır 97-129'daki `_generate_fallback_transcript()` metodu, API anahtarı olmadığında sahte bir transkript üretiyor:
```python
sample_words = [
    ("Merhaba", 0.5, 1.2), ("değerli", 1.3, 1.8), ...
    ("kanalımıza", 15.0, 15.8), ("abone", 15.9, 16.4),
    ("olmayı", 16.5, 17.0), ("unutmayın", 17.1, 18.0)
]
```

**Bu fallback transkript "kanalımıza abone olmayı unutmayın" diye sahte bir cümle üretiyor!** Eğer Whisper API anahtarı yoksa veya bir hata olursa, AI bu uydurma transkribi okuyarak "abone ol yazısı ekleyelim" demesi tamamen bu sahte veriden kaynaklanıyor. Bu, kullanıcının bildirdiği sorunun **doğrudan kaynağı**.

#### C. Gemini Client Modeli Farklılığı
- `.NET` tarafındaki `GeminiChatProvider` → `Mscc.GenerativeAI` paketi ile `gemini-2.0-flash` kullanıyor
- Python Worker tarafındaki `GeminiClient` → `google.generativeai` paketi ile `gemini-2.5-flash` kullanıyor
- Model tutarsızlığı ve paket farklılığı, davranış tutarsızlıklarına yol açabilir

### 2.3 Çözüm Yaklaşımı

#### A. Transkripti Ayrı ve Yapısal Olarak Prompt'a Vur
Transkript, EDL JSON'un içine gömülü bırakılmamalı. Gemini'ye gönderilen prompt'ta **ayrı bir bölüm** olarak, zaman damgalarıyla birlikte açıkça sunulmalı:

```
=== VİDEO TRANSKRİPTİ (Kelime-Zaman Damgalı) ===
[0.5s-1.2s] Merhaba
[1.3s-1.8s] değerli
...
=== TRANSKRİPT SONU ===

=== MEVCUT EDL DURUMU (Transkript Hariç) ===
{ cuts: [...], overlays: [...], settings: {...} }
=== EDL SONU ===
```

#### B. Ayrı Transkript Verisi Çek
`ChatManager` içinde, EDL JSON'dan bağımsız olarak `VideoTranscripts` tablosundan gerçek transkript çekilmeli:

```csharp
var transcript = await _context.VideoTranscripts
    .AsNoTracking()
    .FirstOrDefaultAsync(t => t.Video.ProjectId == projectId, cancellationToken);
```

#### C. System Prompt'u Güçlendir
```
Kurallar:
1. SADECE transkriptte gerçekten söylenen kelimelere ve zaman damgalarına dayanarak cevap ver.
2. Transkriptte geçmeyen bir kelime veya cümle hakkında ASLA varsayım yapma.
3. Eğer kullanıcı "buraya ne ekleyebiliriz" gibi genel bir soru sorarsa, TRANSKRİPT İÇERİĞİNE GÖRE öner.
4. Her önerinin hangi zaman aralığına ve transkriptteki hangi cümleye dayandığını BELIRT.
5. Eğer bir bilgi transkriptte yoksa, "Bu bilgi transkriptte mevcut değil" de.
```

#### D. Temperature Parametresini Düşür
Gemini API çağrısında `temperature: 0.1-0.2` ayarlanarak halüsinasyon riski minimize edilmeli.

#### E. Fallback Transkripti Kaldır veya Uyar
`_generate_fallback_transcript()` uydurma veri üretmek yerine, boş bir transkript dönmeli veya kullanıcıya "API anahtarı eksik, transkript çıkarılamadı" uyarısı gösterilmeli.

---

## 3. Sorun 2 — AI Onay Almadan Doğrudan Edit Yapıyor (MİMARİ)

### 3.1 Sorunun Belirtileri
- Kullanıcı soru soruyor ("bu videonun neresine ne ekleyebiliriz?")
- AI soruyu cevaplamak yerine, doğrudan EDL'ye kesim/overlay ekliyor
- Kullanıcıdan onay alınmıyor

### 3.2 Kök Neden — Niyet (Intent) Ayrımı Yok

`ChatManager.cs` satır 90-107 incelendiğinde:

```csharp
// 4. Gemini AI Provider ile komutu çözümle
var chatResult = await _chatProvider.ProcessCommandAsync(message, edlJson, historyItems, cancellationToken);

// 5. Eğer bir EDL Patch üretilmişse... DOĞRUDAN UYGULA
if (chatResult.EdlPatch.HasValue)
{
    var patchedElement = await EnrichImageOverlaysWithPexelsAsync(projectId, chatResult.EdlPatch.Value, cancellationToken);
    var patchResponse = await _edlService.PatchEdlAsync(projectId, patchedElement, cancellationToken);
    yeniVersiyon = patchResponse.Versiyon;
}
```

**Sorun:** AI bir EDL Patch ürettiği anda, `ChatManager` bu patch'i **hiçbir onay mekanizması olmadan** doğrudan `PatchEdlAsync()` ile kalıcı olarak EDL'ye uyguluyor. Arada:

1. **Niyet sınıflandırması (intent classification) yok:** "Soru" mu soruldu, "komut" mu verildi ayrımı yapılmıyor. Gemini her mesaj için potansiyel bir EDL patch üretebiliyor.
2. **Onay adımı yok:** Kullanıcıya "Bu değişiklikleri yapmak istiyor musunuz?" sorusu sorulmuyor.
3. **Önizleme yok:** Yapılacak değişikliğin ne olduğu kullanıcıya gösterilmiyor.

### 3.3 Çözüm Yaklaşımı — "Öner → Onayla → Uygula" Mimari Değişikliği

#### A. Intent Sınıflandırması Ekle
Gemini system prompt'una üç farklı yanıt modu eklenmeli:

```json
// Mod 1: Sadece soru/bilgi (edit yok)
{ "mesaj": "...", "edlPatch": null, "intent": "bilgi" }

// Mod 2: Öneri (onay bekleyen)
{ "mesaj": "...", "edlPatch": {...}, "intent": "oneri" }

// Mod 3: Kesin komut ("şunu yap" gibi)
{ "mesaj": "...", "edlPatch": {...}, "intent": "komut" }
```

#### B. ChatManager'a Onay Katmanı Ekle
```csharp
if (chatResult.EdlPatch.HasValue)
{
    if (chatResult.Intent == "bilgi")
    {
        // Sadece cevap ver, EDL'ye dokunma
    }
    else if (chatResult.Intent == "oneri")
    {
        // Patch'i "bekleyen değişiklik" olarak kaydet, uygulamadan bekle
        // Frontend'e "Bu değişiklikleri uygulamak ister misiniz?" göster
    }
    else if (chatResult.Intent == "komut")
    {
        // Yine de önce önizle, onay butonuyla uygula
    }
}
```

#### C. Frontend'e Onay UI Bileşeni Ekle
AI bir değişiklik önerdiğinde, chat panelinde:
```
┌──────────────────────────────────────┐
│ 🤖 AI: "10. saniyeye 'Kanala Abone  │
│ Ol' yazısı ekleyebilirim."          │
│                                      │
│ Önerilen Değişiklikler:              │
│ ├─ ➕ text overlay @ 10.0s (5s)     │
│ │   "Kanala Abone Ol"               │
│                                      │
│ [✅ Uygula]  [❌ Reddet]  [✏️ Düzenle] │
└──────────────────────────────────────┘
```

#### D. Pending Patch Tablosu veya Alanı
`ChatMessage` entity'sine veya ayrı bir tabloya `PendingEdlPatch` alanı eklenmeli. Onaylanana kadar EDL'ye uygulanmamalı.

---

## 4. Sorun 3 — Geri Alma (Undo/Redo) Mekanizması Yok (MİMARİ)

### 4.1 Sorunun Belirtileri
- AI yanlış edit yapıyor ama geri almak mümkün değil
- Kullanıcı hatalı bir kesimi düzeltemek istiyor ama önceki duruma dönme yolu yok
- `EditDecisionList` tablosunda sadece son hali tutuluyor

### 4.2 Kök Neden

`EdlManager.cs` satır 143-148:
```csharp
edl.EdlJson = rootNode.ToJsonString(); // Üzerine yaz
edl.Versiyon += 1;                     // Versiyonu artır
edl.GuncellemeTarihi = DateTime.UtcNow;
await _context.SaveChangesAsync(cancellationToken); // Kaydet
```

`EditDecisionList` entity'si (satır 12):
```csharp
public int Versiyon { get; set; } = 1; // Sadece sayaç, eski veriyi tutmuyor
```

**Versiyon numarası artırılıyor ama önceki EDL JSON'u hiçbir yere kaydedilmiyor.** Bir kez `PatchEdlAsync()` çağrıldığında, eski durum tamamen kayboluyor.

### 4.3 Çözüm Yaklaşımı — EDL Anlık Görüntü (Snapshot) Sistemi

#### Seçenek A: Memento Pattern (Basit, Önerilen — MVP İçin)

Yeni bir `EdlSnapshot` tablosu oluştur:

```csharp
public class EdlSnapshot
{
    public long Id { get; set; }
    public Guid ProjectId { get; set; }
    public int Versiyon { get; set; }
    public string EdlJson { get; set; } = "{}";        // O anki tam EDL JSON
    public string? Aciklama { get; set; }               // "AI Chat: 10. saniyeye yazı eklendi"
    public string Kaynak { get; set; } = "system";      // "ai_chat", "manual", "pipeline"
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;

    public Project Project { get; set; } = null!;
}
```

#### EdlManager Değişikliği:
```csharp
public async Task<EdlPatchResponseDto> PatchEdlAsync(...)
{
    // 1. Mevcut durumu snapshot olarak kaydet
    var snapshot = new EdlSnapshot
    {
        ProjectId = projectId,
        Versiyon = edl.Versiyon,
        EdlJson = edl.EdlJson,          // ← Eski hali kaydet
        Aciklama = "EDL güncelleme öncesi durum",
        Kaynak = kaynakBilgisi           // "ai_chat" veya "manual"
    };
    _context.EdlSnapshots.Add(snapshot);

    // 2. Normal patch işlemi devam eder
    ...
}
```

#### Undo Endpoint:
```csharp
// POST /api/projects/{id}/edl/undo
// Son snapshot'ı alıp EdlJson'u ona geri döndürür

// POST /api/projects/{id}/edl/redo
// Redo stack'ten ileri gider
```

#### Snapshot Limiti:
MVP için proje başına son **50 snapshot** tutulmalı (eski olanlar otomatik silinir).

#### Frontend Undo/Redo Butonları:
Editor toolbar'a `Ctrl+Z` / `Ctrl+Y` kısayolları ve görsel butonlar eklenmeli.

---

## 5. Sorun 4 — Manuel Düzenleme Araçları Yok (EKSİK ÖZELLİK)

### 5.1 Sorunun Belirtileri
- Yanlış kesilen bir bölgeyi düzeltmek için araç yok
- Aynı sahneyi birden fazla çektiğinde, birini seçip diğerlerini silmek mümkün değil
- Overlay'lerin zamanını, süresini, içeriğini düzenlemek için form yok
- Timeline üzerinde interaktif kesim yapılamıyor

### 5.2 Mevcut Durum

Frontend `editor.component.ts` incelendiğinde:

**Var olan işlevler:**
- ✅ Timeline görselleştirme (kesimler, overlay'ler görünür)
- ✅ Timeline tıklayarak o saniyeye atlama
- ✅ Overlay silme (`removeOverlay`)
- ✅ Öneri kabul/red (`acceptSuggestion`, `rejectSuggestion`)
- ✅ Canlı EDL simülasyonu (kesilen bölgeleri atlama)

**Eksik olan araçlar:**
- ❌ Kesim (cut) silme/düzeltme — yanlış bir kesimi geri alma
- ❌ Kesim ekleme — manuel olarak bir bölgeyi sessizlik dışında kesme
- ❌ Kesim süresini ayarlama — başlangıç/bitiş noktasını değiştirme
- ❌ Overlay düzenleme — metin, zaman, süre, konum değiştirme formu
- ❌ Seçim ve toplu silme — aynı sahnenin tekrarlarından birini seçip diğerlerini toplu silme
- ❌ Timeline üzerinde sürükleyerek aralık seçme (range selection)

### 5.3 Çözüm Yaklaşımı — Manuel Düzenleme Aracı Seti

#### A. Kesim (Cut) Yönetim Paneli
Timeline altına veya sağ panele "Kesimler" sekmesi eklenmeli:

```
┌──────────────────────────────────────┐
│ 🔴 Kesim: 12.5s → 15.0s             │
│    Neden: silence (otomatik)         │
│    [Geri Al] [Kısalt] [Genişlet]     │
├──────────────────────────────────────┤
│ 🔴 Kesim: 45.0s → 52.0s             │
│    Neden: gesture_dislike (otomatik) │
│    [Geri Al] [Kısalt] [Genişlet]     │
└──────────────────────────────────────┘
```

Her kesim kartında:
- **"Geri Al" butonu:** O kesimi EDL'den siler (`action: "remove"` patch gönderir)
- **"Kısalt/Genişlet":** Başlangıç/bitiş saniyelerini düzenleme formu açar
- **Timeline üzerinde kesim kenarlarını sürükleme:** Drag-and-drop ile başlangıç/bitiş ayarlama

#### B. Manuel Kesim Ekleme
Timeline üzerinde:
1. Kullanıcı videoyu izlerken **"Kesim Başlat" (I)** ve **"Kesim Bitir" (O)** kısayolları
2. Veya timeline üzerinde **sürükleyerek aralık seçme** → "Bu bölgeyi kes" butonu
3. Seçilen aralık `cuts` dizisine `{ reason: "manual", source: "user" }` olarak eklenir

#### C. Overlay Düzenleme Formu
Katmanlar sekmesindeki her overlay kartına **"Düzenle"** butonu eklenmeli:

```
┌─────────────────────────────────┐
│ ✏️ Overlay Düzenle               │
│                                 │
│ Metin:     [Kanala Abone Ol!  ] │
│ Başlangıç: [10.0] saniye       │
│ Süre:      [5.0 ] saniye       │
│ Konum:     [Orta-Alt ▼]        │
│ Animasyon: [Pop-up   ▼]        │
│ Renk:      [#FFFFFF 🎨]        │
│ Yazı Boyu: [48      ] px       │
│                                 │
│        [Kaydet] [İptal]         │
└─────────────────────────────────┘
```

#### D. Sahne Tekrar Yönetimi (Take Selection)
Kullanıcının aynı sahneyi birden fazla çektiği durumlarda:
1. Transkriptteki benzer cümle tekrarlarını tespit et
2. "Tekrar Algılandı" kartları göster
3. Kullanıcı hangisini tutacağını seçsin, diğerleri otomatik kesilsin

Bu özellik ileri MVP'de değerlendirilebilir, ancak basit haliyle "belirli saniye aralığını manuel kes" özelliği bu ihtiyacı da karşılar.

---

## 6. Kök Neden Analizi (Root Cause)

### 6.1 Ana Mimari Sorun: "Fire and Forget" AI Entegrasyonu

Mevcut mimaride AI chat sistemi **"ateşle ve unut"** mantığıyla çalışıyor:

```
Kullanıcı Mesajı
    ↓
GeminiChatProvider (niyeti ayırt etmeden, her şeyi "komut" olarak algıla)
    ↓
ChatManager (AI bir patch ürettiyse DOĞRUDAN uygula)
    ↓
EdlManager.PatchEdlAsync (eski durumu kaydetmeden üzerine yaz)
    ↓
EDL kalıcı olarak değişti — GERİ DÖNÜŞ YOK
```

### 6.2 Halüsinasyon Kaynağı: Context Engineering Eksikliği

AI'ya gönderilen prompt'ta:
1. **Transkript özellikle vurgulanmıyor** — devasa EDL JSON içinde kaybolup gidiyor
2. **"Sadece transkripte dayan" kısıtlaması yok** — model kendi bilgisiyle "yaratıcı" cevaplar üretiyor
3. **Temperature ayarlanmamış** — varsayılan yaratıcılık seviyesi halüsinasyona yol açıyor
4. **Fallback transkript tamamen uydurma** — API yokken sahte veri üretiliyor ve AI buna dayanarak "abone ol" gibi şeyler söylüyor

### 6.3 Özet Tablo

| Sorun | Kök Neden | Tip | Çözüm Kategorisi |
|-------|-----------|-----|-------------------|
| AI uydurma cevap veriyor | Transkript prompt'ta vurgulanmıyor + fallback transkript sahte + temperature yüksek | Mimari | Prompt engineering + context restructuring |
| AI onaysız edit yapıyor | Intent classification yok + doğrudan `PatchEdlAsync()` çağrısı | Mimari | "Öner-Onayla-Uygula" katmanı |
| Geri alma yok | Snapshot/history mekanizması hiç implemente edilmemiş | Mimari | `EdlSnapshot` tablosu + undo/redo API |
| Manuel araçlar yok | Frontend'de sadece görüntüleme var, düzenleme yok | Eksik özellik | Cut/overlay CRUD UI bileşenleri |

---

## 7. Çözüm Planı

### Faz A — Acil Mimari Düzeltmeler (Öncelik 1)

#### A.1 — EDL Snapshot & Undo/Redo Sistemi
**Süre:** 2-3 gün

| Adım | Dosya | İş |
|------|-------|----|
| 1 | `OtoEdit.Data/Entities/EdlSnapshot.cs` | **[YENİ]** `EdlSnapshot` entity oluştur |
| 2 | `OtoEdit.Data/Configurations/EdlSnapshotConfiguration.cs` | **[YENİ]** EF Core konfigürasyon |
| 3 | `OtoEdit.Data/Context/AppDbContext.cs` | `DbSet<EdlSnapshot>` ekle |
| 4 | EF Core Migration | `dotnet ef migrations add AddEdlSnapshots` |
| 5 | `OtoEdit.Business/Interfaces/IEdlService.cs` | `UndoAsync()`, `RedoAsync()`, `GetHistoryAsync()` metodları ekle |
| 6 | `OtoEdit.Business/Services/EdlManager.cs` | `PatchEdlAsync()` içinde snapshot kaydetme + undo/redo implementasyonu |
| 7 | `OtoEdit.API/Controllers/EdlController.cs` | `POST /api/projects/{id}/edl/undo`, `POST .../redo`, `GET .../history` endpoint'leri |
| 8 | Frontend: `edl.service.ts` | Undo/redo HTTP çağrıları |
| 9 | Frontend: `editor.component.ts` | Undo/Redo butonları + `Ctrl+Z`/`Ctrl+Y` kısayolları |

#### A.2 — AI Chat "Öner-Onayla-Uygula" Mekanizması
**Süre:** 2-3 gün

| Adım | Dosya | İş |
|------|-------|----|
| 1 | `OtoEdit.Business/DTOs/Chat/ChatDtos.cs` | `ChatResult`'a `Intent` alanı ekle (`bilgi`, `oneri`, `komut`) |
| 2 | `OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs` | System prompt'a intent sınıflandırma kuralı ekle |
| 3 | `OtoEdit.Business/Services/ChatManager.cs` | Intent'e göre dallanma: `bilgi` → uygulama, `oneri`/`komut` → pending olarak sakla |
| 4 | `OtoEdit.Data/Entities/ChatMessage.cs` | `PatchDurumu` alanı ekle (`pending`, `accepted`, `rejected`) |
| 5 | `OtoEdit.Business/Interfaces/IChatService.cs` | `ApplyPendingPatchAsync(chatMessageId)` metodu ekle |
| 6 | `OtoEdit.API/Controllers/ChatController.cs` | `POST /api/projects/{id}/chat/{messageId}/apply` endpoint'i |
| 7 | Frontend: `editor.component.ts` | Chat yanıtında "Uygula / Reddet / Düzenle" butonları gösterme |

#### A.3 — AI Context Engineering Düzeltmesi
**Süre:** 1-2 gün

| Adım | Dosya | İş |
|------|-------|----|
| 1 | `OtoEdit.Business/Services/ChatManager.cs` | `VideoTranscripts` tablosundan transkript çekip ayrı parametre olarak gönder |
| 2 | `OtoEdit.Business/Interfaces/IChatProvider.cs` | `ProcessCommandAsync` imzasına `string transcriptText` parametresi ekle |
| 3 | `OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs` | System prompt'u yeniden yaz: transkripte dayalı cevaplama, düşük temperature, zorunlu atıf kuralları |
| 4 | `OtoEdit.PythonWorker/pipeline/transcriber.py` | Fallback transkripti "uydurma veri" yerine boş transkript + uyarı mesajı döndürecek şekilde değiştir |
| 5 | `OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs` | EDL JSON'u transkript hariç kırpılmış haliyle gönder (token tasarrufu) |

### Faz B — Manuel Düzenleme Araçları (Öncelik 2)

#### B.1 — Kesim (Cut) Yönetim Paneli
**Süre:** 2-3 gün

| Adım | Dosya | İş |
|------|-------|----|
| 1 | Frontend: `editor.component.ts` | "Kesimler" sekmesi ekle (chat, overlays, cuts) |
| 2 | Frontend: `editor.component.ts` | Her kesim kartında "Geri Al" (remove) butonu |
| 3 | Frontend: `editor.component.ts` | Kesim başlangıç/bitiş düzenleme inline formu |
| 4 | Frontend: `editor.component.ts` | Yeni kesim ekleme: I (In) ve O (Out) kısayolları |
| 5 | Frontend: `editor.component.ts` | Timeline üzerinde sağ tıklama → "Bu aralığı kes" menüsü |

#### B.2 — Overlay Düzenleme Formu
**Süre:** 1-2 gün

| Adım | Dosya | İş |
|------|-------|----|
| 1 | Frontend: `editor.component.ts` | Overlay kartına "Düzenle" butonu |
| 2 | Frontend: `editor.component.ts` | Inline düzenleme formu (metin, zaman, süre, konum, animasyon, renk) |
| 3 | Frontend: `edl.service.ts` | Overlay güncelleme patch isteği (mevcut `patchEdl` yeterli) |

---

## 8. Etkilenen Dosyalar ve Değişiklik Haritası

```
📁 OtoEdit.Data
├── Entities/
│   ├── EdlSnapshot.cs                    [YENİ]  Undo/Redo için snapshot entity
│   ├── EditDecisionList.cs               [GÜNCELLE] — Değişiklik yok, mevcut hali yeterli
│   └── ChatMessage.cs                    [GÜNCELLE] PatchDurumu alanı ekle
├── Configurations/
│   ├── EdlSnapshotConfiguration.cs       [YENİ]  EF konfigürasyon
│   └── ChatMessageConfiguration.cs       [GÜNCELLE] Yeni alan konfigürasyonu
├── Context/
│   └── AppDbContext.cs                   [GÜNCELLE] DbSet<EdlSnapshot> ekle
└── Migrations/                           [YENİ]  Migration

📁 OtoEdit.Business
├── DTOs/Chat/
│   └── ChatDtos.cs                       [GÜNCELLE] Intent alanı ekle
├── DTOs/Edl/
│   └── EdlDtos.cs                        [GÜNCELLE] Snapshot DTO'ları ekle
├── Interfaces/
│   ├── IChatService.cs                   [GÜNCELLE] ApplyPendingPatchAsync ekle
│   └── IEdlService.cs                    [GÜNCELLE] UndoAsync, RedoAsync, GetHistoryAsync ekle
├── Services/
│   ├── ChatManager.cs                    [GÜNCELLE] Intent dallanması + pending patch mantığı
│   └── EdlManager.cs                     [GÜNCELLE] Snapshot kaydetme + undo/redo implementasyonu
└── Infrastructure/AI/
    └── GeminiChatProvider.cs             [GÜNCELLE] Prompt yeniden yazımı + temperature + intent

📁 OtoEdit.API
├── Controllers/
│   ├── ChatController.cs                 [GÜNCELLE] Apply patch endpoint
│   └── EdlController.cs                  [GÜNCELLE] Undo/Redo/History endpoint'leri

📁 OtoEdit.PythonWorker
└── pipeline/
    └── transcriber.py                    [GÜNCELLE] Fallback transkripti boş/uyarı olarak değiştir

📁 OtoEdit.Frontend
└── src/app/
    ├── features/editor/
    │   └── editor.component.ts           [GÜNCELLE] Undo/Redo UI + Onay mekanizması + Manuel araçlar
    └── core/services/
        ├── edl.service.ts                [GÜNCELLE] Undo/redo/history API çağrıları
        └── chat.service.ts               [GÜNCELLE] Apply pending patch çağrısı
```

---

## 9. Uygulama Öncelikleri

| Öncelik | Faz | İş | Bağımlılık | Tahmini Süre |
|---------|-----|----|------------|--------------|
| 🔴 P0 | A.1 | EDL Snapshot & Undo/Redo | Yok | 2-3 gün |
| 🔴 P0 | A.3 | AI Context Engineering (Prompt düzeltme) | Yok | 1-2 gün |
| 🔴 P0 | A.2 | AI Onay Mekanizması | A.1'e bağlı (undo ile birlikte güvenli) | 2-3 gün |
| 🟠 P1 | B.1 | Kesim Yönetim Paneli | A.1'e bağlı | 2-3 gün |
| 🟠 P1 | B.2 | Overlay Düzenleme Formu | Yok | 1-2 gün |

**Toplam Tahmini Süre:** 8-13 gün

---

> **Not:** Bu planda belirtilen tüm çözümler, `docs/gelistirici-dokumani.md`'deki mevcut mimari sözleşmeye (katmanlı mimari, SOLID, interface kullanımı, loglama kuralları, EDL JSON prensibi) uygundur. Yeni entity'ler, interface'ler ve servisler mevcut pattern'lara sadık kalarak implemente edilecektir.

> **Kritik Uyarı:** Bu sorunlar çözülmeden sistem prodüksiyona çıkmamalıdır. AI'nın onaysız edit yapması ve geri alma mekanizmasının olmaması, kullanıcı verisinin geri dönüşü olmayan şekilde bozulmasına yol açabilir.
