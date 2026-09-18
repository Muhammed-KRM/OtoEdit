namespace OtoEdit.Business.Events;

/// <summary>
/// Analiz veya render aşamasında oluşan kritik hataları bildiren event.
/// </summary>
public record PipelineErrorEvent
{
    public Guid ProjectId { get; init; }
    public Guid? VideoId { get; init; }
    public string Asama { get; init; } = string.Empty;
    public string HataMesaji { get; init; } = string.Empty;
}
