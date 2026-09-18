using System.Text.Json;

namespace OtoEdit.Business.DTOs.Edl;

public record EdlDto
{
    public Guid ProjectId { get; init; }
    public int Versiyon { get; init; }
    public JsonElement Edl { get; init; }
    public DateTime? GuncellemeTarihi { get; init; }
}

public record EdlPatchDto
{
    public JsonElement Patch { get; init; }
}

public record EdlPatchResponseDto
{
    public Guid ProjectId { get; init; }
    public int Versiyon { get; init; }
    public string Mesaj { get; init; } = "EDL güncellendi";
}
