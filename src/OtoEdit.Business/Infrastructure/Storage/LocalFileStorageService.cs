using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.Business.Infrastructure.Storage;

/// <summary>
/// Yerel disk tabanlı dosya depolama implementasyonu (Fallback ve yerel test amaçlı).
/// </summary>
public class LocalFileStorageService : IFileStorageService
{
    private readonly string _basePath;
    private readonly ILogger<LocalFileStorageService> _logger;

    public LocalFileStorageService(IHostEnvironment environment, ILogger<LocalFileStorageService> logger)
    {
        _logger = logger;
        _basePath = Path.Combine(environment.ContentRootPath, "App_Data", "Storage");
        if (!Directory.Exists(_basePath))
        {
            Directory.CreateDirectory(_basePath);
        }
    }

    public async Task<string> UploadFileAsync(string objectKey, Stream content, string contentType, CancellationToken cancellationToken = default)
    {
        var fullPath = Path.Combine(_basePath, objectKey.Replace('/', Path.DirectorySeparatorChar));
        var dir = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }

        using var fileStream = new FileStream(fullPath, FileMode.Create, FileAccess.Write, FileShare.None);
        await content.CopyToAsync(fileStream, cancellationToken);
        _logger.LogInformation("Dosya yerel diske kaydedildi: Path={Path}", fullPath);
        return objectKey;
    }

    public Task<Stream> DownloadFileAsync(string objectKey, CancellationToken cancellationToken = default)
    {
        var fullPath = Path.Combine(_basePath, objectKey.Replace('/', Path.DirectorySeparatorChar));
        if (!File.Exists(fullPath))
        {
            throw new FileNotFoundException("Dosya bulunamadı", fullPath);
        }

        var memoryStream = new MemoryStream();
        using (var fileStream = new FileStream(fullPath, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            fileStream.CopyTo(memoryStream);
        }
        memoryStream.Position = 0;
        return Task.FromResult<Stream>(memoryStream);
    }

    public Task<string> GetPresignedUrlAsync(string objectKey, TimeSpan expiry, CancellationToken cancellationToken = default)
    {
        // Yerel depolama için doğrudan göreceli indirme URL'i
        return Task.FromResult($"/api/storage/{objectKey}");
    }

    public Task DeleteFileAsync(string objectKey, CancellationToken cancellationToken = default)
    {
        var fullPath = Path.Combine(_basePath, objectKey.Replace('/', Path.DirectorySeparatorChar));
        if (File.Exists(fullPath))
        {
            File.Delete(fullPath);
        }
        return Task.CompletedTask;
    }

    public Task DeleteDirectoryAsync(string prefix, CancellationToken cancellationToken = default)
    {
        var fullPath = Path.Combine(_basePath, prefix.Replace('/', Path.DirectorySeparatorChar));
        if (Directory.Exists(fullPath))
        {
            Directory.Delete(fullPath, true);
        }
        return Task.CompletedTask;
    }
}
