using System.Text.Json;
using System.Text.Json.Serialization;

namespace OtoEdit.Business.DTOs.Chat;

public record ChatMessageDto
{
    public string Mesaj { get; init; } = string.Empty;
}

public record ChatResponseDto
{
    public Guid Id { get; init; }
    public string Rol { get; init; } = "assistant";
    public string Mesaj { get; init; } = string.Empty;
    public JsonElement? EdlPatch { get; init; }
    public int? EdlVersiyonYeni { get; init; }
}

public record ChatHistoryItem
{
    public string Role { get; init; } = string.Empty; // user / assistant / system
    public string Message { get; init; } = string.Empty;
}

public class ChatResult
{
    [JsonPropertyName("mesaj")]
    public string Mesaj { get; set; } = string.Empty;

    [JsonPropertyName("edlPatch")]
    public JsonElement? EdlPatch { get; set; }
}
