using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Mscc.GenerativeAI;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.Business.Infrastructure.AI;

/// <summary>
/// Yapay zeka destekli video kurgu asistanı servisi.
/// Antigravity Proxy, Groq (OpenAI uyumlu), resmi Google Gemini API ve yerel akıllı çözümleyiciyi destekler.
/// </summary>
public class GeminiChatProvider : IChatProvider
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IAiProviderSettingsService _settingsService;
    private readonly string? _geminiApiKey;
    private readonly string? _groqApiKey;
    private readonly string? _proxyUrl;
    private readonly string? _proxyKey;
    private readonly string _geminiModel;
    private readonly string _groqModel;
    private readonly string _proxyModel;
    private readonly ILogger<GeminiChatProvider> _logger;

    public GeminiChatProvider(
        IConfiguration config,
        IHttpClientFactory httpClientFactory,
        IAiProviderSettingsService settingsService,
        ILogger<GeminiChatProvider> logger)
    {
        _httpClientFactory = httpClientFactory;
        _settingsService = settingsService;
        _geminiApiKey = config["Gemini:ApiKey"] ?? config["GEMINI_API_KEY"];
        _groqApiKey = config["Groq:ApiKey"] ?? config["GROQ_API_KEY"];
        
        // Host Windows üzerinde çalışıyorsa localhost'a yönlendir
        var rawProxyUrl = config["Antigravity:ProxyUrl"] ?? config["ANTIGRAVITY_PROXY_URL"] ?? "http://localhost:8045/v1";
        if (rawProxyUrl.Contains("host.docker.internal"))
        {
            rawProxyUrl = rawProxyUrl.Replace("host.docker.internal", "localhost");
        }
        _proxyUrl = rawProxyUrl;
        _proxyKey = config["Antigravity:ProxyKey"] ?? config["ANTIGRAVITY_PROXY_KEY"] ?? config["GEMINI_API_KEY"];
        
        _geminiModel = config["Gemini:Model"] ?? config["GEMINI_MODEL"] ?? "gemini-2.0-flash";
        _groqModel = config["Groq:Model"] ?? config["GROQ_MODEL"] ?? "openai/gpt-oss-120b";
        _proxyModel = config["Antigravity:ProxyModel"] ?? config["ANTIGRAVITY_PROXY_MODEL"] ?? "gemini-3.8-flash-tiered";
        _logger = logger;
    }

    public Task<ChatResult> ProcessCommandAsync(
        string userMessage,
        string currentEdlJson,
        string? transcriptText,
        List<ChatHistoryItem> history,
        CancellationToken cancellationToken)
        => ProcessCommandAsync(userMessage, currentEdlJson, transcriptText, history, null, cancellationToken);

    public async Task<ChatResult> ProcessCommandAsync(
        string userMessage,
        string currentEdlJson,
        string? transcriptText,
        List<ChatHistoryItem> history,
        string? overrideProvider = null,
        CancellationToken cancellationToken = default)
    {
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

        var userPrompt = $@"{systemPrompt}

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

        string? rawResponse = null;
        var aiSettings = await _settingsService.GetSettingsAsync(cancellationToken);
        var activeProvider = !string.IsNullOrWhiteSpace(overrideProvider) 
            ? overrideProvider.ToLowerInvariant() 
            : (aiSettings.ActiveProvider?.ToLowerInvariant() ?? "antigravity");

        // 1. Eğer OpenRouter aktifse öncelikli olarak OpenRouter çağrılır
        if (activeProvider == "openrouter" && !string.IsNullOrWhiteSpace(aiSettings.OpenRouterApiKey))
        {
            try
            {
                _logger.LogInformation("OpenRouter API ({Model}) deneniyor...", aiSettings.OpenRouterModel);
                rawResponse = await CallOpenAiCompatibleAsync(
                    aiSettings.OpenRouterBaseUrl,
                    aiSettings.OpenRouterApiKey,
                    aiSettings.OpenRouterModel,
                    systemPrompt,
                    userPrompt,
                    timeoutSeconds: 25,
                    cancellationToken,
                    extraHeaders: new Dictionary<string, string>
                    {
                        ["HTTP-Referer"] = "https://otoedit.local",
                        ["X-Title"] = "OtoEdit"
                    });
            }
            catch (Exception ex)
            {
                _logger.LogWarning("OpenRouter API çağrısı başarısız oldu: {Message}", ex.Message);
            }
        }

        // 2. Antigravity Proxy (OpenAI uyumlu yerel proxy)
        if (string.IsNullOrWhiteSpace(rawResponse))
        {
            var proxyUrl = !string.IsNullOrWhiteSpace(aiSettings.AntigravityProxyUrl) ? aiSettings.AntigravityProxyUrl : _proxyUrl;
            var proxyKey = !string.IsNullOrWhiteSpace(aiSettings.AntigravityProxyKey) ? aiSettings.AntigravityProxyKey : _proxyKey;
            var proxyModel = !string.IsNullOrWhiteSpace(aiSettings.AntigravityProxyModel) ? aiSettings.AntigravityProxyModel : _proxyModel;

            if (!string.IsNullOrWhiteSpace(proxyUrl) && !string.IsNullOrWhiteSpace(proxyKey))
            {
                try
                {
                    _logger.LogInformation("Antigravity Proxy ({Url}) deneniyor...", proxyUrl);
                    rawResponse = await CallOpenAiCompatibleAsync(
                        proxyUrl,
                        proxyKey,
                        proxyModel,
                        systemPrompt,
                        userPrompt,
                        timeoutSeconds: 8,
                        cancellationToken);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning("Antigravity Proxy çağrısı başarısız oldu: {Message}", ex.Message);
                }
            }
        }

        // 2.1. Eğer Antigravity seçiliyken başarısız olduysa ve OpenRouter tanımlıysa OpenRouter'ı yedek olarak dene
        if (string.IsNullOrWhiteSpace(rawResponse) && activeProvider != "openrouter" && !string.IsNullOrWhiteSpace(aiSettings.OpenRouterApiKey))
        {
            try
            {
                _logger.LogInformation("Yedek olarak OpenRouter API ({Model}) deneniyor...", aiSettings.OpenRouterModel);
                rawResponse = await CallOpenAiCompatibleAsync(
                    aiSettings.OpenRouterBaseUrl,
                    aiSettings.OpenRouterApiKey,
                    aiSettings.OpenRouterModel,
                    systemPrompt,
                    userPrompt,
                    timeoutSeconds: 20,
                    cancellationToken,
                    extraHeaders: new Dictionary<string, string>
                    {
                        ["HTTP-Referer"] = "https://otoedit.local",
                        ["X-Title"] = "OtoEdit"
                    });
            }
            catch (Exception ex)
            {
                _logger.LogWarning("Yedek OpenRouter API çağrısı başarısız oldu: {Message}", ex.Message);
            }
        }

        // 2. Groq API (Hızlı ve OpenAI uyumlu bulut motoru)
        if (string.IsNullOrWhiteSpace(rawResponse) && !string.IsNullOrWhiteSpace(_groqApiKey) && _groqApiKey.StartsWith("gsk_"))
        {
            try
            {
                _logger.LogInformation("Groq API ({Model}) deneniyor...", _groqModel);
                rawResponse = await CallOpenAiCompatibleAsync(
                    "https://api.groq.com/openai/v1",
                    _groqApiKey,
                    _groqModel,
                    systemPrompt,
                    userPrompt,
                    timeoutSeconds: 15,
                    cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogWarning("Groq API çağrısı başarısız oldu: {Message}", ex.Message);
            }
        }

        // 3. Resmi Google Gemini API (Sadece geçerli 39 karakterlik AIza... anahtarı varsa)
        if (string.IsNullOrWhiteSpace(rawResponse) && !string.IsNullOrWhiteSpace(_geminiApiKey) && _geminiApiKey.StartsWith("AIza") && _geminiApiKey.Length == 39)
        {
            try
            {
                _logger.LogInformation("Resmi Google Gemini API ({Model}) deneniyor...", _geminiModel);
                var googleAi = new GoogleAI(_geminiApiKey);
                var model = googleAi.GenerativeModel(_geminiModel);

                int maxRetries = 2;
                for (int i = 0; i < maxRetries; i++)
                {
                    try
                    {
                        var response = await model.GenerateContent(userPrompt);
                        rawResponse = response.Text ?? string.Empty;
                        break;
                    }
                    catch (Exception ex) when (ex.Message.Contains("503") || ex.Message.Contains("time out") || ex.Message.Contains("Unavailable"))
                    {
                        if (i == maxRetries - 1) throw;
                        await Task.Delay(1500 * (i + 1), cancellationToken);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning("Resmi Google Gemini API çağrısı başarısız oldu: {Message}", ex.Message);
            }
        }

        // 4. Yanıtı Parse Et
        if (!string.IsNullOrWhiteSpace(rawResponse))
        {
            try
            {
                var cleanedJson = rawResponse
                    .Replace("```json", "")
                    .Replace("```", "")
                    .Trim();

                // Eğer metin içinde { ve } varsa json kısmını ayıkla
                int firstBrace = cleanedJson.IndexOf('{');
                int lastBrace = cleanedJson.LastIndexOf('}');
                if (firstBrace >= 0 && lastBrace > firstBrace)
                {
                    cleanedJson = cleanedJson.Substring(firstBrace, lastBrace - firstBrace + 1);
                }

                var parsed = JsonSerializer.Deserialize<ChatResult>(cleanedJson, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                if (parsed != null)
                {
                    return parsed;
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning("LLM JSON çıktısı ayrıştırılamadı, yerel çözümleyiciye geçiliyor: {Message}", ex.Message);
            }
        }

        // 5. Yerel Kurgu Çözümleyicisi (Local Intelligent Fallback)
        return ParseWithLocalHeuristics(userMessage, currentEdlJson, transcriptSection);
    }

    /// <summary>
    /// OpenAI uyumlu /chat/completions uç noktasını çağırır.
    /// </summary>
    private async Task<string?> CallOpenAiCompatibleAsync(
        string baseUrl,
        string apiKey,
        string modelName,
        string systemPrompt,
        string userPrompt,
        int timeoutSeconds,
        CancellationToken cancellationToken,
        IDictionary<string, string>? extraHeaders = null)
    {
        var client = _httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromSeconds(timeoutSeconds);

        var requestUrl = $"{baseUrl.TrimEnd('/')}/chat/completions";
        using var request = new HttpRequestMessage(HttpMethod.Post, requestUrl);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        request.Headers.Add("User-Agent", "OtoEdit/2.0");

        if (extraHeaders != null)
        {
            foreach (var kvp in extraHeaders)
            {
                request.Headers.TryAddWithoutValidation(kvp.Key, kvp.Value);
            }
        }

        var payload = new
        {
            model = modelName,
            messages = new object[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = userPrompt }
            },
            response_format = new { type = "json_object" }
        };

        var jsonBody = JsonSerializer.Serialize(payload);
        request.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");

        var response = await client.SendAsync(request, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var errContent = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogWarning("OpenAI API HTTP {Status}: {Content}", response.StatusCode, errContent);
            return null;
        }

        var responseJson = await response.Content.ReadAsStringAsync(cancellationToken);
        using var doc = JsonDocument.Parse(responseJson);
        var root = doc.RootElement;
        if (root.TryGetProperty("choices", out var choices) && choices.GetArrayLength() > 0)
        {
            var choice = choices[0];
            if (choice.TryGetProperty("message", out var msg) && msg.TryGetProperty("content", out var content))
            {
                return content.GetString();
            }
        }

        return null;
    }

    /// <summary>
    /// Harici API'lere ulaşılamadığında veya kullanıcı doğrudan zaman aralığı ile metin eklemek istediğinde
    /// doğrudan EDL Patch üreten ve transkript sorularını yanıtlayan akıllı yerel kurgu asistanı.
    /// </summary>
    private ChatResult ParseWithLocalHeuristics(string userMessage, string currentEdlJson, string transcriptText)
    {
        // 1. Seçili Aralık kontrolü: "[Seçili Aralık: 1026.5s - 1033.9s] imam gazali yazılacak buraya"
        var rangeMatch = Regex.Match(userMessage, @"\[Seçili\s*Aralık:\s*([0-9.]+)\s*s?\s*-\s*([0-9.]+)\s*s?\]\s*(.*)", RegexOptions.IgnoreCase);
        if (rangeMatch.Success)
        {
            double startSec = double.TryParse(rangeMatch.Groups[1].Value, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var s) ? s : 0.0;
            double endSec = double.TryParse(rangeMatch.Groups[2].Value, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var e) ? e : startSec + 5.0;
            double duration = Math.Max(1.0, Math.Round((endSec - startSec) * 10) / 10.0);
            
            string rawText = rangeMatch.Groups[3].Value.Trim();
            // 'yazılacak buraya', 'yaz', 'koy', 'ekle' gibi komut eklerini temizle
            string cleanedText = Regex.Replace(rawText, @"(?i)\s*(yazılacak(\s*buraya)?|yazılsın|ekle|koy|yaz)\s*$", "").Trim();
            if (string.IsNullOrWhiteSpace(cleanedText))
            {
                cleanedText = rawText;
            }
            if (string.IsNullOrWhiteSpace(cleanedText))
            {
                cleanedText = "Öne Çıkan Başlık";
            }

            long ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            string patchJson = $$"""
            {
              "overlays": [
                {
                  "id": "text_ai_{{ts}}",
                  "type": "text",
                  "content": "{{EscapeJson(cleanedText)}}",
                  "timestamp": {{startSec.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)}},
                  "duration": {{duration.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)}},
                  "positionX": 50,
                  "positionY": 85,
                  "color": "#FACC15",
                  "fontSize": 48,
                  "font": "Montserrat",
                  "animation": "pop-up",
                  "action": "add"
                }
              ]
            }
            """;

            var patchDoc = JsonDocument.Parse(patchJson);

            return new ChatResult
            {
                Mesaj = $"Seçtiğiniz aralık ({startSec:0.#}s - {endSec:0.#}s) için '{cleanedText}' yazı katmanı hazırlandı. 'Onayla' butonuna tıklayarak doğrudan timeline'a ekleyebilir veya 'Önizle' yapabilirsiniz.",
                Intent = "command",
                EdlPatch = patchDoc.RootElement.Clone(),
                FormFields = null
            };
        }

        // 2. Transkript İçi Arama / Soru Yanıtlama (Örn: "kaçıncı saniyede bediüzzamandan bahsettin")
        if (!string.IsNullOrWhiteSpace(transcriptText) && !transcriptText.Contains("[TRANSKRİPT BULUNAMADI]"))
        {
            // Kullanıcı sorgusundaki anahtar kelimeleri çıkar
            var stopWords = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "tüm", "videoda", "kaçıncı", "saniyede", "dakikada", "ne", "zaman", "nerede", "bahsettin",
                "bahsediyor", "geçiyor", "var", "mı", "mi", "mu", "mü", "bir", "ve", "ile", "için", "neden"
            };

            var words = Regex.Matches(userMessage, @"[\wğüşıöçĞÜŞİÖÇ]+")
                .Cast<Match>()
                .Select(m => m.Value)
                .Where(w => w.Length >= 3 && !stopWords.Contains(w))
                .ToList();

            if (words.Count > 0)
            {
                var lines = transcriptText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                var matches = new List<string>();

                foreach (var line in lines)
                {
                    bool matched = false;
                    foreach (var kw in words)
                    {
                        // Türkçe kök eşleşmesi (ilk 4 harf)
                        string prefix = kw.Length > 4 ? kw.Substring(0, 4) : kw;
                        if (line.IndexOf(prefix, StringComparison.OrdinalIgnoreCase) >= 0)
                        {
                            matched = true;
                            break;
                        }
                    }

                    if (matched)
                    {
                        matches.Add(line.Trim());
                        if (matches.Count >= 4) break;
                    }
                }

                if (matches.Count > 0)
                {
                    var joined = string.Join("\n• ", matches);
                    return new ChatResult
                    {
                        Mesaj = $"Videonuzun transkriptinde aradığınız ifade şu noktalarda geçmektedir:\n• {joined}",
                        Intent = "information",
                        EdlPatch = null,
                        FormFields = null
                    };
                }
            }
        }

        // 3. Genel varsayılan yanıt
        return new ChatResult
        {
            Mesaj = $"Komutunuz incelendi: '{userMessage}'. Zaman çizelgesinden bir aralık seçip '... yazısı koy' diyebilir veya videoda geçen bir konuyu sorabilirsiniz.",
            Intent = "information",
            EdlPatch = null,
            FormFields = null
        };
    }

    private static string EscapeJson(string val)
    {
        return val.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "").Replace("\n", " ");
    }
}
