using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Video;

public record VideoDetailDto
{
    public Guid Id { get; init; }
    public Guid ProjectId { get; init; }
    public string Baslik { get; init; } = string.Empty;
    public string DosyaYolu { get; init; } = string.Empty;
    public string? TemizSesYolu { get; init; }
    public TimeSpan? Sure { get; init; }
    public long DosyaBoyutu { get; init; }
    public VideoIslemDurumu IslemDurumu { get; init; }
    public bool TranskriptVar { get; init; }
    public DateTime OlusturmaTarihi { get; init; }
    public DateTime? IslemTamamlanmaTarihi { get; init; }
}
