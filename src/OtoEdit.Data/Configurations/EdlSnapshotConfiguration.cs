using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class EdlSnapshotConfiguration : IEntityTypeConfiguration<EdlSnapshot>
{
    public void Configure(EntityTypeBuilder<EdlSnapshot> builder)
    {
        builder.ToTable("edl_snapshots");
        builder.HasKey(e => e.Id);

        builder.Property(e => e.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(e => e.ProjectId)
            .HasColumnName("project_id")
            .IsRequired();

        builder.Property(e => e.Versiyon)
            .HasColumnName("versiyon")
            .IsRequired();

        builder.Property(e => e.EdlJson)
            .HasColumnName("edl_json")
            .HasColumnType("jsonb")
            .IsRequired();

        builder.Property(e => e.Aciklama)
            .HasColumnName("aciklama")
            .HasMaxLength(255);

        builder.Property(e => e.Kaynak)
            .HasColumnName("kaynak")
            .HasMaxLength(50)
            .IsRequired();

        builder.Property(e => e.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        // Indexes
        builder.HasIndex(e => e.ProjectId)
            .HasDatabaseName("idx_edl_snapshots_project_id");
            
        builder.HasIndex(e => new { e.ProjectId, e.Versiyon })
            .IsUnique()
            .HasDatabaseName("idx_edl_snapshots_project_id_versiyon");

        // Relationships
        builder.HasOne(e => e.Project)
            .WithMany() // We don't necessarily need a collection of snapshots in Project entity for now
            .HasForeignKey(e => e.ProjectId)
            .OnDelete(DeleteBehavior.Cascade)
            .HasConstraintName("fk_edl_snapshots_projects");
    }
}
