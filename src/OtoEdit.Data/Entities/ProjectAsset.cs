namespace OtoEdit.Data.Entities;

/// <summary>
/// Projeye yüklenen harici medya varlıkları (resim, ses, video, logo vb.)
/// </summary>
public class ProjectAsset
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public string DosyaAdi { get; set; } = string.Empty;
    public string MimeTuru { get; set; } = string.Empty; // "image/png", "video/mp4", "audio/mp3" vb.
    public string StorageKey { get; set; } = string.Empty; // MinIO nesne yolu (assets/{projectId}/{assetId}{ext})
    public string Url { get; set; } = string.Empty; // CDN / Presigned indirme veya akış URL'i
    public long BoyutByte { get; set; }
    public DateTime YuklemeTarihi { get; set; } = DateTime.UtcNow;

    // Navigation Property
    public Project Project { get; set; } = null!;
}
