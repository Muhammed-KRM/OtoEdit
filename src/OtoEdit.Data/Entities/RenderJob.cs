using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Entities;

/// <summary>
/// Video render iş kaydı varlığı.
/// </summary>
public class RenderJob
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public string EdlSnapshot { get; set; } = "{}"; // Render anındaki tam EDL kopyası (JSONB)
    public RenderDurumu Durum { get; set; } = RenderDurumu.Kuyrukta;
    public string? CiktiYolu { get; set; } // MinIO'daki nihai video yolu
    public DateTime BaslangicZamani { get; set; } = DateTime.UtcNow;
    public DateTime? BitisZamani { get; set; }
    public int? SureMs { get; set; }
    public string? HataMesaji { get; set; }

    // Navigation Properties
    public Project Project { get; set; } = null!;
}
