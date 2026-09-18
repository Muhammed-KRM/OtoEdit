using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Template;

public record TemplateDto
{
    public Guid Id { get; init; }
    public string Ad { get; init; } = string.Empty;
    public string? Tanim { get; init; }
    public VideoFormati VideoFormati { get; init; }
    public string? LogoYolu { get; init; }
    public string? LogoPozisyonu { get; init; }
    public bool KonusmaciAdGoster { get; init; }
    public string? AltyaziStili { get; init; }
    public string? AltyaziFont { get; init; }
    public string? AltyaziRenk { get; init; }
    public bool AktifMi { get; init; }
}
