using Microsoft.AspNetCore.Http;
using OtoEdit.Business.DTOs.Asset;

namespace OtoEdit.Business.Interfaces;

/// <summary>
/// Projeye ait medya varlıkları (resim, ses, b-roll, logo vb.) iş mantığı servisi.
/// </summary>
public interface IAssetService
{
    Task<ProjectAssetDto> UploadAssetAsync(Guid projectId, IFormFile file, CancellationToken cancellationToken = default);
    Task<IEnumerable<ProjectAssetDto>> GetProjectAssetsAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task DeleteAssetAsync(Guid projectId, Guid assetId, CancellationToken cancellationToken = default);
    Task<(Stream FileStream, string ContentType, string FileName)> GetAssetStreamAsync(Guid projectId, Guid assetId, CancellationToken cancellationToken = default);
    Task<string> GetAssetUrlAsync(Guid projectId, Guid assetId, CancellationToken cancellationToken = default);
}
