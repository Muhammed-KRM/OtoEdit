using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/edl")]
public class EdlController : ControllerBase
{
    private readonly IEdlService _edlService;

    public EdlController(IEdlService edlService)
    {
        _edlService = edlService;
    }

    /// <summary>
    /// Projeye ait güncel Edit Decision List (EDL) JSON verisini getirir.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(EdlDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetEdl(Guid projectId, CancellationToken cancellationToken)
    {
        var edl = await _edlService.GetEdlAsync(projectId, cancellationToken);
        return Ok(edl);
    }

    /// <summary>
    /// EDL JSON üzerinde kısmi güncelleme (patch) uygular.
    /// </summary>
    [HttpPatch]
    [ProducesResponseType(typeof(EdlPatchResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> PatchEdl(Guid projectId, [FromBody] JsonElement patch, CancellationToken cancellationToken)
    {
        var result = await _edlService.PatchEdlAsync(projectId, patch, cancellationToken);
        return Ok(result);
    }
}
