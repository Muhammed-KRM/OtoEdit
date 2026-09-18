using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OtoEdit.Data.Context;
using OtoEdit.Data.Enums;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class PipelineController : ControllerBase
{
    private readonly AppDbContext _context;

    public PipelineController(AppDbContext context)
    {
        _context = context;
    }

    /// <summary>
    /// Projenin analiz pipeline ilerleme durumunu ve aşama loglarını getirir.
    /// </summary>
    [HttpGet("project/{projectId:guid}/progress")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<IActionResult> GetProjectProgress(Guid projectId, CancellationToken cancellationToken)
    {
        var logs = await _context.PipelineLogs
            .Where(p => p.ProjectId == projectId)
            .OrderBy(p => p.BaslangicZamani)
            .AsNoTracking()
            .ToListAsync(cancellationToken);

        var project = await _context.Projects
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.Id == projectId, cancellationToken);

        return Ok(new
        {
            projectId,
            durum = project?.Durum.ToString(),
            logs = logs.Select(l => new
            {
                l.Id,
                asama = l.Asama.ToString(),
                l.Durum,
                l.BaslangicZamani,
                l.BitisZamani,
                l.SureMs,
                l.HataMesaji
            })
        });
    }

    /// <summary>
    /// Belirli bir videonun analiz durumunu getirir.
    /// </summary>
    [HttpGet("video/{videoId:guid}/status")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetVideoStatus(Guid videoId, CancellationToken cancellationToken)
    {
        var video = await _context.Videos
            .AsNoTracking()
            .FirstOrDefaultAsync(v => v.Id == videoId, cancellationToken);

        if (video == null) return NotFound("Video bulunamadı.");

        return Ok(new
        {
            videoId = video.Id,
            projectId = video.ProjectId,
            islemDurumu = video.IslemDurumu.ToString(),
            olusturmaTarihi = video.OlusturmaTarihi,
            islemTamamlanmaTarihi = video.IslemTamamlanmaTarihi
        });
    }
}
