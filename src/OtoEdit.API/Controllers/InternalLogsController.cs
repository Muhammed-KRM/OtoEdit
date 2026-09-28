using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Hubs;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.API.Controllers;

public record PipelineLogRequestDto(
    string? ProjectId,
    string? VideoId,
    string? Stage,
    int ProgressPercentage,
    string? Status,
    string? Message,
    string? DetailsJson,
    string? ErrorMessage,
    DateTime? TimestampUtc
);

/// <summary>
/// Python Worker'dan gelen doğrudan pipeline loglarını alan ve veritabanı ile SignalR'a aktaran dahili kontrolcü.
/// </summary>
[ApiController]
[Route("api/internal/logs")]
public class InternalLogsController : ControllerBase
{
    private readonly AppDbContext _context;
    private readonly IHubContext<PipelineHub> _hubContext;
    private readonly ILogger<InternalLogsController> _logger;

    public InternalLogsController(
        AppDbContext context,
        IHubContext<PipelineHub> hubContext,
        ILogger<InternalLogsController> logger)
    {
        _context = context;
        _hubContext = hubContext;
        _logger = logger;
    }

    /// <summary>
    /// Python Worker'dan gelen aşama durumunu kaydeder ve SignalR ile canlı yayınlar.
    /// </summary>
    [HttpPost("pipeline")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> LogPipelineProgress([FromBody] PipelineLogRequestDto dto, CancellationToken cancellationToken)
    {
        if (dto == null)
            return BadRequest("Log verisi boş olamaz.");

        Guid? parsedProjectId = Guid.TryParse(dto.ProjectId, out var pId) ? pId : null;
        Guid? parsedVideoId = Guid.TryParse(dto.VideoId, out var vId) ? vId : null;

        // Enum çözümleme (Büyük/küçük harf toleranslı)
        PipelineAsamasi parsedStage = PipelineAsamasi.SesIyilestirme;
        if (!string.IsNullOrWhiteSpace(dto.Stage) && Enum.TryParse<PipelineAsamasi>(dto.Stage, true, out var stageVal))
        {
            parsedStage = stageVal;
        }

        try
        {
            var logEntity = new PipelineLog
            {
                ProjectId = parsedProjectId,
                VideoId = parsedVideoId,
                Asama = parsedStage,
                Durum = dto.Status ?? "InProgress",
                BaslangicZamani = dto.TimestampUtc ?? DateTime.UtcNow,
                HataMesaji = dto.ErrorMessage,
                GirdiMetadata = dto.DetailsJson,
                CiktiMetadata = dto.Message,
                CreatedAt = DateTime.UtcNow
            };

            await _context.PipelineLogs.AddAsync(logEntity, cancellationToken);
            await _context.SaveChangesAsync(cancellationToken);

            // SignalR ile bağlı Angular istemcilerine canlı bildirim
            if (parsedProjectId.HasValue)
            {
                await _hubContext.Clients
                    .Group($"project-{parsedProjectId.Value}")
                    .SendAsync("AnalysisProgress", new
                    {
                        projectId = parsedProjectId.Value,
                        asama = parsedStage.ToString(),
                        yuzde = dto.ProgressPercentage,
                        durum = dto.Status,
                        mesaj = dto.Message ?? string.Empty
                    }, cancellationToken);
            }

            return Ok(new { success = true, logId = logEntity.Id });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Pipeline logu kaydedilirken hata oluştu: ProjectId={ProjectId}, Stage={Stage}", dto.ProjectId, dto.Stage);
            // Internal log servisi hata durumunda dahi istemciyi (worker) kitlememeli
            return StatusCode(StatusCodes.Status500InternalServerError, new { success = false, error = ex.Message });
        }
    }
}
