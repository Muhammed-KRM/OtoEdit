using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Interfaces;

public interface IChatService
{
    Task<ChatResponseDto> SendMessageAsync(Guid projectId, string message, CancellationToken cancellationToken = default);
    Task<IEnumerable<ChatMessageHistoryDto>> GetHistoryAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task<EdlPatchResponseDto> ApplyPendingPatchAsync(Guid messageId, CancellationToken cancellationToken = default);
}

public interface IChatProvider
{
    Task<ChatResult> ProcessCommandAsync(
        string userMessage, 
        string currentEdlJson, 
        string? transcriptText,
        List<ChatHistoryItem> history, 
        CancellationToken cancellationToken = default);
}
