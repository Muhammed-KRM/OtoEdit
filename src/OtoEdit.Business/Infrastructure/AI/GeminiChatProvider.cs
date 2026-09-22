using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Mscc.GenerativeAI;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.Business.Infrastructure.AI;

/// <summary>
/// Google Gemini API ile kullanıcı komutlarını EDL patch'e dönüştüren yapay zeka servisi.
/// </summary>
public class GeminiChatProvider : IChatProvider
{
    private readonly string? _apiKey;
    private readonly string _modelName;
    private readonly ILogger<GeminiChatProvider> _logger;

    public GeminiChatProvider(IConfiguration config, ILogger<GeminiChatProvider> logger)
    {
        _apiKey = config["Gemini:ApiKey"] ?? config["GEMINI_API_KEY"];
        _modelName = config["Gemini:Model"] ?? config["GEMINI_MODEL"] ?? "gemini-2.0-flash";
        _logger = logger;
    }

    public async Task<ChatResult> ProcessCommandAsync(
        string userMessage,
        string currentEdlJson,
        string? transcriptText,
        List<ChatHistoryItem> history,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(_apiKey))
        {
            _logger.LogWarning("Gemini API Key tanımlı değil, mock yanıt dönülüyor.");
            return new ChatResult
            {
                Mesaj = $"Komutunuz alındı: '{userMessage}'. (API anahtarı yapılandırılmadığı için simülasyon modunda çalışıldı)",
                EdlPatch = null
            };
        }

        try
        {
            var googleAi = new GoogleAI(_apiKey);
            var model = googleAi.GenerativeModel(_modelName);

            var systemPrompt = """
                Sen profesyonel bir video kurgu asistanısın. 
                Görevin, kullanıcının komutlarını analiz edip uygun niyetle (intent) JSON formatında yanıt vermektir.

                KURALLAR (KESİNLİKLE UYULACAK):
                1. Niyet (intent) 4 çeşittir: 
                   - "information": Kullanıcı sadece soru soruyorsa veya bilgi istiyorsa (EDL değişmez).
                   - "suggestion": Kullanıcı "ne ekleyebiliriz?" diyorsa veya onaya sunulacak bir öneri ise.
                   - "command": Kullanıcı kesin bir dille "şurayı kes", "şunu ekle" diyorsa ve eksik parametre (renk, konum vb.) yoksa.
                   - "clarification": Kullanıcının talebi ("yazı ekle", "başlık koy", "resim ekle" vb.) stil veya konum detayları içermiyorsa KESİNLİKLE bu intent'i kullan ve formFields dön.
                2. Eğer intent "clarification" ise, "formFields" dizisini KESİNLİKLE aşağıdaki şemaya uygun dön:
                   Desteklenen "type" türleri:
                   - "text": Metin girişi (id: "content", label: "Yazı Metni")
                   - "position": 16:9 İnteraktif konumlayıcı (id: "position", label: "Ekran Konumu", defaultValue: "bottom-center")
                   - "color": Zengin renk paleti ve Hex seçici (id: "color", label: "Yazı Rengi", defaultValue: "#FACC15")
                   - "select": Seçim kutusu (Font ve Animasyon için). ZORUNLU options: [ { "value": "...", "label": "..." } ]
                   
                   Standart Font Presetleri (type="select", id="font"):
                   [
                     { "value": "Montserrat", "label": "Montserrat (Kalın & Vurgulu)" },
                     { "value": "Inter", "label": "Inter (Modern & Sade)" },
                     { "value": "Bebas Neue", "label": "Bebas Neue (Büyük Harf)" },
                     { "value": "Anton", "label": "Anton (Ağır & Vurucu)" }
                   ]
                   
                   Standart Animasyon Presetleri (type="select", id="animation"):
                   [
                     { "value": "pop-up", "label": "✨ Büyüyerek Açıl (Pop-up)" },
                     { "value": "fade", "label": "🌫 Yumuşak Geçiş (Fade)" },
                     { "value": "slide-up", "label": "⬆ Aşağıdan Yukarı" },
                     { "value": "none", "label": "⚡ Sabit" }
                   ]

                   Kullanıcı form doldurup "Belirttiğim özellikler ile katmanı ekle: [positionX: 50, positionY: 85]" şeklinde yanıt verirse, intent: "command" olarak edlPatch içinde "positionX" ve "positionY" sayısal yüzdelerini (0-100) kullanarak OverlayItem ekle.
                3. Videonun içeriğini SADECE verilen VİDEO TRANSKRİPTİNE göre değerlendir. Transkriptte geçmeyen HİÇBİR KELİMEYİ VEYA OLAYI UYDURMA. Bilgi yoksa "Bu bilgi transkriptte yok" de.
                4. Zaman damgalarını transkriptteki gerçek sürelere göre belirle.
                5. Sadece "cuts", "overlays", "settings" ve "suggestions" alanlarını değiştirebilir veya ekleme yapabilirsin.
                6. Her cut'a benzersiz id ver (cut_ai_{timestamp}). Her overlay'e benzersiz id ver (text_ai_{timestamp} veya img_ai_{timestamp}).
                7. Yanıtını SADECE aşağıdaki JSON formatında ver:
                {
                   "mesaj": "Kullanıcıya gösterilecek açıklayıcı yanıt metni",
                   "intent": "information, suggestion, command veya clarification",
                   "edlPatch": { ... JSON patch ... } (eğer değişiklik yoksa null),
                   "formFields": [
                      { "id": "content", "type": "text", "label": "Yazı Metni", "defaultValue": "Öne Çıkan Başlık" },
                      { "id": "position", "type": "position", "label": "Ekran Konumu", "defaultValue": "bottom-center" },
                      { "id": "color", "type": "color", "label": "Yazı Rengi", "defaultValue": "#FACC15" },
                      { "id": "font", "type": "select", "label": "Yazı Tipi (Font)", "defaultValue": "Montserrat", "options": [ { "value": "Montserrat", "label": "Montserrat (Kalın & Vurgulu)" } ] },
                      { "id": "animation", "type": "select", "label": "Giriş Animasyonu", "defaultValue": "pop-up", "options": [ { "value": "pop-up", "label": "✨ Pop-up" } ] }
                   ] (eğer intent clarification ise dolu, değilse null)
                }
                """;

            var historyText = string.Join("\n", history.Select(h => $"{h.Role}: {h.Message}"));
            
            var transcriptSection = string.IsNullOrWhiteSpace(transcriptText) 
                ? "[TRANSKRİPT BULUNAMADI]" 
                : transcriptText;

            var prompt = $@"{systemPrompt}

=== VİDEO TRANSKRİPTİ ===
{transcriptSection}
=========================

=== GEÇMİŞ SOHBET ===
{historyText}
=====================

=== MEVCUT EDL ===
{currentEdlJson}
==================

Kullanıcı: {userMessage}";

            var response = await model.GenerateContent(prompt);
            var rawText = response.Text ?? string.Empty;

            var cleanedJson = rawText
                .Replace("```json", "")
                .Replace("```", "")
                .Trim();

            var parsed = JsonSerializer.Deserialize<ChatResult>(cleanedJson, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            return parsed ?? new ChatResult { Mesaj = "Komut işlendi ancak dönüştürme yapılamadı." };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Gemini Chat API çağrısı sırasında hata oluştu.");
            return new ChatResult
            {
                Mesaj = "Üzgünüm, komutunuzu işlerken bir yapay zeka hatası oluştu: " + ex.Message
            };
        }
    }
}
