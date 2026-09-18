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
    [RequestSizeLimit(2147483648)] // 2GB
    [RequestFormLimits(MultipartBodyLengthLimit = 2147483648)]
    [ProducesResponseType(typeof(VideoListDto), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UploadVideo(Guid projectId, IFormFile file, CancellationToken cancellationToken)
    {
        var result = await _videoService.UploadVideoAsync(projectId, file, cancellationToken);
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
}
