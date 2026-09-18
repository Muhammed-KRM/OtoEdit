using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Video;

public record VideoListDto
{
    public Guid Id { get; init; }
    public Guid ProjectId { get; init; }
    public string Baslik { get; init; } = string.Empty;
    public long DosyaBoyutu { get; init; }
    public VideoIslemDurumu IslemDurumu { get; init; }
    public DateTime OlusturmaTarihi { get; init; }
}
