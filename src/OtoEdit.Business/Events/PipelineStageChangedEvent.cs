using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Events;

/// <summary>
/// Pipeline aşaması değiştiğinde yayınlanan event.
/// SignalR üzerinden istemciye canlı ilerleme iletir.
/// </summary>
public record PipelineStageChangedEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
    public PipelineAsamasi Asama { get; init; }
    public int Yuzde { get; init; }
    public string? Mesaj { get; init; }
}
