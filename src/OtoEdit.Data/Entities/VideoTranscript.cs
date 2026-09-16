namespace OtoEdit.Data.Entities;

/// <summary>
/// Whisper STT çıktı varlığı (kelime bazlı zaman damgaları ve ham metin).
/// </summary>
public class VideoTranscript
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid VideoId { get; set; }
    public string HamMetin { get; set; } = string.Empty;
    public string? ZamanDamgalari { get; set; } // JSONB formatında saklanır
    public string Dil { get; set; } = "tr";
    public int KelimeSayisi { get; set; }
    public string SttModel { get; set; } = "whisper-1";
    public int SttSuresiMs { get; set; }
    public DateTime OlusturmaTarihi { get; set; } = DateTime.UtcNow;

    // Navigation Properties
    public Video Video { get; set; } = null!;
}
