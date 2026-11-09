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

    /// <summary>
    /// En son yapılan EDL değişikliğini geri alır (Undo).
    /// </summary>
    [HttpPost("undo")]
    [ProducesResponseType(typeof(EdlDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UndoEdl(Guid projectId, CancellationToken cancellationToken)
    {
        var result = await _edlService.UndoAsync(projectId, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// Geri alınan EDL değişikliğini ileri alır (Redo).
    /// </summary>
    [HttpPost("redo")]
    [ProducesResponseType(typeof(EdlDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> RedoEdl(Guid projectId, CancellationToken cancellationToken)
    {
        var result = await _edlService.RedoAsync(projectId, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// Projeye ait yüksek çözünürlüklü (Zero-Drift dBFS) ses dalga formunu getirir veya eski projeler için otomatik üretir.
    /// </summary>
    [HttpGet("waveform")]
    [ProducesResponseType(typeof(IReadOnlyList<double>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetHighResWaveform(Guid projectId, CancellationToken cancellationToken)
    {
        var peaks = await _edlService.EnsureHighResolutionWaveformAsync(projectId, cancellationToken);
        return Ok(peaks);
    }

    /// <summary>
    /// 3. denetim turu sonrasında veya kullanıcı incelemesinde kurgu senaryosunu onaylar ve uygular.
    /// </summary>
    [HttpPost("scenario/approve")]
    [ProducesResponseType(typeof(EdlDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> ApproveScenario(Guid projectId, CancellationToken cancellationToken)
    {
        var result = await _edlService.ApproveScenarioAsync(projectId, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// Kullanıcının doğal dille verdiği revizyonu ("Şu kısımlara şunu ekle...") kurgu senaryosuna uygular ve tekrar onaya sunar.
    /// </summary>
    [HttpPost("scenario/revise")]
    [ProducesResponseType(typeof(EdlDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> ReviseScenario(
        Guid projectId,
        [FromBody] ScenarioRevisionRequestDto request,
        CancellationToken cancellationToken)
    {
        var result = await _edlService.ReviseScenarioAsync(projectId, request.Feedback, cancellationToken);
        return Ok(result);
    }
}

public record ScenarioRevisionRequestDto(string Feedback);
