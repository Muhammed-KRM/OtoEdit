using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Render;

public record RenderRequestDto
{
    public string? CustomOutputName { get; init; }
}

public record RenderStatusDto
{
    public Guid RenderJobId { get; init; }
    public Guid ProjectId { get; init; }
    public RenderDurumu Durum { get; init; }
    public string? CiktiYolu { get; init; }
    public string? IndirmeUrl { get; init; }
    public int? SureMs { get; init; }
    public DateTime BaslangicZamani { get; init; }
    public DateTime? BitisZamani { get; init; }
    public string? HataMesaji { get; init; }
}
