using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using OtoEdit.Data.Context;
using OtoEdit.Data.Repositories;

namespace OtoEdit.Data;

/// <summary>
/// Data Access katmanı DI servis kayıtları.
/// </summary>
public static class ServiceRegistration
{
    public static IServiceCollection AddDataLayer(this IServiceCollection services, string connectionString)
    {
        // Add DbContext
        services.AddDbContext<AppDbContext>(options =>
        {
            options.UseNpgsql(connectionString, b => b.MigrationsAssembly("OtoEdit.Data"));
            options.ConfigureWarnings(w => w.Ignore(Microsoft.EntityFrameworkCore.Diagnostics.RelationalEventId.PendingModelChangesWarning));
        });

        // Add Repositories
        services.AddScoped(typeof(IRepository<>), typeof(GenericRepository<>));
        services.AddScoped<IProjectRepository, ProjectRepository>();
        services.AddScoped<IVideoRepository, VideoRepository>();

        return services;
    }
}
