using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Project;

public record ProjectUpdateDto
{
    public string Ad { get; init; } = string.Empty;
    public string? Aciklama { get; init; }
    public VideoFormati VideoFormati { get; init; }
    public Guid? TemplateId { get; init; }
    public bool GestureCommandsEnabled { get; init; }
    public bool AudioEnhancementEnabled { get; init; }
}
