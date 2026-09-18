using Microsoft.AspNetCore.SignalR;

namespace OtoEdit.API.Hubs;

/// <summary>
/// Proje analiz ve render durumlarını canlı olarak istemcilere ileten SignalR Hub.
/// </summary>
public class PipelineHub : Hub
{
    private readonly ILogger<PipelineHub> _logger;

    public PipelineHub(ILogger<PipelineHub> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// İstemci belirli bir projenin canlı ilerleme grubuna katılır.
    /// </summary>
    public async Task JoinProjectGroup(string projectId)
    {
        var groupName = $"project-{projectId}";
        await Groups.AddToGroupAsync(Context.ConnectionId, groupName);
        _logger.LogInformation("İstemci {ConnectionId} gruba katıldı: {GroupName}", Context.ConnectionId, groupName);
    }

    /// <summary>
    /// İstemci belirli bir projenin grubundan ayrılır.
    /// </summary>
    public async Task LeaveProjectGroup(string projectId)
    {
        var groupName = $"project-{projectId}";
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, groupName);
        _logger.LogInformation("İstemci {ConnectionId} gruptan ayrıldı: {GroupName}", Context.ConnectionId, groupName);
    }
}
