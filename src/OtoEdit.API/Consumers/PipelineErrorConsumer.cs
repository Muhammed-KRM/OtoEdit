using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Enums;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen hata bildirimlerini dinler.
/// </summary>
public class PipelineErrorConsumer : IConsumer<PipelineErrorEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly IProjectService _projectService;
    private readonly IRenderService _renderService;
    private readonly ILogger<PipelineErrorConsumer> _logger;

    public PipelineErrorConsumer(
        IHubContext<PipelineHub> hubContext,
        IProjectService projectService,
        IRenderService renderService,
        ILogger<PipelineErrorConsumer> logger)
    {
        _hubContext = hubContext;
        _projectService = projectService;
        _renderService = renderService;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<PipelineErrorEvent> context)
    {
        var msg = context.Message;
        _logger.LogError("PipelineError: ProjectId={ProjectId}, Asama={Asama}, Hata={Hata}",
            msg.ProjectId, msg.Asama, msg.HataMesaji);

        await _projectService.UpdateStatusAsync(msg.ProjectId, ProjectDurumu.Hata, context.CancellationToken);

        if (msg.Asama == "Render" && msg.VideoId.HasValue)
        {
            await _renderService.FailRenderAsync(msg.VideoId.Value, msg.HataMesaji, context.CancellationToken);
        }

        await _hubContext.Clients
            .Group($"project-{msg.ProjectId}")
            .SendAsync("PipelineError", new
            {
                projectId = msg.ProjectId,
                hataMesaji = msg.HataMesaji
            }, context.CancellationToken);
    }
}
