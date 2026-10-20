using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.DTOs.Video;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
public class VideosController : ControllerBase
{
    private readonly IVideoService _videoService;

    public VideosController(IVideoService videoService)
    {
        _videoService = videoService;
    }

    /// <summary>
    /// Projeye ham video dosyası yükler ve analiz sürecini başlatır.
    /// </summary>
    [HttpPost("api/projects/{projectId:guid}/videos")]
    [RequestSizeLimit(53687091200L)] // 50GB
    [RequestFormLimits(MultipartBodyLengthLimit = 53687091200L)]
    [ProducesResponseType(typeof(VideoListDto), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UploadVideo(
        Guid projectId, 
        [FromForm] VideoUploadDto dto, 
        CancellationToken cancellationToken)
    {
        var result = await _videoService.UploadVideoAsync(
            projectId, 
            dto.File, 
            dto.AutoJumpcut,
            dto.AutoRetake,
            dto.AutoBroll,
            dto.AutoSubtitles,
            cancellationToken,
            dto.AudioEnhancementEnabled,
            dto.GestureCommandsEnabled,
            dto.AutoDirectorEnabled,
            dto.DirectToEditor);
        return StatusCode(StatusCodes.Status201Created, result);
    }

    /// <summary>
    /// Projeye ait videonun detaylarını getirir.
    /// </summary>
    [HttpGet("api/projects/{projectId:guid}/video")]
    [ProducesResponseType(typeof(VideoDetailDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetVideo(Guid projectId, CancellationToken cancellationToken)
    {
        var video = await _videoService.GetVideoByProjectIdAsync(projectId, cancellationToken);
        if (video == null) return NotFound("Projeye ait video bulunamadı.");
        return Ok(video);
    }

    /// <summary>
    /// Projeye ait videoyu siler.
    /// </summary>
    [HttpDelete("api/projects/{projectId:guid}/video")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteVideo(Guid projectId, CancellationToken cancellationToken)
    {
        await _videoService.DeleteVideoAsync(projectId, cancellationToken);
        return NoContent();
    }

    /// <summary>
    /// Videoyu doğrudan akış (streaming) olarak istemciye iletir.
    /// </summary>
    [HttpGet("api/videos/{videoId:guid}/stream")]
    public async Task<IActionResult> StreamVideo(Guid videoId, CancellationToken cancellationToken)
    {
        var url = await _videoService.GetVideoUrlAsync(videoId, cancellationToken);
        return Redirect(url);
    }

    /// <summary>
    /// Mevcut bir projede seçilen AI analiz adımlarını (Altyazı, Jumpcut, B-Roll, Otonom Yönetmen vb.) isteğe bağlı (On-Demand) tetikler.
    /// </summary>
    [HttpPost("api/projects/{projectId:guid}/reanalyze")]
    public async Task<IActionResult> ReanalyzeProject(
        Guid projectId,
        [FromBody] ReanalyzeRequestDto dto,
        CancellationToken cancellationToken)
    {
        await _videoService.TriggerAnalysisAsync(
            projectId,
            dto.AutoJumpcut,
            dto.AutoRetake,
            dto.AutoBroll,
            dto.AutoSubtitles,
            dto.AudioEnhancementEnabled,
            dto.GestureCommandsEnabled,
            dto.AutoDirectorEnabled,
            cancellationToken);
        return Accepted(new { projectId, status = "AnalizBaslatildi" });
    }
}

public class ReanalyzeRequestDto
{
    public bool AutoJumpcut { get; set; }
    public bool AutoRetake { get; set; }
    public bool AutoBroll { get; set; }
    public bool AutoSubtitles { get; set; } = true;
    public bool AudioEnhancementEnabled { get; set; }
    public bool GestureCommandsEnabled { get; set; }
    public bool AutoDirectorEnabled { get; set; }
}
