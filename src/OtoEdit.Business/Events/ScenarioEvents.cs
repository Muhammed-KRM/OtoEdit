using System.Text.Json;

namespace OtoEdit.Business.Events;

/// <summary>
/// 3. yapay zeka denetim turu sonunda kurgu senaryosu için kullanıcı onayı/revizyonu gerektiğinde Python Worker'dan gelen event.
/// </summary>
public record ScenarioApprovalRequiredEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
    public int IterationCount { get; init; } = 3;
    public string CriticMessage { get; init; } = string.Empty;
    public JsonElement MasterScript { get; init; }
    public JsonDocument EdlJson { get; init; } = default!;
}

/// <summary>
/// Kullanıcının kurgu senaryosu üzerinde doğal dille revizyon ("Şu kısma şunu ekle...") talep ettiğini bildiren event.
/// </summary>
public record ScenarioRevisionRequestedEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
    public string UserFeedback { get; init; } = string.Empty;
}

/// <summary>
/// Kullanıcının kurgu senaryosunu onayladığını bildiren event.
/// </summary>
public record ScenarioApprovedEvent
{
    public Guid ProjectId { get; init; }
    public Guid VideoId { get; init; }
}
