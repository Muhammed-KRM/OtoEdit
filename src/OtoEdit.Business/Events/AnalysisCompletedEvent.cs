using System.Text.Json;

namespace OtoEdit.Business.Events;

/// <summary>
/// Python Worker'ın analiz pipeline'ını tamamladığını ve taslak EDL ürettiğini bildiren event.
/// </summary>
public record AnalysisCompletedEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
    public JsonDocument EdlJson { get; init; } = default!;
}
