using System.Text.Json;
using System.Text.Json.Nodes;
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
    private readonly ICacheService _cacheService;
    private readonly IPexelsService _pexelsService;
    private readonly ILogger<ChatManager> _logger;

    private const string CachePrefix = "chat:";

    public ChatManager(
        AppDbContext context,
        IChatProvider chatProvider,
        IEdlService edlService,
        ICacheService cacheService,
        IPexelsService pexelsService,
        ILogger<ChatManager> logger)
    {
        _context = context;
        _chatProvider = chatProvider;
        _edlService = edlService;
        _cacheService = cacheService;
        _pexelsService = pexelsService;
        _logger = logger;
    }

    public async Task<ChatResponseDto> SendMessageAsync(Guid projectId, string message, CancellationToken cancellationToken = default)
    {
        var project = await _context.Projects.FindAsync(new object[] { projectId }, cancellationToken);
        if (project == null)
        {
            throw new NotFoundException("Proje bulunamadı", projectId);
        }

        var cacheKey = $"{CachePrefix}{projectId}:history";

        // 1. Son 10 sohbet geçmişini getir (Önce Redis, yoksa DB)
        var historyItems = await _cacheService.GetAsync<List<ChatHistoryItem>>(cacheKey, cancellationToken);
        if (historyItems == null)
        {
            var recentMessages = await _context.ChatMessages
                .Where(c => c.ProjectId == projectId)
                .OrderByDescending(c => c.OlusturmaTarihi)
                .Take(10)
                .OrderBy(c => c.OlusturmaTarihi)
                .ToListAsync(cancellationToken);

            historyItems = recentMessages.Select(m => new ChatHistoryItem
            {
                Role = m.Rol,
                Message = m.Mesaj
            }).ToList();

            await _cacheService.SetAsync(cacheKey, historyItems, TimeSpan.FromHours(1), cancellationToken);
        }

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

        // 5. Eğer bir EDL Patch üretilmişse ve içinde resim overlay'i varsa Pexels ile zenginleştir
        int? yeniVersiyon = null;
        if (chatResult.EdlPatch.HasValue)
        {
            try
            {
                var patchedElement = await EnrichImageOverlaysWithPexelsAsync(projectId, chatResult.EdlPatch.Value, cancellationToken);
                var patchResponse = await _edlService.PatchEdlAsync(projectId, patchedElement, cancellationToken);
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

        // 7. Önbelleği temizle
        await _cacheService.RemoveAsync(cacheKey, cancellationToken);

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

    /// <summary>
    /// Eğer EDL Patch içerisinde görsel ekleme komutu varsa ve source belirtilmemişse,
    /// Pexels üzerinden arama yapıp MinIO'ya indirerek patch nesnesini zenginleştirir.
    /// </summary>
    private async Task<JsonElement> EnrichImageOverlaysWithPexelsAsync(Guid projectId, JsonElement edlPatch, CancellationToken cancellationToken)
    {
        var rootNode = JsonNode.Parse(edlPatch.GetRawText());
        if (rootNode is JsonObject jsonObj && jsonObj["overlays"] is JsonArray overlaysArray)
        {
            foreach (var overlayNode in overlaysArray)
            {
                if (overlayNode is JsonObject overlayObj)
                {
                    var type = overlayObj["type"]?.GetValue<string>();
                    var source = overlayObj["source"]?.GetValue<string>();
                    var content = overlayObj["content"]?.GetValue<string>();

                    if (string.Equals(type, "image", StringComparison.OrdinalIgnoreCase) &&
                        (string.IsNullOrWhiteSpace(source) || source.StartsWith("pexels://", StringComparison.OrdinalIgnoreCase)) &&
                        !string.IsNullOrWhiteSpace(content))
                    {
                        var query = source?.StartsWith("pexels://", StringComparison.OrdinalIgnoreCase) == true
                            ? source.Substring("pexels://".Length)
                            : content;

                        var assetKey = await _pexelsService.SearchAndSaveAssetAsync(projectId, query, cancellationToken: cancellationToken);
                        if (!string.IsNullOrEmpty(assetKey))
                        {
                            overlayObj["source"] = assetKey;
                            _logger.LogInformation("Chat görsel overlay'i Pexels ile zenginleştirildi: Query={Query}, AssetKey={AssetKey}", query, assetKey);
                        }
                    }
                }
            }

            using var doc = JsonDocument.Parse(rootNode.ToJsonString());
            return doc.RootElement.Clone();
        }

        return edlPatch;
    }
}
