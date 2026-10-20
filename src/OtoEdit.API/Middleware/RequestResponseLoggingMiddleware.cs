using System.Diagnostics;
using System.Text;
using OtoEdit.Business.Helpers;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Entities;

namespace OtoEdit.API.Middleware;

/// <summary>
/// Tüm HTTP istek ve yanıtlarını otomatik olarak 'endpoint_logs' tablosuna kaydeden middleware.
/// </summary>
public class RequestResponseLoggingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RequestResponseLoggingMiddleware> _logger;

    public RequestResponseLoggingMiddleware(RequestDelegate next, ILogger<RequestResponseLoggingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, ILogService logService)
    {
        var pathVal = context.Request.Path.Value ?? string.Empty;

        // Multipart dosya yüklemelerini, websocket isteklerini ve yüksek frekanslı/büyük EDL & medya akışlarını MemoryStream'e tamponlama
        if (context.Request.Path.StartsWithSegments("/pipeline-hub") ||
            (context.Request.ContentType?.Contains("multipart/form-data") ?? false))
        {
            await _next(context);
            return;
        }

        bool skipBodyBuffering = pathVal.EndsWith("/edl", StringComparison.OrdinalIgnoreCase) ||
                                 pathVal.EndsWith("/waveform", StringComparison.OrdinalIgnoreCase) ||
                                 pathVal.Contains("/stream", StringComparison.OrdinalIgnoreCase) ||
                                 pathVal.Contains("/download", StringComparison.OrdinalIgnoreCase);

        if (skipBodyBuffering)
        {
            var fastSw = Stopwatch.StartNew();
            try
            {
                await _next(context);
            }
            finally
            {
                fastSw.Stop();
                try
                {
                    var fastLog = new EndpointLog
                    {
                        TraceId = context.TraceIdentifier,
                        Method = context.Request.Method,
                        Path = pathVal,
                        Query = context.Request.QueryString.HasValue ? context.Request.QueryString.Value : null,
                        RequestBody = null,
                        ResponseBody = "[SKIPPED_LARGE_STREAM]",
                        StatusCode = context.Response.StatusCode,
                        IpAddress = context.Connection.RemoteIpAddress?.ToString(),
                        UserAgent = context.Request.Headers.UserAgent.ToString(),
                        DurationMs = (int)fastSw.ElapsedMilliseconds,
                        CreatedAt = DateTime.UtcNow
                    };
                    await logService.LogEndpointAsync(fastLog);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "EndpointLog DB kaydı sırasında hata oluştu.");
                }
            }
            return;
        }

        var stopwatch = Stopwatch.StartNew();

        // Request body oku (Sadece 64 KB altındaki istek gövdelerini log için oku)
        string? requestBody = null;
        if (context.Request.ContentLength is > 0 and <= 65536 && context.Request.Body.CanRead)
        {
            context.Request.EnableBuffering();
            using var reader = new StreamReader(context.Request.Body, Encoding.UTF8, leaveOpen: true);
            var rawReq = await reader.ReadToEndAsync();
            context.Request.Body.Position = 0;
            if (!string.IsNullOrEmpty(rawReq))
            {
                var slicedReq = rawReq.Length > 4000 ? rawReq[..4000] : rawReq;
                requestBody = slicedReq.Replace("\0", string.Empty);
            }
        }

        // Response body yakalamak için geçici stream
        var originalBodyStream = context.Response.Body;
        using var responseBodyStream = new MemoryStream();
        context.Response.Body = responseBodyStream;

        try
        {
            await _next(context);
        }
        finally
        {
            stopwatch.Stop();

            responseBodyStream.Seek(0, SeekOrigin.Begin);
            string? responseBody = null;
            if (responseBodyStream.Length <= 65536)
            {
                using var reader = new StreamReader(responseBodyStream, Encoding.UTF8, leaveOpen: true);
                var rawRes = await reader.ReadToEndAsync();
                if (!string.IsNullOrEmpty(rawRes))
                {
                    var slicedRes = rawRes.Length > 4000 ? rawRes[..4000] : rawRes;
                    responseBody = slicedRes.Replace("\0", string.Empty);
                }
            }
            else
            {
                responseBody = $"[LARGE_RESPONSE:{responseBodyStream.Length}_BYTES]";
            }
            responseBodyStream.Seek(0, SeekOrigin.Begin);
            await responseBodyStream.CopyToAsync(originalBodyStream);

            // Log kaydını hazırla ve DB'ye asenkron yaz
            try
            {
                var endpointLog = new EndpointLog
                {
                    TraceId = context.TraceIdentifier,
                    Method = context.Request.Method,
                    Path = context.Request.Path,
                    Query = context.Request.QueryString.HasValue ? context.Request.QueryString.Value : null,
                    RequestBody = requestBody,
                    ResponseBody = responseBody,
                    StatusCode = context.Response.StatusCode,
                    IpAddress = context.Connection.RemoteIpAddress?.ToString(),
                    UserAgent = context.Request.Headers.UserAgent.ToString(),
                    DurationMs = (int)stopwatch.ElapsedMilliseconds,
                    CreatedAt = DateTime.UtcNow
                };

                await logService.LogEndpointAsync(endpointLog);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "EndpointLog DB kaydı sırasında hata oluştu.");
            }
        }
    }
}
