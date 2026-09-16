namespace OtoEdit.Data.Entities;

/// <summary>
/// Edit Decision List (EDL) varlığı — Sistemin kalbi.
/// Tüm AI kesim kararları, yazı/görsel overlay'ler bu JSONB alanında tutulur.
/// </summary>
public class EditDecisionList
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public string EdlJson { get; set; } = "{}"; // JSONB formatında saklanır
    public int Versiyon { get; set; } = 1;
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;
    public DateTime? GuncellemeTarihi { get; set; }

    // Navigation Properties
    public Project Project { get; set; } = null!;
}
