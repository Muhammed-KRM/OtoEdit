using System.Text.Json;
using System.Text.RegularExpressions;

namespace OtoEdit.Business.Helpers;

/// <summary>
/// Loglara hassas veri (şifre, token, API key, e-posta) sızmasını önleyen maskeleme yardımcısı.
/// </summary>
public static class SensitiveDataMasker
{
    private static readonly Regex EmailRegex = new(
        @"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    private static readonly Regex JsonSensitiveKeyRegex = new(
        @"""(?i)(password|token|apiKey|api_key|secret|authorization|access_token)""\s*:\s*""([^""]+)""",
        RegexOptions.Compiled);

    private static readonly Regex HeaderApiKeyRegex = new(
        @"(X-API-Key|Bearer)\s*[:=]\s*([^\s,;]+)",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    /// <summary>
    /// Metin içerisindeki e-posta, şifre, anahtar gibi hassas alanları maskeler.
    /// </summary>
    public static string? Mask(string? input)
    {
        if (string.IsNullOrWhiteSpace(input))
            return input;

        // JSON anahtarlarını maskele
        var masked = JsonSensitiveKeyRegex.Replace(input, "\"$1\": \"***\"");

        // Header ve key eşleşmelerini maskele
        masked = HeaderApiKeyRegex.Replace(masked, "$1: ***");

        // E-postaları maskele
        masked = EmailRegex.Replace(masked, "***@***.***");

        return masked;
    }

    public static string? MaskJson(string? input) => Mask(input);

    /// <summary>
    /// PostgreSQL jsonb kolonlarına (girdi_metadata, cikti_metadata) yazılacak metnin
    /// her zaman geçerli bir JSON dokümanı olmasını garanti eder (22P02 hatasını önler).
    /// </summary>
    public static string? EnsureValidJsonb(string? input)
    {
        var masked = Mask(input);
        if (string.IsNullOrWhiteSpace(masked))
            return null;

        var trimmed = masked.Trim();
        if ((trimmed.StartsWith('{') && trimmed.EndsWith('}')) ||
            (trimmed.StartsWith('[') && trimmed.EndsWith(']')))
        {
            try
            {
                using var _ = JsonDocument.Parse(trimmed);
                return trimmed;
            }
            catch
            {
                // Geçersiz JSON ise aşağıda güvenli nesneye sarılır
            }
        }

        return JsonSerializer.Serialize(new { message = masked });
    }
}
