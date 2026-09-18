using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Services;

/// <summary>
/// Edit Decision List (EDL) iş mantığı implementasyonu.
/// </summary>
public class EdlManager : IEdlService
{
    private readonly AppDbContext _context;
    private readonly ICacheService _cacheService;
    private readonly ILogger<EdlManager> _logger;

    private const string CachePrefix = "edl:";

    public EdlManager(AppDbContext context, ICacheService cacheService, ILogger<EdlManager> logger)
    {
        _context = context;
        _cacheService = cacheService;
        _logger = logger;
    }

    public async Task<EdlDto> GetEdlAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var cacheKey = $"{CachePrefix}{projectId}";
        var cached = await _cacheService.GetAsync<EdlDto>(cacheKey, cancellationToken);
        if (cached != null)
        {
            return cached;
        }

        var edl = await _context.EditDecisionLists
            .AsNoTracking()
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        if (edl == null)
        {
            throw new NotFoundException("Projeye ait EDL bulunamadı", projectId);
        }

        using var doc = JsonDocument.Parse(edl.EdlJson);
        var dto = new EdlDto
        {
            ProjectId = edl.ProjectId,
            Versiyon = edl.Versiyon,
            Edl = doc.RootElement.Clone(),
            GuncellemeTarihi = edl.GuncellemeTarihi ?? edl.OlusturmaTarihi
        };

        await _cacheService.SetAsync(cacheKey, dto, TimeSpan.FromMinutes(2), cancellationToken);
        return dto;
    }

    public async Task<EdlPatchResponseDto> PatchEdlAsync(Guid projectId, JsonElement patch, CancellationToken cancellationToken = default)
    {
        var edl = await _context.EditDecisionLists
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        if (edl == null)
        {
            throw new NotFoundException("Projeye ait EDL bulunamadı", projectId);
        }

        // Mevcut EDL JSON'u JsonNode olarak parse et
        var rootNode = JsonNode.Parse(edl.EdlJson) as JsonObject ?? new JsonObject();

        // Gelen patch alanlarını merge et
        using var patchDoc = JsonDocument.Parse(patch.GetRawText());
        foreach (var property in patchDoc.RootElement.EnumerateObject())
        {
            var patchValueNode = JsonNode.Parse(property.Value.GetRawText());
            rootNode[property.Name] = patchValueNode;
        }

        edl.EdlJson = rootNode.ToJsonString();
        edl.Versiyon += 1;
        edl.GuncellemeTarihi = DateTime.UtcNow;

        await _context.SaveChangesAsync(cancellationToken);
        await _cacheService.RemoveAsync($"{CachePrefix}{projectId}", cancellationToken);

        _logger.LogInformation("EDL patch uygulandı: ProjectId={ProjectId}, YeniVersiyon={Versiyon}", projectId, edl.Versiyon);

        return new EdlPatchResponseDto
        {
            ProjectId = projectId,
            Versiyon = edl.Versiyon,
            Mesaj = "EDL başarıyla güncellendi"
        };
    }

    public async Task<EditDecisionList> CreateOrUpdateAsync(Guid projectId, JsonDocument edlJson, CancellationToken cancellationToken = default)
    {
        var existing = await _context.EditDecisionLists
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        var jsonString = edlJson.RootElement.GetRawText();

        if (existing != null)
        {
            existing.EdlJson = jsonString;
            existing.Versiyon += 1;
            existing.GuncellemeTarihi = DateTime.UtcNow;
            await _context.SaveChangesAsync(cancellationToken);
            await _cacheService.RemoveAsync($"{CachePrefix}{projectId}", cancellationToken);
            return existing;
        }

        var newEdl = new EditDecisionList
        {
            ProjectId = projectId,
            EdlJson = jsonString,
            Versiyon = 1,
            OlusturmaTarihi = DateTime.UtcNow
        };

        _context.EditDecisionLists.Add(newEdl);
        await _context.SaveChangesAsync(cancellationToken);
        await _cacheService.RemoveAsync($"{CachePrefix}{projectId}", cancellationToken);

        return newEdl;
    }
}
