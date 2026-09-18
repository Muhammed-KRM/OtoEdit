using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Project;

public record ProjectListDto
{
    public Guid Id { get; init; }
    public string Ad { get; init; } = string.Empty;
    public VideoFormati VideoFormati { get; init; }
    public ProjectDurumu Durum { get; init; }
    public DateTime OlusturmaTarihi { get; init; }
    public int VideoSayisi { get; init; }
    public string? TemplateAd { get; init; }
}
