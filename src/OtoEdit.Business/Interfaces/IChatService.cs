using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Interfaces;

public interface IChatService
{
    Task<ChatResponseDto> SendMessageAsync(Guid projectId, string message, string? provider = null, CancellationToken cancellationToken = default);
    Task<IEnumerable<ChatMessageHistoryDto>> GetHistoryAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task<EdlPatchResponseDto> ApplyPendingPatchAsync(Guid messageId, CancellationToken cancellationToken = default);
    Task<EdlPatchResponseDto> SubmitFormAsync(Guid projectId, Guid messageId, Dictionary<string, string> parameters, CancellationToken cancellationToken = default);
}

public interface IChatProvider
{
    Task<ChatResult> ProcessCommandAsync(
        string userMessage, 
        string currentEdlJson, 
        string? transcriptText,
        List<ChatHistoryItem> history, 
        string? overrideProvider = null,
        CancellationToken cancellationToken = default);
}
