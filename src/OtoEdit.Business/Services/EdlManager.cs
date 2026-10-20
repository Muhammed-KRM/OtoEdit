using System.Diagnostics;
using System.Text.Encodings.Web;
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
    private readonly IFileStorageService? _fileStorageService;

    private const string CachePrefix = "edl:";
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    public EdlManager(
        AppDbContext context,
        ICacheService cacheService,
        ILogger<EdlManager> logger,
        IFileStorageService? fileStorageService = null)
    {
        _context = context;
        _cacheService = cacheService;
        _logger = logger;
        _fileStorageService = fileStorageService;
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
        var rootElement = doc.RootElement.Clone();

        // Eğer EDL dokümanında transcript alanı yoksa veya boşsa, VideoTranscripts tablosundan otomatik besle
        var hasTranscript = rootElement.TryGetProperty("transcript", out var tProp) &&
                            tProp.ValueKind == JsonValueKind.Object &&
                            tProp.TryGetProperty("segments", out var segs) &&
                            segs.ValueKind == JsonValueKind.Array &&
                            segs.GetArrayLength() > 0;

        if (!hasTranscript)
        {
            var vt = await _context.VideoTranscripts
                .AsNoTracking()
                .FirstOrDefaultAsync(t => t.Video.ProjectId == projectId, cancellationToken);

            if (vt != null && !string.IsNullOrWhiteSpace(vt.ZamanDamgalari))
            {
                try
                {
                    var rootNode = JsonNode.Parse(edl.EdlJson)?.AsObject();
                    if (rootNode != null)
                    {
                        var transcriptNode = JsonNode.Parse(vt.ZamanDamgalari);
                        rootNode["transcript"] = transcriptNode;
                        using var enrichedDoc = JsonDocument.Parse(rootNode.ToJsonString(JsonOptions));
                        rootElement = enrichedDoc.RootElement.Clone();
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "VideoTranscripts verisi EDL ile birleştirilemedi: ProjectId={ProjectId}", projectId);
                }
            }
        }

        var dto = new EdlDto
        {
            ProjectId = edl.ProjectId,
            Versiyon = edl.Versiyon,
            Edl = rootElement,
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

            var isCollectionProp = propName.Equals("cuts", StringComparison.OrdinalIgnoreCase) ||
                                   propName.Equals("overlays", StringComparison.OrdinalIgnoreCase) ||
                                   propName.Equals("suggestions", StringComparison.OrdinalIgnoreCase);

            if (isCollectionProp && patchValueNode is JsonArray patchArray)
            {
                // Case-insensitive olarak mevcut diziyi bul veya oluştur
                var matchingEntry = rootNode.FirstOrDefault(kvp => kvp.Key.Equals(propName, StringComparison.OrdinalIgnoreCase));
                var targetArray = matchingEntry.Value as JsonArray;
                if (targetArray == null)
                {
                    targetArray = new JsonArray();
                    rootNode[matchingEntry.Key ?? propName] = targetArray;
                }

                foreach (var item in patchArray)
                {
                    if (item is JsonObject objItem)
                    {
                        var idKvp = objItem.FirstOrDefault(kvp => kvp.Key.Equals("id", StringComparison.OrdinalIgnoreCase));
                        var itemId = idKvp.Value?.GetValue<string>();
                        var actionKvp = objItem.FirstOrDefault(kvp => kvp.Key.Equals("action", StringComparison.OrdinalIgnoreCase));
                        var isRemove = actionKvp.Value?.GetValue<string>() == "remove";

                        if (!string.IsNullOrEmpty(itemId))
                        {
                            int existingIndex = -1;
                            for (int i = 0; i < targetArray.Count; i++)
                            {
                                if (targetArray[i] is JsonObject existingObj)
                                {
                                    var existingIdKvp = existingObj.FirstOrDefault(kvp => kvp.Key.Equals("id", StringComparison.OrdinalIgnoreCase));
                                    if (existingIdKvp.Value?.GetValue<string>() == itemId)
                                    {
                                        existingIndex = i;
                                        break;
                                    }
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
                                                var existingProp = existingItemObj.FirstOrDefault(p => p.Key.Equals(kvp.Key, StringComparison.OrdinalIgnoreCase));
                                                if (existingProp.Key != null && existingProp.Key != kvp.Key)
                                                {
                                                    existingItemObj.Remove(existingProp.Key);
                                                }
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

        edl.EdlJson = rootNode.ToJsonString(JsonOptions);
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

    public async Task<IReadOnlyList<double>> EnsureHighResolutionWaveformAsync(Guid projectId, CancellationToken cancellationToken = default)
    {
        var edl = await _context.EditDecisionLists
            .FirstOrDefaultAsync(e => e.ProjectId == projectId, cancellationToken);

        if (edl == null)
        {
            throw new NotFoundException("Projeye ait EDL bulunamadı", projectId);
        }

        double duration = 0;
        var existingPeaks = new List<double>();

        using (var doc = JsonDocument.Parse(edl.EdlJson))
        {
            if (doc.RootElement.TryGetProperty("duration", out var dProp) && dProp.TryGetDouble(out var dVal))
            {
                duration = dVal;
            }
            if (doc.RootElement.TryGetProperty("audioPeaks", out var pProp) && pProp.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in pProp.EnumerateArray())
                {
                    if (item.TryGetDouble(out var val))
                    {
                        existingPeaks.Add(val);
                    }
                }
            }
        }

        // Eğer zaten yüksek çözünürlüklü dalga formu varsa (> 2000 nokta veya saniyede >= 20 örnek) doğrudan dön
        int minExpectedHighRes = Math.Max(2000, (int)Math.Round(Math.Max(10.0, duration) * 20.0));
        if (existingPeaks.Count >= minExpectedHighRes || _fileStorageService == null)
        {
            return existingPeaks;
        }

        var video = await _context.Videos
            .AsNoTracking()
            .FirstOrDefaultAsync(v => v.ProjectId == projectId, cancellationToken);

        if (video == null || string.IsNullOrWhiteSpace(video.DosyaYolu))
        {
            return existingPeaks;
        }

        var objectKey = !string.IsNullOrWhiteSpace(video.TemizSesYolu) ? video.TemizSesYolu : video.DosyaYolu;
        var presignedUrl = await _fileStorageService.GetPresignedUrlAsync(objectKey, TimeSpan.FromHours(2), cancellationToken);

        _logger.LogInformation("Eski/Düşük çözünürlüklü dalga formu tespit edildi ({ExistingCount} nokta). Yüksek çözünürlüklü (Zero-Drift dBFS) dalga formu üretiliyor: ProjectId={ProjectId}", existingPeaks.Count, projectId);

        var highResPeaks = await ExtractPerceptualWaveformFromUrlAsync(presignedUrl, duration, cancellationToken);
        if (highResPeaks.Count == 0 && presignedUrl.Contains("://minio:"))
        {
            var localUrl = presignedUrl.Replace("://minio:", "://localhost:");
            highResPeaks = await ExtractPerceptualWaveformFromUrlAsync(localUrl, duration, cancellationToken);
        }

        if (highResPeaks.Count == 0)
        {
            return existingPeaks;
        }

        // EDL JSON içerisindeki audioPeaks dizisini kalıcı olarak güncelle
        var rootNode = JsonNode.Parse(edl.EdlJson) as JsonObject ?? new JsonObject();
        var peaksJsonArray = new JsonArray();
        foreach (var p in highResPeaks)
        {
            peaksJsonArray.Add(p);
        }
        rootNode["audioPeaks"] = peaksJsonArray;

        edl.EdlJson = rootNode.ToJsonString(JsonOptions);
        edl.GuncellemeTarihi = DateTime.UtcNow;

        await _context.SaveChangesAsync(cancellationToken);
        await _cacheService.RemoveAsync($"{CachePrefix}{projectId}", cancellationToken);

        _logger.LogInformation("Yüksek çözünürlüklü dalga formu başarıyla üretildi ve EDL'ye kaydedildi: ProjectId={ProjectId}, YeniNoktaSayisi={Count}", projectId, highResPeaks.Count);
        return highResPeaks;
    }

    private async Task<List<double>> ExtractPerceptualWaveformFromUrlAsync(string mediaUrl, double fallbackDuration, CancellationToken cancellationToken)
    {
        try
        {
            const int sampleRate = 8000;
            const int hopSamples = 80; // 10ms window at 8kHz = 100 Hz

            var psi = new ProcessStartInfo
            {
                FileName = "ffmpeg",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            psi.ArgumentList.Add("-v");
            psi.ArgumentList.Add("error");
            psi.ArgumentList.Add("-i");
            psi.ArgumentList.Add(mediaUrl);
            psi.ArgumentList.Add("-vn");
            psi.ArgumentList.Add("-acodec");
            psi.ArgumentList.Add("pcm_s16le");
            psi.ArgumentList.Add("-ar");
            psi.ArgumentList.Add(sampleRate.ToString());
            psi.ArgumentList.Add("-ac");
            psi.ArgumentList.Add("1");
            psi.ArgumentList.Add("-f");
            psi.ArgumentList.Add("s16le");
            psi.ArgumentList.Add("-");

            using var proc = Process.Start(psi);
            if (proc == null) return new List<double>();

            var hybridWindows = new List<float>(60000);
            var buffer = new byte[hopSamples * 2 * 250]; // 250 windows per read chunk
            int leftoverBytes = 0;
            var windowBuf = new byte[hopSamples * 2];

            var baseStream = proc.StandardOutput.BaseStream;
            while (true)
            {
                int bytesRead = await baseStream.ReadAsync(buffer.AsMemory(leftoverBytes, buffer.Length - leftoverBytes), cancellationToken);
                if (bytesRead <= 0) break;

                int totalBytes = leftoverBytes + bytesRead;
                int fullWindows = totalBytes / (hopSamples * 2);
                int consumedBytes = fullWindows * hopSamples * 2;

                for (int w = 0; w < fullWindows; w++)
                {
                    int offset = w * hopSamples * 2;
                    float maxPeak = 0f;
                    double sumSq = 0.0;
                    for (int s = 0; s < hopSamples; s++)
                    {
                        short sample = BitConverter.ToInt16(buffer, offset + s * 2);
                        float absVal = Math.Abs(sample / 32768f);
                        if (absVal > maxPeak) maxPeak = absVal;
                        sumSq += absVal * absVal;
                    }
                    float rms = (float)Math.Sqrt(sumSq / hopSamples);
                    hybridWindows.Add(0.65f * maxPeak + 0.35f * rms);
                }

                leftoverBytes = totalBytes - consumedBytes;
                if (leftoverBytes > 0)
                {
                    Buffer.BlockCopy(buffer, consumedBytes, buffer, 0, leftoverBytes);
                }
            }

            await proc.WaitForExitAsync(cancellationToken);

            int numWindows = hybridWindows.Count;
            if (numWindows == 0) return new List<double>();

            double duration = numWindows * 0.010;
            if (duration <= 0.1) duration = Math.Max(1.0, fallbackDuration);

            int peaksPerSec = duration <= 1200.0 ? 80 : (duration <= 3600.0 ? 50 : 40);
            int targetPeaks = Math.Max(500, (int)Math.Round(duration * peaksPerSec));

            var rawPeaks = new float[targetPeaks];
            for (int i = 0; i < targetPeaks; i++)
            {
                int sIdx = (int)Math.Floor((double)i * numWindows / targetPeaks);
                int eIdx = (int)Math.Floor((double)(i + 1) * numWindows / targetPeaks);
                sIdx = Math.Clamp(sIdx, 0, numWindows - 1);
                eIdx = Math.Clamp(Math.Max(sIdx + 1, eIdx), 1, numWindows);

                float maxVal = 0f;
                for (int k = sIdx; k < eIdx; k++)
                {
                    if (hybridWindows[k] > maxVal) maxVal = hybridWindows[k];
                }
                rawPeaks[i] = maxVal;
            }

            // Akustik Gürültü Tabanı (15. Persentil) ve 99.2 Persentil Algısal dBFS Ölçekleme
            var sortedAll = (float[])rawPeaks.Clone();
            Array.Sort(sortedAll);
            float noiseFloor = sortedAll[(int)Math.Clamp(sortedAll.Length * 0.15, 0, sortedAll.Length - 1)];
            float gate = Math.Clamp(noiseFloor * 2.2f, 0.0012f, 0.0080f);

            var activeList = new List<float>(rawPeaks.Length);
            foreach (var v in rawPeaks)
            {
                if (v > gate) activeList.Add(v);
            }

            float refCeiling;
            if (activeList.Count > 10)
            {
                activeList.Sort();
                refCeiling = activeList[(int)Math.Clamp(activeList.Count * 0.992, 0, activeList.Count - 1)];
            }
            else
            {
                refCeiling = sortedAll[^1];
            }

            float denom = Math.Max(1e-5f, refCeiling - gate);
            var result = new List<double>(targetPeaks);
            for (int i = 0; i < targetPeaks; i++)
            {
                float v = rawPeaks[i];
                if (v <= gate)
                {
                    result.Add(0.0);
                }
                else
                {
                    double norm = Math.Clamp((v - gate) / denom, 0.0, 1.0);
                    double perceptual = Math.Pow(norm, 0.52);
                    result.Add(Math.Round(perceptual, 3));
                }
            }

            return result;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "FFmpeg ile yüksek çözünürlüklü dalga formu çıkarılamadı: {Url}", mediaUrl);
            return new List<double>();
        }
    }
}
