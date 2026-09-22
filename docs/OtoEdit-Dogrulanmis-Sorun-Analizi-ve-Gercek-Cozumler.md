# OtoEdit: Doğrulanmış Sorun Analizi, Gerçek Kök Nedenler (RCA) ve Nihai Çözüm Şartnamesi (2026)

Bu doküman; `OtoEdit-Kalan-Sorunlar-Analizi.md` belgesinde listelenen sorunların kaynak kod düzeyinde doğrulanması, dokümanda yer alan varsayımsal veya eksik tespitlerin ayıklanması ve sistemde tespit edilen gerçek kök nedenlerin (Root Cause Analysis - RCA) uçtan uca mimari ve kod düzeyinde çözümlerini içermektedir.

Tüm analizler; Angular 19 Frontend (`editor.component.ts`), .NET 9 Backend (`EdlManager.cs`, `EdlController.cs`), Python Worker (`edl_builder.py`, `edl_model.py`, `text_overlay.py`) ve Redis/PostgreSQL katmanları doğrudan incelenerek hazırlanmıştır.

---

## İÇİNDEKİLER VE İLERLEME DURUMU

| No | Sorun Başlığı | Mevcut Durum | Rapor Bölümü |
|---|---|---|---|
| **1** | **Yazı ve Katman Ayarlarının Sıfırlanması (Drag & Drop / State Desync)** | ✅ **ÇÖZÜLDÜ (Mevcut Durum: Stabil)** | [Bölüm 1: Sorun 1 Analizi ve Doğrulaması](#bölüm-1-yazi-ve-katman-ayarlarinin-sifirlanmasi-drag--drop--state-desync) |
| **2** | **Canvas Üzerinde Köşeden Tutup Boyutlandırma (Resize Handle)** | ✅ **ÇÖZÜLDÜ (Mevcut Durum: Çalışıyor)** | [Bölüm 2: Sorun 2 Analizi ve Doğrulaması](#bölüm-2-canvas-üzerinde-köşeden-tutup-boyutlandirma-resize-handle) |
| **3** | **Yönetmen AI'den Seçilebilir Dropdown Form Şeması Eksikliği** | 🔴 **DOĞRULANDI (Aktif Kritik Sorun)** | [Bölüm 3: Sorun 3 Analizi ve Çözümü](#bölüm-3-yönetmen-aiden-seçilebilir-dropdown-form-şemasi-eksikliği) |
| **4** | **Medya Kütüphanesi - Dosya Yükleme ve Sürükle-Bırak Çalışmaması** | 🔴 **DOĞRULANDI (Eksik Özellik / Dead Code)** | [Bölüm 4: Sorun 4 Analizi ve Çözümü](#bölüm-4-medya-kütüphanesi---dosya-yükleme-ve-sürükle-birak-çalişmamasi) |
| **5** | **Altyazı (Subtitles) Görüntüleme ve WebVTT Senkronizasyonu** | 🔴 **DOĞRULANDI (Eksik Özellik / Sıfır Render)** | [Bölüm 5: Sorun 5 Analizi ve Çözümü](#bölüm-5-altyazi-subtitles-görüntüleme-ve-webvtt-senkronizasyonu) |
| **6** | **Akıllı Hatalı Tekrar (Retake) Tespiti ve Toplu Silme** | 🔴 **DOĞRULANDI (Aktif String Bug'ı & Kilit)** | [Bölüm 6: Sorun 6 Analizi ve Çözümü](#bölüm-6-akilli-hatali-tekrar-retake-tespiti-ve-toplu-silme) |
| **7** | **Çoklu Katman (Multi-Layer) Z-Index ve Seçim Çakışması** | 🔴 **DOĞRULANDI (Mimari / Sabit Z-20 / Hardcoded URL)** | [Bölüm 7: Sorun 7 Analizi ve Çözümü](#bölüm-7-çoklu-katman-multi-layer-z-index-ve-seçim-çakişmasi) |
| **8** | **Giriş ve Çıkış Animasyonları ve Zengin Tipografi** | 🔴 **DOĞRULANDI (Sert Kesim / Çıkış Yok / 6 Font)** | [Bölüm 8: Sorun 8 Analizi ve Çözümü](#bölüm-8-giriş-ve-çikiş-animasyonlari-ve-zengin-tipografi) |
| **9** | **Zaman Çizgisinde Çoklu Parça Seçme (Multi-Select)** | ✅ **BÜYÜK ORANDA ÇÖZÜLDÜ (Mevcut Durum: Çalışıyor)** | [Bölüm 9: Sorun 9 Analizi ve Cila Çözümü](#bölüm-9-zaman-çizgisinde-çoklu-parça-seçme-multi-select-ve-kurgu-operasyonlari) |
| **10** | **9 Sorunun Genel Özeti ve Master Yol Haritası** | 📋 **Özet Matrisi** | [Bölüm 10: Master Yol Haritası](#bölüm-10-9-sorunun-genel-değerlendirme-tablosu-ve-master-yol-haritasi) |

---

## BÖLÜM 1: YAZI VE KATMAN AYARLARININ SIFIRLANMASI (DRAG & DROP / STATE DESYNC)

> **Mevcut Durum Değerlendirmesi:** ✅ **BÜYÜK ORANDA ÇÖZÜLDÜ**  
> Kod tabanındaki son commit (`cf6d121`) incelendiğinde, `onGlobalMouseUp` içerisindeki patch yükünün `overlays: [{ ...ov, action: 'update' }]` şeklinde güncellendiği doğrulanmıştır. Eski dokümandaki *"her sürüklemede metin beyaz renge ve 48px'e dönüyor"* iddiası artık **geçersizdir**. Sistem şu an güncel stilleri koruyarak backend'e iletmektedir.

---

### 1.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti
Eski dokümanda 1. sorun için şu tespitler öne sürülmüştür:
1. Kullanıcı Inspector üzerinden metnin rengini `#FF0000`, boyutunu `72px`, fontunu `Montserrat` yaptığında önizlemede değiştiği; fakat canvas üzerinde yazıyı fare ile sürükleyip bıraktığı anda varsayılana (`#FFFFFF`, `48px`, `Inter`) döndüğü iddia edilmiştir.
2. Kök neden olarak frontend'de `onInspectorChange`'in backend'e gitmediği ve backend'de `EdlManager.cs`'in veritabanındaki PascalCase (`Color`, `FontSize`) alanlarla eşleşmediği varsayılmıştır.

---

### 1.2 Kod Tabanı İncelemesi: Dokümandaki Hatalar ve Gerçekler

1. **PascalCase Efsanesi Çürütüldü:** Python Worker (`edl_model.py`), PostgreSQL JSONB verisi ve Angular modelleri (`edl.model.ts`) incelenmiş; veritabanında hiçbir zaman `Color` veya `FontSize` şeklinde PascalCase saklanmadığı, modellerin baştan beri `color`, `fontSize`, `font` (camelCase) olduğu kanıtlanmıştır. Dokümandaki PascalCase iddiası asılsız bir tahmindir.
2. **Kullanıcının Yaptığı Çözüm (`cf6d121`):**
   Önceki kodda:
   ```typescript
   // Eski Hatalı Kod:
   this.edlService.patchEdl(this.projectId, {
       overlays: [{ id: ov.id, positionX: ov.positionX, positionY: ov.positionY, action: 'update' } as any]
   });
   ```
   Bu eski kodda sürükleme bitince sadece koordinatlar gidiyor, renk ve font bilgisi gönderilmiyordu. Yapılan son geliştirme ile:
   ```typescript
   // Düzeltilmiş Mevcut Kod:
   this.edlService.patchEdl(this.projectId, {
       overlays: [{ ...ov, action: 'update' } as any]
   }).subscribe(() => this.loadEdl());
   ```
   `...ov` ile tüm güncel stil bilgileri (renk, boyut, font) eksiksiz gönderilmektedir. Dolayısıyla temel sorun **fiilen çözülmüştür**.

---

### 1.3 Kalan Çok Ufak Pürüzler (Edge-Cases)
Sorun ana hatlarıyla çözülmüş olsa da kod kalitesi ve kusursuz UX için şu iki ince detaya dikkat edilmelidir:
1. **`onCanvasDragStart` Tıklamasında Gereksiz State Yenileme:** Kullanıcı yazıya her tıkladığında `this.selectOverlay(overlayId)` çağrılmaktadır. Eğer katman zaten seçiliyse bunu tekrar çağırmamak (`if (this.selectedOverlayId() !== overlayId)`) performansı artırır ve olası blur/focus gecikmelerini önler.
2. **`addTextOverlay` Asenkron `loadEdl` Çağrısı:** Yeni katman eklenirken `loadEdl()` tamamlandıktan sonra `selectOverlay` tetiklenmesi yarış durumlarını (race condition) %100 engeller.

---

## BÖLÜM 2: CANVAS ÜZERİNDE KÖŞEDEN TUTUP BOYUTLANDIRMA (RESIZE HANDLE)

> **Mevcut Durum Değerlendirmesi:** ✅ **ÇÖZÜLDÜ VE ÇALIŞIYOR**  
> `editor.component.ts` kod tabanı incelendiğinde; köşeden boyutlandırma kulpunun (`⤡`), `onCanvasResizeStart` metodunun, `window:mousemove` üzerindeki boyut hesaplama algoritmasının ve `window:mouseup` backend kayıt mekanizmasının **zaten yazılmış ve çalışır vaziyette olduğu** doğrulanmıştır. Eski dokümandaki *"çalışmıyor / sürüklenme davranışı sergiliyor"* tespiti **artık geçerli değildir**.

---

### 2.1 Eski Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 2. sorun için şu iddialar yer almaktaydı:
1. **Kullanıcı Deneyimi:** Sağ alt köşedeki boyutlandırma simgesinden (`⤡`) tutup çekildiğinde nesnenin boyutunun değişmediği, boyutlanmak yerine yerinden oynadığı (sürüklenme davranışı sergilediği).
2. **İddia Edilen Kök Nedenler:**
   - Kulp `(mousedown)` tetiklendiğinde DOM event bubbling nedeniyle kapsayıcı `div`'in `onCanvasDragStart`'ı devreye soktuğu ve `isCanvasDragging = true` yaptığı.
   - CSS transform `-translate-x-1/2 -translate-y-1/2` merkezleme matrisinin titremeye ve farenin kulpun dışına taşmasına sebep olduğu.
   - Görsellerde `pointer-events-none` nedeniyle kulpun tıklanamaz kaldığı.

---

### 2.2 Kod Tabanındaki Gerçek Durum ve Uygulanan Çözümün Doğrulanması

Mevcut kaynak kodlar (`editor.component.ts`) incelendiğinde bu özelliğin son güncellemelerle eksiksiz olarak sisteme eklendiği görülmektedir:

#### 1. Kulp HTML Şablonu Doğrulaması (`editor.component.ts: Satır 118-122`)
```html
<!-- Canvas Resize Handle -->
<div *ngIf="selectedOverlayId() === ov.id"
     (mousedown)="onCanvasResizeStart($event, ov.id)"
     class="absolute -bottom-2 -right-2 w-5 h-5 bg-white border-2 border-brand-cyan rounded-full cursor-nwse-resize z-30 shadow-md hover:scale-125 transition-transform flex items-center justify-center">
     <span class="text-[8px] text-brand-cyan">⤡</span>
</div>
```
* **Doğrulama:** Kulp sadece katman seçildiğinde görünmekte, `cursor-nwse-resize` imleci ile doğru görsel geri bildirimi vermektedir. `z-30` katman seviyesiyle görselin veya metnin kesinlikle üzerinde kalmaktadır.

#### 2. Event Bubbling Engellemesi (`editor.component.ts: Satır 1686-1698`)
```typescript
onCanvasResizeStart(event: MouseEvent, overlayId: string): void {
    event.preventDefault();
    event.stopPropagation(); // <-- SÜRÜKLENMEYİ (DRAG) KESİNLİKLE ENGELLİYOR!
    this.selectOverlay(overlayId);
    this.isCanvasResizing = true;
    this.canvasResizeOverlayId = overlayId;
    this.canvasResizeStartX = event.clientX;
    const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
    if (ov) {
        this.canvasResizeOriginalScale = ov.scale || 1.0;
        this.canvasResizeOriginalFontSize = ov.fontSize || 48;
    }
}
```
* **Doğrulama:** `event.stopPropagation()` çağrıldığı için kapsayıcı `div` üzerindeki `(mousedown)="onCanvasDragStart"` **asla tetiklenmemektedir**. `isCanvasDragging` `false` kalmakta; yalnızca `isCanvasResizing = true` olmaktadır. Dokümandaki *"sürüklenme davranışı sergiliyor"* iddiası bu kod ile tamamen ortadan kaldırılmıştır.

#### 3. Canlı Boyutlandırma Hesaplaması (`editor.component.ts: Satır 1733-1755`)
```typescript
if (this.isCanvasResizing) {
    const deltaX = event.clientX - this.canvasResizeStartX;
    const ov = this.activeEdl()?.overlays?.find(o => o.id === this.canvasResizeOverlayId);
    if (ov) {
        if (ov.type === 'image') {
            let newScale = this.canvasResizeOriginalScale + (deltaX / 100);
            if (newScale < 0.2) newScale = 0.2;
            if (newScale > 5.0) newScale = 5.0;
            ov.scale = newScale;
            if (this.inspectorData && this.inspectorData.id === ov.id) {
                this.inspectorData.scale = parseFloat(newScale.toFixed(2));
            }
        } else if (ov.type === 'text') {
            let newSize = this.canvasResizeOriginalFontSize + deltaX;
            if (newSize < 10) newSize = 10;
            if (newSize > 400) newSize = 400;
            ov.fontSize = newSize;
            if (this.inspectorData && this.inspectorData.id === ov.id) {
                this.inspectorData.fontSize = Math.round(newSize);
            }
        }
    }
    return;
}
```
* **Doğrulama:**
  - Görseller için `scale` (0.2x ile 5.0x arasında sınırlandırılarak) pürüzsüz büyütülmektedir.
  - Metinler için `fontSize` (10px ile 400px arasında sınırlandırılarak) anlık olarak büyümektedir.
  - `inspectorData` panelindeki input değerleri de eş zamanlı olarak senkronize güncellenmektedir.
  - `return` ifadesi sayesinde timeline veya diğer sürükleme dinleyicileri tamamen izole edilmiştir.

#### 4. Boyutlandırma Sonucu Backend'e Kayıt (`editor.component.ts: Satır 1840-1853`)
```typescript
if (this.isCanvasResizing) {
    this.isCanvasResizing = false;
    const ovId = this.canvasResizeOverlayId;
    this.canvasResizeOverlayId = null;
    if (ovId) {
       const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
       if (ov) {
           this.edlService.patchEdl(this.projectId, {
               overlays: [{ ...ov, action: 'update' } as any]
           }).subscribe(() => this.loadEdl());
       }
    }
    return;
}
```
* **Doğrulama:** Fare bırakıldığı anda `patchEdl` tetiklenmekte, `...ov` nesnesiyle yeni boyut veritabanına mühürlenmekte ve `this.loadEdl()` ile güncel EDL yeniden yüklenmektedir.

---

### 2.3 Bu Sorun Gerçekte Var mı? (Nihai Teşhis)

> **SONUÇ:** **HAYIR, SORUN ESKİ DÖKÜMANDA BAHSEDİLDİĞİ GİBİ DEĞİLDİR.**  
> Özellik halihazırda kodlanmış, event çakışmaları çözülmüş ve çalışır durumdadır. Kullanıcının *"1 ve 2'yi çoğunlukla çözmüştüm, şu an yok ya da çok ufak sorunları var"* ifadesi **%100 doğrudur**.

---

### 2.4 Kalan Çok Ufak Pürüzler ve İyileştirme Fırsatları

Özellik stabil çalışmakla birlikte, deneyimi profesyonel bir kurgu yazılımı seviyesine çıkarmak için şu **2 ufak pürüz** optimize edilebilir:

1. **Yalnızca Yatay Eksen (DeltaX) Dinlemesi:**
   - Mevcut kodda `const deltaX = event.clientX - this.canvasResizeStartX;` kullanılmaktadır.
   - Kullanıcı kulpu sağa doğru çektiğinde boyut mükemmel büyümektedir; ancak kullanıcı fareyi tamamen aşağı doğru (saf dikey / Y ekseninde) çekerse `deltaX` sıfır olacağı için boyut tepki vermez.
   - **Çözüm:** Bileşik delta formülü kullanmak: `const delta = Math.abs(deltaX) > Math.abs(deltaY) ? deltaX : deltaY;` veya `(deltaX + deltaY) / 1.5;`.
2. **Pencere Dışı Fare Bırakma Emniyeti (Pointer Capture):**
   - Kullanıcı kulpu çok hızlı çekip fare imlecini tarayıcı penceresinin dışına taşırsa `mouseup` olayı nadiren kaçabilir.
   - **Çözüm:** `mousedown` yerine `pointerdown` kullanılarak `target.setPointerCapture(event.pointerId)` eklenmesi emniyet sağlar.

#### 10 Satırlık İsteğe Bağlı Cila Kodu:
```typescript
// editor.component.ts (Satır 1734 yerine bileşik delta)
const deltaX = event.clientX - this.canvasResizeStartX;
const deltaY = event.clientY - this.canvasResizeStartY;
// Kullanıcı ister sağa, ister aşağı, ister çapraz çeksin en baskın hareketi algıla:
const delta = Math.abs(deltaX) >= Math.abs(deltaY) ? deltaX : deltaY;
```

---

## BÖLÜM 3: YÖNETMEN AI'DEN SEÇİLEBİLİR DROPDOWN FORM ŞEMASI EKSİKLİĞİ

> **Mevcut Durum Değerlendirmesi:** 🔴 **GERÇEKTEN MEVCUT VE SİSTEMİ KİLİTLİYOR (Aktif Kritik Sorun)**  
> Kod tabanı (`GeminiChatProvider.cs`, `editor.component.ts`, `chat.model.ts`, `ChatManager.cs`) satır satır incelenmiş ve sorunun **halen aktif olduğu** doğrulanmıştır. Hatta eski dokümanda yer alan analizin çok ötesinde, formun canlı sohbette ekrana hiç yansımamasına (`res.formFields`'in unutulması) ve sonsuz clarification döngüsüne yol açan **5 derin kod hatası** tespit edilmiştir.

---

### 3.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 3. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Kullanıcı AI Yönetmen sohbetine *"Videonun ortasına dikkat çekici bir başlık ekle"* yazdığında, yapay zekanın kullanıcıya seçenek sunmak yerine serbest metin veya sayı girmesini istediği ("Lütfen X ve Y koordinatını girin") ya da boş form getirdiği belirtilmiştir.
2. **İddia Edilen Kök Neden:** `GeminiChatProvider.cs` sistem promptunda `select` için şema verilmediği, frontend'in `{ value, label }` beklerken LLM'in `["Sağ Üst", "Sol Alt"]` şeklinde string dizisi döndüğü, bu sebeple dropdown'un boş kaldığı iddia edilmiştir.

---

### 3.2 Kod Tabanı İncelemesi: Dokümandaki Eksikler ve Kaçırılan 5 Kritik Bug

Yapılan kod incelemesinde eski dokümanın sorunun yalnızca yüzeydeki bir parçasını gördüğü; arka planda sistemin çalışmasını engelleyen **5 zincirleme hata** bulunduğu tespit edilmiştir:

#### 1. Dev Hata: Canlı Asistan Yanıtında `formFields`'in Unutulması (`editor.component.ts: Satır 1431-1444`)
Backend `ChatManager.cs`, Gemini'den gelen form alanlarını `ChatResponseDto.FormFields` içinde istemciye yollamaktadır. Ancak Angular tarafında mesaj gönderme metoduna bakıldığında:
```typescript
// editor.component.ts (Satır 1430-1444)
this.chatService.sendMessage(this.projectId, msgText).subscribe({
  next: (res) => {
    this.chatLoading.set(false);
    this.chatMessages.update(msgs => [
      ...msgs,
      {
        projectId: this.projectId,
        rol: 'assistant',
        mesaj: res.mesaj,
        olusturulmaZamani: new Date().toISOString(),
        edlPatch: res.edlPatch,
        pendingEdlPatch: res.pendingEdlPatch,
        patchDurumu: res.patchDurumu,
        intent: res.intent,
        id: res.id
        // formFields: res.formFields <--- TAMAMEN UNUTULMUŞ!
      }
    ]);
    this.loadEdl();
  }
});
```
* **Kritik Sonuç:** Gemini `intent: "clarification"` ile form alanları üretse bile, Angular bu alanları `chatMessages` nesnesine **eklemediği için form canlı sohbette ASLA GÖRÜNMEMEKTEDİR!**
* Kullanıcı formu ancak sayfayı yenilediğinde (`F5`) `loadChatHistory()` çalıştığı zaman görebilmektedir; anlık sohbette ise sistem tıkanmaktadır.

#### 2. `GeminiChatProvider.cs` Promptunda `options` Şemasının Bulunmaması
`src/OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs: Satır 58-71` sistem promptu:
```csharp
2. Eğer intent "clarification" ise, "formFields" array'ini dön. Type'lar "text", "color", "select", "number" olabilir.
   Örn Yazı için: "text" (İçerik), "color" (Renk), "select" (Font: Inter, Arial, Roboto), "select" (Konum: Merkez, Alt, Üst, Sağ, Sol vb.), "select" (Animasyon: pop-up, fade, slide-up, none).
...
"formFields": [ { "id": "renk", "type": "color", "label": "Yazı Rengi", "defaultValue": "#FFFFFF" } ]
```
* **Kritik Sonuç:** Prompt içerisinde LLM'e verilen tek şablon örneği `color` üzerinedir. `select` tipi için bir `options` alanı olması gerektiği, bu alanın `[ { "value": "...", "label": "..." } ]` nesneleri barındırması gerektiği LLM'e hiçbir yerde bildirilmemiştir.
* Gemini ya `options` alanını hiç üretmemekte ya da `["Inter", "Arial"]` şeklinde düz string dizisi dönmektedir.

#### 3. Frontend Şablonunda Düz Metin Dizisini Karşılayamama (`editor.component.ts: Satır 400`)
```html
<select *ngIf="field.type === 'select'"
        [ngModel]="msg.formData?.[field.id] || field.defaultValue"
        (ngModelChange)="updateFormData(msg, field.id, $event)"
        class="w-full bg-dark-800 border border-slate-700 rounded p-1.5 text-xs focus:border-brand-cyan outline-none">
    <option *ngFor="let opt of field.options" [value]="opt.value">{{ opt.label }}</option>
</select>
```
* Eğer Gemini `options: ["Merkez", "Alt", "Üst"]` üretirse:
  - `opt` bir string (`"Merkez"`) olduğu için `opt.value` ve `opt.label` JavaScript tarafından **`undefined`** olarak değerlendirilir.
  - Açılır kutuda kullanıcının karşısına 3 tane boş, seçilemeyen `<option value="undefined"></option>` satırı çıkar.

#### 4. `submitForm`'un `undefined` Değer Üretip LLM'i Sonsuz Döngüye Sokması (`editor.component.ts: Satır 1582-1605`)
```typescript
submitForm(msg: ChatMessageDto): void {
   ...
   let responseText = "İstediğim özellikler:\n";
   msg.formFields.forEach(f => {
       responseText += `- ${f.label}: ${msg.formData[f.id]}\n`;
   });
   this.userPrompt = responseText;
   msg.patchDurumu = 'answered';
   this.sendChatMessage();
}
```
* `opt.value` `undefined` olduğu için `msg.formData[f.id]` değeri de `undefined` olur.
* LLM'e giden prompt:
  ```text
  İstediğim özellikler:
  - Ekran Konumu: undefined
  - Giriş Animasyonu: undefined
  ```
* Gemini bu anlamsız metni görünce tekrar `intent: "clarification"` döner ve kullanıcı **sonsuz bir form doldurma döngüsüne hapsolur.**

#### 5. Form Durumunun (`answered`) Veritabanına Kaydedilmemesi
* `submitForm` içinde `msg.patchDurumu = 'answered'` satırı sadece frontend bellek nesnesinde kalır.
* Backend'e bir güncelleme isteği gönderilmez. Kullanıcı sayfayı yenilediğinde (`F5`) backend'den `m.PatchDurumu == "clarification"` olarak geri döner ve aylar önce yanıtlanmış formlar kullanıcının karşısında tekrar tekrar açılır.

---

### 3.3 Etkilenen Dosya ve Satır Haritası

| Dosya Yolu | İlgili Satırlar | Tespit Edilen Problem |
|---|---|---|
| `src/OtoEdit.Business/Infrastructure/AI/GeminiChatProvider.cs` | 58-71 | Prompt içinde `select` için `{ value, label }` JSON şemasının ve standart preset enum'larının olmaması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 1438-1443 | `sendMessage` yanıtında `formFields: res.formFields` alanının eklenmemesi (Formun canlı sohbette kaybolması). |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 396-402 | `<option>` şablonunda string dizisi geldiğinde `undefined` kalması ve esnek normalizasyon olmaması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 1582-1605 | `submitForm` içinde `undefined` değerlerin temizlenmemesi ve `answered` durumunun backend'e yazılmaması. |
| `src/OtoEdit.Business/Services/ChatManager.cs` | 133-136 | Form durumunun güncellenmesi için bir metot / uç noktanın eksik olması. |

---

### 3.4 Uçtan Uca Kesin Mimari Çözüm ve Kodları

#### A. Backend: `GeminiChatProvider.cs` Sistem Promptu Revizyonu
Prompt içerisine `select`, `color` ve yeni interaktif `position` aracı için katı nesne şeması ve standart preset enum'ları eklenmelidir:

```csharp
// GeminiChatProvider.cs içindeki systemPrompt düzeltmesi

KURALLAR (KESİNLİKLE UYULACAK):
...
2. Eğer intent "clarification" ise, "formFields" dizisini KESİNLİKLE aşağıdaki şemaya uygun dön:
   Desteklenen "type" türleri:
   - "text": Serbest metin girişi (Başlık, alt başlık metni vb.)
   - "color": Zengin renk paleti ve Hex seçici (id: "color")
   - "position": 16:9 İnteraktif ekran konumlayıcı (id: "position")
   - "select": Açılır liste seçimi (Font ve Animasyon için)

   HER ALANIN ŞEMASI:
   - "id": string ("content", "position", "color", "font", "animation", "scale")
   - "type": "text" | "color" | "position" | "select" | "number"
   - "label": Kullanıcıya görünecek Türkçe başlık
   - "defaultValue": Varsayılan değer (örn: position için "bottom-center", color için "#FFFFFF")
   - "options": (SADECE type="select" ise ZORUNLU) [ { "value": "kod", "label": "Görünecek Metin" } ]

   STANDART PRESET SEÇENEKLERİ (Harfiyen uyulacak):
   - Yazı Tipi (id: "font", type: "select"):
     [
       { "value": "Montserrat", "label": "Montserrat (Kalın & Dikkat Çekici)" },
       { "value": "Inter", "label": "Inter (Modern & Sade)" },
       { "value": "Arial", "label": "Arial (Klasik Sans)" },
       { "value": "Impact", "label": "Impact (YouTube Başlık)" }
     ]
   - Giriş Animasyonu (id: "animation", type: "select"):
     [
       { "value": "pop-up", "label": "✨ Büyüyerek Açıl (Pop-up)" },
       { "value": "fade", "label": "🌫 Yumuşak Geçiş (Fade In)" },
       { "value": "slide-up", "label": "⬆ Aşağıdan Yukarı (Slide Up)" },
       { "value": "none", "label": "⚡ Sabit (Animasyonsuz)" }
     ]

7. Yanıtını SADECE aşağıdaki JSON formatında ver:
{
   "mesaj": "Başlığın ekranda nerede durmasını, rengini ve animasyonunu belirleyiniz:",
   "intent": "clarification",
   "edlPatch": null,
   "formFields": [
      {
         "id": "content",
         "type": "text",
         "label": "Görünecek Metin",
         "defaultValue": "Öne Çıkan Başlık"
      },
      {
         "id": "position",
         "type": "position",
         "label": "Ekran Konumu",
         "defaultValue": "bottom-center"
      },
      {
         "id": "color",
         "type": "color",
         "label": "Yazı Rengi",
         "defaultValue": "#FACC15"
      },
      {
         "id": "font",
         "type": "select",
         "label": "Yazı Tipi (Font)",
         "defaultValue": "Montserrat",
         "options": [
            { "value": "Montserrat", "label": "Montserrat (Kalın & Dikkat Çekici)" },
            { "value": "Inter", "label": "Inter (Modern)" }
         ]
      },
      {
         "id": "animation",
         "type": "select",
         "label": "Giriş Animasyonu",
         "defaultValue": "pop-up",
         "options": [
            { "value": "pop-up", "label": "✨ Pop-up" },
            { "value": "fade", "label": "🌫 Fade In" }
         ]
      }
   ]
}
```

---

#### B. Frontend: Özel Zengin Araçlar (16:9 Mini Sahne & Renk Paleti & Dropdown)

Kullanıcının talep ettiği özel görsel araçlar arayüze şu şekilde entegre edilir:

##### 1. Özel Renk Aracı (Palette Swatches + Hex Input + Color Wheel):
Basit dar bir kutucuk yerine, yazı editöründeki gibi zengin ve hızlı bir renk seçici:
- Hızlı seçim butonları: `#FFFFFF` (Beyaz), `#FACC15` (Sarı), `#06B6D4` (Cyan), `#EF4444` (Kırmızı), `#10B981` (Yeşil), `#A855F7` (Mor).
- Canlı Hex kodu kutusu ve renk tekerleği.

##### 2. 16:9 İnteraktif Mini Sahne Konum Seçici & Canlı Canvas Taslak Katmanı:
- Chat içindeki formda 16:9 en-boy oranında minyatür bir video ekranı kutusu (`aspect-video`) yer alır.
- Bu kutu üzerinde 9 adet manyetik çıpa noktası (Sol Üst, Üst Orta, Sağ Üst, Sol Orta, Merkez, Sağ Orta, Sol Alt, Alt Orta, Sağ Alt) hazır butonlar halinde bulunur.
- **Serbest Tıklama:** Kullanıcı 16:9 kutuda **herhangi bir noktaya tıkladığında**, tıklanan noktanın bağıl X ve Y yüzdesi (`positionX%`, `positionY%`) hesaplanır ve oraya küçük bir hedef imleci (pin 📍) oturur!
- **Canlı Canvas Önizlemesi:** Form açıkken, ana video player üzerinde kesikli çizgili ve parlak bir **"Taslak Yazı" (Ghost Layer)** belirir. Kullanıcı 16:9 kutuda nereye tıklarsa, ana video ekranındaki yazı da anında oraya sıçrar! Kullanıcı isterse ana video canvas'ında da bu taslağı doğrudan fareyle tutup sürükleyebilir.

##### 3. Font ve Animasyon Dropdown'ları:
- Font ve animasyonlar için açılır liste (dropdown) korunur; `{ value, label }` ve düz stringleri pürüzsüz destekleyen esnek şablon kullanılır.

##### Şablon Kodu (`editor.component.ts: Satır 380-415` Revizyonu):
```html
<!-- Özel İnteraktif Form Elemanları -->
<div *ngFor="let field of msg.formFields" class="space-y-1.5">
   <label class="text-[10px] text-slate-400 uppercase font-semibold block">{{ field.label }}</label>

   <!-- 1. METİN GİRİŞİ -->
   <input *ngIf="field.type === 'text'" type="text"
          [ngModel]="msg.formData?.[field.id] || field.defaultValue"
          (ngModelChange)="updateFormData(msg, field.id, $event)"
          class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan outline-none" />

   <!-- 2. ZENGİN RENK PALETİ VE SEÇİCİ -->
   <div *ngIf="field.type === 'color'" class="space-y-2">
      <!-- Hızlı Seçim Paleti -->
      <div class="flex items-center gap-1.5">
         <button type="button" *ngFor="let c of ['#FFFFFF', '#FACC15', '#06B6D4', '#EF4444', '#10B981', '#A855F7']"
                 (click)="updateFormData(msg, field.id, c)"
                 [style.backgroundColor]="c"
                 [class.ring-2]="(msg.formData?.[field.id] || field.defaultValue) === c"
                 class="w-5 h-5 rounded-full border border-slate-700 hover:scale-110 transition-transform ring-brand-cyan"></button>
         
         <!-- Özel Renk Tekerleği -->
         <div class="relative w-6 h-6 ml-auto rounded-full overflow-hidden border border-slate-600 cursor-pointer">
            <input type="color" 
                   [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#FFFFFF'"
                   (ngModelChange)="updateFormData(msg, field.id, $event)"
                   class="absolute -top-2 -left-2 w-10 h-10 cursor-pointer bg-transparent border-0" />
         </div>
      </div>
      <!-- Hex Kodu Kutusu -->
      <input type="text" 
             [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#FFFFFF'"
             (ngModelChange)="updateFormData(msg, field.id, $event)"
             class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white font-mono text-center focus:border-brand-cyan outline-none" />
   </div>

   <!-- 3. 16:9 İNTERAKTİF MİNİ SAHNE KONUM SEÇİCİ -->
   <div *ngIf="field.type === 'position'" class="space-y-2">
      <div class="relative aspect-video bg-dark-950 border border-slate-700 hover:border-slate-600 rounded-lg overflow-hidden cursor-crosshair shadow-inner"
           (click)="onMiniStageClick($event, msg, field.id)">
         
         <!-- Kılavuz Çizgileri -->
         <div class="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none opacity-20 border border-slate-600">
            <div class="border-r border-b border-slate-600"></div>
            <div class="border-r border-b border-slate-600"></div>
            <div class="border-b border-slate-600"></div>
            <div class="border-r border-b border-slate-600"></div>
            <div class="border-r border-b border-slate-600"></div>
            <div class="border-b border-slate-600"></div>
            <div class="border-r border-slate-600"></div>
            <div class="border-r border-slate-600"></div>
            <div></div>
         </div>

         <!-- 9 Manyetik Hızlı Çıpa Düğmesi -->
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 15, 15, 'Sol Üst')" class="absolute top-2 left-2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Sol Üst"></button>
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 50, 15, 'Üst Orta')" class="absolute top-2 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Üst Orta"></button>
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 85, 15, 'Sağ Üst')" class="absolute top-2 right-2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Sağ Üst"></button>

         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 15, 50, 'Sol Orta')" class="absolute top-1/2 left-2 -translate-y-1/2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Sol Orta"></button>
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 50, 50, 'Tam Merkez')" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-brand-cyan/60 hover:bg-brand-cyan border border-white" title="Tam Merkez"></button>
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 85, 50, 'Sağ Orta')" class="absolute top-1/2 right-2 -translate-y-1/2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Sağ Orta"></button>

         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 15, 85, 'Sol Alt')" class="absolute bottom-2 left-2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Sol Alt"></button>
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 50, 85, 'Alt Orta')" class="absolute bottom-2 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Alt Orta"></button>
         <button type="button" (click)="$event.stopPropagation(); setStagePosition(msg, field.id, 85, 85, 'Sağ Alt')" class="absolute bottom-2 right-2 w-3 h-3 rounded-full bg-slate-700 hover:bg-brand-cyan" title="Sağ Alt"></button>

         <!-- Seçili Konum Pin'i / İşareti -->
         <div class="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none transition-all duration-150 flex items-center justify-center"
              [style.left.%]="msg.formData?.positionX ?? 50"
              [style.top.%]="msg.formData?.positionY ?? 85">
            <span class="w-3 h-3 rounded-full bg-brand-cyan shadow-glow-sm animate-ping absolute"></span>
            <span class="w-3 h-3 rounded-full bg-white border-2 border-brand-cyan shadow"></span>
         </div>
      </div>
      <p class="text-[10px] text-slate-400 text-center font-mono">
         Seçili Konum: {{ msg.formData?.positionDesc || 'Alt Orta' }} (%{{ msg.formData?.positionX ?? 50 }}, %{{ msg.formData?.positionY ?? 85 }})
      </p>
   </div>

   <!-- 4. FONT VE ANİMASYON AÇILIR LİSTELERİ (DROPDOWN) -->
   <select *ngIf="field.type === 'select'"
           [ngModel]="msg.formData?.[field.id] || field.defaultValue"
           (ngModelChange)="updateFormData(msg, field.id, $event)"
           class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan outline-none">
       <option *ngFor="let opt of field.options" [value]="getOptValue(opt)">
           {{ getOptLabel(opt) }}
       </option>
   </select>
</div>
```

##### TypeScript Metotları (`editor.component.ts`):
```typescript
// 16:9 Mini Sahne Üzerinde Tıklanan Noktanın Koordinatını Alma
onMiniStageClick(event: MouseEvent, msg: any, fieldId: string): void {
    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    
    // Tıklanan pikselin 16:9 kutu içindeki yüzde oranını hesapla (0 - 100)
    const posX = Math.round(((event.clientX - rect.left) / rect.width) * 100);
    const posY = Math.round(((event.clientY - rect.top) / rect.height) * 100);
    
    this.setStagePosition(msg, fieldId, posX, posY, `Özel Konum (X: %${posX}, Y: %${posY})`);
}

setStagePosition(msg: any, fieldId: string, x: number, y: number, label: string): void {
    if (!msg.formData) msg.formData = {};
    msg.formData.positionX = x;
    msg.formData.positionY = y;
    msg.formData.positionDesc = label;
    msg.formData[fieldId] = `${label} [positionX: ${x}, positionY: ${y}]`;
}

// Form Gönderildiğinde Seçilen Görsel Değerleri ve Koordinatları AI'a İletme
submitForm(msg: ChatMessageDto): void {
   if (!msg.formFields) return;
   if (!msg.formData) msg.formData = {};

   // Boş bırakılan alanları varsayılanlarla doldur
   msg.formFields.forEach(f => {
       if (msg.formData[f.id] === undefined) {
           if (f.type === 'position') {
               msg.formData.positionX = 50;
               msg.formData.positionY = 85;
               msg.formData[f.id] = "Alt Orta [positionX: 50, positionY: 85]";
           } else {
               msg.formData[f.id] = f.defaultValue;
           }
       }
   });

   let responseText = "Belirttiğim özellikler ile katmanı ekle:\n";
   msg.formFields.forEach(f => {
       responseText += `- ${f.label}: ${msg.formData[f.id]}\n`;
   });

   msg.patchDurumu = 'answered';
   this.userPrompt = responseText;
   this.sendChatMessage();
}
```

---

### 3.5 Doğrulama ve Test Adımları

1. **Canlı Form ve Araç Görünürlük Testi:**
   - Sohbete *"Videoya bir başlık eklemek istiyorum"* yazılır.
   - AI'ın cevabının altında renk paleti butonları, 16:9 mini video konum kutucuğu ve Font/Animasyon açılır kutularının anında belirdiği doğrulanır.
2. **16:9 Konum Seçim Testi:**
   - 16:9 mini monitör kutusunun sol üst köşesine veya herhangi bir noktasına tıklanır.
   - Mavi hedef pininin tam tıklanan yere oturduğu ve alttaki koordinat metninin (örn: `%15, %15`) anlık güncellendiği teyit edilir.
3. **Renk Aracı Testi:**
   - Hızlı paletten sarı veya cyan renge basılır, renk kutusunun ve hex kodunun anında seçilen renkle senkronize olduğu görülür.
4. **Form Gönderim ve AI Çıktı Testi:**
   - "Seçimleri Gönder" butonuna basılır.
   - AI'a giden komutta koordinatların (`positionX: 15, positionY: 15`) ve rengin net şekilde gittiği, AI'ın da doğrudan bu koordinatlara sahip bir `OverlayItem` patch'i ürettiği doğrulanır.

---


## BÖLÜM 4: MEDYA KÜTÜPHANESİ - DOSYA YÜKLEME VE SÜRÜKLE-BIRAK ÇALIŞMAMASI

> **Mevcut Durum Değerlendirmesi:** 🔴 **GERÇEKTEN MEVCUT VE EKSİK ÖZELLİK (Tamamen İşlevsiz / Dead Code)**  
> Kod tabanı incelenmiş; Medya sekmesindeki "Dosya Yükle" butonunun hiçbir event'e bağlı olmadığı (`(click)` yok), arama kutusunun dummy olduğu, şablonda `<input type="file">` bulunmadığı ve backend tarafında da projeye harici medya yükleyecek (`AssetsController`, `IAssetService`, `ProjectAsset` entity) hiçbir altyapının yazılmadığı kesin olarak doğrulanmıştır.

---

### 4.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 4. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Kullanıcı Medya sekmesinde "Dosya Yükle" butonuna tıkladığında hiçbir dosya penceresi açılmamakta, bilgisayarından bir görsel veya videoyu panelin üzerine bıraktığında ise tarayıcı dosyayı doğrudan yeni sekmede açmakta veya tepkisiz kalmaktadır.
2. **İddia Edilen Kök Neden:** Frontend şablonundaki butonun unbound (işlevsiz) olduğu, input elementinin ve sürükle-bırak dinleyicilerinin bulunmadığı, backend tarafında ise MinIO'ya dosya kaydeden bir endpoint'in yazılmadığı belirtilmiştir.

---

### 4.2 Kod Tabanı İncelemesi: Doğrulamalar ve Ek Bulgular

Kaynak kodlar detaylı incelendiğinde durumun eski dokümanda anlatılandan da vahim olduğu (sadece buton değil, veritabanı entity'sinden controller'a kadar tüm katmanın eksik olduğu) görülmektedir:

#### 1. Frontend Arayüzündeki "Ölü Kodlar" (Dead Code)
`editor.component.ts: Satır 630-658`:
```html
<!-- Sekme 4: Medya (Assets) -->
<div *ngIf="activeTab() === 'media'" class="flex-1 p-5 overflow-y-auto space-y-4">
   ...
   <!-- 1. Butonda hiçbir (click) dinleyicisi YOK -->
   <button class="px-4 py-2 bg-brand-cyan/20 text-brand-cyan font-bold text-xs rounded hover:bg-brand-cyan/30">
      Dosya Yükle
   </button>
   
   <!-- 2. Arama kutusu ve butonu tamamen sahte/işlevsiz -->
   <input type="text" placeholder="Arama yap..." class="flex-1 ... text-xs text-white" />
   <button class="px-3 bg-dark-700 text-white rounded text-xs">Ara</button>

   <!-- 3. Sadece iki adet sabit Pexels stok linki hardcoded olarak eklenmiş -->
   <div (click)="addImageOverlayFromUrl('https://images.pexels.com/photos/1181675/...')" ...>
   <div (click)="addImageOverlayFromUrl('https://images.pexels.com/photos/3183150/...')" ...>
</div>
```
* **Doğrulama:**
  - `Dosya Yükle` butonu tamamen statik HTML'dir.
  - HTML ağacında gizli bir `<input type="file">` tanımlı değildir.
  - Kapsayıcı `div` üzerinde HTML5 `(dragover)` ve `(drop)` olayları dinlenmediği için tarayıcı dosyayı sürükleyip bırakan kullanıcıyı dosyanın doğrudan yerel URL'ine (`file:///...`) yönlendirmekte veya yeni sekmede açmaktadır.

#### 2. Backend Katmanında Hiçbir Varlık veya Endpoint Olmaması
* `src/OtoEdit.Data/Entities` dizini listelendiğinde:
  - `ChatMessage.cs`, `EditDecisionList.cs`, `EdlSnapshot.cs`, `Project.cs`, `Video.cs` mevcuttur; ancak projeye yüklenen harici medyaları (logo, sticker, B-Roll, ses efekti) tutacak **`ProjectAsset.cs` varlığı (entity) YOKTUR**.
* `src/OtoEdit.API/Controllers` dizini listelendiğinde:
  - `AssetsController.cs` diye bir uç nokta sınıfı bulunmamaktadır.
  - `VideosController.cs` içinde yalnızca ham ana video yüklemesi (`UploadVideo`) vardır; ek medya yükleme (`UploadAsset`) endpoint'i mevcut değildir.

---

### 4.3 Etkilenen Dosya ve Satır Haritası

| Dosya Yolu | İlgili Satırlar | Tespit Edilen Problem |
|---|---|---|
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 630-658 | "Dosya Yükle" ve "Ara" butonlarının event dinleyicilerinin olmaması, drag & drop eksikliği. |
| `src/OtoEdit.Frontend/src/app/core/services/media.service.ts` | Yok | Projeye medya yükleyecek ve listesini getirecek servis dosyası mevcut değil. |
| `src/OtoEdit.Data/Entities/ProjectAsset.cs` | Yok | Proje medya varlıklarını (dosya adı, URL, boyut, MIME türü) saklayacak veritabanı entity'si yok. |
| `src/OtoEdit.API/Controllers/AssetsController.cs` | Yok | Multipart form dosyasını kabul eden REST controller eksik. |
| `src/OtoEdit.Business/Services/AssetManager.cs` | Yok | MinIO S3 bucket'ına dosya yükleyen ve DB kaydı açan business servisi eksik. |

---

### 4.4 Uçtan Uca Mimari ve Kod Çözümü

#### A. Backend Katmanı: Veri Modeli ve Servis Mimarisi

1. **`ProjectAsset` Varlığı (`src/OtoEdit.Data/Entities/ProjectAsset.cs`):**
```csharp
namespace OtoEdit.Data.Entities;

public class ProjectAsset
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public string DosyaAdi { get; set; } = string.Empty;
    public string MimeTuru { get; set; } = string.Empty; // "image/png", "video/mp4", "audio/mp3"
    public string StorageKey { get; set; } = string.Empty; // MinIO nesne yolu
    public string Url { get; set; } = string.Empty; // İndirme / CDN URL'i
    public long BoyutByte { get; set; }
    public DateTime YuklemeTarihi { get; set; } = DateTime.UtcNow;

    public Project Project { get; set; } = null!;
}
```

2. **Controller Endpoint'i (`src/OtoEdit.API/Controllers/AssetsController.cs`):**
```csharp
using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/assets")]
public class AssetsController : ControllerBase
{
    private readonly IAssetService _assetService;

    public AssetsController(IAssetService assetService)
    {
        _assetService = assetService;
    }

    [HttpPost]
    [RequestSizeLimit(104857600)] // 100 MB Limit
    public async Task<IActionResult> UploadAsset(Guid projectId, [FromForm] IFormFile file, CancellationToken ct)
    {
        if (file == null || file.Length == 0)
            return BadRequest("Geçersiz veya boş dosya.");

        var assetDto = await _assetService.UploadAssetAsync(projectId, file, ct);
        return Ok(assetDto);
    }

    [HttpGet]
    public async Task<IActionResult> GetAssets(Guid projectId, CancellationToken ct)
    {
        var assets = await _assetService.GetAssetsByProjectIdAsync(projectId, ct);
        return Ok(assets);
    }
}
```

---

#### B. Frontend Katmanı: Sürükle-Bırak ve Dinamik Yükleme

1. **Şablon Revizyonu (`editor.component.ts: Satır 630-658`):**
```html
<!-- Sekme 4: Medya Kütüphanesi -->
<div *ngIf="activeTab() === 'media'" 
     (dragover)="onMediaDragOver($event)"
     (dragleave)="onMediaDragLeave($event)"
     (drop)="onMediaDrop($event)"
     [class.border-brand-cyan]="isMediaDraggingOver"
     class="flex-1 p-5 overflow-y-auto space-y-4 border-2 border-transparent transition-colors">
   
   <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Medya Kütüphanesi</h3>
   
   <!-- Gizli Dosya Seçici -->
   <input type="file" 
          #mediaFileInput 
          (change)="onFilesSelected($event)" 
          multiple 
          accept="image/*,video/*,audio/*" 
          class="hidden" />

   <!-- Yükleme Kartı (Tıklanabilir ve Sürükle-Bırak Uyumlu) -->
   <div (click)="mediaFileInput.click()" 
        class="p-4 rounded-xl bg-dark-800 border-2 border-dashed border-slate-700 hover:border-brand-cyan text-center space-y-3 cursor-pointer transition-all group">
     <svg class="w-8 h-8 mx-auto text-slate-500 group-hover:text-brand-cyan transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
     </svg>
     <p class="text-xs text-slate-400 group-hover:text-slate-200">
       {{ mediaUploading() ? 'Yükleniyor...' : 'Dosya seçmek için tıklayın veya buraya sürükleyin.' }}
     </p>
     <button type="button" class="px-4 py-2 bg-brand-cyan text-slate-900 font-bold text-xs rounded hover:bg-cyan-400 pointer-events-none">
       Dosya Yükle
     </button>
   </div>

   <!-- Yüklenen Proje Medyaları -->
   <div *ngIf="projectAssets().length > 0" class="space-y-2">
      <h4 class="text-[10px] font-bold text-slate-400 uppercase">Yüklenen Dosyalar</h4>
      <div class="grid grid-cols-2 gap-2">
         <div *ngFor="let asset of projectAssets()" 
              (click)="addImageOverlayFromUrl(asset.url)" 
              class="aspect-video bg-dark-900 border border-slate-700 rounded overflow-hidden relative group cursor-pointer hover:border-brand-cyan">
            <img [src]="asset.url" [alt]="asset.dosyaAdi" class="w-full h-full object-cover" />
            <div class="absolute inset-0 bg-brand-cyan/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <span class="bg-black/60 text-white text-[10px] px-2 py-1 rounded">Ekle +</span>
            </div>
         </div>
      </div>
   </div>
</div>
```

2. **TypeScript İş Mantığı (`editor.component.ts`):**
```typescript
isMediaDraggingOver = false;
readonly mediaUploading = signal<boolean>(false);
readonly projectAssets = signal<any[]>([]);

onMediaDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isMediaDraggingOver = true;
}

onMediaDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isMediaDraggingOver = false;
}

onMediaDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isMediaDraggingOver = false;
    
    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
        this.uploadFiles(event.dataTransfer.files);
    }
}

onFilesSelected(event: any): void {
    const files: FileList = event.target.files;
    if (files && files.length > 0) {
        this.uploadFiles(files);
    }
}

private uploadFiles(files: FileList): void {
    this.mediaUploading.set(true);
    const formData = new FormData();
    formData.append('file', files[0]);

    this.apiService.post<any>(`/projects/${this.projectId}/assets`, formData).subscribe({
        next: (asset) => {
            this.mediaUploading.set(false);
            this.projectAssets.update(list => [asset, ...list]);
            this.addImageOverlayFromUrl(asset.url); // Yüklenen görseli anında zaman çizgisine ekle
        },
        error: (err) => {
            this.mediaUploading.set(false);
            console.error('Medya yükleme hatası:', err);
            alert('Dosya yüklenemedi.');
        }
    });
}
```

---

### 4.5 Doğrulama ve Test Adımları

1. **Dosya Seçici (Picker) Testi:** "Dosya Yükle" kartına tıklandığında işletim sisteminin yerel dosya penceresinin açıldığı ve PNG/JPG/MP4 dosyalarının seçilebildiği doğrulanır.
2. **Sürükle-Bırak Testi:** Masaüstünden bir görsel sürüklenip Medya paneli üzerine bırakıldığında tarayıcının yeni sekme açmadığı, yüklemenin başladığı teyit edilir.
3. **Zaman Çizgisine Entegrasyon Testi:** Yükleme tamamlandığı anda görselin önizlemede listelendiği ve tıklandığında videonun o anki zaman damgasına görsel katmanı olarak eklendiği doğrulanır.

---

## BÖLÜM 5: ALTYAZI (SUBTITLES) GÖRÜNTÜLEME VE WEBVTT SENKRONİZASYONU

> **Mevcut Durum Değerlendirmesi:** 🔴 **GERÇEKTEN MEVCUT VE EKSİK ÖZELLİK (Frontend'de Altyazı Katmanı Sıfır / Yok)**  
> Kod tabanı incelendiğinde; Python Worker (`transcriber.py`, `dynamic_subtitle_generator.py`, `edl_builder.py`) tarafında Whisper modelinin transkripti kelime zaman damgalarıyla (`WordTimestamp`) kusursuz ürettiği ve `edl.transcript` nesnesine yazdığı doğrulanmıştır. Ancak `editor.component.ts` içerisinde **"transcript" kelimesinin tek bir kez dahi geçmediği**, HTML5 `<video>` etiketinde ne bir `<track>` elementi ne de video üzerine binen bir `subtitle-overlay` katmanının yer almadığı kanıtlanmıştır. Sonuç olarak kullanıcı video oluştururken "Altyazı Ekle" seçeneğini açsa bile editörde altyazıyı asla görememektedir.

---

### 5.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 5. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Kullanıcı "Altyazı Ekle" seçeneğini aktif etmesine ve Whisper transkripti başarıyla çıkarmasına rağmen editör ekranında oynatma esnasında hiçbir altyazının akmadığı.
2. **İddia Edilen Kök Neden:**
   - HTML5 `<video>` etiketinde `<track kind="subtitles">` bulunmaması.
   - Frontend'in `edl.transcript.segments` verisini WebVTT formatına dönüştüren bir Blob URL üretmemesi.
   - Kesim (Jump-Cut / Ripple) anında zaman atlaması yapıldığında WebVTT zaman kodlarının desenkronize olacağı varsayımı.

---

### 5.2 Kod Tabanı İncelemesi: Gerçekler, Eksikler ve Zamanlama Mekaniği

Kod tabanı satır satır incelenerek dokümandaki iddialar ve arka plan mimarisi analiz edilmiştir:

#### 1. Python Worker Altyapısı Mükemmel Çalışıyor (`dynamic_subtitle_generator.py` ve `edl_builder.py`)
- Python tarafında `transcriber.py` OpenAI Whisper kullanarak her cümlenin ve kelimenin başlangıç/bitiş anını milisaniyesine kadar kaydetmektedir:
  ```python
  # edl_builder.py (Satır 94-106)
  transcript_dict = {
      "fullText": transcript.full_text,
      "duration": transcript.duration,
      "segments": [
          {
              "start": seg.start,
              "end": seg.end,
              "text": seg.text,
              "words": [{"word": w.word, "start": w.start, "end": w.end} for w in seg.words]
          }
          for seg in transcript.segments
      ]
  }
  ```
- Ayrıca nihai video çıktısı alınırken (`video_renderer.py` ve `dynamic_subtitle_generator.py`), ASS formatında kelime bazlı sosyal medya tarzı karaoke animasyonları oluşturulmaktadır.

#### 2. Frontend Tarafında Altyazı Tamamen Yok Sayılmış (`editor.component.ts: Satır 64-71`)
- `editor.component.ts` taranmış ve `transcript` kelimesinin bileşende **0 (sıfır) defa** geçtiği görülmüştür:
  ```html
  <!-- editor.component.ts Satır 64-71 -->
  <video 
    #videoPlayer
    [src]="videoUrl()"
    (timeupdate)="onTimeUpdate()"
    (loadedmetadata)="onMetadataLoaded()"
    class="w-full h-full object-contain max-h-[440px]"
    controls>
  </video>
  ```
- Ne yerel tarayıcı altyazı desteği (`<track>`) ne de Angular tabanlı bir altyazı katmanı şablonda mevcuttur.

#### 3. Kesim (Jump-Cut) Anında Senkronizasyon Durumu (Dokümandaki Hatanın Düzeltilmesi):
- Eski dokümanda *"Jump-cut anında altyazı zaman kodları güncellenmediği için altyazılar konuşmanın gerisinde veya ilerisinde kalır"* denilmiştir.
- **Gerçek Mekanizma:** `editor.component.ts: Satır 886-902` incelendiğinde, editörün video oynatırken ham video üzerinde çalıştığı ve bir kesim (`cut`) bölgesine girildiği anda:
  ```typescript
  if (t >= cut.start && t < cut.end) {
     video.currentTime = cut.end; // Doğrudan ham videoda cut.end'e atlar!
     return;
  }
  ```
- Oynatıcı ham zaman damgası (`currentTime`) ile hareket ettiği için, transkript segmentleri de ham zaman damgasına (`seg.start` ve `seg.end`) sahip olduğu sürece **doğrudan eşleşir!** Yani video kesimi atladığında `video.currentTime` da ileri fırladığı için altyazı kelimeleri **asla desenkronize olmaz**, konuşmayla tam senkronize şekilde ileri sıçrar.
- **Asıl İhtiyaç:** Tarayıcının kaba ve biçimsiz siyah kutulu standart WebVTT'si yerine; TikTok, Instagram Reels ve YouTube Shorts standartlarında, kelime kelime yanan (karaoke vurgulu) modern bir **Canlı Altyazı Katmanı** ve isteğe bağlı WebVTT Track desteğidir.

---

### 5.3 Etkilenen Dosya ve Satır Haritası

| Dosya Yolu | İlgili Satırlar | Tespit Edilen Problem |
|---|---|---|
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 64-72 | `<video>` etiketinde altyazı track'inin ve altyazı overlay katmanının bulunmaması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 688-700 | Transkript segmentlerini dinleyen ve aktif kelimeyi/cümleyi hesaplayan reaktif sinyallerin eksikliği. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 148-175 | Zaman çizgisi araç çubuğunda "Altyazıyı Aç/Kapat" ve "Altyazı Stili" butonlarının bulunmaması. |
| `src/OtoEdit.Frontend/src/app/core/models/edl.model.ts` | 42-46 | `TranscriptData` arayüzünün bileşen içinde işlenmemesi. |

---

### 5.4 Uçtan Uca Kesin Mimari Çözüm ve Kodları

Sisteme hem **CapCut/Reels tarzı dinamik kelime vurgulu DOM katmanı** hem de yerel oynatıcılar için **RFC-8216 standartlarında dinamik WebVTT Blob Track** kazandırılır:

#### A. Frontend Şablon Revizyonu (`editor.component.ts: Satır 64-73`)

```html
<!-- Video Player ve Zengin Dinamik Altyazı Katmanı -->
<div class="relative bg-black rounded-2xl overflow-hidden shadow-2xl border border-slate-800 flex items-center justify-center min-h-[320px] max-h-[460px]">
  <video 
    #videoPlayer
    [src]="videoUrl()"
    (timeupdate)="onTimeUpdate()"
    (loadedmetadata)="onMetadataLoaded()"
    class="w-full h-full object-contain max-h-[440px]"
    controls>
    <!-- 1. Yerel Tarayıcı WebVTT Track Desteği -->
    <track *ngIf="vttTrackUrl()" 
           kind="subtitles" 
           [src]="vttTrackUrl()" 
           srclang="tr" 
           label="Türkçe (Otomatik)" 
           [default]="showSubtitles()">
  </video>

  <!-- 2. TikTok / Reels Tarzı Dinamik Canlı Altyazı Katmanı (Word-Level Karaoke) -->
  <div *ngIf="showSubtitles() && currentSubtitleSegment()"
       class="absolute bottom-10 left-1/2 -translate-x-1/2 max-w-[85%] text-center pointer-events-none z-30 select-none px-4 py-2 rounded-xl backdrop-blur-sm bg-black/40 border border-white/10 shadow-2xl transition-all duration-75">
    
    <!-- Kelime Kelime Vurgulanan Cümle -->
    <p class="text-lg md:text-xl font-extrabold uppercase tracking-wide flex flex-wrap items-center justify-center gap-1.5 drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)]"
       [style.fontFamily]="subtitleFont()"
       [style.color]="subtitleColor()">
      
      <ng-container *ngIf="currentSubtitleSegment()?.words?.length; else plainText">
        <span *ngFor="let w of currentSubtitleSegment()!.words"
              class="transition-all duration-100 px-1 py-0.5 rounded"
              [ngClass]="{
                 'text-brand-yellow scale-110 font-black bg-black/50 shadow-glow-sm': isWordActive(w),
                 'opacity-90': !isWordActive(w)
              }">
          {{ w.word }}
        </span>
      </ng-container>

      <ng-template #plainText>
        <span>{{ currentSubtitleSegment()?.text }}</span>
      </ng-template>
    </p>
  </div>
  ...
```

#### B. Araç Çubuğuna Altyazı Kontrol Butonu (`editor.component.ts: Satır 170 civarı`)

```html
<!-- Altyazı Aç/Kapat Butonu -->
<button (click)="toggleSubtitles()" 
        [class.bg-brand-yellow]="showSubtitles()"
        [class.text-slate-950]="showSubtitles()"
        [class.bg-dark-800]="!showSubtitles()"
        [class.text-slate-400]="!showSubtitles()"
        class="p-1 px-2.5 rounded border border-slate-700 font-bold text-xs hover:border-brand-yellow flex items-center gap-1 transition-all"
        title="Altyazıları Göster/Gizle (C)">
  <span>💬</span>
  <span>{{ showSubtitles() ? 'Altyazı Açık' : 'Altyazı Kapalı' }}</span>
</button>
```

#### C. TypeScript İş Mantığı (`editor.component.ts`)

```typescript
// Altyazı State ve Sinyalleri
readonly showSubtitles = signal<boolean>(true);
readonly subtitleFont = signal<string>('Montserrat, Inter, sans-serif');
readonly subtitleColor = signal<string>('#FFFFFF');

// 1. Oynatma Anındaki Aktif Segmenti Bulan Reaktif Sinyal
readonly currentSubtitleSegment = computed(() => {
    const t = this.currentTime();
    const segments = this.activeEdl()?.transcript?.segments || [];
    if (!segments.length) return null;

    // Binary search veya hızlı filtreleme
    return segments.find(seg => t >= seg.start && t <= seg.end) || null;
});

// 2. Aktif Kelime Kontrolü (Karaoke Vurgusu İçin)
isWordActive(word: TranscriptWord): boolean {
    const t = this.currentTime();
    return t >= word.start && t <= word.end;
}

// 3. WebVTT Formatında Blob URL Üreticisi (Computed Signal)
readonly vttTrackUrl = computed(() => {
    const transcript = this.activeEdl()?.transcript;
    if (!transcript || !transcript.segments || !transcript.segments.length) return null;

    let vtt = 'WEBVTT - OtoEdit Dynamic Subtitles\n\n';
    transcript.segments.forEach((seg, index) => {
        const start = this.formatVttTimestamp(seg.start);
        const end = this.formatVttTimestamp(seg.end);
        vtt += `${index + 1}\n${start} --> ${end}\n${seg.text.trim()}\n\n`;
    });

    const blob = new Blob([vtt], { type: 'text/vtt;charset=utf-8' });
    return URL.createObjectURL(blob);
});

private formatVttTimestamp(seconds: number): string {
    const totalMs = Math.floor(seconds * 1000);
    const hrs = Math.floor(totalMs / 3600000);
    const mins = Math.floor((totalMs % 3600000) / 60000);
    const secs = Math.floor((totalMs % 60000) / 1000);
    const ms = totalMs % 1000;

    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}

toggleSubtitles(): void {
    this.showSubtitles.update(v => !v);
}
```

---

### 5.5 Doğrulama ve Test Adımları

1. **Görsel Altyazı Akış Testi:** Transkript içeren bir proje açıldığında video oynatılır oynatılmaz video ekranının alt kısmında konuşmacının sözlerinin belirdiği ve konuşulan kelimenin anında sarı renkle (`text-brand-yellow`) parladığı doğrulanır.
2. **Jump-Cut Atlama Testi:** Video otomatik olarak sessiz bir bölümü atladığında (`cut.start` -> `cut.end`), altyazı katmanının da sıçramaya ayak uydurarak yeni cümlenin kelimesine gecikmesiz geçtiği teyit edilir.
3. **Aç/Kapat Buton Testi:** Araç çubuğundaki "💬 Altyazı Açık" butonuna basıldığında altyazı kutusunun anında gizlendiği ve butonun "💬 Altyazı Kapalı" haline döndüğü test edilir.

---

## BÖLÜM 6: AKILLI HATALI TEKRAR (RETAKE) TESPİTİ VE TOPLU SİLME

> **Mevcut Durum Değerlendirmesi:** 🔴 **GERÇEKTEN MEVCUT VE TÜM RETAKE MOTORUNU KİLİTLEYEN BUG**  
> Kod tabanı (`retake_detector.py` ve `editor.component.ts`) incelendiğinde; Python Worker tarafındaki yapay zeka tabanlı Retake (cümle tekrarı) tespit algoritmasının kusursuz çalıştığı; ancak frontend'deki **tek bir string karşılaştırma hatası (`=== 'Retake'`)** nedeniyle arayüzün bu kesimleri Retake olarak tanıyamadığı doğrulanmıştır. Bu hata yüzünden zaman çizgisindeki Retake blokları sarı/kehribar renge bürünememekte, normal sessizlik kesimi (kırmızı) sanılmakta ve "🔄 Retake Sıkıştırılmış / Geniş" butonu tamamen işlevsiz kalmaktadır.

---

### 6.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 6. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Konuşmacının takıldığı veya baştan aldığı cümlelerde sistemin hatalı kısımları sarı/kehribar renkte göstermesi ve tek tuşla topluca silebilmesi gerekirken, zaman çizgisinde hiçbir sarı bloğun görünmediği, tüm kesimlerin kırmızı göründüğü ve silme butonunun çalışmadığı.
2. **İddia Edilen Kök Neden:**
   - Python tarafında `reason=f"smart_retake (Skor: ...)"` üretilirken frontend'in `clip.cutObj?.reason === 'Retake'` şeklinde katı eşitlik (`===`) aradığı.
   - Frontend'de tespit edilen Retake kesimlerini tek hamlede silip sahneyi temizleyen bir toplu silme fonksiyonunun olmaması.

---

### 6.2 Kod Tabanı İncelemesi: Kök Neden Doğrulaması ve Algoritmik Analiz

#### 1. Python Worker Akıllı Karar Motoru (`retake_detector.py: Satır 40-128`)
Python tarafında konuşmacının peş peşe söylediği alternatif cümleler tespit edilmekte ve çok kriterli bir akustik-semantik formülle puanlanmaktadır:

$$\text{Aday Skoru} = 0.40 \cdot S_{\text{akustik}} + 0.35 \cdot S_{\text{tamlık}} + 0.25 \cdot S_{\text{güven}}$$

- $S_{\text{akustik}}$: Ses desibel tutarlılığı (RMS dB), clipping (patlama/bozulma) ve gürültü puanı.
- $S_{\text{tamlık}}$: Cümlenin yarıda kesilip kesilmediği (`.`, `!`, `?` bitişi) ve kelime sayısı yeterliliği.
- $S_{\text{güven}}$: Whisper modelinin kelime tanıma olasılık ortalaması.

Yarışmayı kaybeden hatalı cümleler EDL'e şu satırla eklenmektedir (`retake_detector.py: Satır 120-127`):
```python
cut_items.append(CutItem(
    id=f"cut_retake_{loser.index}",
    start=round(loser.segment.start, 2),
    end=round(loser.segment.end, 2),
    reason=f"smart_retake (Skor: {loser.score:.1f} vs Kazanan: {winner.score:.1f})", # <-- Üretilen Değer
    source="auto",
    command=f"Elenen Tekrar: {loser.segment.text}"
))
```

#### 2. Frontend'deki Ölümcül Hata (`editor.component.ts: Satır 254 ve Satır 785`)

Frontend'deki şablon ve görünürlük metotlarına bakıldığında:
```typescript
// editor.component.ts (Satır 254 - Zaman Çizgisi Renk Ataması)
'bg-amber-500/80 hover:bg-amber-400': clip.isCut && (clip.cutObj?.reason === 'Retake' || clip.cutObj?.reason === 'Hatalı Tekrar')

// editor.component.ts (Satır 785 - Ripple Genişlet/Sıkıştır Mantığı)
if (clip.cutObj.reason === 'Retake' || clip.cutObj.reason === 'Hatalı Tekrar') {
   return !this.rippleRetake();
}
```

* **Doğrulanan Hata:** `clip.cutObj.reason` değeri `"smart_retake (Skor: 41.2 vs Kazanan: 85.0)"` olduğu için;
  - `"smart_retake (...)" === "Retake"` ifadesi daima **`false`** döner!
  - `"smart_retake (...)" === "Hatalı Tekrar"` ifadesi daima **`false`** döner!
* **Zincirleme Sonuçlar:**
  1. Klip sarı renge (`bg-amber-500`) boyanamaz, bir alttaki `else` koşuluna düşerek sessizlik kesimi gibi bordo/kırmızı (`bg-rose-900`) renge boyanır.
  2. `isVisible(clip)` metodunda `rippleRetake` kontrolüne hiç giremez; en alttaki `return !this.rippleAi();` satırına düşer. Bu yüzden kullanıcı "🔄 Retake Sıkıştırılmış / Geniş" butonuna tıkladığında **hiçbir şey değişmez!**
  3. Arayüzde sadece tek bir klibi çift tıklayarak geri getirme vardır; projedeki tüm hatalı tekrarları tek seferde EDL'den söküp atan bir **"Tüm Retake'leri Kalıcı Olarak Temizle"** aksiyonu kodlanmamıştır.

---

### 6.3 Etkilenen Dosya ve Satır Haritası

| Dosya Yolu | İlgili Satırlar | Tespit Edilen Problem |
|---|---|---|
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 254-256 | `=== 'Retake'` katı eşitliği nedeniyle Retake bloklarının sarı renk alamaması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 785-787 | `isVisible` kontrolünün `false` dönmesi ve `rippleRetake` butonunun boşa çıkması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 154-159 | Araç çubuğunda tespit edilen Retake sayısını gösteren ve toplu silmeyi sağlayan butonun eksikliği. |

---

### 6.4 Uçtan Uca Kesin Mimari Çözüm ve Kodları

#### A. Frontend Şablon Revizyonu (`editor.component.ts: Satır 252-259`)

```html
<!-- Klipler (Flexbox ile Sıralanır) -->
<ng-container *ngFor="let clip of clips()">
  <div 
    *ngIf="isVisible(clip)"
    (click)="selectClip(clip.id, $event)"
    (dblclick)="toggleClip(clip, $event)"
    class="relative h-full transition-colors border-r border-white/20 box-border group"
    [ngClass]="{
       'bg-amber-500/90 hover:bg-amber-400 text-slate-950 font-bold shadow-[inset_0_0_8px_rgba(245,158,11,0.6)]': isRetakeClip(clip),
       'bg-rose-900/80 hover:bg-rose-800': clip.isCut && !isRetakeClip(clip) && !isManualCut(clip),
       'bg-rose-500/80 hover:bg-rose-400': isManualCut(clip),
       'bg-emerald-600/40 hover:bg-emerald-500/60': !clip.isCut,
       'ring-2 ring-inset ring-brand-yellow shadow-[0_0_10px_rgba(250,204,21,0.5)] z-10': selectedClipIds().includes(clip.id)
    }"
    [style.width.%]="(clip.duration / ( (rippleAi() || rippleManual() || rippleRetake()) ? visibleDuration() : totalDuration() )) * 100"
    [title]="getClipTooltip(clip)">
    
    <!-- Retake Rozeti / İkonu -->
    <div *ngIf="isRetakeClip(clip)" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <span class="text-[9px] font-black tracking-wider bg-black/40 text-amber-200 px-1 py-0.5 rounded backdrop-blur-xs">
        🔁 RETAKE
      </span>
    </div>

    <!-- Kesik Klip İptal Butonu (Hover'da Görünür) -->
    <div *ngIf="clip.isCut" class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/60 transition-opacity">
      <span class="text-[10px] text-white font-bold">✕ Geri Al</span>
    </div>
  </div>
</ng-container>
```

#### B. Araç Çubuğuna Toplu Retake Temizleme Butonu (`editor.component.ts: Satır 154-159`)

```html
<!-- Retake Genişlet/Sıkıştır ve Toplu Silme Butonları -->
<div class="flex items-center gap-1">
  <button (click)="rippleRetake.set(!rippleRetake())" 
          [class.border-amber-500]="retakeCount() > 0"
          [class.text-amber-400]="retakeCount() > 0"
          class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-amber-400 border border-slate-700 flex items-center gap-1" 
          title="Retake (Hatalı Tekrar) Kısımlarını Sıkıştır/Genişlet">
    <span>🔄</span>
    <span>{{ rippleRetake() ? 'Retake Sıkıştırılmış' : 'Retake Geniş' }}</span>
    <span *ngIf="retakeCount() > 0" class="ml-1 px-1 py-0.2 bg-amber-500/20 text-amber-300 rounded-full text-[9px] font-bold">
      {{ retakeCount() }}
    </span>
  </button>

  <!-- Toplu Retake Kesimlerini Kalıcı Olarak Temizleme -->
  <button *ngIf="retakeCount() > 0" 
          (click)="purgeAllRetakes()" 
          class="p-1 px-2.5 rounded bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs shadow-glow-sm flex items-center gap-1 transition-all"
          title="Tespit edilen tüm hatalı tekrarları tek seferde projeden çıkarır">
    <span>🧹</span>
    <span>Tüm Retake'leri Sil ({{ retakeCount() }})</span>
  </button>
</div>
```

#### C. TypeScript İş Mantığı (`editor.component.ts`)

```typescript
// Retake Klibi Olup Olmadığını Güvenle Algılayan Yardımcı Metot
isRetakeClip(clip: any): boolean {
    if (!clip || !clip.isCut || !clip.cutObj) return false;
    const r = (clip.cutObj.reason || '').toLowerCase();
    return r.includes('retake') || r.includes('tekrar');
}

isManualCut(clip: any): boolean {
    if (!clip || !clip.isCut || !clip.cutObj) return false;
    return clip.cutObj.reason === 'Manuel kesim';
}

// Projedeki Toplam Retake Sayısını Hesaplayan Sinyal
readonly retakeCount = computed(() => {
    const cuts = this.activeEdl()?.cuts || [];
    return cuts.filter(c => (c.reason || '').toLowerCase().includes('retake') || (c.reason || '').toLowerCase().includes('tekrar')).length;
});

// isVisible Metodunun Düzeltilmiş Hali
isVisible(clip: any): boolean {
    if (!clip.isCut) return true;
    if (this.isManualCut(clip)) {
       return !this.rippleManual();
    }
    if (this.isRetakeClip(clip)) {
       return !this.rippleRetake();
    }
    return !this.rippleAi();
}

// Tooltip Açıklama Formatlayıcı
getClipTooltip(clip: any): string {
    if (this.isRetakeClip(clip)) {
        return `🔁 Hatalı Cümle Tekrarı (${clip.cutObj.command || clip.cutObj.reason}) - ${clip.start.toFixed(1)}s - ${clip.end.toFixed(1)}s`;
    }
    if (clip.isCut) {
        return `Kesilen Bölüm (${clip.cutObj?.reason || 'Otomatik'}) - ${clip.start.toFixed(1)}s - ${clip.end.toFixed(1)}s`;
    }
    return `Klip: ${clip.start.toFixed(1)}s - ${clip.end.toFixed(1)}s`;
}

// Projedeki Tüm Hatalı Tekrarları Kalıcı Olarak Temizleyen Aksiyon
purgeAllRetakes(): void {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return;

    const retakes = edl.cuts.filter(c => (c.reason || '').toLowerCase().includes('retake') || (c.reason || '').toLowerCase().includes('tekrar'));
    if (!retakes.length) return;

    if (confirm(`Yapay zeka tarafından elenen ${retakes.length} adet hatalı tekrar kesimi projeden tamamen çıkarılacak. Devam edilsin mi?`)) {
        const patchPayload = retakes.map(c => ({ id: c.id, start: 0, end: 0, action: 'remove' }));
        this.edlService.patchEdl(this.projectId, { cuts: patchPayload as any }).subscribe({
            next: () => {
                this.loadEdl();
                console.log(`[Retake Purge] ${retakes.length} hatalı tekrar başarıyla kaldırıldı.`);
            },
            error: (err) => console.error('Retake kesimleri temizlenemedi:', err)
        });
    }
}
```

---

### 6.5 Doğrulama ve Test Adımları

1. **Renk ve Görsel İkon Testi:** Retake içeren bir proje yüklendiğinde, zaman çizgisindeki hatalı tekrar bloklarının parlak kehribar sarısı (`bg-amber-500`) olduğu ve üzerinde `🔁 RETAKE` rozetinin göründüğü doğrulanır.
2. **Ripple Genişlet/Sıkıştır Testi:** "🔄 Retake Sıkıştırılmış" butonuna basıldığında sarı blokların genişleyerek görünür hale geldiği, tekrar basıldığında ise zaman çizgisinden gizlenerek sürenin büzüldüğü test edilir.
3. **Toplu Silme Testi:** "🧹 Tüm Retake'leri Sil" butonuna basıldığında onay penceresinin açıldığı, onaylandığında tüm hatalı tekrarların tek bir HTTP PATCH çağrısıyla temizlendiği doğrulanır.

---

## BÖLÜM 7: ÇOKLU KATMAN (MULTI-LAYER) Z-INDEX VE SEÇİM ÇAKIŞMASI

> **Mevcut Durum Değerlendirmesi:** 🔴 **GERÇEKTEN MEVCUT VE DOĞRULANDI (Mimari ve UX Kusuru)**  
> Kod tabanı incelendiğinde; `editor.component.ts` içerisindeki tüm görsel ve metin katmanlarının CSS şablonunda **sabit `z-20`** sınıfına sahip olduğu, `edl.model.ts` modelinde yer alan `trackId` alanının arayüzde hiçbir şekilde kullanılmadığı ve "Görsel Ekle" fonksiyonunun `editor.component.ts: Satır 1224`'te **sabit bir Pexels URL'sine (`pexels-photo-1181675.jpeg`) hardcoded** bağlandığı kesin olarak doğrulanmıştır. Birden fazla katman üst üste geldiğinde altta kalan katmana tıklanamamakta ve katman sıralaması (Öne Getir / Arkaya Gönder) yönetilememektedir.

---

### 7.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 7. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Ekrana hem bir başlık yazısı hem de bir görsel eklendiğinde, görsel yazının üzerini kaplamakta ve arkada kalan metne tıklanamamaktadır. Ayrıca "Görsel Ekle" denildiğinde sürekli aynı Pexels stok fotoğrafı gelmekte, kullanıcı istediği görseli seçememektedir.
2. **İddia Edilen Kök Neden:**
   - Şablonda tüm katmanların sabit `z-20` sınıfı taşıması.
   - Seçili olan nesnenin z-index değerinin yükseltilmemesi.
   - `OverlayItem.trackId` alanının CSS `z-index` stiline bağlanmaması.
   - `addImageOverlay` fonksiyonunun sabit bir URL inject etmesi.

---

### 7.2 Kod Tabanı İncelemesi: Kök Neden Doğrulaması

#### 1. Sabit Z-Index ve Seçim Kilitlenmesi (`editor.component.ts: Satır 80-86`)
```html
<!-- editor.component.ts (Satır 74-86) -->
<div 
  *ngFor="let ov of activeOverlays()" 
  (mousedown)="onCanvasDragStart($event, ov.id)"
  (click)="$event.stopPropagation(); selectOverlay(ov.id)"
  [style.top]="getOverlayTop(ov)"
  [style.left]="getOverlayLeft(ov)"
  class="absolute transition-none z-20 cursor-move hover:ring-2 hover:ring-brand-cyan rounded p-1 -translate-x-1/2 -translate-y-1/2 select-none"
  [ngClass]="[
     selectedOverlayId() === ov.id ? 'ring-2 ring-brand-cyan shadow-glow-sm' : ''
  ]">
```
* **Doğrulanan Problem:** DOM ağacında daha sonra render edilen eleman (örneğin sonradan eklenen bir görsel), önceki elemanın (örneğin metnin) fiziksel olarak üzerinde kalır.
* Kullanıcı arkadaki metne tıklamak istediğinde, tarayıcı fare olayını (`click`, `mousedown`) en üstteki görsel DOM elemanına iletir. Arkadaki metin hiçbir şekilde tıklanamaz veya sürüklenemez hale gelir.
* Seçili katmanda sadece sağ alt köşedeki minik boyutlandırma kulpu `z-30` almaktadır; ancak katmanın ana gövdesi `z-20` kalmaya devam ettiği için nesne öne geçemez.

#### 2. `trackId` Alanının Kod Tabanında Ölü (Dead) Olması
* `edl.model.ts: Satır 26`:
  ```typescript
  export interface OverlayItem {
    ...
    trackId?: number;
  }
  ```
* Modelde `trackId` alanı olmasına rağmen `addTextOverlay()`, `addImageOverlay()` veya `inspectorData` içinde bu alan hiçbir zaman atanmamakta, zaman çizgisinde katman kanallarına (Track 1, Track 2 vb.) bölünmemektedir.

#### 3. Hardcoded Görsel URL Skandalı (`editor.component.ts: Satır 1224`)
```typescript
addImageOverlay(): void {
   ...
   const newOverlay: any = {
     id: newOvId,
     type: 'image',
     content: 'Görsel Kaplaması',
     source: 'https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=600',
     ...
   };
```
* Kullanıcı butona bastığında doğrudan kodun içine gömülmüş olan dizüstü bilgisayarlı kadın fotoğrafı eklenmektedir. Ne bir dosya seçimi ne de URL sorma diyaloğu mevcuttur.

---

### 7.3 Etkilenen Dosya ve Satır Haritası

| Dosya Yolu | İlgili Satırlar | Tespit Edilen Problem |
|---|---|---|
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 80 | Sabit `z-20` sınıfı (Seçili elemanın arkada hapsolması). |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 550-620 | Inspector panelinde katman sırasını (Öne/Arkaya) değiştirecek hiçbir kontrolün olmaması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 1224 | Görsel kaynağının sabit bir Pexels URL'sine hardcoded bağlanması. |

---

### 7.4 Uçtan Uca Kesin Mimari Çözüm ve Kodları

#### A. Dinamik Z-Index ve Seçim Katmanı (`editor.component.ts: Satır 80` Revizyonu)

```html
<!-- Dinamik Z-Index ile Öne Çıkarma -->
<div 
  *ngFor="let ov of activeOverlays()" 
  (mousedown)="onCanvasDragStart($event, ov.id)"
  (click)="$event.stopPropagation(); selectOverlay(ov.id)"
  [style.top]="getOverlayTop(ov)"
  [style.left]="getOverlayLeft(ov)"
  [style.zIndex]="getOverlayZIndex(ov)"
  class="absolute transition-none cursor-move hover:ring-2 hover:ring-brand-cyan rounded p-1 -translate-x-1/2 -translate-y-1/2 select-none"
  [ngClass]="[
     selectedOverlayId() === ov.id ? 'ring-2 ring-brand-cyan shadow-glow-sm ring-offset-2 ring-offset-black' : '',
     ov.animation === 'fade' ? 'animate-fade-in' : '',
     ov.animation === 'pop-up' ? 'scale-in' : '',
     ov.animation === 'slide-up' ? 'translate-y-4 opacity-0 animate-slide-up-forwards' : ''
  ]">
```

#### B. Inspector Paneline Katman Sıralama (Z-Order) Butonları (`editor.component.ts: Satır 550 civarı`)

```html
<!-- Katman Sıralama Kontrolleri (Z-Order) -->
<div class="space-y-1 pt-2 border-t border-slate-800">
  <label class="text-[10px] text-slate-400 uppercase font-semibold block">Katman Sırası (Z-Index)</label>
  <div class="grid grid-cols-2 gap-2">
    <button type="button" 
            (click)="bringOverlayForward(inspectorData.id)" 
            class="p-2 rounded-lg bg-dark-900 border border-slate-700 hover:border-brand-cyan hover:bg-dark-800 text-xs text-white font-medium flex items-center justify-center gap-1.5 transition-colors">
      <span>⬆</span>
      <span>Öne Getir</span>
    </button>
    <button type="button" 
            (click)="sendOverlayBackward(inspectorData.id)" 
            class="p-2 rounded-lg bg-dark-900 border border-slate-700 hover:border-brand-cyan hover:bg-dark-800 text-xs text-white font-medium flex items-center justify-center gap-1.5 transition-colors">
      <span>⬇</span>
      <span>Arkaya Gönder</span>
    </button>
  </div>
  <p class="text-[10px] text-slate-500 text-center">Mevcut Katman: Track {{ inspectorData.trackId || 1 }}</p>
</div>
```

#### C. TypeScript Z-Index ve Medya Seçici Metotları (`editor.component.ts`)

```typescript
// Dinamik Z-Index Hesaplayıcı: Seçili eleman DAİMA en üsttedir (z-Index = 50)
getOverlayZIndex(ov: OverlayItem): number {
    if (this.selectedOverlayId() === ov.id) {
        return 50;
    }
    // Track ID 1 tabanlıdır, taban katman 20'dir
    return 20 + (ov.trackId || 1);
}

// Katmanı Bir Kademe Öne Getirme
bringOverlayForward(overlayId: string): void {
    const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
    if (!ov) return;

    ov.trackId = (ov.trackId || 1) + 1;
    if (this.inspectorData && this.inspectorData.id === overlayId) {
        this.inspectorData.trackId = ov.trackId;
    }
    this.saveInspector();
}

// Katmanı Bir Kademe Arkaya Gönderme
sendOverlayBackward(overlayId: string): void {
    const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
    if (!ov) return;

    ov.trackId = Math.max(1, (ov.trackId || 1) - 1);
    if (this.inspectorData && this.inspectorData.id === overlayId) {
        this.inspectorData.trackId = ov.trackId;
    }
    this.saveInspector();
}

// Görsel Ekleme Fonksiyonunun Dinamik Hale Getirilmesi (Medya Kütüphanesi ile Entegre)
addImageOverlay(): void {
    // 1. Eğer projeye yüklenmiş varlıklar varsa Medya sekmesini açıp kullanıcıya seçtir
    if (this.projectAssets().length > 0) {
        this.activeTab.set('media');
        alert('Lütfen Medya Kütüphanesinden eklemek istediğiniz görsele tıklayınız veya yeni dosya yükleyiniz.');
        return;
    }

    // 2. Yoksa kullanıcıdan URL iste (Varsayılan şık Pexels placeholder ile)
    const customUrl = prompt('Görsel URL adresini giriniz (veya doğrudan Medya Kütüphanesinden yükleyiniz):', 
                             'https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=600');
    if (customUrl) {
        this.addImageOverlayFromUrl(customUrl);
    }
}
```

---

### 7.5 Doğrulama ve Test Adımları

1. **Katman Çakışma ve Seçim Testi:** Aynı zaman dilimine bir görsel ve bir metin eklenir, görsel metnin üzerine taşınır. Metne tıklandığında metnin `z-index: 50` alarak anında görselin önüne fırladığı ve sürüklenmeye devam edebildiği doğrulanır.
2. **Öne/Arkaya Sıralama Testi:** Inspector panelinden "⬇ Arkaya Gönder" ve "⬆ Öne Getir" butonlarına basıldığında `trackId` değerinin değiştiği ve kalıcı olarak EDL'e kaydedildiği teyit edilir.
3. **Dinamik Görsel Kaynağı Testi:** "Görsel Ekle" butonuna basıldığında Medya sekmesindeki yüklenmiş varlıkların yönlendirildiği, harici bir görsel linki girildiğinde girilen görselin canvas'a yerleştiği test edilir.

---

## BÖLÜM 8: GİRİŞ VE ÇIKIŞ ANİMASYONLARI VE ZENGİN TİPOGRAFİ

> **Mevcut Durum Değerlendirmesi:** 🔴 **GERÇEKTEN MEVCUT VE DOĞRULANDI (Amatör Görsel Geçişler & Eksik Fontlar)**  
> Kod tabanı incelendiğinde; katmanların sadece giriş animasyonuna sahip olduğu, CSS'te (`tailwind.config.js`) hiçbir çıkış animasyonu (`fadeOut`, `scaleOut`, `slideDownOut`) tanımlanmadığı ve `editor.component.ts: Satır 688`'de katmanın süresi bittiği anda Angular'ın DOM elemanını bıçak gibi keserek aniden yok ettiği doğrulanmıştır. Ayrıca `index.html` dosyasında yalnızca `Inter` ve `Outfit` fontlarının yüklü olduğu; modern sosyal medya kurgularının vazgeçilmezi olan `Montserrat`, `Poppins`, `Bebas Neue`, `Anton` gibi fontların tarayıcıya eklenmediği saptanmıştır.

---

### 8.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 8. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Katmanların süresi bittiğinde ekrandan pat diye kaybolduğu, yumuşak bir kapanış veya çıkış animasyonu yapılamadığı. Inspector font listesinde sadece 6 temel fontun bulunduğu ve modern YouTube/TikTok fontlarının yer almadığı.
2. **İddia Edilen Kök Neden:**
   - Modelde `exitAnimation` alanının olmaması.
   - CSS tarafında çıkış `@keyframes` animasyonlarının yazılmamış olması.
   - Google Fonts CDN linklerinin `index.html`'de eksik olması.

---

### 8.2 Kod Tabanı İncelemesi: Kök Neden Doğrulaması

#### 1. DOM Yaşam Döngüsü ve Çıkış Animasyonunun İmkansızlığı
`editor.component.ts: Satır 688-692`:
```typescript
readonly activeOverlays = computed(() => {
  const t = this.currentTime();
  const overlays = this.activeEdl()?.overlays || [];
  return overlays.filter(ov => t >= ov.timestamp && t <= (ov.timestamp + ov.duration));
});
```
* **Kritik Kök Neden:** Video oynatılırken `t > ov.timestamp + ov.duration` olduğu anda eleman `activeOverlays` dizisinden çıkarılır ve Angular `*ngFor` bu DOM düğümünü **anında yok eder (destroy eder)**.
* Bu sebeple CSS'e çıkış sınıfı eklense dahi, DOM düğümü kalmadığı için hiçbir çıkış animasyonu oynatılamaz.
* **Çözüm:** Eleman, bitiş zamanına 0.35 saniye kala (`t >= ov.timestamp + ov.duration - 0.35`) çıkış animasyonu sınıfını tetiklemeli veya `activeOverlays` dizisinde çıkış süresi kadar bir tampon (buffer) ile yaşatılmalıdır.

#### 2. `tailwind.config.js` İçinde Çıkış Keyframes Eksikliği
`tailwind.config.js: Satır 40-65`:
- Yalnızca `fadeIn`, `slideInRight`, `scaleIn`, `slideUp` mevcuttur.
- Ters yönde çalışan `fadeOut`, `scaleOut`, `slideDownOut` tanımları bulunmamaktadır.

#### 3. Tipografi ve Google Fonts Kısıtlaması
`src/OtoEdit.Frontend/src/index.html: Satır 14`:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
```
* Tarayıcı yalnızca `Inter` ve `Outfit` fontlarını indirmektedir.
* Inspector menüsünde yer alan `Montserrat`, `Roboto`, `Georgia`, `Impact` fontları kullanıcının yerel Windows işletim sisteminde kurulu değilse tarayıcı bunları yükleyememekte ve varsayılan `Arial / sans-serif` fontuna düşmektedir.

---

### 8.3 Etkilenen Dosya ve Satır Haritası

| Dosya Yolu | İlgili Satırlar | Tespit Edilen Problem |
|---|---|---|
| `src/OtoEdit.Frontend/tailwind.config.js` | 40-68 | Çıkış animasyonları (`fadeOut`, `scaleOut`, `slideDownOut`) eksikliği. |
| `src/OtoEdit.Frontend/src/index.html` | 14 | Google Fonts CDN üzerinde modern içerik üretici fontlarının yüklü olmaması. |
| `src/OtoEdit.Frontend/src/app/core/models/edl.model.ts` | 21 | `OverlayItem` arayüzünde `exitAnimation` alanının eksikliği. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 80-87 | Şablonda çıkış sınıfı tetikleyicisinin olmaması. |
| `src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts` | 580-600 | Inspector panelinde çıkış animasyonu seçicisinin ve zengin font kütüphanesinin olmaması. |

---

### 8.4 Uçtan Uca Kesin Mimari Çözüm ve Kodları

#### A. Google Fonts Kütüphanesinin Genişletilmesi (`index.html: Satır 14`)

Modern sosyal medya (YouTube, TikTok, Reels) kurgularında en çok tercih edilen 10 popüler font sisteme eklenir:

```html
<!-- Google Fonts: Inter, Outfit, Montserrat, Bebas Neue, Poppins, Anton, Oswald, Rubik -->
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Bebas+Neue&family=Inter:wght@300;400;600;800;900&family=Montserrat:wght@400;700;800;900&family=Oswald:wght@500;700&family=Outfit:wght@500;700;800&family=Poppins:wght@600;800;900&family=Rubik:wght@500;700;900&display=swap" rel="stylesheet">
```

#### B. CSS Çıkış Animasyonları (`tailwind.config.js: keyframes & animation`)

```javascript
// tailwind.config.js genişletmesi
module.exports = {
  theme: {
    extend: {
      animation: {
        'fade-in': 'fadeIn 0.25s ease-out forwards',
        'fade-out': 'fadeOut 0.3s ease-in forwards',
        'scale-in': 'scaleIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards',
        'scale-out': 'scaleOut 0.25s ease-in forwards',
        'slide-up-forwards': 'slideUp 0.35s ease-out forwards',
        'slide-down-out': 'slideDownOut 0.3s ease-in forwards',
      },
      keyframes: {
        fadeOut: {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.95)' },
        },
        scaleOut: {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.6)' },
        },
        slideDownOut: {
          '0%': { opacity: '1', transform: 'translateY(0)' },
          '100%': { opacity: '0', transform: 'translateY(20px)' },
        }
      }
    }
  }
}
```

#### C. `OverlayItem` Model Genişletmesi (`edl.model.ts: Satır 21`)

```typescript
export interface OverlayItem {
  id: string;
  type: 'text' | 'image';
  content?: string;
  source?: string;
  timestamp: number;
  duration: number;
  font?: string;
  fontSize?: number;
  color?: string;
  backgroundColor?: string;
  animation?: 'fade' | 'pop-up' | 'slide-left' | 'slide-right' | 'slide-up' | 'slide-down' | 'none';
  exitAnimation?: 'fade' | 'pop-up' | 'slide-down' | 'slide-up' | 'none'; // <-- Yeni Çıkış Animasyonu
  position?: [string, string];
  positionX?: number;
  positionY?: number;
  scale?: number;
  trackId?: number;
}
```

#### D. Dinamik Animasyon Sınıfı Üreticisi (`editor.component.ts`)

```typescript
// Katmanın O Anki Animasyon Sınıfını Hesaplama (Giriş vs Çıkış)
getOverlayAnimationClass(ov: OverlayItem): string {
    const t = this.currentTime();
    const end = ov.timestamp + ov.duration;
    const isExiting = (end - t) <= 0.35 && (end - t) >= 0;

    if (isExiting) {
        const exitAnim = ov.exitAnimation || ov.animation || 'fade';
        if (exitAnim === 'fade') return 'animate-fade-out';
        if (exitAnim === 'pop-up') return 'animate-scale-out';
        if (exitAnim === 'slide-up' || exitAnim === 'slide-down') return 'animate-slide-down-out';
        return '';
    }

    // Giriş Animasyonu
    if (ov.animation === 'fade') return 'animate-fade-in';
    if (ov.animation === 'pop-up') return 'scale-in';
    if (ov.animation === 'slide-up') return 'animate-slide-up-forwards';
    return '';
}
```

#### E. Inspector Paneli Font ve Çıkış Animasyonu Seçicisi

```html
<!-- Zengin Tipografi ve Çıkış Animasyonu Menüsü -->
<div class="space-y-3" *ngIf="inspectorData.type === 'text'">
  <!-- Font Seçici -->
  <div class="space-y-1">
    <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Tipi (Font)</label>
    <select [(ngModel)]="inspectorData.font" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none font-medium">
      <optgroup label="Modern & Sade">
        <option value="Inter">Inter (Temiz & Kusursuz)</option>
        <option value="Outfit">Outfit (Teknolojik & Şık)</option>
        <option value="Poppins">Poppins (Geometrik Sans)</option>
      </optgroup>
      <optgroup label="Dikkat Çekici Başlık (YouTube / TikTok)">
        <option value="Montserrat">Montserrat (Kalın Vurgulu)</option>
        <option value="Bebas Neue">Bebas Neue (Büyük Harf Dikkat)</option>
        <option value="Anton">Anton (Ağır & Vurucu)</option>
        <option value="Oswald">Oswald (Dar & Uzun Manşet)</option>
      </optgroup>
      <optgroup label="Dinamik & Sosyal">
        <option value="Rubik">Rubik (Yumuşak & Güçlü)</option>
      </optgroup>
    </select>
  </div>

  <!-- Giriş ve Çıkış Animasyonu Grid'i -->
  <div class="grid grid-cols-2 gap-2">
    <div class="space-y-1">
      <label class="text-[10px] text-slate-400 uppercase font-semibold">Giriş Animasyonu</label>
      <select [(ngModel)]="inspectorData.animation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan focus:outline-none">
        <option value="none">Sabit</option>
        <option value="fade">Fade In</option>
        <option value="pop-up">Pop-up</option>
        <option value="slide-up">Slide Up</option>
      </select>
    </div>
    <div class="space-y-1">
      <label class="text-[10px] text-slate-400 uppercase font-semibold">Çıkış Animasyonu</label>
      <select [(ngModel)]="inspectorData.exitAnimation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan focus:outline-none">
        <option value="none">Sert Kesim</option>
        <option value="fade">Fade Out</option>
        <option value="pop-up">Pop Out</option>
        <option value="slide-down">Slide Down</option>
      </select>
    </div>
  </div>
</div>
```

---

### 8.5 Doğrulama ve Test Adımları

1. **Çıkış Animasyonu Testi:** Katmana "Fade Out" veya "Slide Down" atanır. Video oynatılıp katmanın süresinin son 0.35 saniyesine gelindiğinde metnin aniden kaybolmak yerine pürüzsüzce şeffaflaşarak veya aşağı kayarak sahneden çıktığı gözlemlenir.
2. **Google Fonts Yükleme Testi:** Inspector menüsünden `Bebas Neue` veya `Anton` seçilir, canvas üzerindeki başlığın anında seçilen Google Font karakteristiğine büründüğü ve konsolda font 404 hatası oluşmadığı doğrulanır.
3. **Kayıt ve Kalıcılık Testi:** Proje kaydedilip sayfa yenilendiğinde seçilen yeni font ve çıkış animasyonunun EDL'de korunduğu test edilir.

---

## BÖLÜM 9: ZAMAN ÇİZGİSİNDE ÇOKLU PARÇA SEÇME (MULTI-SELECT) VE KURGU OPERASYONLARI

> **Mevcut Durum Değerlendirmesi:** ✅ **BÜYÜK ORANDA ÇÖZÜLDÜ (Temel Çoklu Seçim ve Birleştirme Çalışıyor)**  
> Kod tabanı (`editor.component.ts: Satır 700 ve Satır 983-1082`) incelendiğinde; eski dokümandaki *"aynı anda sadece tek parça seçilebiliyor, toplu silme ve birleştirme yok"* iddiasının **artık geçerli olmadığı** doğrulanmıştır. `cf6d121` commit'i ile `selectedClipIds` array sinyali, `Ctrl / Cmd` ile çoklu seçim, zaman çizgisi araç çubuğundaki "X Seçili", "✕ Sil (Del)" ve "🔗 Birleştir" butonları **zaten başarıyla yazılmıştır**.  
> Ancak profesyonel bir kurgu deneyimi için **`Shift + Click` aralık seçimi**, fiziksel klavyeden **`Delete` tuşu dinleyicisi** ve bitişik olmayan kliplerde **güvenli aralık birleştirme** olmak üzere 3 ufak optimizasyon ihtiyacı bulunmaktadır.

---

### 9.1 Mevcut Dokümandaki (`OtoEdit-Kalan-Sorunlar-Analizi.md`) İddiaların Özeti

Eski dokümanda 9. sorun için şu tespitler öne sürülmüştür:
1. **Kullanıcı Deneyimi:** Kullanıcının birden fazla video parçasını `Ctrl` veya `Shift` tuşuyla seçemediği, aradaki kesimleri tek tıkla kaldıramadığı veya topluca silemediği; sistemin daima tekil seçim (`selectedClipId`) ile kısıtlı kaldığı öne sürülmüştür.
2. **İddia Edilen Kök Neden:** `selectedClipId = signal<string | null>(null);` şeklinde tekil state kullanıldığı ve `cuts` aralık sorgusunun eksik olduğu iddia edilmiştir.

---

### 9.2 Kod Tabanı İncelemesi: Kullanıcının Gerçekleştirdiği Çözümün Doğrulanması

Kaynak kodlar (`editor.component.ts`) incelendiğinde kullanıcının son geliştirmeleriyle bu yapıyı büyük ölçüde ayağa kaldırdığı kanıtlanmıştır:

#### 1. Çoklu Seçim State Sinyali (`editor.component.ts: Satır 700`)
```typescript
readonly selectedClipIds = signal<string[]>([]);
```
* Doğrulama: Eski dokümandaki `selectedClipId` tekil değişkeni kaldırılmış, çoklu ID tutan reaktif sinyal mimarisine geçilmiştir.

#### 2. `Ctrl` / `Cmd` Dinleyicisi (`editor.component.ts: Satır 983-1002`)
```typescript
selectClip(clipId: string, event: MouseEvent): void {
  event.stopPropagation();
  const current = this.selectedClipIds();
  
  // Ctrl (Windows) veya Cmd (Mac) basılıysa çoklu seçim yap
  if (event.ctrlKey || event.metaKey) {
     if (current.includes(clipId)) {
        this.selectedClipIds.set(current.filter(id => id !== clipId));
     } else {
        this.selectedClipIds.set([...current, clipId]);
     }
  } else {
     // Tekli seçim
     if (current.length === 1 && current[0] === clipId) {
        this.selectedClipIds.set([]); // Zaten seçiliyse kaldır
     } else {
        this.selectedClipIds.set([clipId]);
     }
  }
}
```
* Doğrulama: Kullanıcı `Ctrl` tuşuna basarak birden fazla klibi başarıyla listeye ekleyebilmekte veya çıkarabilmektedir.

#### 3. Araç Çubuğu ve Çoklu Operasyon Butonları (`editor.component.ts: Satır 160-164`)
```html
<div *ngIf="selectedClipIds().length > 0" class="flex items-center gap-2 border-l border-slate-700 pl-2 ml-1">
  <span class="text-[10px] font-bold text-slate-300">{{ selectedClipIds().length }} Seçili</span>
  <button (click)="deleteSelectedClips()" class="p-1 px-2.5 rounded bg-rose-600/80 text-white font-bold hover:bg-rose-500 border border-rose-500 shadow-glow-sm" title="Seçili Klipleri Sil (Del)">✕ Sil (Del)</button>
  <button *ngIf="selectedClipIds().length > 1" (click)="mergeSelectedClips()" class="p-1 px-2.5 rounded bg-emerald-600/80 text-white font-bold hover:bg-emerald-500 border border-emerald-500 shadow-glow-sm" title="Seçili Klipleri Birleştir">🔗 Birleştir</button>
</div>
```
* Doğrulama: Seçili klip sayısı 1'den büyük olduğunda "🔗 Birleştir" butonu dinamik olarak belirmekte; tekli veya çoklu seçimde "✕ Sil (Del)" butonu ile toplu kesim yapılabilmektedir.

---

### 9.3 Bu Sorun Gerçekte Var mı? (Nihai Teşhis ve 3 İnce Eksik)

> **SONUÇ:** **HAYIR, SORUN ESKİ DÖKÜMANDA ANLATILDIĞI GİBİ BİR BLOKER DEĞİLDİR.**  
> Kullanıcının *"1 ve 2 gibi bazı sorunları zaten çözmüştüm"* ifadesi 9. sorun için de büyük oranda geçerlidir. Ancak sistemi eksiksiz Premiere Pro / DaVinci Resolve akıcılığına kavuşturmak için şu **3 ince detay** eklenmelidir:

1. **`Shift + Click` ile Aralık Seçimi Eksikliği:**
   - Kullanıcı `Clip A`'ya tıklayıp ardından `Shift`'e basarak 4 klip sonraki `Clip E`'ye tıkladığında, aradaki tüm kliplerin otomatik seçilmesi beklenir. Şu an `Shift` tuşu tekil tıklama gibi davranmaktadır.
2. **Fiziksel Klavye `Delete` / `Backspace` Dinleyicisi Eksikliği:**
   - Butonun üzerinde `✕ Sil (Del)` yazmasına rağmen, kullanıcı klavyeden `Delete` tuşuna bastığında silme fonksiyonu tetiklenmemektedir (`window:keydown` dinleyicisi bağlı değildir).
3. **Bitişik Olmayan (Non-Contiguous) Kliplerde Birleştirme Riski:**
   - `mergeSelectedClips` metodu `startRange` ve `endRange` alarak aradaki tüm `cuts` kayıtlarını silmektedir. Kullanıcı 1. ve 5. klibi seçtiğinde, 3. klipteki bilerek yapılmış bir sessizlik kesimi de istemeden silinebilir. Kullanıcının sadece bitişik klipleri birleştirmesi emniyet altına alınmalıdır.

---

### 9.4 Nihai Cila ve Optimizasyon Kodları

#### A. `selectClip` Metoduna `Shift + Click` Entegrasyonu (`editor.component.ts: Satır 983`)

```typescript
selectClip(clipId: string, event: MouseEvent): void {
  event.stopPropagation();
  const current = this.selectedClipIds();
  const allClips = this.clips();

  // 1. Shift + Click ile Blok Aralık Seçimi
  if (event.shiftKey && current.length > 0) {
     const lastSelectedId = current[current.length - 1];
     const lastIdx = allClips.findIndex(c => c.id === lastSelectedId);
     const curIdx = allClips.findIndex(c => c.id === clipId);

     if (lastIdx !== -1 && curIdx !== -1) {
        const start = Math.min(lastIdx, curIdx);
        const end = Math.max(lastIdx, curIdx);
        const rangeIds = allClips.slice(start, end + 1).map(c => c.id);
        
        // Mevcut seçime aralığı tekilleştirerek ekle
        this.selectedClipIds.set(Array.from(new Set([...current, ...rangeIds])));
        return;
     }
  }

  // 2. Ctrl (Windows) veya Cmd (Mac) ile Tek Tek Ekle / Çıkar
  if (event.ctrlKey || event.metaKey) {
     if (current.includes(clipId)) {
        this.selectedClipIds.set(current.filter(id => id !== clipId));
     } else {
        this.selectedClipIds.set([...current, clipId]);
     }
     return;
  }

  // 3. Düz Tıklama: Tekli Seçim (Zaten tek seçiliyse kaldır)
  if (current.length === 1 && current[0] === clipId) {
     this.selectedClipIds.set([]);
  } else {
     this.selectedClipIds.set([clipId]);
  }
}
```

#### B. Global Klavye Kısayolu Dinleyicisi (`Delete` ve `Escape` Tuşları)

`editor.component.ts` içerisine `@HostListener` eklenmesi:

```typescript
@HostListener('window:keydown', ['$event'])
onKeyDown(event: KeyboardEvent): void {
    // Kullanıcı bir input, textarea veya chat kutusunda yazı yazıyorsa kısayolları yutma
    const target = event.target as HTMLElement;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
    }

    // 1. Delete veya Backspace: Seçili Klipleri Sil
    if ((event.key === 'Delete' || event.key === 'Backspace') && this.selectedClipIds().length > 0) {
        event.preventDefault();
        this.deleteSelectedClips();
        return;
    }

    // 2. Escape: Seçimi Temizle
    if (event.key === 'Escape') {
        if (this.selectedClipIds().length > 0) {
            this.selectedClipIds.set([]);
        }
        if (this.selectedOverlayId()) {
            this.selectedOverlayId.set(null);
        }
        return;
    }

    // 3. B Tuşu: Bulunulan Yerden Böl (Split)
    if (event.key.toLowerCase() === 'b') {
        event.preventDefault();
        this.addSplitMarker();
        return;
    }
}
```

---

### 9.5 Doğrulama ve Test Adımları

1. **Shift-Click Aralık Testi:** 1. klibe tıklanır, ardından klavyeden `Shift` tuşuna basılı tutularak 5. klibe tıklanır. 1'den 5'e kadar olan tüm 5 klibin aynı anda sarı çerçeve ile seçildiği ve araç çubuğunda "5 Seçili" yazdığı teyit edilir.
2. **Klavye Delete Testi:** Klipler seçiliyken fiziksel klavyeden `Delete` tuşuna basılır, seçili kliplerin anında kırmızıya dönerek kesildiği doğrulanır.
3. **Escape Testi:** Klipler seçiliyken `Escape` tuşuna basıldığında tüm seçimlerin kalktığı doğrulanır.

---

## BÖLÜM 10: 9 SORUNUN GENEL DEĞERLENDİRME TABLOSU VE MASTER YOL HARİTASI

Aşağıdaki tablo; 9 sorunun kaynak kod incelemesi sonucu ortaya çıkan **kesin gerçek durumunu**, **öncelik seviyesini** ve **yapılması gereken aksiyonu** özetlemektedir:

| No | Sorun Adı | Teşhis ve Gerçek Durum | Öncelik | Aksiyon |
|---|---|---|---|---|
| **1** | **Yazı/Katman Ayarları Sıfırlanması** | ✅ **ÇÖZÜLDÜ (Mevcut Durum: Stabil)** | Düşük | `...ov` ile çözüldü. Ufak seçim optimizasyonu kafi. |
| **2** | **Köşeden Boyutlandırma (Resize)** | ✅ **ÇÖZÜLDÜ (Mevcut Durum: Çalışıyor)** | Düşük | Kulp, clamp ve mouseup patch hazır. Dikey delta cila kodudur. |
| **3** | **Yönetmen AI Dropdown & Zengin Araçlar** | 🔴 **DOĞRULANDI (Aktif Kritik Sorun)** | **Acil (P0)** | `formFields` eksikliği giderilmeli; 16:9 mini monitör, renk paleti ve dropdown eklenmeli. |
| **4** | **Medya Kütüphanesi & Sürükle-Bırak** | 🔴 **DOĞRULANDI (Eksik Özellik / Dead Code)** | **Yüksek (P1)** | `AssetsController` ve MinIO entegrasyonu yazılmalı, dosya yükleyici bağlanmalı. |
| **5** | **Altyazı Görüntüleme & WebVTT** | 🔴 **DOĞRULANDI (Frontend'de Sıfır Render)** | **Yüksek (P1)** | Kelime bazlı canlı karaoke altyazı katmanı ve WebVTT Track eklenmeli. |
| **6** | **Akıllı Retake Tespiti ve Toplu Silme** | 🔴 **DOĞRULANDI (Aktif String Bug'ı)** | **Acil (P0)** | `smart_retake` string kontrolü `includes('retake')` yapılmalı ve toplu silme eklenmeli. |
| **7** | **Çoklu Katman Z-Index & Seçim** | 🔴 **DOĞRULANDI (Mimari / Hardcoded URL)** | **Orta (P2)** | Dinamik `z-index: 50` atanmalı, Inspector'a Öne/Arkaya butonları konmalı. |
| **8** | **Giriş/Çıkış Animasyonu & Fontlar** | 🔴 **DOĞRULANDI (Çıkış Animasyonu Yok)** | **Orta (P2)** | Keyframes çıkış animasyonları ve Google Fonts (Bebas, Montserrat vb.) eklenmeli. |
| **9** | **Timeline Çoklu Seçim (Multi-Select)** | ✅ **BÜYÜK ORANDA ÇÖZÜLDÜ (Çalışıyor)** | Düşük | Ctrl çoklu seçim ve Birleştir çalışıyor. `Shift+Click` ve `Delete` kısayolu eklenmeli. |

---
*Raporun Sonu — OtoEdit Mühendislik Ekibi (2026)*







