using System.Reflection;
using FluentValidation;
using MassTransit;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Minio;
using OtoEdit.Business.Infrastructure.AI;
using OtoEdit.Business.Infrastructure.Cache;
using OtoEdit.Business.Infrastructure.Storage;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using StackExchange.Redis;

namespace OtoEdit.Business;

/// <summary>
/// Business katmanı servis ve bağımlılık kayıtları.
/// </summary>
public static class DependencyInjection
{
    public static IServiceCollection AddBusinessLayer(
        this IServiceCollection services,
        IConfiguration configuration,
        Action<IBusRegistrationConfigurator>? configureMassTransit = null)
    {
        // 1. FluentValidation
        services.AddValidatorsFromAssembly(Assembly.GetExecutingAssembly());

        // 2. MinIO S3 Object Storage
        var endpoint = configuration["Minio:Endpoint"] ?? "localhost:9000";
        var accessKey = configuration["Minio:AccessKey"] ?? "minioadmin";
        var secretKey = configuration["Minio:SecretKey"] ?? "minioadmin";
        var useSsl = configuration.GetValue<bool>("Minio:UseSSL");

        services.AddMinio(configureClient => configureClient
            .WithEndpoint(endpoint)
            .WithCredentials(accessKey, secretKey)
            .WithSSL(useSsl)
            .Build());

        services.AddScoped<IFileStorageService, MinioFileStorageService>();

        // 3. Redis Cache
        var redisConn = configuration["Redis:ConnectionString"] ?? "localhost:6379";
        var redisOptions = ConfigurationOptions.Parse(redisConn);
        redisOptions.AbortOnConnectFail = false;
        services.AddSingleton<IConnectionMultiplexer>(ConnectionMultiplexer.Connect(redisOptions));
        services.AddSingleton<ICacheService, RedisCacheService>();

        // 4. AI Chat Provider (Gemini)
        services.AddScoped<IChatProvider, GeminiChatProvider>();

        // 5. Business Services
        services.AddScoped<ILogService, LogManager>();
        services.AddScoped<IPipelineNotificationService, PipelineNotificationManager>();
        services.AddScoped<IProjectService, ProjectManager>();
        services.AddScoped<IVideoService, VideoManager>();
        services.AddScoped<IEdlService, EdlManager>();
        services.AddScoped<IChatService, ChatManager>();
        services.AddScoped<IRenderService, RenderManager>();
        services.AddScoped<ITemplateService, TemplateManager>();
        services.AddHttpClient<IPexelsService, PexelsService>()
            .AddStandardResilienceHandler();

        // 6. MassTransit (RabbitMQ) ile Raw JSON Serializer (Python Worker entegrasyonu)
        services.AddMassTransit(x =>
        {
            configureMassTransit?.Invoke(x);

            x.UsingRabbitMq((context, cfg) =>
            {
                var host = configuration["RabbitMQ:Host"] ?? "localhost";
                var portStr = configuration["RabbitMQ:Port"];
                ushort port = ushort.TryParse(portStr, out var p) ? p : (ushort)5672;

                cfg.Host(host, port, "/", h =>
                {
                    h.Username(configuration["RabbitMQ:Username"] ?? "guest");
                    h.Password(configuration["RabbitMQ:Password"] ?? "guest");
                });

                // Python Worker ile saf JSON uyumluluğu (MassTransit envelope atlanır)
                cfg.UseRawJsonSerializer();
                cfg.UseRawJsonDeserializer();

                // Dış servis dayanıklılığı için retry
                cfg.UseMessageRetry(r => r.Exponential(3, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(2)));

                cfg.ConfigureEndpoints(context);
            });
        });

        return services;
    }
}
