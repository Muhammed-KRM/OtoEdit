using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Pipeline;

public record PipelineStatusDto
{
    public Guid? VideoId { get; init; }
    public Guid ProjectId { get; init; }
    public PipelineAsamasi Asama { get; init; }
    public string Durum { get; init; } = string.Empty;
    public int Yuzde { get; init; }
    public string? Mesaj { get; init; }
    public DateTime GuncellemeZamani { get; init; }
}
