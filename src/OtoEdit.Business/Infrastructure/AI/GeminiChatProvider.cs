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
                Sen bir video editörü asistanısın. Kullanıcının doğal dildeki kurgu komutunu alıp,
                mevcut EDL JSON üzerinde yapılacak değişiklikleri JSON patch olarak döndürüyorsun.

                Kurallar:
                - Sadece "cuts", "overlays", "settings" ve "suggestions" alanlarını değiştirebilir veya ekleme yapabilirsin.
                - Her cut'a benzersiz id ver (cut_ai_{timestamp}).
                - Her overlay'e benzersiz id ver (text_ai_{timestamp} veya img_ai_{timestamp}).
                - Yanıtını SADECE geçerli bir JSON formatında ver:
                {
                    "mesaj": "Kullanıcıya gösterilecek samimi Türkçe yanıt",
                    "edlPatch": { ...değişecek alanlar... }
                }
                - Başka hiçbir açıklama, markdown tag'i olmadan sadece JSON dön.
                """;

            var historyText = string.Join("\n", history.Select(h => $"{h.Role}: {h.Message}"));
            var prompt = $"{systemPrompt}\n\nGeçmiş Sohbet:\n{historyText}\n\nMevcut EDL:\n{currentEdlJson}\n\nKullanıcı: {userMessage}";

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
