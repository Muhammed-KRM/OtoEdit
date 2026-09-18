using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Enums;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen aşama ilerleme ve hata bildirimlerini dinler,
/// SignalR üzerinden canlı olarak istemciye iletir.
/// </summary>
public class PipelineProgressConsumer :
    IConsumer<PipelineStageChangedEvent>,
    IConsumer<PipelineErrorEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly IProjectService _projectService;
    private readonly ILogger<PipelineProgressConsumer> _logger;

    public PipelineProgressConsumer(
        IHubContext<PipelineHub> hubContext,
        IProjectService projectService,
        ILogger<PipelineProgressConsumer> logger)
    {
        _hubContext = hubContext;
        _projectService = projectService;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<PipelineStageChangedEvent> context)
    {
        var msg = context.Message;
        _logger.LogInformation("PipelineStageChanged: ProjectId={ProjectId}, Asama={Asama}, Yuzde={Yuzde}, Mesaj={Mesaj}",
            msg.ProjectId, msg.Asama, msg.Yuzde, msg.Mesaj);

        await _hubContext.Clients
            .Group($"project-{msg.ProjectId}")
            .SendAsync("AnalysisProgress", new
            {
                projectId = msg.ProjectId,
                asama = msg.Asama.ToString(),
                yuzde = msg.Yuzde,
                mesaj = msg.Mesaj
            }, context.CancellationToken);
    }

    public async Task Consume(ConsumeContext<PipelineErrorEvent> context)
    {
        var msg = context.Message;
        _logger.LogError("PipelineError: ProjectId={ProjectId}, Asama={Asama}, Hata={Hata}",
            msg.ProjectId, msg.Asama, msg.HataMesaji);

        await _projectService.UpdateStatusAsync(msg.ProjectId, ProjectDurumu.Hata, context.CancellationToken);

        await _hubContext.Clients
            .Group($"project-{msg.ProjectId}")
            .SendAsync("PipelineError", new
            {
                projectId = msg.ProjectId,
                hataMesaji = msg.HataMesaji
            }, context.CancellationToken);
    }
}
