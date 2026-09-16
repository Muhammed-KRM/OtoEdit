using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Entities;

/// <summary>
/// Python Worker ve Render pipeline aşamalarını izleyen log varlığı.
/// </summary>
public class PipelineLog
{
    public long Id { get; set; }
    public Guid? VideoId { get; set; }
    public Guid? ProjectId { get; set; }
    public Guid? RenderJobId { get; set; }
    public PipelineAsamasi Asama { get; set; }
    public string Durum { get; set; } = string.Empty; // "Basladi", "Tamamlandi", "Hata"
    public DateTime BaslangicZamani { get; set; } = DateTime.UtcNow;
    public DateTime? BitisZamani { get; set; }
    public int? SureMs { get; set; }
    public string? HataMesaji { get; set; }
    public string? HataDetayi { get; set; }
    public string? GirdiMetadata { get; set; } // JSONB
    public string? CiktiMetadata { get; set; } // JSONB
    public string? TraceId { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation Properties
    public Video? Video { get; set; }
    public Project? Project { get; set; }
}
