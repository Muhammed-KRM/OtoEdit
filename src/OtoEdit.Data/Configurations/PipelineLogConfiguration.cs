using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class PipelineLogConfiguration : IEntityTypeConfiguration<PipelineLog>
{
    public void Configure(EntityTypeBuilder<PipelineLog> builder)
    {
        builder.ToTable("pipeline_logs");
        builder.HasKey(p => p.Id);

        builder.Property(p => p.Id)
            .HasColumnName("id")
            .UseIdentityAlwaysColumn();

        builder.Property(p => p.VideoId)
            .HasColumnName("video_id");

        builder.Property(p => p.ProjectId)
            .HasColumnName("project_id");

        builder.Property(p => p.RenderJobId)
            .HasColumnName("render_job_id");

        builder.Property(p => p.Asama)
            .HasColumnName("asama")
            .IsRequired();

        builder.Property(p => p.Durum)
            .HasColumnName("durum")
            .HasMaxLength(20)
            .IsRequired();

        builder.Property(p => p.BaslangicZamani)
            .HasColumnName("baslangic_zamani")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        builder.Property(p => p.BitisZamani)
            .HasColumnName("bitis_zamani")
            .HasColumnType("timestamptz");

        builder.Property(p => p.SureMs)
            .HasColumnName("sure_ms");

        builder.Property(p => p.HataMesaji)
            .HasColumnName("hata_mesaji")
            .HasColumnType("text");

        builder.Property(p => p.HataDetayi)
            .HasColumnName("hata_detayi")
            .HasColumnType("text");

        builder.Property(p => p.GirdiMetadata)
            .HasColumnName("girdi_metadata")
            .HasColumnType("jsonb");

        builder.Property(p => p.CiktiMetadata)
            .HasColumnName("cikti_metadata")
            .HasColumnType("jsonb");

        builder.Property(p => p.TraceId)
            .HasColumnName("trace_id")
            .HasMaxLength(50);

        builder.Property(p => p.CreatedAt)
            .HasColumnName("created_at")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        // Indexes
        builder.HasIndex(p => p.VideoId)
            .HasDatabaseName("idx_pipeline_logs_video_id");

        builder.HasIndex(p => p.ProjectId)
            .HasDatabaseName("idx_pipeline_logs_project_id");

        builder.HasIndex(p => p.Asama)
            .HasDatabaseName("idx_pipeline_logs_asama");

        builder.HasIndex(p => p.CreatedAt)
            .HasDatabaseName("idx_pipeline_logs_created_at")
            .IsDescending();

        // Relationships
        builder.HasOne(p => p.Video)
            .WithMany(v => v.PipelineLogs)
            .HasForeignKey(p => p.VideoId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasOne(p => p.Project)
            .WithMany(pr => pr.PipelineLogs)
            .HasForeignKey(p => p.ProjectId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
