namespace OtoEdit.API.Middleware;

/// <summary>
/// Admin tek kullanıcılı X-API-Key kimlik doğrulama middleware'i.
/// </summary>
public class ApiKeyAuthMiddleware
{
    private readonly RequestDelegate _next;
    private const string ApiKeyHeaderName = "X-API-Key";

    public ApiKeyAuthMiddleware(RequestDelegate next)
    {
        _next = next;
    }

    public async Task InvokeAsync(HttpContext context, IConfiguration configuration)
    {
        // CORS preflight istekleri şartsız geçer
        if (context.Request.Method == "OPTIONS")
        {
            await _next(context);
            return;
        }

        // Swagger dokümantasyonu, sağlık kontrolleri ve SignalR hub bağlantısı serbesttir
        if (context.Request.Path.StartsWithSegments("/swagger") ||
            context.Request.Path.StartsWithSegments("/health") ||
            context.Request.Path.StartsWithSegments("/pipeline-hub"))
        {
            await _next(context);
            return;
        }

        string? extractedApiKey = null;
        if (context.Request.Headers.TryGetValue(ApiKeyHeaderName, out var headerValue))
        {
            extractedApiKey = headerValue.ToString();
        }
        else if (context.Request.Query.TryGetValue("apiKey", out var queryValue) ||
                 context.Request.Query.TryGetValue("access_token", out queryValue))
        {
            extractedApiKey = queryValue.ToString();
        }

        if (string.IsNullOrEmpty(extractedApiKey))
        {
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            context.Response.ContentType = "application/json";
            await context.Response.WriteAsync("{\"error\": \"API Key zorunludur. Lütfen 'X-API-Key' başlığını ekleyin.\"}");
            return;
        }

        var configuredKey = configuration.GetValue<string>("ApiKey")
                            ?? configuration.GetValue<string>("ADMIN_API_KEY")
                            ?? "SUPER_SECRET_OTOEDIT_KEY_123!";

        if (!configuredKey.Equals(extractedApiKey))
        {
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            context.Response.ContentType = "application/json";
            await context.Response.WriteAsync("{\"error\": \"Geçersiz API Key.\"}");
            return;
        }

        await _next(context);
    }
}
