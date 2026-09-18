using System.Net.Http.Headers;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.Business.Infrastructure.AI;

public class PexelsService : IPexelsService
{
    private readonly HttpClient _httpClient;
    private readonly IFileStorageService _fileStorageService;
    private readonly ILogger<PexelsService> _logger;
    private readonly string? _apiKey;

    public PexelsService(
        HttpClient httpClient,
        IFileStorageService fileStorageService,
        IConfiguration configuration,
        ILogger<PexelsService> logger)
    {
        _httpClient = httpClient;
        _fileStorageService = fileStorageService;
        _logger = logger;
        _apiKey = configuration["Pexels:ApiKey"] ?? configuration["PEXELS_API_KEY"];
    }

    public async Task<string?> SearchPhotoUrlAsync(string query, string orientation = "landscape", CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(_apiKey))
        {
            _logger.LogWarning("Pexels API Key tanımlı değil, görsel aranamıyor.");
            return null;
        }

        try
        {
            using var request = new HttpRequestMessage(
                HttpMethod.Get,
                $"https://api.pexels.com/v1/search?query={Uri.EscapeDataString(query)}&per_page=1&orientation={orientation}");

            request.Headers.Add("Authorization", _apiKey);

            var response = await _httpClient.SendAsync(request, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Pexels API çağrısı başarısız oldu: StatusCode={StatusCode}", response.StatusCode);
                return null;
            }

            var content = await response.Content.ReadAsStringAsync(cancellationToken);
            using var doc = JsonDocument.Parse(content);

            if (doc.RootElement.TryGetProperty("photos", out var photos) && photos.GetArrayLength() > 0)
            {
                var firstPhoto = photos[0];
                if (firstPhoto.TryGetProperty("src", out var src))
                {
                    if (src.TryGetProperty("large", out var largeUrl))
                        return largeUrl.GetString();
                    if (src.TryGetProperty("original", out var originalUrl))
                        return originalUrl.GetString();
                }
            }

            _logger.LogInformation("Pexels aramasında görsel bulunamadı: Query={Query}", query);
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Pexels görsel araması sırasında hata oluştu: Query={Query}", query);
            return null;
        }
    }

    public async Task<string?> SearchAndSaveAssetAsync(Guid projectId, string query, string orientation = "landscape", CancellationToken cancellationToken = default)
    {
        var photoUrl = await SearchPhotoUrlAsync(query, orientation, cancellationToken);
        if (string.IsNullOrEmpty(photoUrl))
        {
            return null;
        }

        try
        {
            var response = await _httpClient.GetAsync(photoUrl, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Pexels görseli indirilemedi: Url={Url}", photoUrl);
                return null;
            }

            await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            var assetId = Guid.NewGuid();
            var objectKey = $"assets/{projectId}/{assetId}.jpg";

            await _fileStorageService.UploadFileAsync(objectKey, stream, "image/jpeg", cancellationToken);
            _logger.LogInformation("Pexels görseli MinIO asset'i olarak kaydedildi: ProjectId={ProjectId}, ObjectKey={ObjectKey}", projectId, objectKey);

            return objectKey;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Pexels görseli indirilip kaydedilirken hata oluştu: ProjectId={ProjectId}, Query={Query}", projectId, query);
            return null;
        }
    }
}
