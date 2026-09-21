using System.Reflection;
using Microsoft.EntityFrameworkCore;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Context;

/// <summary>
/// OtoEdit ana veritabanı bağlamı.
/// </summary>
public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public virtual DbSet<Project> Projects { get; set; } = null!;
    public virtual DbSet<Video> Videos { get; set; } = null!;
    public virtual DbSet<VideoTranscript> VideoTranscripts { get; set; } = null!;
    public virtual DbSet<EditDecisionList> EditDecisionLists { get; set; } = null!;
    public virtual DbSet<EdlSnapshot> EdlSnapshots { get; set; } = null!;
    public virtual DbSet<Template> Templates { get; set; } = null!;
    public virtual DbSet<ChatMessage> ChatMessages { get; set; } = null!;
    public virtual DbSet<RenderJob> RenderJobs { get; set; } = null!;
    public virtual DbSet<EndpointLog> EndpointLogs { get; set; } = null!;
    public virtual DbSet<FunctionLog> FunctionLogs { get; set; } = null!;
    public virtual DbSet<PipelineLog> PipelineLogs { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Derlemedeki tüm IEntityTypeConfiguration sınıflarını otomatik uygula
        modelBuilder.ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly());
    }
}
