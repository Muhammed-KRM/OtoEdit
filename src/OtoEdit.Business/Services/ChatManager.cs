using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Services;

/// <summary>
/// AI Sohbet ve kurgu komutları iş mantığı implementasyonu.
/// </summary>
public class ChatManager : IChatService
{
    private readonly AppDbContext _context;
    private readonly IChatProvider _chatProvider;
    private readonly IEdlService _edlService;
    private readonly ILogger<ChatManager> _logger;

    public ChatManager(
        AppDbContext context,
        IChatProvider chatProvider,
        IEdlService edlService,
        ILogger<ChatManager> logger)
    {
        _context = context;
        _chatProvider = chatProvider;
        _edlService = edlService;
        _logger = logger;
    }

    public async Task<ChatResponseDto> SendMessageAsync(Guid projectId, string message, CancellationToken cancellationToken = default)
    {
        var project = await _context.Projects.FindAsync(new object[] { projectId }, cancellationToken);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", projectId);
        }

        // 1. Son 10 sohbet geçmişini getir
        var recentMessages = await _context.ChatMessages
            .Where(c => c.ProjectId == projectId)
            .OrderByDescending(c => c.OlusturmaTarihi)
            .Take(10)
            .OrderBy(c => c.OlusturmaTarihi)
            .ToListAsync(cancellationToken);

        var historyItems = recentMessages.Select(m => new ChatHistoryItem
        {
            Role = m.Rol,
            Message = m.Mesaj
        }).ToList();

        // 2. Mevcut EDL JSON'u oku
        var currentEdl = await _context.EditDecisionLists
            .AsNoTracking()
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        var edlJson = currentEdl?.EdlJson ?? "{}";

        // 3. Kullanıcı mesajını kaydet
        var userChatMessage = new ChatMessage
        {
            ProjectId = projectId,
            Rol = "user",
            Mesaj = message,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _context.ChatMessages.Add(userChatMessage);

        // 4. Gemini AI Provider ile komutu çözümle
        var chatResult = await _chatProvider.ProcessCommandAsync(message, edlJson, historyItems, cancellationToken);

        // 5. Eğer bir EDL Patch üretilmişse uygula
        int? yeniVersiyon = null;
        if (chatResult.EdlPatch.HasValue)
        {
            try
            {
                var patchResponse = await _edlService.PatchEdlAsync(projectId, chatResult.EdlPatch.Value, cancellationToken);
                yeniVersiyon = patchResponse.Versiyon;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "AI tarafından üretilen EDL Patch uygulanamadı.");
            }
        }

        // 6. Asistan yanıtını kaydet
        var assistantChatMessage = new ChatMessage
        {
            ProjectId = projectId,
            Rol = "assistant",
            Mesaj = chatResult.Mesaj,
            EdlPatch = chatResult.EdlPatch?.GetRawText(),
            OlusturmaTarihi = DateTime.UtcNow
        };
        _context.ChatMessages.Add(assistantChatMessage);
        await _context.SaveChangesAsync(cancellationToken);

        return new ChatResponseDto
        {
            Id = assistantChatMessage.Id,
            Rol = "assistant",
            Mesaj = chatResult.Mesaj,
            EdlPatch = chatResult.EdlPatch,
            EdlVersiyonYeni = yeniVersiyon
        };
    }

    public async Task<IEnumerable<ChatMessage>> GetHistoryAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        return await _context.ChatMessages
            .Where(c => c.ProjectId == projectId)
            .OrderBy(c => c.OlusturmaTarihi)
            .AsNoTracking()
            .ToListAsync(cancellationToken);
    }
}
