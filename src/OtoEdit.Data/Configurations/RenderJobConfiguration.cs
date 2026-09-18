using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Configurations;

public class RenderJobConfiguration : IEntityTypeConfiguration<RenderJob>
{
    public void Configure(EntityTypeBuilder<RenderJob> builder)
    {
        builder.ToTable("render_jobs");
        builder.HasKey(r => r.Id);

        builder.Property(r => r.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(r => r.ProjectId)
            .HasColumnName("project_id")
            .IsRequired();

        builder.Property(r => r.EdlSnapshot)
            .HasColumnName("edl_snapshot")
            .HasColumnType("jsonb")
            .IsRequired();

        builder.Property(r => r.Durum)
            .HasColumnName("durum")
            .IsRequired()
            .HasDefaultValue(RenderDurumu.Kuyrukta);

        builder.Property(r => r.CiktiYolu)
            .HasColumnName("cikti_yolu")
            .HasMaxLength(500);

        builder.Property(r => r.BaslangicZamani)
            .HasColumnName("baslangic_zamani")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        builder.Property(r => r.BitisZamani)
            .HasColumnName("bitis_zamani")
            .HasColumnType("timestamptz");

        builder.Property(r => r.SureMs)
            .HasColumnName("sure_ms");

        builder.Property(r => r.HataMesaji)
            .HasColumnName("hata_mesaji")
            .HasColumnType("text");

        // Indexes
        builder.HasIndex(r => r.ProjectId)
            .HasDatabaseName("idx_render_jobs_project_id");

        builder.HasIndex(r => r.Durum)
            .HasDatabaseName("idx_render_jobs_durum");
    }
}
