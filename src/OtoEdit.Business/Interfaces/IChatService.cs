using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Interfaces;

public interface IChatService
{
    Task<ChatResponseDto> SendMessageAsync(Guid projectId, string message, CancellationToken cancellationToken = default);
    Task<IEnumerable<ChatMessage>> GetHistoryAsync(Guid projectId, CancellationToken cancellationToken = default);
}

public interface IChatProvider
{
    Task<ChatResult> ProcessCommandAsync(
        string userMessage, 
        string currentEdlJson, 
        List<ChatHistoryItem> history, 
        CancellationToken cancellationToken = default);
}
