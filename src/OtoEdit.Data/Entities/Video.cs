using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Entities;

/// <summary>
/// Projeye bağlı video varlığı.
/// </summary>
public class Video
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public string Baslik { get; set; } = string.Empty;
    public string DosyaYolu { get; set; } = string.Empty;
    public string? TemizSesYolu { get; set; }
    public TimeSpan? Sure { get; set; }
    public long DosyaBoyutu { get; set; }
    public VideoIslemDurumu IslemDurumu { get; set; } = VideoIslemDurumu.Bekliyor;
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;
    public DateTime? IslemTamamlanmaTarihi { get; set; }

    // Navigation Properties
    public Project Project { get; set; } = null!;
    public VideoTranscript? Transcript { get; set; }
    public ICollection<PipelineLog> PipelineLogs { get; set; } = new List<PipelineLog>();
}
