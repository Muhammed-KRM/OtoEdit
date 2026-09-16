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
    public string? EdlPatch { get; set; } // JSONB formatında saklanır
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;

    // Navigation Properties
    public Project Project { get; set; } = null!;
}
