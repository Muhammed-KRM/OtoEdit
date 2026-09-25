# Altyazı ve Transkript Sorunları — Doğrulanmış Kök Neden Analizi ve Düzeltme Planı

> Aşağıdaki her tespit, kodun ilgili satırı ve hata loglarıyla birebir doğrulanmıştır.

---

## ✅ DOĞRULANMIŞ TESPİT 1: Ses İyileştirme 32 kbps MP3 Sorunu

**Kanıt:**
- [`audio_enhancer.py:46`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/audio_enhancer.py#L46): `cleaned_segment.export(output_mp3, format="mp3", bitrate="32k")`
- [`audio_enhancer.py:54`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/audio_enhancer.py#L54): Fallback yolunda da: `-b:a 32k`
- Her iki yolda da ses **32 kbps MP3** olarak sıkıştırılıyor.

**Etki:** 32 kbps MP3, 4 kHz üzerindeki tüm ses harmoniklerini ve sürtünmeli ünsüzleri (s, ş, z, c, ç) yok eder. 22 dakikalık bir konuşma videosunda normalde ~2500-3000 kelime beklenir ancak Whisper sadece **374 kelime** (videonun %12-15'i) çıkarmıştır. Bu, sesin Whisper için büyük ölçüde anlaşılmaz hale geldiğinin doğrudan kanıtıdır.

**Düzeltme:** Çıktı formatını `format="wav"` (kayıpsız) veya en az `bitrate="192k"` MP3 olarak değiştir. `prop_decrease` değerini `0.8`→`0.6`'ya çek.

---

## ✅ DOĞRULANMIŞ TESPİT 2: faster-whisper Halüsinasyon Döngüsü Parametreleri Eksik

**Kanıt:**
- [`transcriber.py:104-108`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py#L104-L108):
  ```python
  segments_iter, info = local_model.transcribe(
      audio_path,
      language="tr",
      word_timestamps=True
  )
  ```
  `condition_on_previous_text`, `vad_filter`, `repetition_penalty` parametreleri **HİÇBİRİ YOK**.

**Log kanıtı (halüsinasyon döngüsü):**
- `hata1.txt` satır 5351-5395: `'birinci öncül,'` ifadesi retake loglarında art arda 35+ kez geçiyor
- `hata1.txt:5396`: `Akıllı Retake analizi bitti: Toplam 33 hatalı tekrar budandı.`
- Whisper aynı cümleyi tekrar tekrar üretmiş, RetakeDetector da bunları birbiriyle eşleştirip 33'ünü videondan silmiş.

**Düzeltme:** `condition_on_previous_text=False`, `vad_filter=True`, `repetition_penalty=1.15` parametrelerini ekle.

---

## ✅ DOĞRULANMIŞ TESPİT 3: `_extract_audio_peaks` MP3'te Her Çalıştırmada Çöküyor

**Kanıt (kod):**
- [`analysis_consumer.py:164`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L164): `audio_peaks = self._extract_audio_peaks(clean_audio_path)` — Bu `clean_audio_path` daima `_clean.mp3` dosyasıdır (Tespit 1'den).
- [`analysis_consumer.py:194`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py#L194): `sample_rate, data = wavfile.read(audio_path)` — `scipy.io.wavfile` SADECE WAV formatını okuyabilir.
- Hata alındığında satır 207-208: `logger.error(...)` → `return []` — Boş dizi dönüyor.

**Log kanıtı (7 farklı çalıştırmada aynı hata):**
```
hata1.txt:3895: Waveform çıkarılamadı: File format b'ID3\x04' not understood. Only 'RIFF', 'RIFX', and 'RF64' supported.
hata1.txt:4316: Waveform çıkarılamadı: File format b'ID3\x04' not understood...
hata1.txt:5457: Waveform çıkarılamadı: File format b'ID3\x04' not understood...
```
Toplam **7 kez** aynı hata. `audio_peaks` **HER ZAMAN** boş liste (`[]`) olarak EDL'e gönderiliyor.

**Düzeltme:** `pydub.AudioSegment` ile MP3'i okuyup numpy array'e çevirerek peak hesapla (veya öncesinde `ffmpeg -i input.mp3 -ac 1 -ar 16000 temp.wav` ile WAV'a dönüştür).

---

## ✅ DOĞRULANMIŞ TESPİT 4: Sayfa Yenilenince Waveform Düşmesinin Nedeni

**Kanıt zinciri (A→B→C→D):**

**(A)** Backend `audioPeaks = []` gönderir (Tespit 3).

**(B)** Frontend `loadEdl()` içinde backend'den gelen `audioPeaks`'i okumaz bile! Hiçbir yerde `res.edl.audioPeaks` atanmamış:
- [`editor.component.ts:1929-1960`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L1929-L1960): `loadEdl()` fonksiyonu — `audioPeaks` kelimesi sadece satır 1955'te `!this.audioPeaks()` şeklinde kontrol amacıyla var.

**(C)** `audioPeaks` boş olduğu için [`editor.component.ts:1955-1956`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L1955-L1956):
```typescript
if (!this.audioPeaks()) {
  this.generateFallbackWaveform();
}
```
Fallback tetiklenir.

**(D)** [`editor.component.ts:2013-2038`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L2013-L2038):
```typescript
const segments = edl?.transcript?.segments || []; // Transkript segmentleri
...
const isSpeech = segments.some(s => time >= s.start && time <= s.end);
...
if (isSpeech) {
  peaks.push(0.35 + ...); // Yüksek dalga
} else {
  peaks.push(0.12 + Math.random() * 0.1); // DÜŞÜK dalga (0.12-0.22)
}
```
Transkript'in olmadığı yerlerde ses dalgası minimum (`0.12`) çiziliyor.

**(E)** 3-4 saniye sonra [`loadAudioWaveform`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts#L1964-L2011) Web Audio API ile gerçek videoyu decode edip gerçek ses dalgasını basıyor → dalga aniden yükseliyor.

**Sonuç:** Kullanıcının gözlemlediği "sayfa yenileyince altyazısız yerlerde ses dalgası düşük, sonra düzeliyor" anomalisi **%100** bu fallback zincirinden kaynaklanıyor.

---

## ✅ DOĞRULANMIŞ TESPİT 5: Chunking'te Virgül/İki Nokta Tek Kelimelik Segment Üretiyor

**Kanıt:**
- [`transcriber.py:191`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py#L191): `is_terminal = w.word.strip().endswith(('.', '!', '?', ',', ':'))`
- [`transcriber.py:194`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py#L194): `if ... or is_terminal:` → Tek kelime bile olsa virgül görürse hemen ayrı segment oluşturuyor.

**Log kanıtı:**
- `hata1.txt:5295`: `Retake'te atlandı: #1 'bir,'` — 1 kelimelik segment
- `hata1.txt:5296`: `Retake'te atlandı: #6 'Hatta,'` — 1 kelimelik segment
- `hata1.txt:5302`: `Retake'te atlandı: #25 'günlük'` — 1 kelimelik segment

**Düzeltme:** Virgül ve iki noktayı terminal sayma kuralından çıkar. Sadece `.`, `!`, `?` gerçek cümle sonlarında ve kelime sayısı ≥ 3 olduğunda bölme yap.

---

## ✅ DOĞRULANMIŞ TESPİT 6: OPENAI_API_KEY Placeholder

**Kanıt:**
- [`.env:35`](file:///d:/OtoEdit/OtoEdit/.env#L35): `OPENAI_API_KEY=sk-...` — Placeholder değeri
- Loglarda toplam **14 kez** 401 hatası fırlatılmış: `Error code: 401 - invalid_api_key`
- Her analiz çalıştırmasında gereksiz yere OpenAI API'ye istek atılıp hata alınıyor, vakit kaybediliyor.

**Düzeltme:** `transcriber.py`'de API key'in geçerli olup olmadığını kontrol et (`len(self.api_key) > 10 and not self.api_key.startswith("sk-...")`). Placeholder ise doğrudan yerel motora geç.

---

## Proposed Changes

### Python Worker

#### [MODIFY] [audio_enhancer.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/audio_enhancer.py)
- `bitrate="32k"` → `format="wav"` veya `bitrate="192k"` olarak değiştir (her iki yolda: satır 46 ve satır 54)
- `prop_decrease=0.8` → `0.6` (konuşma frekanslarını boğmasın)

#### [MODIFY] [transcriber.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py)
- API key placeholder kontrolü ekle (satır 34 civarı)
- `faster-whisper` çağrısına `condition_on_previous_text=False`, `vad_filter=True`, `repetition_penalty=1.15` ekle (satır 104-108)
- `_chunk_segments`: Virgül ve iki noktayı terminal olmaktan çıkar, minimum 3 kelime kuralı ekle (satır 191-194)

#### [MODIFY] [analysis_consumer.py](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/consumers/analysis_consumer.py)
- `_extract_audio_peaks`: `wavfile.read` yerine `pydub.AudioSegment` veya ffmpeg ile WAV'a çevirip okuyan sağlam bir yol kullan (satır 192-208)

### Frontend

#### [MODIFY] [editor.component.ts](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.Frontend/src/app/features/editor/editor.component.ts)
- `loadEdl()` içinde `res.edl.audioPeaks` varsa `this.audioPeaks.set(res.edl.audioPeaks)` ile direkt set et (satır 1943 civarına ekle)
- Fallback waveform'u iyileştir: konuşma olmayan ama kesilmemiş yerlere de 0.25-0.40 arası değer ver
- **Detaylı konsol loglama sistemi ekle** (daha önce scrubbing için yapılan renkli log sistemiyle aynı mantık):
  - `[SUBTITLE:ACTIVE]`: Video oynarken aktif altyazı her değiştiğinde
  - `[SUBTITLE:TRACK_RENDER]`: Timeline'daki altyazı kanalı render edildiğinde
  - `[SUBTITLE:EDIT]`: Altyazı düzenlendiğinde
  - `[WAVEFORM:EDL_PEAKS]`: EDL'den gerçek peaks geldiğinde
  - `[WAVEFORM:FALLBACK]`: Geçici dalga üretildiğinde
  - `[WAVEFORM:DECODE]`: Web Audio API ile gerçek ses çözüldüğünde
  - `[TRANSCRIPT:SEEK]`: Transkript panelinden bir satıra tıklandığında

---

## Verification Plan

### Otomatik Testler
- `docker restart otoedit-dev-worker && docker logs --tail 50 otoedit-dev-worker` ile worker'ın hatasız başladığını doğrula

### Manuel Doğrulama
1. F12 konsolunda `[SUBTITLE:...]`, `[WAVEFORM:...]` loglarının renkli olarak aktığını doğrula
2. Sayfa yenilendiğinde altyazısız yerlerde ses dalgasının artık düşmediğini doğrula
3. Yeni bir video yükleyerek transkript kalitesinin iyileştiğini gözle
