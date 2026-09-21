namespace OtoEdit.Data.Entities;

/// <summary>
/// AI sohbet mesajı ve üretilen EDL Patch varlığı.
/// </summary>
public class ChatMessage
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ProjectId { get; set; }
    public string Rol { get; set; } = "user"; // "user" veya "assistant"
    public string Mesaj { get; set; } = string.Empty;
    public string? EdlPatch { get; set; } // Orijinal, doğrudan patch için veya history için
    public string? PendingEdlPatch { get; set; } // JSONB formatında onay bekleyen patch
    public string PatchDurumu { get; set; } = "none"; // "none", "pending", "applied", "rejected"
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;

    // Navigation Properties
    public Project Project { get; set; } = null!;
}
