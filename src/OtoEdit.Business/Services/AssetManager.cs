using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Asset;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Services;

/// <summary>
/// Medya Kütüphanesi varlıkları yönetimi iş mantığı implementasyonu.
/// </summary>
public class AssetManager : IAssetService
{
    private readonly AppDbContext _context;
    private readonly IFileStorageService _fileStorageService;
    private readonly ILogger<AssetManager> _logger;

    public const long MaxFileSize = 52428800; // 50MB
    public static readonly HashSet<string> AllowedExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        // Resimler
        ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
        // Sesler
        ".mp3", ".wav", ".aac", ".m4a", ".ogg",
        // B-Roll / Kısa Videolar
        ".mp4", ".mov", ".webm"
    };

    public AssetManager(
        AppDbContext context,
        IFileStorageService fileStorageService,
        ILogger<AssetManager> logger)
    {
        _context = context;
        _fileStorageService = fileStorageService;
        _logger = logger;
    }

    public async Task<ProjectAssetDto> UploadAssetAsync(Guid projectId, IFormFile file, CancellationToken cancellationToken = default)
    {
        var project = await _context.Projects.FindAsync(new object[] { projectId }, cancellationToken);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", projectId);
        }

        if (file == null || file.Length == 0)
        {
            throw new BusinessException("Yüklenecek medya dosyası boş olamaz.");
        }

        if (file.Length > MaxFileSize)
        {
            throw new BusinessException("Medya boyutu maksimum 50MB olabilir.");
        }

        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (!AllowedExtensions.Contains(ext))
        {
            throw new BusinessException($"Geçersiz dosya formatı. İzin verilen formatlar: {string.Join(", ", AllowedExtensions)}");
        }

        var assetId = Guid.NewGuid();
        var objectKey = $"assets/{projectId}/{assetId}{ext}";

        // 1. MinIO S3 bucket'ına stream ile yükle
        using (var stream = file.OpenReadStream())
        {
            var contentType = string.IsNullOrWhiteSpace(file.ContentType) ? GetDefaultContentType(ext) : file.ContentType;
            await _fileStorageService.UploadFileAsync(objectKey, stream, contentType, cancellationToken);
        }

        // 2. Presigned URL oluştur
        var presignedUrl = await GetSanitizedPresignedUrlAsync(objectKey, cancellationToken);

        // 3. Veritabanına kaydet
        var asset = new ProjectAsset
        {
            Id = assetId,
            ProjectId = projectId,
            DosyaAdi = file.FileName,
            MimeTuru = string.IsNullOrWhiteSpace(file.ContentType) ? GetDefaultContentType(ext) : file.ContentType,
            StorageKey = objectKey,
            Url = presignedUrl,
            BoyutByte = file.Length,
            YuklemeTarihi = DateTime.UtcNow
        };

        _context.ProjectAssets.Add(asset);
        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Yeni medya varlığı yüklendi: AssetId={AssetId}, ProjectId={ProjectId}, DosyaAdi={DosyaAdi}", 
            assetId, projectId, file.FileName);

        return new ProjectAssetDto
        {
            Id = asset.Id,
            ProjectId = asset.ProjectId,
            DosyaAdi = asset.DosyaAdi,
            MimeTuru = asset.MimeTuru,
            Url = asset.Url,
            BoyutByte = asset.BoyutByte,
            YuklemeTarihi = asset.YuklemeTarihi
        };
    }

    public async Task<IEnumerable<ProjectAssetDto>> GetProjectAssetsAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var assets = await _context.ProjectAssets
            .Where(a => a.ProjectId == projectId)
            .OrderByDescending(a => a.YuklemeTarihi)
            .AsNoTracking()
            .ToListAsync(cancellationToken);

        var result = new List<ProjectAssetDto>(assets.Count);
        foreach (var a in assets)
        {
            var freshUrl = await GetSanitizedPresignedUrlAsync(a.StorageKey, cancellationToken);
            result.Add(new ProjectAssetDto
            {
                Id = a.Id,
                ProjectId = a.ProjectId,
                DosyaAdi = a.DosyaAdi,
                MimeTuru = a.MimeTuru,
                Url = freshUrl,
                BoyutByte = a.BoyutByte,
                YuklemeTarihi = a.YuklemeTarihi
            });
        }

        return result;
    }

    public async Task DeleteAssetAsync(Guid projectId, Guid assetId, CancellationToken cancellationToken = default)
    {
        var asset = await _context.ProjectAssets
            .FirstOrDefaultAsync(a => a.ProjectId == projectId && a.Id == assetId, cancellationToken);

        if (asset == null)
        {
            throw new NotFoundException("Medya varlığı bulunamadı", assetId);
        }

        try
        {
            await _fileStorageService.DeleteFileAsync(asset.StorageKey, cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "MinIO medya dosyası silinemedi: StorageKey={StorageKey}", asset.StorageKey);
        }

        _context.ProjectAssets.Remove(asset);
        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Medya varlığı silindi: AssetId={AssetId}, ProjectId={ProjectId}", assetId, projectId);
    }

    public async Task<(Stream FileStream, string ContentType, string FileName)> GetAssetStreamAsync(Guid projectId, Guid assetId, CancellationToken cancellationToken = default)
    {
        var asset = await _context.ProjectAssets
            .AsNoTracking()
            .FirstOrDefaultAsync(a => a.ProjectId == projectId && a.Id == assetId, cancellationToken);

        if (asset == null)
        {
            throw new NotFoundException("Medya varlığı bulunamadı", assetId);
        }

        var stream = await _fileStorageService.DownloadFileAsync(asset.StorageKey, cancellationToken);
        return (stream, asset.MimeTuru, asset.DosyaAdi);
    }

    public async Task<string> GetAssetUrlAsync(Guid projectId, Guid assetId, CancellationToken cancellationToken = default)
    {
        var asset = await _context.ProjectAssets
            .AsNoTracking()
            .FirstOrDefaultAsync(a => a.ProjectId == projectId && a.Id == assetId, cancellationToken);

        if (asset == null)
        {
            throw new NotFoundException("Medya varlığı bulunamadı", assetId);
        }

        return await GetSanitizedPresignedUrlAsync(asset.StorageKey, cancellationToken);
    }

    private async Task<string> GetSanitizedPresignedUrlAsync(string objectKey, CancellationToken cancellationToken)
    {
        var presignedUrl = await _fileStorageService.GetPresignedUrlAsync(objectKey, TimeSpan.FromHours(24), cancellationToken);
        if (presignedUrl.Contains("://minio:"))
        {
            presignedUrl = presignedUrl.Replace("://minio:", "://localhost:");
        }
        return presignedUrl;
    }

    private static string GetDefaultContentType(string ext) => ext switch
    {
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".webp" => "image/webp",
        ".gif" => "image/gif",
        ".svg" => "image/svg+xml",
        ".mp3" => "audio/mpeg",
        ".wav" => "audio/wav",
        ".aac" => "audio/aac",
        ".m4a" => "audio/mp4",
        ".ogg" => "audio/ogg",
        ".mp4" => "video/mp4",
        ".mov" => "video/quicktime",
        ".webm" => "video/webm",
        _ => "application/octet-stream"
    };
}
