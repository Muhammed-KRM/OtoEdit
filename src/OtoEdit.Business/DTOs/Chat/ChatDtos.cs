using System.Text.Json;
using System.Text.Json.Serialization;

namespace OtoEdit.Business.DTOs.Chat;

public record ChatMessageDto
{
    public string Mesaj { get; init; } = string.Empty;
}

public record ChatMessageHistoryDto
{
    public Guid Id { get; init; }
    public Guid ProjectId { get; init; }
    public string Rol { get; init; } = string.Empty;
    public string Mesaj { get; init; } = string.Empty;
    public string PatchDurumu { get; init; } = "none";
    public DateTime OlusturulmaZamani { get; init; }
    public JsonElement? PendingEdlPatch { get; init; }
    public JsonElement? FormFields { get; init; }
}

public record ChatResponseDto
{
    public Guid Id { get; init; }
    public string Rol { get; init; } = "assistant";
    public string Mesaj { get; init; } = string.Empty;
    public string Intent { get; init; } = "information";
    public JsonElement? EdlPatch { get; init; }
    public JsonElement? PendingEdlPatch { get; init; }
    public JsonElement? FormFields { get; init; }
    public string PatchDurumu { get; init; } = "none";
    public int? EdlVersiyonYeni { get; init; }
}

public record ChatHistoryItem
{
    public string Role { get; init; } = string.Empty; // user / assistant / system
    public string Message { get; init; } = string.Empty;
}

public class ChatResult
{
    [JsonPropertyName("intent")]
    public string Intent { get; set; } = "information";

    [JsonPropertyName("mesaj")]
    public string Mesaj { get; set; } = string.Empty;

    [JsonPropertyName("edlPatch")]
    public JsonElement? EdlPatch { get; set; }

    [JsonPropertyName("formFields")]
    public JsonElement? FormFields { get; set; }
}
