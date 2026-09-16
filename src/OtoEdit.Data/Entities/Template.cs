using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Entities;

/// <summary>
/// Video şablon varlığı (Yatay Anlatım, Reels/Shorts, Kare vb.).
/// </summary>
public class Template
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Ad { get; set; } = string.Empty;
    public string? Tanim { get; set; }
    public VideoFormati VideoFormati { get; set; } = VideoFormati.Yatay_16_9;
    public string? LogoYolu { get; set; }
    public string? LogoPozisyonu { get; set; } // JSONB formatında saklanır: ["center", "bottom"]
    public bool KonusmaciAdGoster { get; set; } = false;
    public string? AltyaziStili { get; set; } // karaoke, static, none
    public string? AltyaziFont { get; set; }
    public string? AltyaziRenk { get; set; }
    public bool AktifMi { get; set; } = true;
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;

    // Navigation Properties
    public ICollection<Project> Projects { get; set; } = new List<Project>();
}
