using FluentValidation;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Project;
using OtoEdit.Business.DTOs.Render;
using OtoEdit.Business.DTOs.Video;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;
using OtoEdit.Data.Repositories;

namespace OtoEdit.Business.Services;

/// <summary>
/// Proje yönetimi iş mantığı implementasyonu.
/// </summary>
public class ProjectManager : IProjectService
{
    private readonly IProjectRepository _projectRepository;
    private readonly IFileStorageService _fileStorageService;
    private readonly ICacheService _cacheService;
    private readonly IValidator<ProjectCreateDto> _createValidator;
    private readonly IValidator<ProjectUpdateDto> _updateValidator;
    private readonly ILogService _logService;
    private readonly ILogger<ProjectManager> _logger;

    private const string CachePrefix = "project:";

    public ProjectManager(
        IProjectRepository projectRepository,
        IFileStorageService fileStorageService,
        ICacheService cacheService,
        IValidator<ProjectCreateDto> createValidator,
        IValidator<ProjectUpdateDto> updateValidator,
        ILogService logService,
        ILogger<ProjectManager> logger)
    {
        _projectRepository = projectRepository;
        _fileStorageService = fileStorageService;
        _cacheService = cacheService;
        _createValidator = createValidator;
        _updateValidator = updateValidator;
        _logService = logService;
        _logger = logger;
    }

    public async Task<IEnumerable<ProjectListDto>> GetAllAsync(CancellationToken cancellationToken = default)
    {
        var (items, _) = await _projectRepository.GetProjectsPagedAsync(1, 100, asNoTracking: true);
        return items.Select(p => new ProjectListDto
        {
            Id = p.Id,
            Ad = p.Ad,
            VideoFormati = p.VideoFormati,
            Durum = p.Durum,
            OlusturmaTarihi = p.OlusturmaTarihi,
            VideoSayisi = p.Video != null ? 1 : 0,
            TemplateAd = p.Template?.Ad
        });
    }

    public async Task<ProjectDetailDto> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var cacheKey = $"{CachePrefix}{id}";
        var cached = await _cacheService.GetAsync<ProjectDetailDto>(cacheKey, cancellationToken);
        if (cached != null)
        {
            return cached;
        }

        var project = await _projectRepository.GetProjectWithDetailsAsync(id, asNoTracking: true);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", id);
        }

        var sonRenderJob = project.RenderJobs.OrderByDescending(r => r.BaslangicZamani).FirstOrDefault();

        var dto = new ProjectDetailDto
        {
            Id = project.Id,
            Ad = project.Ad,
            Aciklama = project.Aciklama,
            VideoFormati = project.VideoFormati,
            TemplateId = project.TemplateId,
            TemplateAd = project.Template?.Ad,
            GestureCommandsEnabled = project.GestureCommandsEnabled,
            AudioEnhancementEnabled = project.AudioEnhancementEnabled,
            Durum = project.Durum,
            OlusturmaTarihi = project.OlusturmaTarihi,
            GuncellemeTarihi = project.GuncellemeTarihi,
            Video = project.Video != null ? new VideoDetailDto
            {
                Id = project.Video.Id,
                ProjectId = project.Video.ProjectId,
                Baslik = project.Video.Baslik,
                DosyaYolu = project.Video.DosyaYolu,
                TemizSesYolu = project.Video.TemizSesYolu,
                Sure = project.Video.Sure,
                DosyaBoyutu = project.Video.DosyaBoyutu,
                IslemDurumu = project.Video.IslemDurumu,
                OlusturmaTarihi = project.Video.OlusturmaTarihi,
                IslemTamamlanmaTarihi = project.Video.IslemTamamlanmaTarihi,
                TranskriptVar = project.Video.Transcript != null
            } : null,
            EdlVersiyon = project.EditDecisionList?.Versiyon,
            ChatMesajSayisi = project.ChatMessages.Count,
            SonRender = sonRenderJob != null ? new RenderStatusDto
            {
                RenderJobId = sonRenderJob.Id,
                ProjectId = sonRenderJob.ProjectId,
                Durum = sonRenderJob.Durum,
                CiktiYolu = sonRenderJob.CiktiYolu,
                BaslangicZamani = sonRenderJob.BaslangicZamani,
                BitisZamani = sonRenderJob.BitisZamani,
                SureMs = sonRenderJob.SureMs,
                HataMesaji = sonRenderJob.HataMesaji
            } : null
        };

        await _cacheService.SetAsync(cacheKey, dto, TimeSpan.FromMinutes(5), cancellationToken);
        return dto;
    }

    public async Task<ProjectDetailDto> CreateAsync(ProjectCreateDto dto, CancellationToken cancellationToken = default)
    {
        var validationResult = await _createValidator.ValidateAsync(dto, cancellationToken);
        if (!validationResult.IsValid)
        {
            throw new BusinessException(validationResult.Errors.First().ErrorMessage);
        }

        var project = new Project
        {
            Ad = dto.Ad,
            Aciklama = dto.Aciklama,
            VideoFormati = dto.VideoFormati,
            TemplateId = dto.TemplateId,
            GestureCommandsEnabled = dto.GestureCommandsEnabled,
            AudioEnhancementEnabled = dto.AudioEnhancementEnabled,
            Durum = ProjectDurumu.Taslak,
            OlusturmaTarihi = DateTime.UtcNow
        };

        await _projectRepository.AddAsync(project);
        await _projectRepository.SaveChangesAsync();

        _logger.LogInformation("Yeni proje oluşturuldu: Id={Id}, Ad={Ad}", project.Id, project.Ad);
        return await GetByIdAsync(project.Id, cancellationToken);
    }

    public async Task<ProjectDetailDto> UpdateAsync(Guid id, ProjectUpdateDto dto, CancellationToken cancellationToken = default)
    {
        var validationResult = await _updateValidator.ValidateAsync(dto, cancellationToken);
        if (!validationResult.IsValid)
        {
            throw new BusinessException(validationResult.Errors.First().ErrorMessage);
        }

        var project = await _projectRepository.GetByIdAsync(id);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", id);
        }

        project.Ad = dto.Ad;
        project.Aciklama = dto.Aciklama;
        project.VideoFormati = dto.VideoFormati;
        project.TemplateId = dto.TemplateId;
        project.GestureCommandsEnabled = dto.GestureCommandsEnabled;
        project.AudioEnhancementEnabled = dto.AudioEnhancementEnabled;
        project.GuncellemeTarihi = DateTime.UtcNow;

        _projectRepository.Update(project);
        await _projectRepository.SaveChangesAsync();

        await _cacheService.RemoveAsync($"{CachePrefix}{id}", cancellationToken);
        return await GetByIdAsync(id, cancellationToken);
    }

    public async Task DeleteAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var project = await _projectRepository.GetByIdAsync(id);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", id);
        }

        // 1. MinIO S3 Temizliği (Uygulama Seviyesi: videos/{id}/, audio/{id}/, renders/{id}/)
        try
        {
            await _fileStorageService.DeleteDirectoryAsync($"videos/{id}/", cancellationToken);
            await _fileStorageService.DeleteDirectoryAsync($"audio/{id}/", cancellationToken);
            await _fileStorageService.DeleteDirectoryAsync($"renders/{id}/", cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Proje silinirken MinIO dosyaları silinemedi: ProjectId={Id}", id);
        }

        // 2. PostgreSQL DB CASCADE silme
        _projectRepository.Delete(project);
        await _projectRepository.SaveChangesAsync();

        await _cacheService.RemoveAsync($"{CachePrefix}{id}", cancellationToken);
        _logger.LogInformation("Proje ve bağlı tüm kayıtlar silindi: ProjectId={Id}", id);
    }

    public async Task UpdateStatusAsync(Guid id, ProjectDurumu durum, CancellationToken cancellationToken = default)
    {
        var success = await _projectRepository.UpdateStatusAsync(id, durum);
        if (!success)
        {
            throw new NotFoundException("Proje bulunamadı", id);
        }

        await _cacheService.RemoveAsync($"{CachePrefix}{id}", cancellationToken);
    }
}
