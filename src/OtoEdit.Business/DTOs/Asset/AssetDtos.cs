namespace OtoEdit.Business.DTOs.Asset;

/// <summary>
/// Proje medya varlığı DTO'su.
/// </summary>
public record ProjectAssetDto
{
    public Guid Id { get; init; }
    public Guid ProjectId { get; init; }
    public string DosyaAdi { get; init; } = string.Empty;
    public string MimeTuru { get; init; } = string.Empty;
    public string Url { get; init; } = string.Empty;
    public long BoyutByte { get; init; }
    public DateTime YuklemeTarihi { get; init; }
}
