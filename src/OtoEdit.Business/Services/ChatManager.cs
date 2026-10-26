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

    public async Task<ChatResponseDto> SendMessageAsync(Guid projectId, string message, string? provider = null, CancellationToken cancellationToken = default)
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

        // Eğer VideoTranscripts tablosunda transkript yoksa, EDL JSON içerisindeki segments alanından zaman damgalı metni çıkar
        if (string.IsNullOrWhiteSpace(transcriptText) && !string.IsNullOrWhiteSpace(edlJson))
        {
            try
            {
                using var edlDoc = JsonDocument.Parse(edlJson);
                if (edlDoc.RootElement.TryGetProperty("transcript", out var tElem))
                {
                    if (tElem.TryGetProperty("segments", out var segsElem) && segsElem.ValueKind == JsonValueKind.Array)
                    {
                        var sb = new System.Text.StringBuilder();
                        foreach (var seg in segsElem.EnumerateArray())
                        {
                            var start = seg.TryGetProperty("start", out var s) ? s.GetDouble() : 0;
                            var end = seg.TryGetProperty("end", out var e) ? e.GetDouble() : 0;
                            var txt = seg.TryGetProperty("text", out var tx) ? tx.GetString() : "";
                            if (!string.IsNullOrWhiteSpace(txt))
                            {
                                int mStart = (int)(start / 60);
                                int sStart = (int)(start % 60);
                                sb.AppendLine($"[{mStart:D2}:{sStart:D2} ({start:F1}s)] {txt.Trim()}");
                            }
                        }
                        transcriptText = sb.ToString();
                    }
                    else if (tElem.TryGetProperty("fullText", out var ftElem))
                    {
                        transcriptText = ftElem.GetString();
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "EDL transkripti ayrıştırılırken hata oluştu.");
            }
        }

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
        var chatResult = await _chatProvider.ProcessCommandAsync(message, edlJson, transcriptText, historyItems, provider, cancellationToken);

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

    public async Task<EdlPatchResponseDto> SubmitFormAsync(Guid projectId, Guid messageId, Dictionary<string, string> parameters, CancellationToken cancellationToken = default)
    {
        var message = await _context.ChatMessages.FindAsync(new object[] { messageId }, cancellationToken);
        if (message == null || message.ProjectId != projectId)
            throw new NotFoundException("Chat mesajı bulunamadı", messageId);

        // Form parametrelerinden overlay nesnesi derle
        var textContent = parameters.GetValueOrDefault("content") 
                          ?? parameters.GetValueOrDefault("text") 
                          ?? parameters.GetValueOrDefault("title") 
                          ?? "Yeni Başlık";
        
        var sourceUrl = parameters.GetValueOrDefault("source") 
                        ?? parameters.GetValueOrDefault("imageUrl");
        
        var isImage = !string.IsNullOrEmpty(sourceUrl) || parameters.GetValueOrDefault("type") == "image";
        
        var overlayId = $"ov_{Guid.NewGuid().ToString("N")[..8]}";
        var font = parameters.GetValueOrDefault("font") ?? "Montserrat-Bold";
        var color = parameters.GetValueOrDefault("color") ?? "#FFFFFF";
        var bgColor = parameters.GetValueOrDefault("backgroundColor") ?? "#00000080";
        var animation = parameters.GetValueOrDefault("animation") ?? "pop-up";

        double.TryParse(parameters.GetValueOrDefault("timestamp"), System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var timestamp);
        if (!double.TryParse(parameters.GetValueOrDefault("duration"), System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var duration) || duration <= 0)
            duration = 5.0;

        int.TryParse(parameters.GetValueOrDefault("fontSize"), out var fontSize);
        if (fontSize <= 0) fontSize = 48;

        double.TryParse(parameters.GetValueOrDefault("positionX"), System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var posX);
        if (posX <= 0) posX = 50.0;

        double.TryParse(parameters.GetValueOrDefault("positionY"), System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var posY);
        if (posY <= 0) posY = 85.0;

        var overlayObj = new JsonObject
        {
            ["id"] = overlayId,
            ["type"] = isImage ? "image" : "text",
            ["content"] = textContent,
            ["source"] = sourceUrl,
            ["timestamp"] = timestamp,
            ["duration"] = duration,
            ["font"] = font,
            ["fontSize"] = fontSize,
            ["color"] = color,
            ["backgroundColor"] = bgColor,
            ["positionX"] = posX,
            ["positionY"] = posY,
            ["animation"] = animation,
            ["action"] = "add"
        };

        var patchObj = new JsonObject
        {
            ["overlays"] = new JsonArray { overlayObj }
        };

        // Eğer görsel ise ve pexels gerekirse zenginleştir
        using var patchDoc = JsonDocument.Parse(patchObj.ToJsonString());
        var enrichedPatch = await EnrichImageOverlaysWithPexelsAsync(projectId, patchDoc.RootElement, cancellationToken);

        // EDL'ye uygula
        var result = await _edlService.PatchEdlAsync(projectId, enrichedPatch, cancellationToken);

        // Mesaj durumunu güncelle
        message.PatchDurumu = "applied";
        message.EdlPatch = enrichedPatch.GetRawText();
        
        // Kullanıcı onay mesajını ekle
        var userConfirmMsg = new ChatMessage
        {
            ProjectId = projectId,
            Rol = "user",
            Mesaj = $"Form onaylandı: {textContent} ({posX}%, {posY}%)",
            PatchDurumu = "none"
        };
        _context.ChatMessages.Add(userConfirmMsg);
        await _context.SaveChangesAsync(cancellationToken);

        // Önbelleği temizle
        await _cacheService.RemoveAsync($"{CachePrefix}{projectId}:history", cancellationToken);

        return result;
    }

    public async Task<IEnumerable<ChatMessageHistoryDto>> GetHistoryAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var messages = await _context.ChatMessages
            .Where(c => c.ProjectId == projectId)
            .OrderBy(c => c.OlusturmaTarihi)
            .AsNoTracking()
            .ToListAsync(cancellationToken);
            
        return messages.Select(m => new ChatMessageHistoryDto
        {
            Id = m.Id,
            ProjectId = m.ProjectId,
            Rol = m.Rol,
            Mesaj = m.Mesaj,
            PatchDurumu = m.PatchDurumu,
            OlusturulmaZamani = m.OlusturmaTarihi,
            PendingEdlPatch = string.IsNullOrEmpty(m.PendingEdlPatch) ? (JsonElement?)null : JsonDocument.Parse(m.PendingEdlPatch).RootElement,
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
