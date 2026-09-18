using Microsoft.Extensions.Logging;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Services;

/// <summary>
/// Pipeline canlı durum ve ilerleme bildirim servisi.
/// </summary>
public class PipelineNotificationManager : IPipelineNotificationService
{
    private readonly ILogger<PipelineNotificationManager> _logger;

    // HubContext veya SignalR delegation API katmanında veya burada delegate ile bağlanır.
    public static Func<Guid, string, object, Task>? SendSignalRMessageAsync { get; set; }

    public PipelineNotificationManager(ILogger<PipelineNotificationManager> logger)
    {
        _logger = logger;
    }

    public async Task NotifyAnalysisProgressAsync(Guid projectId, PipelineAsamasi asama, int yuzde, string? mesaj, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("AnalysisProgress: ProjectId={ProjectId}, Asama={Asama}, Yuzde={Yuzde}", projectId, asama, yuzde);
        if (SendSignalRMessageAsync != null)
        {
            await SendSignalRMessageAsync(projectId, "AnalysisProgress", new
            {
                projectId,
                asama = asama.ToString(),
                yuzde,
                mesaj
            });
        }
    }

    public async Task NotifyAnalysisCompletedAsync(Guid projectId, int edlVersiyon, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("AnalysisCompleted: ProjectId={ProjectId}, Versiyon={Versiyon}", projectId, edlVersiyon);
        if (SendSignalRMessageAsync != null)
        {
            await SendSignalRMessageAsync(projectId, "AnalysisCompleted", new
            {
                projectId,
                edlVersiyon
            });
        }
    }

    public async Task NotifyRenderProgressAsync(Guid projectId, Guid renderJobId, int yuzde, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("RenderProgress: ProjectId={ProjectId}, RenderJobId={RenderJobId}, Yuzde={Yuzde}", projectId, renderJobId, yuzde);
        if (SendSignalRMessageAsync != null)
        {
            await SendSignalRMessageAsync(projectId, "RenderProgress", new
            {
                projectId,
                renderJobId,
                yuzde
            });
        }
    }

    public async Task NotifyRenderCompletedAsync(Guid projectId, Guid renderJobId, string indirmeUrl, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("RenderCompleted: ProjectId={ProjectId}, RenderJobId={RenderJobId}", projectId, renderJobId);
        if (SendSignalRMessageAsync != null)
        {
            await SendSignalRMessageAsync(projectId, "RenderCompleted", new
            {
                projectId,
                renderJobId,
                indirmeUrl
            });
        }
    }

    public async Task NotifyPipelineErrorAsync(Guid projectId, Guid? videoId, string asama, string hataMesaji, CancellationToken cancellationToken = default)
    {
        _logger.LogError("PipelineError: ProjectId={ProjectId}, Asama={Asama}, Hata={Hata}", projectId, asama, hataMesaji);
        if (SendSignalRMessageAsync != null)
        {
            await SendSignalRMessageAsync(projectId, "PipelineError", new
            {
                projectId,
                videoId,
                asama,
                hataMesaji
            });
        }
    }
}
