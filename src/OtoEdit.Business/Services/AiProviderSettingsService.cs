using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.Business.Services;

public class AiProviderSettingsService : IAiProviderSettingsService
{
    private readonly ICacheService _cacheService;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<AiProviderSettingsService> _logger;
    private readonly AiProviderSettingsDto _currentSettings;
    private const string RedisCacheKey = "otoedit:settings:ai_provider";

    public AiProviderSettingsService(
        IConfiguration config,
        ICacheService cacheService,
        IHttpClientFactory httpClientFactory,
        ILogger<AiProviderSettingsService> logger)
    {
        _cacheService = cacheService;
        _httpClientFactory = httpClientFactory;
        _logger = logger;

        var rawProxyUrl = config["Antigravity:ProxyUrl"] ?? config["ANTIGRAVITY_PROXY_URL"] ?? "http://localhost:8045/v1";
        if (rawProxyUrl.Contains("host.docker.internal"))
        {
            rawProxyUrl = rawProxyUrl.Replace("host.docker.internal", "localhost");
        }

        _currentSettings = new AiProviderSettingsDto
        {
            ActiveProvider = config["AI_ACTIVE_PROVIDER"] ?? "antigravity",
            OpenRouterApiKey = config["OpenRouter:ApiKey"] ?? config["OPENROUTER_API_KEY"] ?? "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",
            OpenRouterBaseUrl = config["OpenRouter:BaseUrl"] ?? config["OPENROUTER_BASE_URL"] ?? "https://openrouter.ai/api/v1",
            OpenRouterModel = config["OpenRouter:Model"] ?? config["OPENROUTER_MODEL"] ?? "google/gemini-3.8-flash",
            AntigravityProxyUrl = rawProxyUrl,
            AntigravityProxyKey = config["Antigravity:ProxyKey"] ?? config["ANTIGRAVITY_PROXY_KEY"] ?? "sk-ea6e0c519b12403784eb5cdf79ca2615",
            AntigravityProxyModel = config["Antigravity:ProxyModel"] ?? config["ANTIGRAVITY_PROXY_MODEL"] ?? "gemini-3.8-flash-tiered"
        };
    }

    public async Task<AiProviderSettingsDto> GetSettingsAsync(CancellationToken ct = default)
    {
        try
        {
            var cached = await _cacheService.GetAsync<AiProviderSettingsDto>(RedisCacheKey, ct);
            if (cached != null)
            {
                _currentSettings.ActiveProvider = cached.ActiveProvider ?? _currentSettings.ActiveProvider;
                _currentSettings.OpenRouterApiKey = cached.OpenRouterApiKey ?? _currentSettings.OpenRouterApiKey;
                _currentSettings.OpenRouterBaseUrl = cached.OpenRouterBaseUrl ?? _currentSettings.OpenRouterBaseUrl;
                _currentSettings.OpenRouterModel = cached.OpenRouterModel ?? _currentSettings.OpenRouterModel;
                _currentSettings.AntigravityProxyUrl = cached.AntigravityProxyUrl ?? _currentSettings.AntigravityProxyUrl;
                _currentSettings.AntigravityProxyKey = cached.AntigravityProxyKey ?? _currentSettings.AntigravityProxyKey;
                _currentSettings.AntigravityProxyModel = cached.AntigravityProxyModel ?? _currentSettings.AntigravityProxyModel;
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning("Redis'ten AI ayarları okunurken uyarı: {Message}", ex.Message);
        }

        return new AiProviderSettingsDto
        {
            ActiveProvider = _currentSettings.ActiveProvider,
            OpenRouterApiKey = _currentSettings.OpenRouterApiKey,
            OpenRouterBaseUrl = _currentSettings.OpenRouterBaseUrl,
            OpenRouterModel = _currentSettings.OpenRouterModel,
            AntigravityProxyUrl = _currentSettings.AntigravityProxyUrl,
            AntigravityProxyKey = _currentSettings.AntigravityProxyKey,
            AntigravityProxyModel = _currentSettings.AntigravityProxyModel
        };
    }

    public async Task<AiProviderSettingsDto> UpdateSettingsAsync(AiProviderSettingsDto newSettings, CancellationToken ct = default)
    {
        if (!string.IsNullOrWhiteSpace(newSettings.ActiveProvider))
        {
            _currentSettings.ActiveProvider = newSettings.ActiveProvider.ToLowerInvariant();
        }

        if (!string.IsNullOrWhiteSpace(newSettings.OpenRouterApiKey))
        {
            _currentSettings.OpenRouterApiKey = newSettings.OpenRouterApiKey.Trim();
        }

        if (!string.IsNullOrWhiteSpace(newSettings.OpenRouterBaseUrl))
        {
            _currentSettings.OpenRouterBaseUrl = newSettings.OpenRouterBaseUrl.Trim();
        }

        if (!string.IsNullOrWhiteSpace(newSettings.OpenRouterModel))
        {
            _currentSettings.OpenRouterModel = newSettings.OpenRouterModel.Trim();
        }

        if (!string.IsNullOrWhiteSpace(newSettings.AntigravityProxyUrl))
        {
            _currentSettings.AntigravityProxyUrl = newSettings.AntigravityProxyUrl.Trim();
        }

        if (!string.IsNullOrWhiteSpace(newSettings.AntigravityProxyKey))
        {
            _currentSettings.AntigravityProxyKey = newSettings.AntigravityProxyKey.Trim();
        }

        if (!string.IsNullOrWhiteSpace(newSettings.AntigravityProxyModel))
        {
            _currentSettings.AntigravityProxyModel = newSettings.AntigravityProxyModel.Trim();
        }

        try
        {
            await _cacheService.SetAsync(RedisCacheKey, _currentSettings, TimeSpan.FromDays(30), ct);
            _logger.LogInformation("AI sağlayıcı ayarları güncellendi. Aktif Sağlayıcı: {Provider}", _currentSettings.ActiveProvider);
        }
        catch (Exception ex)
        {
            _logger.LogWarning("Redis'e AI ayarları kaydedilirken hata: {Message}", ex.Message);
        }

        return await GetSettingsAsync(ct);
    }

    public async Task<TestConnectionResultDto> TestConnectionAsync(string provider, CancellationToken ct = default)
    {
        var settings = await GetSettingsAsync(ct);
        var targetProvider = (provider ?? settings.ActiveProvider).ToLowerInvariant();
        var client = _httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromSeconds(10);
        var sw = Stopwatch.StartNew();

        if (targetProvider == "openrouter")
        {
            var key = settings.OpenRouterApiKey;
            if (string.IsNullOrWhiteSpace(key))
            {
                return new TestConnectionResultDto
                {
                    Success = false,
                    Message = "OpenRouter API anahtarı boş bırakılamaz.",
                    LatencyMs = 0
                };
            }

            try
            {
                var request = new HttpRequestMessage(HttpMethod.Get, $"{settings.OpenRouterBaseUrl.TrimEnd('/')}/auth/key");
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", key);
                request.Headers.Add("User-Agent", "OtoEdit/2.0");

                var resp = await client.SendAsync(request, ct);
                sw.Stop();

                if (resp.IsSuccessStatusCode)
                {
                    var body = await resp.Content.ReadAsStringAsync(ct);
                    string details = "";
                    try
                    {
                        using var doc = JsonDocument.Parse(body);
                        if (doc.RootElement.TryGetProperty("data", out var data))
                        {
                            if (data.TryGetProperty("limit_remaining", out var limitRem))
                            {
                                details = $" (Kalan Limit: {limitRem.GetRawText()})";
                            }
                        }
                    }
                    catch { }

                    return new TestConnectionResultDto
                    {
                        Success = true,
                        Message = $"OpenRouter bağlantısı başarılı! Model: {settings.OpenRouterModel}{details}",
                        LatencyMs = sw.ElapsedMilliseconds
                    };
                }
                else
                {
                    var err = await resp.Content.ReadAsStringAsync(ct);
                    return new TestConnectionResultDto
                    {
                        Success = false,
                        Message = $"OpenRouter API Hatası ({resp.StatusCode}): {err}",
                        LatencyMs = sw.ElapsedMilliseconds
                    };
                }
            }
            catch (Exception ex)
            {
                sw.Stop();
                return new TestConnectionResultDto
                {
                    Success = false,
                    Message = $"OpenRouter sunucusuna bağlanılamadı: {ex.Message}",
                    LatencyMs = sw.ElapsedMilliseconds
                };
            }
        }
        else
        {
            // Antigravity Proxy
            try
            {
                var url = settings.AntigravityProxyUrl.TrimEnd('/');
                var request = new HttpRequestMessage(HttpMethod.Get, $"{url}/models");
                if (!string.IsNullOrWhiteSpace(settings.AntigravityProxyKey))
                {
                    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", settings.AntigravityProxyKey);
                }

                var resp = await client.SendAsync(request, ct);
                sw.Stop();

                if (resp.IsSuccessStatusCode)
                {
                    return new TestConnectionResultDto
                    {
                        Success = true,
                        Message = $"Antigravity Proxy bağlantısı başarılı! Model: {settings.AntigravityProxyModel}",
                        LatencyMs = sw.ElapsedMilliseconds
                    };
                }
                else
                {
                    return new TestConnectionResultDto
                    {
                        Success = true,
                        Message = $"Antigravity Proxy yanıt verdi ({resp.StatusCode}). Model: {settings.AntigravityProxyModel}",
                        LatencyMs = sw.ElapsedMilliseconds
                    };
                }
            }
            catch (Exception ex)
            {
                sw.Stop();
                return new TestConnectionResultDto
                {
                    Success = false,
                    Message = $"Antigravity Proxy'ye erişilemedi ({settings.AntigravityProxyUrl}): {ex.Message}",
                    LatencyMs = sw.ElapsedMilliseconds
                };
            }
        }
    }

    public async Task<List<ModelOptionDto>> GetAvailableModelsAsync(string provider = "openrouter", CancellationToken ct = default)
    {
        var settings = await GetSettingsAsync(ct);
        var client = _httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromSeconds(15);

        if (provider.Equals("antigravity", StringComparison.OrdinalIgnoreCase))
        {
            try
            {
                var url = settings.AntigravityProxyUrl.TrimEnd('/');
                var request = new HttpRequestMessage(HttpMethod.Get, $"{url}/models");
                if (!string.IsNullOrWhiteSpace(settings.AntigravityProxyKey))
                {
                    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", settings.AntigravityProxyKey);
                }
                var resp = await client.SendAsync(request, ct);
                if (resp.IsSuccessStatusCode)
                {
                    var body = await resp.Content.ReadAsStringAsync(ct);
                    using var doc = JsonDocument.Parse(body);
                    var list = new List<ModelOptionDto>();
                    if (doc.RootElement.TryGetProperty("data", out var dataArr) && dataArr.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var item in dataArr.EnumerateArray())
                        {
                            var id = item.TryGetProperty("id", out var idProp) ? idProp.GetString() ?? "" : "";
                            if (!string.IsNullOrWhiteSpace(id))
                            {
                                list.Add(new ModelOptionDto { Id = id, Name = id });
                            }
                        }
                    }
                    if (list.Count > 0) return list;
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning("Antigravity modelleri alınamadı: {Message}", ex.Message);
            }

            return new List<ModelOptionDto>
            {
                new() { Id = "gemini-3.8-flash-tiered", Name = "gemini-3.8-flash-tiered (Gemini 3.8 Flash)" },
                new() { Id = "gemini-3.7-flash-tiered", Name = "gemini-3.7-flash-tiered" },
                new() { Id = "gemini-3.6-flash-tiered", Name = "gemini-3.6-flash-tiered" }
            };
        }

        // OpenRouter modelleri
        try
        {
            var cacheKey = "otoedit:cache:openrouter_models";
            var cached = await _cacheService.GetAsync<List<ModelOptionDto>>(cacheKey, ct);
            if (cached != null && cached.Count > 0)
            {
                return cached;
            }

            var request = new HttpRequestMessage(HttpMethod.Get, "https://openrouter.ai/api/v1/models");
            request.Headers.Add("User-Agent", "OtoEdit/2.0");
            if (!string.IsNullOrWhiteSpace(settings.OpenRouterApiKey))
            {
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", settings.OpenRouterApiKey);
            }

            var resp = await client.SendAsync(request, ct);
            if (resp.IsSuccessStatusCode)
            {
                var body = await resp.Content.ReadAsStringAsync(ct);
                using var doc = JsonDocument.Parse(body);
                var list = new List<ModelOptionDto>();
                if (doc.RootElement.TryGetProperty("data", out var dataArr) && dataArr.ValueKind == JsonValueKind.Array)
                {
                    foreach (var item in dataArr.EnumerateArray())
                    {
                        var id = item.TryGetProperty("id", out var idProp) ? idProp.GetString() ?? "" : "";
                        var name = item.TryGetProperty("name", out var nameProp) ? nameProp.GetString() ?? id : id;
                        var desc = item.TryGetProperty("description", out var descProp) ? descProp.GetString() : null;
                        int? ctx = item.TryGetProperty("context_length", out var ctxProp) && ctxProp.TryGetInt32(out var ctxVal) ? ctxVal : null;

                        if (!string.IsNullOrWhiteSpace(id))
                        {
                            list.Add(new ModelOptionDto
                            {
                                Id = id,
                                Name = name,
                                Description = desc,
                                ContextLength = ctx
                            });
                        }
                    }
                }

                if (list.Count > 0)
                {
                    // Popüler sağlayıcıları öne al
                    var ordered = list.OrderBy(m =>
                    {
                        if (m.Id == "google/gemini-3.8-flash") return 0;
                        if (m.Id == "google/gemini-2.0-flash-001") return 1;
                        if (m.Id == "anthropic/claude-3.5-sonnet") return 2;
                        if (m.Id == "openai/gpt-4o") return 3;
                        if (m.Id == "deepseek/deepseek-chat") return 4;
                        if (m.Id == "deepseek/deepseek-r1") return 5;
                        if (m.Id.StartsWith("google/")) return 10;
                        if (m.Id.StartsWith("anthropic/")) return 20;
                        if (m.Id.StartsWith("openai/")) return 30;
                        if (m.Id.StartsWith("deepseek/")) return 40;
                        if (m.Id.StartsWith("meta-llama/")) return 50;
                        if (m.Id.StartsWith("mistralai/")) return 60;
                        if (m.Id.StartsWith("qwen/")) return 70;
                        return 100;
                    }).ThenBy(m => m.Name).ToList();

                    try
                    {
                        await _cacheService.SetAsync(cacheKey, ordered, TimeSpan.FromMinutes(15), ct);
                    }
                    catch { }

                    return ordered;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning("OpenRouter modelleri çekilirken hata: {Message}", ex.Message);
        }

        // Yedek model listesi
        return GetFallbackOpenRouterModels();
    }

    private static List<ModelOptionDto> GetFallbackOpenRouterModels()
    {
        return new List<ModelOptionDto>
        {
            new() { Id = "google/gemini-3.8-flash", Name = "Google: Gemini 3.8 Flash (Varsayılan)", ContextLength = 1048576 },
            new() { Id = "google/gemini-2.0-flash-001", Name = "Google: Gemini 2.0 Flash", ContextLength = 1048576 },
            new() { Id = "google/gemini-2.5-flash", Name = "Google: Gemini 2.5 Flash", ContextLength = 1048576 },
            new() { Id = "anthropic/claude-3.5-sonnet", Name = "Anthropic: Claude 3.5 Sonnet", ContextLength = 200000 },
            new() { Id = "anthropic/claude-3-opus", Name = "Anthropic: Claude 3 Opus", ContextLength = 200000 },
            new() { Id = "openai/gpt-4o", Name = "OpenAI: GPT-4o", ContextLength = 128000 },
            new() { Id = "openai/gpt-4o-mini", Name = "OpenAI: GPT-4o Mini", ContextLength = 128000 },
            new() { Id = "deepseek/deepseek-chat", Name = "DeepSeek: DeepSeek V3", ContextLength = 64000 },
            new() { Id = "deepseek/deepseek-r1", Name = "DeepSeek: DeepSeek R1", ContextLength = 64000 },
            new() { Id = "meta-llama/llama-3.3-70b-instruct", Name = "Meta: Llama 3.3 70B Instruct", ContextLength = 131072 },
            new() { Id = "mistralai/mistral-large-2411", Name = "Mistral: Mistral Large 2411", ContextLength = 128000 },
            new() { Id = "qwen/qwen-2.5-72b-instruct", Name = "Qwen: Qwen 2.5 72B Instruct", ContextLength = 32768 }
        };
    }
}
