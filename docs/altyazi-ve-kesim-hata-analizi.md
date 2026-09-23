# OtoEdit: Oto-Kurgu ve Altyazı Mimarisinde Tespit Edilen Kritik Hataların (Bugs) Kök Neden Analizi (Deep Debugging Raporu)

Kullanıcının gönderdiği test çıktıları, UI ekran görüntüleri ve timeline davranışları üzerinde yapılan derinlemesine "reverse-engineering" (tersine mühendislik) analizi sonucunda, üç ana bileşende (Sessizlik Algılayıcı, Retake Algılayıcı ve Altyazı Render Motoru) mantıksal işlem (logic) hataları tespit edilmiştir. Bu doküman, her bir fonksiyonun girdi/çıktılarını, verinin nereye kaydedilip hangi fonksiyon tarafından kullanıldığını ve sistemin **tam olarak nerede patladığını** yüzlerce satırlık inceleme ile özetlemektedir.

---

## BÖLÜM 1: Auto-Jumpcut (Sessizlik Kesimleri) Neden Kelimeleri Yutuyor?

### Veri Akışı ve Mimari İncelemesi:
1. **Girdi:** Kullanıcı videoyu yükler. Arka planda `silence_detector.py` dosyasına sesin bir kopyası (`audio_path`) gönderilir.
2. **İşlem (Process):** 
   - `SilenceDetector.detect()` fonksiyonu çalışır.
   - Pydub kütüphanesinden `detect_silence(audio, min_silence_len=..., silence_thresh=...)` çağrılır.
   - Bu fonksiyon, videodaki sessiz aralıkları bir liste olarak döner: `[(start_ms, end_ms), (start_ms2, end_ms2)]`.
3. **Sorunlu Kod Bloğu (Patlayan Yer):**
   ```python
   min_keep_ms = self.min_keep_duration_sec * 1000.0  # 350 milisaniye
   for current in silent_ranges_ms:
       if not merged_silences:
           merged_silences.append(current)
       else:
           prev = merged_silences[-1]
           gap = current[0] - prev[1]  # <- BUG BURADA! GAP SESİN KENDİSİDİR!
           if gap < min_keep_ms:
               # Kısa sesleri gürültü sanıp sessizlikleri BİRLEŞTİRİR
               merged_silences[-1] = (prev[0], current[1])
   ```
4. **Sorunun Tam Kaynağı (The Bug):** İki sessizlik alanı (örneğin 1.0s - 2.0s ve 2.2s - 3.0s) arasındaki boşluk (`gap`) aslında kişinin **konuştuğu sesli alandır** (2.0s ile 2.2s arası = 200 milisaniyelik bir kelime, örn: "Ve", "Ne", "Ama"). Kod, `gap < 350ms` ise bu konuşmayı "gürültü" (noise) veya nefes sanarak iki sessizliği tek bir devasa sessizliğe dönüştürür (1.0s - 3.0s).
5. **Kayıt Aşaması:** Birleştirilen bu devasa sessizlik alanı `CutItem` nesnesine (reason="silence") dönüştürülür ve `edl.json` dosyasına kaydedilir.
6. **Frontend'in Çuvallaması:** `editor.component.ts` dosyası içindeki `loadEdl()` fonksiyonu bu kesimi okur. Timeline'da (Kırmızı `SESSİZLİK` kutusu) o 2 saniyeyi tamamen kesilmiş gösterir. Fakat ses dalgası (waveform) ham sesten çizildiği için, UI üzerinde kesilmiş kırmızı alanın tam ortasında devasa bir ses peak'i görünür. (Bu, gönderdiğiniz 2. ekran görüntüsündeki hatadır).
7. **Çözüm Planı:** `silence_detector.py` dosyasındaki `gap < min_keep_ms` şartı ya tamamen kaldırılmalı ya da sadece 50ms altı (çıtırtı/klik sesleri) için uygulanmalıdır. Böylece 350ms altındaki tek kelimelik "kısa" tepkiler sessizliğe kurban gitmeyecektir.

---

## BÖLÜM 2: Retake (Hatalı Tekrar) Algılayıcısı Neden Sessizlikleri Kesiyor?

### Veri Akışı ve Mimari İncelemesi:
1. **Girdi:** Ses dosyası (`audio_path`) ve Whisper'ın ürettiği metinler (`TranscriptResult`) `retake_detector.py` dosyasına girer.
2. **İşlem (Process):** `detect_retakes()` fonksiyonu, Whisper'dan gelen metin parçalarını kronolojik olarak gezer. Aynı veya benzer metinleri (örneğin iki kez "merhaba") gruplar halinde birleştirir.
3. **Sorunlu Kod Bloğu (Patlayan Yer):**
   ```python
   sim = self.calculate_similarity(segments[i].text, segments[j].text)
   ```
   Ve ardından akustik puanlama yapılır:
   ```python
   acoustics = self.scorer.score_audio_segment(...)
   # Sadece en yüksek puanlı olan kazanır, kaybeden retake olarak kesilir.
   ```
4. **Sorunun Tam Kaynağı (The Bug):** Whisper yapay zekası (özellikle eski sürümleri veya gürültülü ortamlarda), sesin tamamen **sessiz** olduğu anlarda (klima sesi vs.) halüsinasyon görüp ekrana "İzlediğiniz için teşekkürler", "abone olmayı unutmayın" gibi rastgele cümleler basar. 
   - Whisper bu halüsinasyon metnini `TranscriptResult` içine kaydeder.
   - `retake_detector.py`, bu metni okur ve "Aaa, burada bir konuşma var" sanır. 
   - İki halüsinasyon birbiriyle eşleşirse veya bir kelime "başa sar" gibi bir meta-komuta benzerse, Retake motoru bu **tamamen sessiz** olan yeri bir kurgu hatası sanarak keser.
   - Oysa akustik skorda `current_rms_db` değerinin o an "tamamen sessizlik" (örneğin -60 dB) olduğunu kontrol etseydi, Whisper'ın halüsinasyon gördüğünü anlayıp o metni çöpe atabilirdi. Fakat sadece göreceli karşılaştırma yaptığı için sessizlikleri `TEKRAR` (Retake) olarak işaretliyor (Gönderdiğiniz 3. ekran görüntüsündeki hata).
5. **Kayıt ve Tüketim:** Halüsinasyon görülen yer `cut_items` listesine eklenir, `edl.json`'a yazılır, Frontend timeline bunu `TEKRAR` olarak kırmızıya boyar (Fakat altında ses dalgası hiç yoktur).
6. **Çözüm Planı:** `retake_detector.py` içine "Absolute Silence Threshold" kuralı eklenecektir. Eğer bir parçanın RMS (ses yüksekliği) seviyesi -45dB'den küçükse, Whisper ne demiş olursa olsun bu metin bir halüsinasyon sayılacak ve Retake algoritmasından çıkarılacaktır.

---

## BÖLÜM 3: Altyazılar Neden Devasa Büyüklükte, Yanlış Yerde ve Düzenlenemiyor?

### Veri Akışı ve Mimari İncelemesi:
1. **Girdi:** Ses dosyası `transcriber.py` dosyasına yollanır. OpenAI Whisper veya `faster-whisper` çalıştırılır.
2. **İşlem:** Whisper sesi kelime kelime (`WordTimestamp`) çözer. Ancak kelimeleri birleştirirken kendi iç yapısına göre "Segment" (cümle) oluşturur. Bir segment, konuşmacı nefes alıp duraksayana kadar veya nokta koyulana kadar devam edebilir. Bazen bu 10-15 saniyelik, 20-30 kelimelik devasa bir metin olur.
3. **Kayıt Aşaması:** `TranscriptSegment` (içinde uzun metinle) `edl.json` içindeki `overlays` (altyazı olmayan) veya analiz sonuçlarındaki `transcript` nesnesine gömülür.
4. **Sorunlu Kod Bloğu (Frontend - Patlayan Yerler):**
   - **Render 1 (Video Üstü):** `editor.component.ts` içerisindeki `currentSubtitleSegment()` fonksiyonu o anki saniyeyi alıp, `seg.start <= t && t <= seg.end` olan segmenti bulur. Eğer segment 10 saniye uzunluğundaysa, `editor.component.html` satır 456'daki `TikTok / Reels Karaoke Altyazı` dive girilir ve 30 kelime birden ekranın ortasına basılır! Kullanıcının "Altyazılar çok uzun ve ekranı kaplıyor" şikayeti doğrudan bu segment mimarisinin bölünmemiş (chunklanmamış) olmasından kaynaklanmaktadır.
   - **Render 2 (Timeline):** `getVisibleSubtitleSegments()` fonksiyonu bu uzun segmentleri `Altyazı Kanalı` içine çizer. Ancak segment uzun olduğu için, iki uzun segment birbirine çok yakınsa CSS `left` ve `width` değerleri yüzünden ekranda birbirlerinin üstüne binerler veya timeline UI'sını patlatırlar ("altyazı katmanlara koyarken birbirine giriyor").
   - **Render 3 (Düzenleme):** `editor.component.html` içerisinde altyazılar sadece okuma amaçlı (Read-Only) `{{ seg.text }}` şeklinde basılmıştır. Kullanıcının müdahale edip kelime hatasını düzeltmesi için hiçbir `(dblclick)` event'i veya `<input>` / `<textarea>` DOM manipülasyonu yazılmamıştır. ("Düzenlenemiyor olmaları").
5. **Çözüm Planı (3 Aşamalı):**
   - **Backend Chunking:** `transcriber.py` içinde Whisper'dan dönen upuzun kelime listesi (words), algoritmik olarak **maksimum 5 kelime veya 2 saniye** olacak şekilde kısa kısa "mikro-segmentlere" (chunk) bölünecektir.
   - **Frontend UI Bugfix:** Kısa segmentler sayesinde video üstündeki metin ekrana sığacak, timeline'daki kutucuklar birbiriyle çakışmayacaktır. Ayrıca timeline render kısmında milisaniyelik `seg.end` sınır kaymaları (boundary fix) uygulanacaktır.
   - **Frontend Düzenlenebilirlik:** `editor.component.ts` içine bir `onSubtitleEdit(seg)` fonksiyonu yazılacak. Altyazı kutusuna çift tıklandığında bir Modal (Dialog) veya satır içi Input açılacak, metin düzeltilip onaylandığında bu `edlService.patchEdl` üzerinden backend'e geri gönderilerek güncellenecektir.

---

### ÖZET (Sonuç)
Sizin gözlemlediğiniz hatalar hiçbir şekilde rastgele veya "bozuk çalışıyor" durumu değil; tamamen kod mimarisindeki sert eşik değerlerinin (0.35s sessizlik birleştirme limiti), yapay zeka halüsinasyonlarına karşı savunmasızlığın (RMS kontrol eksikliği) ve veri gösterim katmanındaki esneklik eksikliğinin (Chunking yapılmaması ve Read-Only UI) matematiksel sonuçlarıdır. 
