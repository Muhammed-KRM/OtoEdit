using System.Net;
using System.Text.Json;
using FluentValidation;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Middleware;

/// <summary>
/// Global exception handling middleware. Hataları yakalar, FunctionLog tablosuna kaydeder ve ProblemDetails döner.
/// </summary>
public class ExceptionHandlingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionHandlingMiddleware> _logger;

    public ExceptionHandlingMiddleware(RequestDelegate next, ILogger<ExceptionHandlingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, ILogService logService)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "İşlenmemiş istisna oluştu: {Message}", ex.Message);

            // FunctionLog tablosuna kaydet
            try
            {
                await logService.LogFunctionErrorAsync(
                    errorCode: "API_UNHANDLED_ERR",
                    ex: ex,
                    input: new { context.Request.Path, context.Request.Method },
                    traceId: context.TraceIdentifier);
            }
            catch
            {
                // Log servisi hatası ana akışı engellememeli
            }

            await HandleExceptionAsync(context, ex);
        }
    }

    private static Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        var statusCode = HttpStatusCode.InternalServerError;
        var result = string.Empty;

        switch (exception)
        {
            case ValidationException validationException:
                statusCode = HttpStatusCode.BadRequest;
                result = JsonSerializer.Serialize(new
                {
                    type = "https://tools.ietf.org/html/rfc7231#section-6.5.1",
                    title = "Doğrulama Hatası",
                    status = (int)statusCode,
                    errors = validationException.Errors.Select(e => new { e.PropertyName, e.ErrorMessage })
                });
                break;

            case NotFoundException notFoundException:
                statusCode = HttpStatusCode.NotFound;
                result = JsonSerializer.Serialize(new
                {
                    type = "https://tools.ietf.org/html/rfc7231#section-6.5.4",
                    title = "Kayıt Bulunamadı",
                    status = (int)statusCode,
                    detail = notFoundException.Message
                });
                break;

            case BusinessException businessException:
                statusCode = HttpStatusCode.BadRequest;
                result = JsonSerializer.Serialize(new
                {
                    type = "https://tools.ietf.org/html/rfc7231#section-6.5.1",
                    title = "İş Kuralı İhlali",
                    status = (int)statusCode,
                    detail = businessException.Message
                });
                break;

            default:
                statusCode = HttpStatusCode.InternalServerError;
                result = JsonSerializer.Serialize(new
                {
                    type = "https://tools.ietf.org/html/rfc7231#section-6.6.1",
                    title = "Sunucu Hatası",
                    status = (int)statusCode,
                    detail = exception.Message
                });
                break;
        }

        context.Response.ContentType = "application/problem+json";
        context.Response.StatusCode = (int)statusCode;
        return context.Response.WriteAsync(result);
    }
}
