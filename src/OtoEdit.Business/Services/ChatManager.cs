using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.DTOs.Edl;
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

        // 3. Mevcut transkripti oku
        var transcript = await _context.VideoTranscripts
            .AsNoTracking()
            .FirstOrDefaultAsync(t => t.Video.ProjectId == projectId, cancellationToken);
        var transcriptText = transcript?.HamMetin;

        // 4. Kullanıcı mesajını kaydet
        var userChatMessage = new ChatMessage
        {
            ProjectId = projectId,
            Rol = "user",
            Mesaj = message,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _context.ChatMessages.Add(userChatMessage);

        // 5. Gemini AI Provider ile komutu çözümle
        var chatResult = await _chatProvider.ProcessCommandAsync(message, edlJson, transcriptText, historyItems, cancellationToken);

        // 6. Niyet sınıflandırmasına göre patch uygula veya beklemeye al (HitL)
        int? yeniVersiyon = null;
        string patchDurumu = "none";
        string? pendingPatchString = null;
        
        if (chatResult.EdlPatch.HasValue)
        {
            if (chatResult.Intent == "information")
            {
                // Sadece bilgi, işlem yapma
            }
            else // "suggestion" veya "command"
            {
                // HitL: Değişikliği kalıcı yapmak yerine onaya sun (Pending)
                try
                {
                    var patchedElement = await EnrichImageOverlaysWithPexelsAsync(projectId, chatResult.EdlPatch.Value, cancellationToken);
                    pendingPatchString = patchedElement.GetRawText();
                    patchDurumu = "pending";
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "AI tarafından üretilen EDL Patch zenginleştirilemedi.");
                }
            }
        }

        // 7. Asistan yanıtını kaydet
        var assistantChatMessage = new ChatMessage
        {
            ProjectId = projectId,
            Rol = "assistant",
            Mesaj = chatResult.Mesaj,
            EdlPatch = chatResult.FormFields.HasValue ? chatResult.FormFields.Value.GetRawText() : null, // Geçici olarak form verilerini EdlPatch alanında saklıyoruz (tablo yapısını değiştirmemek için)
            PendingEdlPatch = pendingPatchString,
            PatchDurumu = chatResult.Intent == "clarification" ? "clarification" : patchDurumu,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _context.ChatMessages.Add(assistantChatMessage);
        await _context.SaveChangesAsync(cancellationToken);

        // 8. Önbelleği temizle
        await _cacheService.RemoveAsync(cacheKey, cancellationToken);

        return new ChatResponseDto
        {
            Id = assistantChatMessage.Id,
            Rol = "assistant",
            Mesaj = chatResult.Mesaj,
            Intent = chatResult.Intent,
            EdlPatch = null,
            PendingEdlPatch = string.IsNullOrEmpty(pendingPatchString) ? null : JsonDocument.Parse(pendingPatchString).RootElement,
            FormFields = chatResult.FormFields,
            PatchDurumu = assistantChatMessage.PatchDurumu,
            EdlVersiyonYeni = yeniVersiyon
        };
    }

    public async Task<EdlPatchResponseDto> ApplyPendingPatchAsync(Guid messageId, CancellationToken cancellationToken = default)
    {
        var message = await _context.ChatMessages.FindAsync(new object[] { messageId }, cancellationToken);
        if (message == null)
            throw new NotFoundException("Chat mesajı bulunamadı", messageId);

        if (message.PatchDurumu != "pending" || string.IsNullOrEmpty(message.PendingEdlPatch))
            throw new InvalidOperationException("Bu mesajda onay bekleyen geçerli bir değişiklik yok.");

        using var patchDoc = JsonDocument.Parse(message.PendingEdlPatch);
        
        // EDL'ye kalıcı olarak uygula (EdlManager zaten snapshot alacak)
        var result = await _edlService.PatchEdlAsync(message.ProjectId, patchDoc.RootElement, cancellationToken);

        // Mesajın durumunu güncelle
        message.PatchDurumu = "applied";
        
        // Asıl EdlPatch alanına kopyalayabiliriz veya sadece durumu applied olarak bırakabiliriz
        message.EdlPatch = message.PendingEdlPatch;
        message.PendingEdlPatch = null; // Bekleyen iş kalmadı

        await _context.SaveChangesAsync(cancellationToken);
        
        // Önbelleği temizle
        await _cacheService.RemoveAsync($"{CachePrefix}{message.ProjectId}:history", cancellationToken);

        return result;
    }

    public async Task<IEnumerable<object>> GetHistoryAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var messages = await _context.ChatMessages
            .Where(c => c.ProjectId == projectId)
            .OrderBy(c => c.OlusturmaTarihi)
            .AsNoTracking()
            .ToListAsync(cancellationToken);
            
        return messages.Select(m => new
        {
            Id = m.Id,
            ProjectId = m.ProjectId,
            Rol = m.Rol,
            Mesaj = m.Mesaj,
            PatchDurumu = m.PatchDurumu,
            OlusturulmaZamani = m.OlusturmaTarihi,
            PendingEdlPatch = string.IsNullOrEmpty(m.PendingEdlPatch) ? null : JsonDocument.Parse(m.PendingEdlPatch).RootElement,
            FormFields = (m.PatchDurumu == "clarification" && !string.IsNullOrEmpty(m.EdlPatch)) ? JsonDocument.Parse(m.EdlPatch).RootElement : (JsonElement?)null
        });
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
