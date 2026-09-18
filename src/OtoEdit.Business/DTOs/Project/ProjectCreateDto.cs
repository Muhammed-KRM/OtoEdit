using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Project;

public record ProjectCreateDto
{
    public string Ad { get; init; } = string.Empty;
    public string? Aciklama { get; init; }
    public VideoFormati VideoFormati { get; init; } = VideoFormati.Dikey_9_16;
    public Guid? TemplateId { get; init; }
    public bool GestureCommandsEnabled { get; init; } = true;
    public bool AudioEnhancementEnabled { get; init; } = true;
}
