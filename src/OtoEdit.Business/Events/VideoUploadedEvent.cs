namespace OtoEdit.Business.Events;

/// <summary>
/// Projeye video yüklendiğinde yayınlanan event.
/// Python Worker bu event'i alarak tam analiz pipeline'ını başlatır.
/// </summary>
public record VideoUploadedEvent
{
    public Guid VideoId { get; init; }
    public Guid ProjectId { get; init; }
    public string DosyaYolu { get; init; } = string.Empty;
    public int VideoFormati { get; init; }
    public bool GestureCommandsEnabled { get; init; }
    public bool AudioEnhancementEnabled { get; init; }
    public bool AutoJumpcutEnabled { get; init; } = true;
    public bool AutoRetakeEnabled { get; init; } = true;
    public bool AutoBrollEnabled { get; init; } = true;
    public bool AutoSubtitlesEnabled { get; init; } = false;
}
