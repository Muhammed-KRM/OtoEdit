namespace OtoEdit.Data.Entities;

/// <summary>
/// Memento deseni için EDL anlık görüntülerini (snapshots) saklar.
/// Her kalıcı değişiklikte bu tabloya önceki durum eklenir.
/// </summary>
public class EdlSnapshot
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public int Versiyon { get; set; }
    public string EdlJson { get; set; } = string.Empty;
    public string? Aciklama { get; set; }
    public string Kaynak { get; set; } = "system"; // 'ai_chat', 'manual', vs.
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;

    // Navigation Properties
    public Project Project { get; set; } = null!;
}
