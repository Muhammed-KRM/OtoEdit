using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.DTOs.Render;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
public class RenderController : ControllerBase
{
    private readonly IRenderService _renderService;

    public RenderController(IRenderService renderService)
    {
        _renderService = renderService;
    }

    /// <summary>
    /// Proje için render işlemi başlatır (asenkron kuyruğa gönderir).
    /// </summary>
    [HttpPost("api/projects/{projectId:guid}/render")]
    [ProducesResponseType(typeof(RenderStatusDto), StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> RequestRender(Guid projectId, [FromBody] RenderRequestDto? dto, CancellationToken cancellationToken)
    {
        var result = await _renderService.RequestRenderAsync(projectId, dto, cancellationToken);
        return Accepted(result);
    }

    /// <summary>
    /// Belirtilen render işinin durumunu getirir.
    /// </summary>
    [HttpGet("api/projects/{projectId:guid}/render/{renderJobId:guid}")]
    [ProducesResponseType(typeof(RenderStatusDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetRenderStatus(Guid projectId, Guid renderJobId, CancellationToken cancellationToken)
    {
        var status = await _renderService.GetRenderStatusAsync(projectId, renderJobId, cancellationToken);
        return Ok(status);
    }

    /// <summary>
    /// Tamamlanan render videosunun presigned indirme URL'ini döner.
    /// </summary>
    [HttpGet("api/projects/{projectId:guid}/render/{renderJobId:guid}/download")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Download(Guid projectId, Guid renderJobId, CancellationToken cancellationToken)
    {
        var downloadUrl = await _renderService.GetDownloadUrlAsync(projectId, renderJobId, cancellationToken);
        return Ok(new { downloadUrl });
    }
}
