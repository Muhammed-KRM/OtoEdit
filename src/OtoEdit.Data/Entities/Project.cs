using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Entities;

/// <summary>
/// Video düzenleme projesi ana varlığı.
/// </summary>
public class Project
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Ad { get; set; } = string.Empty;
    public string? Aciklama { get; set; }
    public VideoFormati VideoFormati { get; set; } = VideoFormati.Yatay_16_9;
    public Guid? TemplateId { get; set; }
    public bool GestureCommandsEnabled { get; set; } = true;
    public bool AudioEnhancementEnabled { get; set; } = true;
    public ProjectDurumu Durum { get; set; } = ProjectDurumu.Taslak;
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;
    public DateTime? GuncellemeTarihi { get; set; }

    // Navigation Properties
    public Video? Video { get; set; }
    public EditDecisionList? EditDecisionList { get; set; }
    public Template? Template { get; set; }
    public ICollection<ChatMessage> ChatMessages { get; set; } = new List<ChatMessage>();
    public ICollection<RenderJob> RenderJobs { get; set; } = new List<RenderJob>();
    public ICollection<PipelineLog> PipelineLogs { get; set; } = new List<PipelineLog>();
    public ICollection<ProjectAsset> Assets { get; set; } = new List<ProjectAsset>();
}
