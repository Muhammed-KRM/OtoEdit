using MassTransit;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Video;
using OtoEdit.Business.Events;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;
using OtoEdit.Data.Repositories;

namespace OtoEdit.Business.Services;

/// <summary>
/// Video yükleme, akış ve dosya yönetimi implementasyonu.
/// </summary>
public class VideoManager : IVideoService
{
    private readonly IVideoRepository _videoRepository;
    private readonly IProjectRepository _projectRepository;
    private readonly IFileStorageService _fileStorageService;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogService _logService;
    private readonly ILogger<VideoManager> _logger;

    private static readonly string[] AllowedExtensions = { ".mp4", ".mkv", ".avi", ".mov", ".webm" };
    private const long MaxFileSize = 53687091200L; // 50GB

    public VideoManager(
        IVideoRepository videoRepository,
        IProjectRepository projectRepository,
        IFileStorageService fileStorageService,
        IPublishEndpoint publishEndpoint,
        ILogService logService,
        ILogger<VideoManager> logger)
    {
        _videoRepository = videoRepository;
        _projectRepository = projectRepository;
        _fileStorageService = fileStorageService;
        _publishEndpoint = publishEndpoint;
        _logService = logService;
        _logger = logger;
    }

    public async Task<VideoListDto> UploadVideoAsync(
        Guid projectId, 
        IFormFile file, 
        bool autoJumpcut = true,
        bool autoRetake = true,
        bool autoBroll = true,
        bool autoSubtitles = false,
        CancellationToken cancellationToken = default)
    {
        var project = await _projectRepository.GetByIdAsync(projectId);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", projectId);
        }

        if (file == null || file.Length == 0)
        {
            throw new BusinessException("Video dosyası boş olamaz.");
        }

        if (file.Length > MaxFileSize)
        {
            throw new BusinessException("Video boyutu maksimum 50GB olabilir.");
        }

        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (!AllowedExtensions.Contains(ext))
        {
            throw new BusinessException($"Geçersiz video formatı. İzin verilenler: {string.Join(", ", AllowedExtensions)}");
        }

        var videoId = Guid.NewGuid();
        var objectKey = $"videos/{projectId}/{videoId}{ext}";

        // 1. MinIO'ya stream ile yükle
        using (var stream = file.OpenReadStream())
        {
            await _fileStorageService.UploadFileAsync(objectKey, stream, file.ContentType, cancellationToken);
        }

        // 2. Video entity oluştur ve DB'ye kaydet
        var video = new Video
        {
            Id = videoId,
            ProjectId = projectId,
            Baslik = Path.GetFileNameWithoutExtension(file.FileName),
            DosyaYolu = objectKey,
            DosyaBoyutu = file.Length,
            IslemDurumu = VideoIslemDurumu.Bekliyor,
            OlusturmaTarihi = DateTime.UtcNow
        };

        await _videoRepository.AddAsync(video);
        await _videoRepository.SaveChangesAsync();

        // 3. Proje durumunu güncelle
        await _projectRepository.UpdateStatusAsync(projectId, ProjectDurumu.AnalizEdiliyor);

        // 4. RabbitMQ üzerinden Python Worker'a event publish et
        await _publishEndpoint.Publish(new VideoUploadedEvent
        {
            VideoId = video.Id,
            ProjectId = projectId,
            DosyaYolu = objectKey,
            VideoFormati = (int)project.VideoFormati,
            GestureCommandsEnabled = project.GestureCommandsEnabled,
            AudioEnhancementEnabled = project.AudioEnhancementEnabled,
            AutoJumpcutEnabled = autoJumpcut,
            AutoRetakeEnabled = autoRetake,
            AutoBrollEnabled = autoBroll,
            AutoSubtitlesEnabled = autoSubtitles
        }, cancellationToken);

        _logger.LogInformation("VideoUploadedEvent publish edildi: VideoId={VideoId}, ProjectId={ProjectId}", video.Id, projectId);

        return new VideoListDto
        {
            Id = video.Id,
            ProjectId = video.ProjectId,
            Baslik = video.Baslik,
            DosyaBoyutu = video.DosyaBoyutu,
            IslemDurumu = video.IslemDurumu,
            OlusturmaTarihi = video.OlusturmaTarihi
        };
    }

    public async Task<VideoDetailDto?> GetVideoByProjectIdAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var video = await _videoRepository.GetByProjectIdAsync(projectId, asNoTracking: true);
        if (video == null) return null;

        return new VideoDetailDto
        {
            Id = video.Id,
            ProjectId = video.ProjectId,
            Baslik = video.Baslik,
            DosyaYolu = video.DosyaYolu,
            TemizSesYolu = video.TemizSesYolu,
            Sure = video.Sure,
            DosyaBoyutu = video.DosyaBoyutu,
            IslemDurumu = video.IslemDurumu,
            OlusturmaTarihi = video.OlusturmaTarihi,
            IslemTamamlanmaTarihi = video.IslemTamamlanmaTarihi,
            TranskriptVar = video.Transcript != null
        };
    }

    public async Task DeleteVideoAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var video = await _videoRepository.GetByProjectIdAsync(projectId, asNoTracking: false);
        if (video == null)
        {
            throw new NotFoundException("Projeye ait video bulunamadı", projectId);
        }

        try
        {
            await _fileStorageService.DeleteFileAsync(video.DosyaYolu, cancellationToken);
            if (!string.IsNullOrEmpty(video.TemizSesYolu))
            {
                await _fileStorageService.DeleteFileAsync(video.TemizSesYolu, cancellationToken);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "MinIO video dosyası silinemedi: VideoId={VideoId}", video.Id);
        }

        _videoRepository.Delete(video);
        await _videoRepository.SaveChangesAsync();
    }

    private static readonly HttpClient _httpClient = new HttpClient();

    public async Task<(Stream FileStream, string ContentType, string FileName)> GetVideoStreamAsync(Guid videoId, CancellationToken cancellationToken = default)
    {
        var video = await _videoRepository.GetByIdAsync(videoId);
        if (video == null) throw new NotFoundException("Video bulunamadı", videoId);
        var presignedUrl = await _fileStorageService.GetPresignedUrlAsync(video.DosyaYolu, TimeSpan.FromHours(12), cancellationToken);
        var request = new HttpRequestMessage(HttpMethod.Get, presignedUrl);
        var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();
        var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        
        var ext = Path.GetExtension(video.DosyaYolu).ToLowerInvariant();
        var contentType = ext switch { ".mp4" => "video/mp4", ".webm" => "video/webm", ".mov" => "video/quicktime", ".mkv" => "video/x-matroska", _ => "application/octet-stream" };
        return (stream, contentType, $"{video.Baslik}{ext}");
    }

    public async Task<string> GetVideoUrlAsync(Guid videoId, CancellationToken cancellationToken = default)
    {
        var video = await _videoRepository.GetByIdAsync(videoId);
        if (video == null) throw new NotFoundException("Video bulunamadı", videoId);

        var presignedUrl = await _fileStorageService.GetPresignedUrlAsync(video.DosyaYolu, TimeSpan.FromHours(12), cancellationToken);
        // Replace internal docker network host 'minio' with 'localhost' so the browser can reach it.
        if (presignedUrl.Contains("://minio:"))
        {
            presignedUrl = presignedUrl.Replace("://minio:", "://localhost:");
        }
        
        return presignedUrl;
    }
}
