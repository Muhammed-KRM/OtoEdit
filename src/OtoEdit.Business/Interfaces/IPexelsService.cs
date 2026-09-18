namespace OtoEdit.Business.Interfaces;

/// <summary>
/// Pexels API üzerinden telifsiz stok görsel arama ve MinIO'ya asset kaydetme servisi.
/// </summary>
public interface IPexelsService
{
    /// <summary>
    /// Pexels API üzerinde görsel arar ve ilk görselin URL'sini döner.
    /// </summary>
    Task<string?> SearchPhotoUrlAsync(string query, string orientation = "landscape", CancellationToken cancellationToken = default);

    /// <summary>
    /// Belirtilen arama sorgusu ile görseli indirir ve MinIO'ya proje asset'i olarak kaydeder.
    /// </summary>
    /// <returns>MinIO S3 object key (örn: assets/{projectId}/{guid}.jpg)</returns>
    Task<string?> SearchAndSaveAssetAsync(Guid projectId, string query, string orientation = "landscape", CancellationToken cancellationToken = default);
}
