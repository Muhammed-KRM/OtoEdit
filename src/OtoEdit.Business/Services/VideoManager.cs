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
    private readonly IEdlService? _edlService;

    private static readonly string[] AllowedExtensions = { ".mp4", ".mkv", ".avi", ".mov", ".webm" };
    private const long MaxFileSize = 53687091200L; // 50GB

    public VideoManager(
        IVideoRepository videoRepository,
        IProjectRepository projectRepository,
        IFileStorageService fileStorageService,
        IPublishEndpoint publishEndpoint,
        ILogService logService,
        ILogger<VideoManager> logger,
        IEdlService? edlService = null)
    {
        _videoRepository = videoRepository;
        _projectRepository = projectRepository;
        _fileStorageService = fileStorageService;
        _publishEndpoint = publishEndpoint;
        _logService = logService;
        _logger = logger;
        _edlService = edlService;
    }

    public async Task<VideoListDto> UploadVideoAsync(
        Guid projectId, 
        IFormFile file, 
        bool autoJumpcut = true,
        bool autoRetake = true,
        bool autoBroll = true,
        bool autoSubtitles = true,
        CancellationToken cancellationToken = default,
        bool? audioEnhancementEnabled = null,
        bool? gestureCommandsEnabled = null,
        bool autoDirectorEnabled = false,
        bool directToEditor = false)
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

        bool effectiveAudioEnhancement = audioEnhancementEnabled ?? project.AudioEnhancementEnabled;
        bool effectiveGesture = gestureCommandsEnabled ?? project.GestureCommandsEnabled;
        bool isDirectMode = directToEditor || (!autoJumpcut && !autoRetake && !autoBroll && !autoSubtitles && !effectiveAudioEnhancement && !effectiveGesture && !autoDirectorEnabled);

        if (isDirectMode && _edlService != null)
        {
            string formatStr = project.VideoFormati switch
            {
                VideoFormati.Dikey_9_16 => "9:16",
                VideoFormati.Kare_1_1 => "1:1",
                _ => "16:9"
            };
            string initialEdlJson = $"{{\"version\":\"1.0\",\"projectId\":\"{projectId}\",\"videoId\":\"{video.Id}\",\"duration\":0,\"cuts\":[],\"transcript\":[],\"overlays\":[],\"transitions\":[],\"sfxClips\":[],\"videoClips\":[],\"audioPeaks\":[],\"settings\":{{\"format\":\"{formatStr}\",\"subtitlesEnabled\":false,\"audioCleaned\":false,\"templateId\":\"default\"}}}}";
            using var initialDoc = System.Text.Json.JsonDocument.Parse(initialEdlJson);
            await _edlService.CreateOrUpdateAsync(projectId, initialDoc, cancellationToken);
            video.IslemDurumu = VideoIslemDurumu.AnalizTamamlandi;
            await _videoRepository.SaveChangesAsync();
            await _projectRepository.UpdateStatusAsync(projectId, ProjectDurumu.AnalizTamamlandi);
        }
        else
        {
            // 3. Proje durumunu güncelle
            await _projectRepository.UpdateStatusAsync(projectId, ProjectDurumu.AnalizEdiliyor);
        }

        // 4. RabbitMQ üzerinden Python Worker'a event publish et
        await _publishEndpoint.Publish(new VideoUploadedEvent
        {
            VideoId = video.Id,
            ProjectId = projectId,
            DosyaYolu = objectKey,
            VideoFormati = (int)project.VideoFormati,
            GestureCommandsEnabled = effectiveGesture,
            AudioEnhancementEnabled = effectiveAudioEnhancement,
            AutoJumpcutEnabled = autoJumpcut,
            AutoRetakeEnabled = autoRetake,
            AutoBrollEnabled = autoBroll,
            AutoSubtitlesEnabled = autoSubtitles,
            AutoDirectorEnabled = autoDirectorEnabled,
            DirectToEditor = isDirectMode
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

    public async Task TriggerAnalysisAsync(
        Guid projectId,
        bool autoJumpcut = false,
        bool autoRetake = false,
        bool autoBroll = false,
        bool autoSubtitles = true,
        bool audioEnhancement = false,
        bool gestureCommands = false,
        bool autoDirector = false,
        CancellationToken cancellationToken = default)
    {
        var project = await _projectRepository.GetByIdAsync(projectId)
            ?? throw new NotFoundException("Proje bulunamadı", projectId);
        var video = await _videoRepository.GetByProjectIdAsync(projectId, asNoTracking: false)
            ?? throw new NotFoundException("Projeye ait video bulunamadı", projectId);

        await _projectRepository.UpdateStatusAsync(projectId, ProjectDurumu.AnalizEdiliyor);

        await _publishEndpoint.Publish(new VideoUploadedEvent
        {
            VideoId = video.Id,
            ProjectId = projectId,
            DosyaYolu = video.DosyaYolu,
            VideoFormati = (int)project.VideoFormati,
            GestureCommandsEnabled = gestureCommands,
            AudioEnhancementEnabled = audioEnhancement,
            AutoJumpcutEnabled = autoJumpcut,
            AutoRetakeEnabled = autoRetake,
            AutoBrollEnabled = autoBroll,
            AutoSubtitlesEnabled = autoSubtitles,
            AutoDirectorEnabled = autoDirector,
            DirectToEditor = false
        }, cancellationToken);
    }
}
