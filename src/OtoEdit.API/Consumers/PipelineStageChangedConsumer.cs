using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen aşama ilerleme bildirimlerini dinler,
/// SignalR üzerinden canlı olarak istemciye iletir.
/// </summary>
public class PipelineStageChangedConsumer : IConsumer<PipelineStageChangedEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly ILogger<PipelineStageChangedConsumer> _logger;

    public PipelineStageChangedConsumer(
        IHubContext<PipelineHub> hubContext,
        ILogger<PipelineStageChangedConsumer> logger)
    {
        _hubContext = hubContext;
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
}
