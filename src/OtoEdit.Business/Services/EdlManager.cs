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

        // --- MEMENTO PATTERN: Mevcut durumu snapshot olarak kaydet ---
        await SaveSnapshotAsync(projectId, edl, "EDL Patch Öncesi", "system", cancellationToken);

        // Mevcut EDL JSON'u JsonNode olarak parse et
        var rootNode = JsonNode.Parse(edl.EdlJson) as JsonObject ?? new JsonObject();

        // Gelen patch alanlarını akıllıca merge et (cuts, overlays, settings vb.)
        using var patchDoc = JsonDocument.Parse(patch.GetRawText());
        foreach (var property in patchDoc.RootElement.EnumerateObject())
        {
            var propName = property.Name;
            var patchValueNode = JsonNode.Parse(property.Value.GetRawText());

            if ((propName.Equals("cuts", StringComparison.OrdinalIgnoreCase) ||
                 propName.Equals("overlays", StringComparison.OrdinalIgnoreCase) ||
                 propName.Equals("suggestions", StringComparison.OrdinalIgnoreCase)) &&
                patchValueNode is JsonArray patchArray &&
                rootNode[propName] is JsonArray targetArray)
            {
                foreach (var item in patchArray)
                {
                    if (item is JsonObject objItem)
                    {
                        var itemId = objItem["id"]?.GetValue<string>();
                        var isRemove = objItem["action"]?.GetValue<string>() == "remove";

                        if (!string.IsNullOrEmpty(itemId))
                        {
                            int existingIndex = -1;
                            for (int i = 0; i < targetArray.Count; i++)
                            {
                                if (targetArray[i] is JsonObject existingObj &&
                                    existingObj["id"]?.GetValue<string>() == itemId)
                                {
                                    existingIndex = i;
                                    break;
                                }
                            }

                            if (isRemove)
                            {
                                if (existingIndex >= 0)
                                    targetArray.RemoveAt(existingIndex);
                            }
                            else
                            {
                                if (existingIndex >= 0)
                                {
                                    if (targetArray[existingIndex] is JsonObject existingItemObj)
                                    {
                                        foreach (var kvp in objItem)
                                        {
                                            if (!kvp.Key.Equals("action", StringComparison.OrdinalIgnoreCase))
                                            {
                                                existingItemObj[kvp.Key] = kvp.Value?.DeepClone();
                                            }
                                        }
                                    }
                                    else
                                    {
                                        targetArray[existingIndex] = objItem.DeepClone();
                                    }
                                }
                                else
                                {
                                    targetArray.Add(objItem.DeepClone());
                                }
                            }
                        }
                        else
                        {
                            targetArray.Add(objItem.DeepClone());
                        }
                    }
                }
            }
            else if (propName.Equals("settings", StringComparison.OrdinalIgnoreCase) &&
                     patchValueNode is JsonObject patchSettings &&
                     rootNode["settings"] is JsonObject targetSettings)
            {
                foreach (var settingProp in patchSettings)
                {
                    targetSettings[settingProp.Key] = settingProp.Value?.DeepClone();
                }
            }
            else
            {
                rootNode[propName] = patchValueNode;
            }
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

    public async Task<EdlDto> UndoAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var edl = await _context.EditDecisionLists
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        if (edl == null)
            throw new NotFoundException("Projeye ait EDL bulunamadı", projectId);

        // En son 'system' kaynaklı snapshot'ı bul (bu bizim döneceğimiz önceki state)
        var lastSystemSnapshot = await _context.EdlSnapshots
            .Where(s => s.ProjectId == projectId && s.Kaynak == "system")
            .OrderByDescending(s => s.OlusturmaTarihi)
            .FirstOrDefaultAsync(cancellationToken);

        if (lastSystemSnapshot == null)
            throw new InvalidOperationException("Geri alınacak bir işlem bulunamadı.");

        // Mevcut durumu Redo (system_undo) olarak kaydet
        var redoSnapshot = new EdlSnapshot
        {
            ProjectId = projectId,
            Versiyon = edl.Versiyon,
            EdlJson = edl.EdlJson,
            Aciklama = "Undo Öncesi (Redo için)",
            Kaynak = "system_undo"
        };
        _context.EdlSnapshots.Add(redoSnapshot);

        // EDL'i önceki state'e geri döndür
        edl.EdlJson = lastSystemSnapshot.EdlJson;
        edl.Versiyon += 1; // Frontend'in değişikliği algılaması için arttırıyoruz
        edl.GuncellemeTarihi = DateTime.UtcNow;

        // Kullanılan snapshot'ı 'system' stack'inden çıkar
        _context.EdlSnapshots.Remove(lastSystemSnapshot);

        await _context.SaveChangesAsync(cancellationToken);
        await _cacheService.RemoveAsync($"{CachePrefix}{projectId}", cancellationToken);

        using var doc = JsonDocument.Parse(edl.EdlJson);
        return new EdlDto
        {
            ProjectId = edl.ProjectId,
            Versiyon = edl.Versiyon,
            Edl = doc.RootElement.Clone(),
            GuncellemeTarihi = edl.GuncellemeTarihi.Value
        };
    }

    public async Task<EdlDto> RedoAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var edl = await _context.EditDecisionLists
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        if (edl == null)
            throw new NotFoundException("Projeye ait EDL bulunamadı", projectId);

        // En son 'system_undo' kaynaklı snapshot'ı bul
        var redoSnapshot = await _context.EdlSnapshots
            .Where(s => s.ProjectId == projectId && s.Kaynak == "system_undo")
            .OrderByDescending(s => s.OlusturmaTarihi)
            .FirstOrDefaultAsync(cancellationToken);

        if (redoSnapshot == null)
            throw new InvalidOperationException("İleri alınacak bir işlem bulunamadı.");

        // Mevcut durumu 'system' stack'ine geri ekle (Undo için)
        var undoSnapshot = new EdlSnapshot
        {
            ProjectId = projectId,
            Versiyon = edl.Versiyon,
            EdlJson = edl.EdlJson,
            Aciklama = "Redo Öncesi (Undo için)",
            Kaynak = "system"
        };
        _context.EdlSnapshots.Add(undoSnapshot);

        // EDL'i ileri state'e döndür
        edl.EdlJson = redoSnapshot.EdlJson;
        edl.Versiyon += 1;
        edl.GuncellemeTarihi = DateTime.UtcNow;

        // Kullanılan redo snapshot'ını sil
        _context.EdlSnapshots.Remove(redoSnapshot);

        await _context.SaveChangesAsync(cancellationToken);
        await _cacheService.RemoveAsync($"{CachePrefix}{projectId}", cancellationToken);

        using var doc = JsonDocument.Parse(edl.EdlJson);
        return new EdlDto
        {
            ProjectId = edl.ProjectId,
            Versiyon = edl.Versiyon,
            Edl = doc.RootElement.Clone(),
            GuncellemeTarihi = edl.GuncellemeTarihi.Value
        };
    }

    private async Task SaveSnapshotAsync(Guid projectId, EditDecisionList edl, string aciklama, string kaynak, CancellationToken cancellationToken)
    {
        // Normal bir işlem yapılıyorsa (kaynak == system), ileri alma (redo) geçmişini temizle
        if (kaynak == "system")
        {
            var redoSnapshots = await _context.EdlSnapshots
                .Where(s => s.ProjectId == projectId && s.Kaynak == "system_undo")
                .ToListAsync(cancellationToken);
            _context.EdlSnapshots.RemoveRange(redoSnapshots);
        }

        var snapshot = new EdlSnapshot
        {
            ProjectId = projectId,
            Versiyon = edl.Versiyon,
            EdlJson = edl.EdlJson,
            Aciklama = aciklama,
            Kaynak = kaynak
        };
        
        _context.EdlSnapshots.Add(snapshot);
        
        // Snapshot limitini koru (Örn: Son 50)
        var snapshotCount = await _context.EdlSnapshots.CountAsync(s => s.ProjectId == projectId, cancellationToken);
        if (snapshotCount >= 50)
        {
            var oldestSnapshots = await _context.EdlSnapshots
                .Where(s => s.ProjectId == projectId)
                .OrderBy(s => s.OlusturmaTarihi)
                .Take(snapshotCount - 49) // 1 tane de yeni ekleneceği için 49
                .ToListAsync(cancellationToken);
                
            _context.EdlSnapshots.RemoveRange(oldestSnapshots);
        }
    }

    public async Task<EditDecisionList> CreateOrUpdateAsync(Guid projectId, JsonDocument edlJson, CancellationToken cancellationToken = default)
    {
        var existing = await _context.EditDecisionLists
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        var jsonString = edlJson.RootElement.GetRawText();

        if (existing != null)
        {
            await SaveSnapshotAsync(projectId, existing, "CreateOrUpdate Öncesi", "system", cancellationToken);
            
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
