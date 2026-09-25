# OtoEdit Katman, Timeline ve UI Hata Analiz Raporu

**Tarih:** 24 Eylül 2026
**Uygulama:** OtoEdit (Frontend - editor.component.ts)

Bu doküman, OtoEdit arayüzünde tespit edilen görsel kaymalar, zaman çizelgesi tutarsızlıkları, altyazı düzenleme sınırları ve API kaynaklı erişilebilirlik sorunlarının teknik analizini ve uygulanan kodlama düzeyindeki çözümlerini içerir.

---

## 1. Katmanların (Görsel ve Yazı) Yanlış Konumda Belirip Sonradan Düzelmesi (Zıplama Sorunu)

### Sorun Açıklaması
Kullanıcı ekrana yeni bir metin veya görsel katmanı eklediğinde, katman doğru (X,Y) koordinatlarında belirmiyor; ekranın köşesine veya başka bir yerine kayıyor ve tam 1 saniye (veya animasyon süresi) sonra zıplayarak doğru konuma yerleşiyordu. Ayrıca "geliş-gidiş" (fade, pop-up) animasyonları hiç çalışmıyordu.

### Kök Neden (Root Cause) Analizi
Bu hatanın kök nedeni **CSS Transform çakışmasıdır**.
1. Ekranda katmanları tam olarak merkezlemek (`center`) için `editor.component.ts` şablonunda şu sınıf kullanılmıştır: `-translate-x-1/2 -translate-y-1/2`. Bu Tailwind sınıfı arka planda `transform: translate(-50%, -50%)` uygular.
2. Katmana giriş animasyonu verildiğinde (`animate-fade-in` vs.), Tailwind CSS `keyframes` devreye girer. Örneğin `fadeIn` animasyonu `transform: translateY(0)` kuralını içerir.
3. Animasyon tetiklendiğinde `transform: translateY(0)` kuralı, katmanın sahip olduğu `transform: translate(-50%, -50%)` kuralını **tamamen ezer**. Element bir anda merkez özelliğini kaybeder ve kayar. Animasyon bittiğinde (0.5 saniye sonra) animasyon sınıfı kalkar ve merkezleme sınıfı tekrar aktif olur. Bu da katmanın aniden eski yerine "zıplamasına" neden olur.
4. Ayrıca `getOverlayAnimationClass` metodunda döndürülen `animate-pop-up` sınıfı Tailwind konfigürasyonunda tanımlı değildi (yerine `scale-in` tanımlıydı).

### Uygulanan Çözüm
- `editor.component.ts` içerisindeki katman döngüsünde (`*ngFor="let ov of activeOverlays()"`) DOM yapısı yeniden düzenlendi.
- Ana `<div>`'e sadece pozisyon (`left`, `top`) ve merkezleme (`translate`) sınıfları bırakıldı.
- Hemen içine **animasyonlar için ayrılmış yepyeni bir `<div>`** sarıcısı eklendi.
- Böylece merkezleme (`translate`) ve animasyon (`keyframes transform`) işlemleri farklı HTML elementlerinde gerçekleştiği için çakışma ortadan kalktı. Katman zıplama sorunu tamamen çözüldü ve animasyonlar aktif hale getirildi.
- TypeScript içindeki hatalı CSS sınıf isimleri Tailwind ayarlarıyla birebir eşleştirildi.

---

## 2. Timeline'da (Zaman Çubuğu) Kısa Süreli Katmanların Küçülememesi

### Sorun Açıklaması
Kullanıcı zaman çizelgesinde bir katmanın süresini (duration) kısalttığında, o katmanı temsil eden kutucuğun eni (width) belirli bir orandan sonra daha fazla küçülmüyor. Süre 0.5 saniye olsa bile kutu ekranda 3-4 saniyelikmiş gibi devasa kalıyordu.

### Kök Neden (Root Cause) Analizi
Timeline render edilirken HTML sınıfı olarak `min-w-[70px]` (Minimum Genişlik = 70 piksel) kullanılmıştı. Sistem arka planda kutunun genişliğini `%1` veya `10px` olarak hesaplasa dahi, CSS `min-width` kuralı devreye girip o kutunun 70 pikselden daha dar olmasını engelliyordu.
Ayrıca, `getOverlayStyle` fonksiyonunda katmanların genişliği (yüzdelik olarak) hesaplanırken `Math.max(1.0, (duration / totalDur) * 100)` kuralı kullanılmıştı. Bu durum, süresi ne kadar kısa olursa olsun, 1300 saniyelik devasa bir projede bir katmanın asgari `%1` (yaklaşık 13 saniye) genişlikte gösterilmesine neden oluyordu. Bu yüzden resimdeki 11.75 ve 9.75 saniyelik iki katman tamamen aynı (%1) genişlikte görünüyordu.

### Uygulanan Çözüm
- Timeline katman HTML yapısındaki `min-w-[70px]` sınıfı `min-w-[4px]` olarak değiştirildi.
- `editor.component.ts` dosyasındaki asgari `%1.0` genişlik kısıtlaması (limit) `%0.1` seviyesine çekildi.
- Artık çok kısa süreli animasyonlar veya katmanlar, uzun metrajlı videolarda dahi zaman çubuğunda tam olarak kendi süresine karşılık gelen fiziksel genişliği alabilecek.

---

## 3. Altyazıların (Transcript) Düzenleme Sınırları

### Sorun Açıklaması
Kullanıcı altyazılar üzerinde ekleme/çıkarma, konum değiştirme veya renk/font gibi görsel düzenlemeleri yapamıyor, sağ panelde (Inspector) bunlar görünmüyor. Yalnızca kelime içeriğini çift tıklayıp değiştirebiliyor.

### Mimari Analiz ve Nedenleri
OtoEdit'in veri mimarisi iki ayrı yapı üzerine kuruludur:
1. **OverlayItem (Metin ve Görsel Katmanları):** Bağımsız koordinatları (`positionX`, `positionY`), renkleri, boyutları olan ve sağ panelden anlık kontrol edilebilen objelerdir.
2. **TranscriptSegment (Altyazılar):** Whisper yapay zekasından saniyelik zaman damgalarıyla topluca gelen, arka planda tek bir düzende gösterilen ve ekranda sadece o anki zamanla eşleştiğinde beliren kelime öbekleridir.

Sağ panel (Inspector), performansı korumak adına yalnızca `OverlayItem`'ları yönetecek şekilde tasarlanmıştır. Altyazıların rengini veya fontunu tek tek (her kelime için ayrı ayrı) değiştirmek, devasa video projelerinde veri yönetimini felç edeceği için bu özellik kapatılmıştır.

### Çözüm & Kullanım Önerisi
Bir videodaki **sadece belirli bir altyazı kelimesine veya cümlesine** odaklanıp, onu büyütmek, kırmızı yapmak veya ekranda başka bir yere taşımak istiyorsanız:
1. Zaman çubuğundan o altyazı kelimesini çift tıklayarak silin.
2. Sisteme sağ üst köşeden yepyeni bir **"+ Katman Ekle (Metin)"** işlemi yapın.
3. Eklenen bu Metin (Overlay) sağ panel üzerinden dilediğiniz gibi renklendirilebilir, büyütülebilir ve sürüklenebilir.

---

## 4. Yapay Zeka Komut Sistemindeki "503 - Unavailable" Hatası

### Sorun Açıklaması
Yapay Zeka Sohbet Asistanına bir komut gönderildiğinde sistem çöküyor ve `{"error": {"code": 503, "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.", "status": "UNAVAILABLE"}}` şeklinde bir hata veriyor.

### Neden ve Çözüm
Bu hata doğrudan **Google/OpenAI sunucularından** (LLM API Sağlayıcısından) dönen evrensel bir HTTP 503 hatasıdır. 
- **OtoEdit ile İlgisi:** Kodlarınızda hiçbir hata yoktur. Sistem istek göndermiş ancak API sağlayıcısı "Şu an sunucularım çok dolu (high demand), sana yanıt veremiyorum" diyerek bağlantıyı reddetmiştir.
- **Çözüm:** Bu gibi "Spike" (anlık yoğunluk) durumları genellikle saniyeler veya dakikalar içinde düzelir. Birkaç dakika sonra asistanı tekrar kullanmayı denemeniz yeterlidir. Eğer bu çok sık yaşanıyorsa, API anahtarınızın bağlı olduğu hizmetin kotaları artırılmalıdır (Tier 1 veya Tier 2 hesaba geçiş yapılabilir).

---

## 5. TypeScript (2367) Uyumsuzluk Hatası

### Sorun Açıklaması
`editor.component.ts` satır 2915'te yer alan şu kod bloğunda TypeScript hatası meydana geldi:
`if (anim === 'pop-up' || anim === 'scale-in') return 'animate-scale-in';`
Hata: `"This comparison appears to be unintentional because the types '"none" | "slide-left" ...' and '"scale-in"' have no overlap."`

### Kök Neden ve Çözüm
`OverlayItem` arayüz modelinde (Interface) `animation` değişkeni yalnızca belirli kelimeler alabileceği şeklinde tanımlanmıştı (`'fade' | 'pop-up' | 'slide-left' | 'slide-right' | 'slide-up' | 'slide-down' | 'none'`). Fakat kodun içinde olmayan `'scale-in'` kelimesi ile kontrol (`===`) yapılmaya çalışıldı.
TypeScript bu ihtimalin matematiksel olarak imkânsız olduğunu saptayıp uyarı verdi. Hatalı olan `anim === 'scale-in'` mantık kontrolü silinerek hata giderildi.
