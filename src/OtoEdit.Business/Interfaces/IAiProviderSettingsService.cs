namespace OtoEdit.Business.Interfaces;

public class AiProviderSettingsDto
{
    public string ActiveProvider { get; set; } = "antigravity"; // "antigravity" | "openrouter"
    public string OpenRouterApiKey { get; set; } = "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";
    public string OpenRouterBaseUrl { get; set; } = "https://openrouter.ai/api/v1";
    public string OpenRouterModel { get; set; } = "google/gemini-3.8-flash";
    public string AntigravityProxyUrl { get; set; } = "http://localhost:8045/v1";
    public string AntigravityProxyKey { get; set; } = "sk-ea6e0c519b12403784eb5cdf79ca2615";
    public string AntigravityProxyModel { get; set; } = "gemini-3.8-flash-tiered";
}

public class TestConnectionResultDto
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public long LatencyMs { get; set; }
}

public class ModelOptionDto
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public int? ContextLength { get; set; }
}

public interface IAiProviderSettingsService
{
    Task<AiProviderSettingsDto> GetSettingsAsync(CancellationToken ct = default);
    Task<AiProviderSettingsDto> UpdateSettingsAsync(AiProviderSettingsDto newSettings, CancellationToken ct = default);
    Task<TestConnectionResultDto> TestConnectionAsync(string provider, CancellationToken ct = default);
    Task<List<ModelOptionDto>> GetAvailableModelsAsync(string provider = "openrouter", CancellationToken ct = default);
}
