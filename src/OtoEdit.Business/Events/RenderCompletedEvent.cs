namespace OtoEdit.Business.Events;

/// <summary>
/// Python Worker'ın render işlemini tamamlayıp çıktıyı MinIO'ya yüklediğini bildiren event.
/// </summary>
public record RenderCompletedEvent
{
    public Guid RenderJobId { get; init; }
    public Guid ProjectId { get; init; }
    public string IndirmeUrl { get; init; } = string.Empty;
}
