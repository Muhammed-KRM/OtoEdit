using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.DTOs.Asset;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/assets")]
public class AssetsController : ControllerBase
{
    private readonly IAssetService _assetService;

    public AssetsController(IAssetService assetService)
    {
        _assetService = assetService;
    }

    /// <summary>
    /// Projeye görsel, ses veya video gibi harici medya dosyası yükler.
    /// </summary>
    [HttpPost]
    [RequestSizeLimit(52428800)] // 50MB
    [RequestFormLimits(MultipartBodyLengthLimit = 52428800)]
    [ProducesResponseType(typeof(ProjectAssetDto), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UploadAsset(
        Guid projectId,
        IFormFile file,
        CancellationToken cancellationToken)
    {
        if (file == null || file.Length == 0)
        {
            return BadRequest("Yüklenecek medya dosyası boş olamaz.");
        }

        var asset = await _assetService.UploadAssetAsync(projectId, file, cancellationToken);
        return StatusCode(StatusCodes.Status201Created, asset);
    }

    /// <summary>
    /// Projeye yüklenmiş tüm medya varlıklarını listeler.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<ProjectAssetDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetAssets(Guid projectId, CancellationToken cancellationToken)
    {
        var assets = await _assetService.GetProjectAssetsAsync(projectId, cancellationToken);
        return Ok(assets);
    }

    /// <summary>
    /// Projeye ait bir medya varlığını siler.
    /// </summary>
    [HttpDelete("{assetId:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteAsset(
        Guid projectId, 
        Guid assetId, 
        CancellationToken cancellationToken)
    {
        await _assetService.DeleteAssetAsync(projectId, assetId, cancellationToken);
        return NoContent();
    }

    /// <summary>
    /// Medya dosyasını doğrudan istemciye yönlendirir veya akıtır.
    /// </summary>
    [HttpGet("{assetId:guid}/stream")]
    public async Task<IActionResult> StreamAsset(
        Guid projectId, 
        Guid assetId, 
        CancellationToken cancellationToken)
    {
        var url = await _assetService.GetAssetUrlAsync(projectId, assetId, cancellationToken);
        return Redirect(url);
    }
}
