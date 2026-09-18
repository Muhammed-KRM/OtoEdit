using MassTransit;
using Microsoft.AspNetCore.SignalR;
using OtoEdit.API.Consumers;
using OtoEdit.API.Hubs;
using OtoEdit.API.Middleware;
using OtoEdit.Business;
using OtoEdit.Business.Services;
using OtoEdit.Data;

var builder = WebApplication.CreateBuilder(args);

// Kök dizinde .env dosyası varsa ortam değişkenlerini yükle
var searchDir = new DirectoryInfo(Directory.GetCurrentDirectory());
while (searchDir != null)
{
    var envPath = Path.Combine(searchDir.FullName, ".env");
    if (File.Exists(envPath))
    {
        foreach (var line in File.ReadAllLines(envPath))
        {
            var trimmed = line.Trim();
            if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#')) continue;
            var parts = trimmed.Split('=', 2);
            if (parts.Length == 2)
            {
                var key = parts[0].Trim();
                var val = parts[1].Trim();
                Environment.SetEnvironmentVariable(key, val);
                builder.Configuration[key] = val;
            }
        }
        break;
    }
    searchDir = searchDir.Parent;
}

// 1. Controller ve JSON Serileştirme
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter());
    });

// 2. Swagger
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// 3. SignalR Canlı Bildirim
builder.Services.AddSignalR();

// 4. Kestrel 2GB Limitleri
builder.WebHost.ConfigureKestrel(serverOptions =>
{
    serverOptions.Limits.MaxRequestBodySize = 2147483648; // 2GB
});

builder.Services.Configure<Microsoft.AspNetCore.Http.Features.FormOptions>(options =>
{
    options.ValueLengthLimit = int.MaxValue;
    options.MultipartBodyLengthLimit = 2147483648; // 2GB
    options.MultipartHeadersLengthLimit = int.MaxValue;
});

// 5. Data ve Business Katmanlarının Kaydı
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
                       ?? "Host=localhost;Port=5432;Database=otoedit;Username=postgres;Password=postgres";

builder.Services.AddDataLayer(connectionString);
builder.Services.AddBusinessLayer(builder.Configuration, x =>
{
    // Python Worker'dan gelen event'leri dinleyen MassTransit Consumer'lar
    x.AddConsumer<AnalysisNotificationConsumer>();
    x.AddConsumer<RenderNotificationConsumer>();
});

// 6. CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.SetIsOriginAllowed(_ => true)
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials();
    });
});

var app = builder.Build();

// 7. PipelineNotificationManager ile SignalR Hub bağlantısı
var hubContext = app.Services.GetRequiredService<IHubContext<PipelineHub>>();
PipelineNotificationManager.SendSignalRMessageAsync = async (projectId, method, payload) =>
{
    await hubContext.Clients.Group($"project-{projectId}").SendAsync(method, payload);
};

// 8. Middleware Pipeline Sıralaması
app.UseMiddleware<ExceptionHandlingMiddleware>();
app.UseMiddleware<RequestResponseLoggingMiddleware>();

if (app.Environment.IsDevelopment() || true) // Swagger her zaman erişilebilir
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "OtoEdit API v1");
    });
}

app.UseCors("AllowFrontend");

// X-API-Key doğrulaması
app.UseMiddleware<ApiKeyAuthMiddleware>();

app.UseAuthorization();
app.MapControllers();
app.MapHub<PipelineHub>("/pipeline-hub");

app.Run();

public partial class Program { }
