using System.Text.Json;

namespace OtoEdit.Business.Events;

/// <summary>
/// Kullanıcı dışa aktarma (render) talep ettiğinde yayınlanan event.
/// Python Worker bu event ile FFmpeg render işlemini başlatır.
/// </summary>
public record RenderRequestedEvent
{
    public Guid RenderJobId { get; init; }
    public Guid ProjectId { get; init; }
    public JsonDocument EdlJson { get; init; } = default!;
}
