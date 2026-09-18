using System.Text.Json;
using MassTransit;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Render;
using OtoEdit.Business.Events;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Services;

/// <summary>
/// Video render iş yönetimi implementasyonu.
/// </summary>
public class RenderManager : IRenderService
{
    private readonly AppDbContext _context;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly IFileStorageService _fileStorageService;
    private readonly ILogger<RenderManager> _logger;

    public RenderManager(
        AppDbContext context,
        IPublishEndpoint publishEndpoint,
        IFileStorageService fileStorageService,
        ILogger<RenderManager> logger)
    {
        _context = context;
        _publishEndpoint = publishEndpoint;
        _fileStorageService = fileStorageService;
        _logger = logger;
    }

    public async Task<RenderStatusDto> RequestRenderAsync(Guid projectId, RenderRequestDto? requestDto = null, CancellationToken cancellationToken = default)
    {
        var project = await _context.Projects
            .Include(p => p.EditDecisionList)
            .FirstOrDefaultAsync(p => p.Id == projectId, cancellationToken);

        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", projectId);
        }

        if (project.EditDecisionList == null || string.IsNullOrWhiteSpace(project.EditDecisionList.EdlJson))
        {
            throw new BusinessException("Projeye ait geçerli bir EDL bulunamadı. Render başlatılamaz.");
        }

        var renderJob = new RenderJob
        {
            ProjectId = projectId,
            EdlSnapshot = project.EditDecisionList.EdlJson,
            Durum = RenderDurumu.Kuyrukta,
            BaslangicZamani = DateTime.UtcNow
        };

        _context.RenderJobs.Add(renderJob);
        project.Durum = ProjectDurumu.RenderEdiliyor;
        await _context.SaveChangesAsync(cancellationToken);

        // RabbitMQ üzerinden Python Worker'a event publish et
        await _publishEndpoint.Publish(new RenderRequestedEvent
        {
            RenderJobId = renderJob.Id,
            ProjectId = projectId,
            EdlJson = JsonDocument.Parse(renderJob.EdlSnapshot)
        }, cancellationToken);

        _logger.LogInformation("RenderRequestedEvent publish edildi: RenderJobId={RenderJobId}, ProjectId={ProjectId}", renderJob.Id, projectId);

        return new RenderStatusDto
        {
            RenderJobId = renderJob.Id,
            ProjectId = projectId,
            Durum = renderJob.Durum,
            BaslangicZamani = renderJob.BaslangicZamani
        };
    }

    public async Task<RenderStatusDto> GetRenderStatusAsync(Guid projectId, Guid renderJobId, CancellationToken cancellationToken = default)
    {
        var renderJob = await _context.RenderJobs
            .AsNoTracking()
            .FirstOrDefaultAsync(r => r.Id == renderJobId && r.ProjectId == projectId, cancellationToken);

        if (renderJob == null)
        {
            throw new NotFoundException("Render görevi bulunamadı", renderJobId);
        }

        return new RenderStatusDto
        {
            RenderJobId = renderJob.Id,
            ProjectId = renderJob.ProjectId,
            Durum = renderJob.Durum,
            CiktiYolu = renderJob.CiktiYolu,
            BaslangicZamani = renderJob.BaslangicZamani,
            BitisZamani = renderJob.BitisZamani,
            SureMs = renderJob.SureMs,
            HataMesaji = renderJob.HataMesaji
        };
    }

    public async Task<string> GetDownloadUrlAsync(Guid projectId, Guid renderJobId, CancellationToken cancellationToken = default)
    {
        var renderJob = await _context.RenderJobs
            .AsNoTracking()
            .FirstOrDefaultAsync(r => r.Id == renderJobId && r.ProjectId == projectId, cancellationToken);

        if (renderJob == null)
        {
            throw new NotFoundException("Render görevi bulunamadı", renderJobId);
        }

        if (string.IsNullOrEmpty(renderJob.CiktiYolu))
        {
            throw new BusinessException("Render çıktısı henüz hazır değil.");
        }

        return await _fileStorageService.GetPresignedUrlAsync(renderJob.CiktiYolu, TimeSpan.FromHours(2), cancellationToken);
    }

    public async Task CompleteRenderAsync(Guid renderJobId, string indirmeUrl, CancellationToken cancellationToken = default)
    {
        var renderJob = await _context.RenderJobs.FindAsync(new object[] { renderJobId }, cancellationToken);
        if (renderJob != null)
        {
            renderJob.Durum = RenderDurumu.Tamamlandi;
            renderJob.CiktiYolu = indirmeUrl;
            renderJob.BitisZamani = DateTime.UtcNow;
            renderJob.SureMs = (int)(renderJob.BitisZamani.Value - renderJob.BaslangicZamani).TotalMilliseconds;

            var project = await _context.Projects.FindAsync(new object[] { renderJob.ProjectId }, cancellationToken);
            if (project != null)
            {
                project.Durum = ProjectDurumu.Tamamlandi;
            }

            await _context.SaveChangesAsync(cancellationToken);
            _logger.LogInformation("Render tamamlandı olarak işaretlendi: RenderJobId={RenderJobId}", renderJobId);
        }
    }

    public async Task FailRenderAsync(Guid renderJobId, string hataMesaji, CancellationToken cancellationToken = default)
    {
        var renderJob = await _context.RenderJobs.FindAsync(new object[] { renderJobId }, cancellationToken);
        if (renderJob != null)
        {
            renderJob.Durum = RenderDurumu.Hata;
            renderJob.HataMesaji = hataMesaji;
            renderJob.BitisZamani = DateTime.UtcNow;
            renderJob.SureMs = (int)(renderJob.BitisZamani.Value - renderJob.BaslangicZamani).TotalMilliseconds;

            await _context.SaveChangesAsync(cancellationToken);
            _logger.LogInformation("Render hata olarak işaretlendi: RenderJobId={RenderJobId}", renderJobId);
        }
    }
}
