using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Enums;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen 3. tur kurgu senaryosu onay/revizyon bildirimini dinler.
/// Taslak EDL ve MasterEditingScript'i kaydeder, proje durumunu SenaryoOnayiBekliyor yapar ve SignalR ile bildirir.
/// </summary>
public class ScenarioNotificationConsumer : IConsumer<ScenarioApprovalRequiredEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly IEdlService _edlService;
    private readonly IProjectService _projectService;
    private readonly ILogger<ScenarioNotificationConsumer> _logger;

    public ScenarioNotificationConsumer(
        IHubContext<PipelineHub> hubContext,
        IEdlService edlService,
        IProjectService projectService,
        ILogger<ScenarioNotificationConsumer> logger)
    {
        _hubContext = hubContext;
        _edlService = edlService;
        _projectService = projectService;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<ScenarioApprovalRequiredEvent> context)
    {
        var msg = context.Message;
        _logger.LogInformation(
            "ScenarioApprovalRequiredEvent alındı: ProjectId={ProjectId}, VideoId={VideoId}, Tur={IterationCount}",
            msg.ProjectId, msg.VideoId, msg.IterationCount);

        try
        {
            var edl = await _edlService.CreateOrUpdateAsync(msg.ProjectId, msg.EdlJson, context.CancellationToken);

            await _projectService.UpdateStatusAsync(
                msg.ProjectId,
                ProjectDurumu.SenaryoOnayiBekliyor,
                context.CancellationToken);

            await _hubContext.Clients
                .Group($"project-{msg.ProjectId}")
                .SendAsync("ScenarioApprovalRequired", new
                {
                    projectId = msg.ProjectId,
                    videoId = msg.VideoId,
                    iterationCount = msg.IterationCount,
                    criticMessage = msg.CriticMessage,
                    masterScript = msg.MasterScript,
                    edlVersiyon = edl.Versiyon
                }, context.CancellationToken);

            _logger.LogInformation("Senaryo onayı bildirimi istemcilere gönderildi: ProjectId={ProjectId}", msg.ProjectId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "ScenarioApprovalRequiredEvent işlenirken hata oluştu: ProjectId={ProjectId}", msg.ProjectId);
            throw;
        }
    }
}
