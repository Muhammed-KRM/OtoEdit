using System.Runtime.CompilerServices;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.Helpers;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Services;

/// <summary>
/// 3 Katmanlı Loglama Servisi (EndpointLog, PipelineLog, FunctionLog).
/// </summary>
public class LogManager : ILogService
{
    private readonly AppDbContext _context;
    private readonly ILogger<LogManager> _logger;

    public LogManager(AppDbContext context, ILogger<LogManager> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task LogEndpointAsync(EndpointLog log, CancellationToken cancellationToken = default)
    {
        try
        {
            if (!string.IsNullOrEmpty(log.RequestBody))
            {
                log.RequestBody = SensitiveDataMasker.MaskJson(log.RequestBody);
            }

            _context.EndpointLogs.Add(log);
            await _context.SaveChangesAsync(cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Endpoint log DB kaydı başarısız oldu.");
        }
    }

    public async Task<long> LogPipelineStartAsync(
        Guid? videoId,
        Guid? projectId,
        PipelineAsamasi asama,
        string? traceId = null,
        string? girdiMetadata = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var log = new PipelineLog
            {
                VideoId = videoId,
                ProjectId = projectId,
                Asama = asama,
                Durum = "Basladi",
                TraceId = traceId,
                GirdiMetadata = girdiMetadata != null ? SensitiveDataMasker.MaskJson(girdiMetadata) : null,
                BaslangicZamani = DateTime.UtcNow,
                CreatedAt = DateTime.UtcNow
            };

            _context.PipelineLogs.Add(log);
            await _context.SaveChangesAsync(cancellationToken);
            return log.Id;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Pipeline start log DB kaydı başarısız oldu.");
            return 0;
        }
    }

    public async Task LogPipelineEndAsync(long logId, string? ciktiMetadata = null, CancellationToken cancellationToken = default)
    {
        if (logId <= 0) return;

        try
        {
            var log = await _context.PipelineLogs.FindAsync(new object[] { logId }, cancellationToken);
            if (log != null)
            {
                log.Durum = "Tamamlandi";
                log.BitisZamani = DateTime.UtcNow;
                log.SureMs = (int)(log.BitisZamani.Value - log.BaslangicZamani).TotalMilliseconds;
                log.CiktiMetadata = ciktiMetadata != null ? SensitiveDataMasker.MaskJson(ciktiMetadata) : null;
                await _context.SaveChangesAsync(cancellationToken);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Pipeline end log DB kaydı başarısız oldu: LogId={LogId}", logId);
        }
    }

    public async Task LogPipelineErrorAsync(long logId, Exception ex, CancellationToken cancellationToken = default)
    {
        if (logId <= 0) return;

        try
        {
            var log = await _context.PipelineLogs.FindAsync(new object[] { logId }, cancellationToken);
            if (log != null)
            {
                log.Durum = "Hata";
                log.BitisZamani = DateTime.UtcNow;
                log.SureMs = (int)(log.BitisZamani.Value - log.BaslangicZamani).TotalMilliseconds;
                log.HataMesaji = ex.Message;
                log.HataDetayi = ex.StackTrace;
                await _context.SaveChangesAsync(cancellationToken);
            }
        }
        catch (Exception logEx)
        {
            _logger.LogError(logEx, "Pipeline error log DB kaydı başarısız oldu: LogId={LogId}", logId);
        }
    }

    public async Task LogFunctionErrorAsync(
        string errorCode,
        Exception ex,
        object? input = null,
        string? traceId = null,
        [CallerMemberName] string methodName = "",
        [CallerFilePath] string filePath = "",
        [CallerLineNumber] int lineNumber = 0,
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogError(ex, "Function hatası [{ErrorCode}] in {MethodName} ({FilePath}:{LineNumber})", errorCode, methodName, filePath, lineNumber);

            string? inputJson = null;
            if (input != null)
            {
                try { inputJson = JsonSerializer.Serialize(input); }
                catch { inputJson = input.ToString(); }
            }

            var className = Path.GetFileNameWithoutExtension(filePath);

            var log = new FunctionLog
            {
                ErrorCode = errorCode,
                ClassName = string.IsNullOrEmpty(className) ? "Unknown" : className,
                MethodName = methodName,
                FilePath = filePath,
                LineNumber = lineNumber,
                ErrorMessage = ex.Message,
                StackTrace = ex.StackTrace,
                InputType = input?.GetType().Name,
                InputValue = inputJson != null ? SensitiveDataMasker.MaskJson(inputJson) : null,
                TraceId = traceId,
                Severity = ex is OutOfMemoryException or StackOverflowException ? "Critical" : "Error",
                CreatedAt = DateTime.UtcNow
            };

            _context.FunctionLogs.Add(log);
            await _context.SaveChangesAsync(cancellationToken);
        }
        catch (Exception dbEx)
        {
            _logger.LogError(dbEx, "FunctionLog DB kaydı başarısız oldu.");
        }
    }
}
