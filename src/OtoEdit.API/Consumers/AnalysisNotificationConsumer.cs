using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Enums;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen analiz tamamlanma event'ini dinler.
/// EDL JSON'u veritabanına kaydeder, proje durumunu günceller ve SignalR ile bildirir.
/// </summary>
public class AnalysisNotificationConsumer : IConsumer<AnalysisCompletedEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly IEdlService _edlService;
    private readonly IProjectService _projectService;
    private readonly ILogger<AnalysisNotificationConsumer> _logger;

    public AnalysisNotificationConsumer(
        IHubContext<PipelineHub> hubContext,
        IEdlService edlService,
        IProjectService projectService,
        ILogger<AnalysisNotificationConsumer> logger)
    {
        _hubContext = hubContext;
        _edlService = edlService;
        _projectService = projectService;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<AnalysisCompletedEvent> context)
    {
        var msg = context.Message;
        _logger.LogInformation("AnalysisCompletedEvent alındı: ProjectId={ProjectId}, VideoId={VideoId}", msg.ProjectId, msg.VideoId);

        try
        {
            // 1. EDL JSON'u DB'ye kaydet
            var edl = await _edlService.CreateOrUpdateAsync(msg.ProjectId, msg.EdlJson, context.CancellationToken);

            // 2. Proje durumunu güncelle
            await _projectService.UpdateStatusAsync(msg.ProjectId, ProjectDurumu.AnalizTamamlandi, context.CancellationToken);

            // 3. SignalR ile istemcilere bildir
            await _hubContext.Clients
                .Group($"project-{msg.ProjectId}")
                .SendAsync("AnalysisCompleted", new
                {
                    projectId = msg.ProjectId,
                    edlVersiyon = edl.Versiyon
                }, context.CancellationToken);

            _logger.LogInformation("Analiz tamamlandı ve istemcilere bildirildi: ProjectId={ProjectId}", msg.ProjectId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "AnalysisCompletedEvent işlenirken hata oluştu: ProjectId={ProjectId}", msg.ProjectId);
            throw;
        }
    }
}
