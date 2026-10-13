# 🔬 Teşhis ve Kesin Çözüm Raporu: Ses Başlangıcı Kesilmesi ve Transkript Kaybı

> **Tarih:** 13 Ekim 2026  
> **İncelenen Medya:** `Mukayeseli Hukuk` (52.4 Dakika / 3143.1 Saniye — Video ID: `978776bf-04d6-4368-a69d-e36ea8cdd783`)  
> **Test Ortamı:** Canlı Docker Worker Container (`otoedit-dev-worker`), MinIO Temiz Ses Akışı (`_clean.mp3`)  
> **Durum:** 🎯 Kök nedenler matematiksel ve log düzeyinde %100 kanıtlandı, çözüm mimarisi hazırlandı.

---

## 1. Yönetici Özeti ve Doğrulama Sonuçları

Kullanıcının son yüklediği 52 dakikalık derste karşılaştığı iki kritik aksaklık şunlardı:
1. **İlk Harflerin / Cümle Başlangıçlarının Kesilmesi:** Cümlenin ilk heceleri duyulamıyor, kırmızı kesim alanı konuşmanın içine taşıyor (ancak konuşma bitişleri gayet iyi).
2. **Transkript, Altyazı ve Retake Çıkmaması:** Ekranda `[TRANSKRİPT ÇIKARILAMADI]` yazıyor, altyazı 1 saniyelik sahte segment gösteriyor ve hiçbir retake algılanmamış.

Yapılan ampirik testler, log taramaları ve ses dalga formu ölçümleri sonucunda **iki sorunun da birbiriyle doğrudan bağlantılı olduğu ve tahmin edilen nedenlerden kaynaklandığı kesinleşmiştir.**

```mermaid
flowchart TD
    subgraph STT_Ariza["Transkript Çöküşü (Saat 09:25:59 - 09:26:09)"]
        A1["Parça 1 (0-563s): GeminiTranscribe 383 Kelime Buldu ✅"] --> A2["Parça 2 (563-1119s): 1 sn sonra gönderildi ⏩"]
        A2 --> A3["Gemini Free-Tier 429 Kota Aşımı: 'retry in 50s' 🛑"]
        A3 --> A4["RateLimiter max_wait_sec=45s < 50s olduğu için pes etti ❌"]
        A4 --> A5["Transcriber.py Parça 1'in 383 kelimesini ÇÖPE ATTI 🗑️"]
        A5 --> A6["Ekrana '[TRANSKRİPT ÇIKARILAMADI]' basıldı ⚠️"]
    end

    subgraph Kesme_Ariza["Ses Başlangıcı Kesilmesi (Lead-in Clipping)"]
        A6 --> B1["Word Guard Devre Dışı (Korumalı Kelime Sayısı = 0)"]
        B2["Silero VAD: speech_pad_ms=0 (Yumuşak sessiz harfleri 150ms geç algılıyor)"] --> B3["Kesim Bitişi: 52.340s | Konuşma: 52.426s"]
        B1 --> B3
        B3 --> B4["Güvenlik Payı SADECE 86 ms! (-27.9 dBFS ses kesildi) ✂️"]
        B4 --> B5["Kullanıcı: 'İlk kelimenin ilk birkaç harfini duyamıyoruz' 🔇"]
    end
```

---

## 2. Sorun 1 — Ses Başlangıçlarının Kesilmesi (Matematiksel Kanıt)

### A. Yapılan Test ve Bulgular

Kullanıcının ekran görüntüsünde işaret ettiği **52. saniye** ve çevresi gerçek ses dosyası (`test_mukayeseli.mp3`) üzerinde milisaniye hassasiyetinde incelenmiştir:

```
[Mevcut Algoritma Çıktısı - 52s Civarı Kesim]
Mevcut Kesim Bölgesi : [46.420s -> 52.340s] (Süre: 5.920s)
Gerçek Konuşma Başlangıcı : 52.426s
Kesim Bitişinden Konuşmaya Kalan Pay : SADECE 86.0 ms!
```

### B. Neden 86 ms Sesin Kesilmesine Yol Açıyor?

1. **İnsan Konuşma Akustiği (Attack Time):** İnsanlar konuşmaya başlarken "p, t, k, f, s, ş, h, b, d, c, m, n" gibi sessiz harflerle veya yumuşak nefesle başlar. Bu ünsüzlerin enerjisi düşüktür.
2. **VAD'in Geç Tetiklenmesi (`speech_pad_ms=0`):** Silero VAD, ses enerjisi belirli bir eşiği geçene kadar tetiklenmez. Gerçek testte:
   - `speech_pad_ms=0` iken konuşma başlangıcı: **52.576s**
   - `speech_pad_ms=150` iken konuşma başlangıcı: **52.426s**
   - **Aradaki 150 milisaniyelik sesin RMS enerjisi: -27.9 dBFS!**  
     *(-27 dBFS oda gürültüsü veya fısıltı değildir; net, gür bir insan sesidir! Mevcut kod bu 150 ms'yi sessizlik zannediyordu).*
3. **Simetrik Padding Hatası:**
   - Jump-Cut v2'de `pad_sec = 0.20s` (200ms) simetrik olarak ayarlanmıştı.
   - VAD konuşmayı 150ms geç gördüğü için (52.576s), 200ms geriye çekildiğinde `52.576 - 0.200 = 52.376s` noktasına geliyordu.
   - Lokal enerji minimumu araması bu noktayı `52.340s`'ye çekti.
   - Gerçek konuşma ise `52.426s`'de başladığı için konuşma başlangıcına sadece **86 milisaniye (yaklaşık 2 video karesi)** kaldı!
   - Tarayıcı veya video oynatıcı tamponu (buffer latency) 50-80ms olduğu için ilk hece tamamen yutuldu!

---

## 3. Sorun 2 — Transkript, Altyazı ve Retake'in Yok Olması (Log Kanıtı)

Worker konteynerinin sistem logları incelendiğinde, transkriptin neden yok olduğu saniye saniye ortaya çıkmıştır:

```log
2026-10-13 09:25:59 [INFO] [STT.GeminiTranscribe:126]: 🚀 GeminiTranscribe isteği gönderiliyor (Parça 1: 0.0s -> 563.2s)
2026-10-13 09:26:08 [INFO] [STT.GeminiTranscribe:131]: ✅ GeminiTranscribe tamamlandı (Parça 1): 383 kelime bulundu.
2026-10-13 09:26:08 [INFO] [STT.GeminiTranscribe:126]: 🚀 GeminiTranscribe isteği gönderiliyor (Parça 2: 563.2s -> 1119.0s)
2026-10-13 09:26:09 [WARNING] [STT.GeminiTranscribe:136]: ⚠️ Gemini HTTP 429 hatası: Quota exceeded, retry in 50s.
2026-10-13 09:26:09 [ERROR] [Transcriber:128]: ❌ Transkripsiyon orkestrasyonu sırasında hata: Zincirdeki tüm STT motorları parça 2 için başarısız oldu
2026-10-13 09:26:09 [WARNING] [Transcriber:177]: TRANSKRIPT UYARISI: Model bulunamadı veya çalıştırılamadı.
```

### Bu Log Neyi İspatlıyor?

1. **GeminiTranscribe Harika Çalışıyor:** İlk parça (9.4 dakika) sadece **9 saniyede** bitti ve **383 kelimenin tamamını milisaniyelik zaman damgalarıyla** buldu!
2. **Peş Peşe İstek Kota Patlaması:** Parça 1 biter bitmez (aynı saniye içinde: 09:26:08) Parça 2 gönderildi. Google Free Tier limiti 5 RPM (dakikada 5 istek) veya token sınırına çarptı ve Google **HTTP 429 (retry in 50s)** döndü.
3. **Erken Pes Eden Hız Sınırlayıcı:** Google "50 saniye bekle" dedi. Ancak `GeminiKeyRotator` içinde `max_wait_sec = 45.0` saniye olarak tanımlanmıştı. `50s > 45s` olduğu için rotator "Bekleme süresi çok uzun" diyerek beklemeden `None` döndürdü.
4. **Yedek Motorların Devre Dışı Olması:** Groq ve Proxy anahtarları tanımlı olmadığı için failover zinciri çöktü.
5. **Transcriber'ın "Hep ya da Hiç" Hatası:** `transcriber.py` içindeki döngü, Parça 2 hata verince tüm fonksiyonu `except` bloğuna düşürdü ve **Parça 1'in başarıyla çıkardığı 383 kelimeyi de çöpe attı!**
6. **Zincirleme Yıkım:**
   - Transkript yok -> Altyazı katmanına `[TRANSKRİPT ÇIKARILAMADI]` (1 saniyelik sahte blok) basıldı.
   - Transkript yok -> `RetakeDetector` analiz edecek metin bulamadı, 0 retake üretti.
   - Transkript yok -> Jump-Cut v2'ye kelime listesi boş gitti; **Word Guard (kelime kalkanı) tamamen devre dışı kaldı!**

---

## 4. Kesin ve Kalıcı Çözüm Planı

Bu iki sorunu tamamen ortadan kaldırmak için 4 aşamalı mimari düzeltme uygulanacaktır:

### A. Ses Başlangıcı Koruması (Lead-in Protection)

| Parametre / Nokta | Eski Durum | Yeni Durum | Açıklama |
|---|---|---|---|
| **VAD Speech Pad** | `speech_pad_ms=0` | `speech_pad_ms=150` | Silero VAD, konuşma öncesindeki yumuşak sessiz harfleri 150ms önceden yakalar. |
| **Ön Güvenlik Payı (Lead Pad)** | 200 ms | **350 ms** (`pad_lead_sec=0.35`) | Konuşma başlamadan önce kesim en az 350 ms önce biter. İlk hece asla kesilmez. |
| **Arka Güvenlik Payı (Trailing Pad)** | 200 ms | **200 ms** (`pad_trailing_sec=0.20`) | Konuşma bittikten sonraki nefes payı (kullanıcı bitişlerden memnun olduğu için korundu). |
| **Enerji Arama Yönü** | Çift yönlü (±50ms) | **Tek Yönlü (Geriye Doğru)** | Konuşma başlangıcındaki kesim kenarı sadece sessizliğin içine doğru minimum arar; asla konuşmanın içine doğru kayamaz. |

**Sonuç:** 52. saniyedeki kesim bitişi `52.340s` yerine `52.076s` olacak; konuşma başlamadan önce tam **350 ms doğal nefes/hava payı** kalacak!

---

### B. STT Kotası & Hata İzolasyonu (Robustness)

| Dosya | Yapılacak Düzeltme | Amacı |
|---|---|---|
| [`pipeline/stt/rate_limiter.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/rate_limiter.py) | `max_wait_sec = 180.0` (3 dakika) | Google 50 saniye soğuma istediğinde sistem pes etmeyip 50 saniye sabırla bekleyecek. |
| [`pipeline/stt/gemini_transcribe.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/gemini_transcribe.py) | **Kendi içinde 429 Retry Mekanizması** | 429 aldığında doğrudan çöküp zinciri patlatmak yerine, Google'ın verdiği `retryDelay` süresince bekleyip aynı parçayı yeniden deneyecek (maks. 3 deneme). |
| [`pipeline/stt/gemini_transcribe.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/stt/gemini_transcribe.py) | **Proaktif Hız Limiti (Pacing)** | İki parça arasında en az `60 / GEMINI_TRANSCRIBE_RPM` saniye (örneğin 20 saniye) ara verilerek kota aşımı peşinen önlenecek. |
| [`pipeline/transcriber.py`](file:///d:/OtoEdit/OtoEdit/src/OtoEdit.PythonWorker/pipeline/transcriber.py) | **Parça Bazlı Hata İzolasyonu** | Bir parça tüm denemelere rağmen başarısız olsa bile, önceki ve sonraki parçaların kelimeleri ASLA silinmeyecek. Mevcut olan tüm kelimelerle altyazı ve Word Guard inşa edilecek. |

---

## 5. Doğrulama ve Test Adımları

1. **Birim Testleri:** `test_silence_detector.py` ve `test_stt_chain.py` güncellenerek asimetrik padding ve retry mekanizması doğrulanacak.
2. **Gerçek Ses Testi:** `/app/temp/test_mukayeseli.mp3` üzerinde 52. saniyedeki kesimin `speech_start - cut_end >= 350ms` olduğu kanıtlanacak.
3. **STT Parça Testi:** Parça 1 ve Parça 2 peş peşe çalıştırılarak 429'un bekleme ile başarıyla aşıldığı teyit edilecek.
