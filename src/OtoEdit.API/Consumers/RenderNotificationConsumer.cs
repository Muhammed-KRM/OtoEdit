using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Consumers;

/// <summary>
/// Python Worker'dan gelen render tamamlanma event'ini dinler.
/// RenderJob'ı günceller ve SignalR ile indirme linkini istemcilere iletir.
/// </summary>
public class RenderNotificationConsumer : IConsumer<RenderCompletedEvent>
{
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly IRenderService _renderService;
    private readonly ILogger<RenderNotificationConsumer> _logger;

    public RenderNotificationConsumer(
        IHubContext<PipelineHub> hubContext,
        IRenderService renderService,
        ILogger<RenderNotificationConsumer> logger)
    {
        _hubContext = hubContext;
        _renderService = renderService;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<RenderCompletedEvent> context)
    {
        var msg = context.Message;
        _logger.LogInformation("RenderCompletedEvent alındı: RenderJobId={RenderJobId}, ProjectId={ProjectId}", msg.RenderJobId, msg.ProjectId);

        try
        {
            // 1. RenderJob'ı tamamlandı olarak işaretle
            await _renderService.CompleteRenderAsync(msg.RenderJobId, msg.IndirmeUrl, context.CancellationToken);

            // 2. SignalR ile istemcilere bildir
            await _hubContext.Clients
                .Group($"project-{msg.ProjectId}")
                .SendAsync("RenderCompleted", new
                {
                    renderJobId = msg.RenderJobId,
                    projectId = msg.ProjectId,
                    indirmeUrl = msg.IndirmeUrl
                }, context.CancellationToken);

            _logger.LogInformation("Render tamamlandı ve istemcilere bildirildi: RenderJobId={RenderJobId}", msg.RenderJobId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "RenderCompletedEvent işlenirken hata oluştu: RenderJobId={RenderJobId}", msg.RenderJobId);
            throw;
        }
    }
}
