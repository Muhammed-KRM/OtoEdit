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
        // Multipart dosya yüklemelerini ve websocket isteklerini log gövdesine almayız
        if (context.Request.Path.StartsWithSegments("/pipeline-hub") ||
            (context.Request.ContentType?.Contains("multipart/form-data") ?? false))
        {
            await _next(context);
            return;
        }

        var stopwatch = Stopwatch.StartNew();

        // Request body oku
        context.Request.EnableBuffering();
        string? requestBody = null;
        if (context.Request.ContentLength > 0 && context.Request.Body.CanRead)
        {
            using var reader = new StreamReader(context.Request.Body, Encoding.UTF8, leaveOpen: true);
            requestBody = await reader.ReadToEndAsync();
            context.Request.Body.Position = 0;
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
            using (var reader = new StreamReader(responseBodyStream, Encoding.UTF8, leaveOpen: true))
            {
                responseBody = await reader.ReadToEndAsync();
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
                    RequestBody = requestBody != null ? (requestBody.Length > 4000 ? requestBody[..4000] : requestBody) : null,
                    ResponseBody = responseBody != null ? (responseBody.Length > 4000 ? responseBody[..4000] : responseBody) : null,
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
