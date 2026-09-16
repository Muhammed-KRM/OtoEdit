using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class EditDecisionListConfiguration : IEntityTypeConfiguration<EditDecisionList>
{
    public void Configure(EntityTypeBuilder<EditDecisionList> builder)
    {
        builder.ToTable("edit_decision_lists");
        builder.HasKey(e => e.Id);

        builder.Property(e => e.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(e => e.ProjectId)
            .HasColumnName("project_id")
            .IsRequired();

        builder.Property(e => e.EdlJson)
            .HasColumnName("edl_json")
            .HasColumnType("jsonb")
            .HasDefaultValue("{}")
            .IsRequired();

        builder.Property(e => e.Versiyon)
            .HasColumnName("versiyon")
            .IsRequired()
            .HasDefaultValue(1);

        builder.Property(e => e.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        builder.Property(e => e.GuncellemeTarihi)
            .HasColumnName("guncelleme_tarihi")
            .HasColumnType("timestamptz");

        // Indexes
        builder.HasIndex(e => e.ProjectId)
            .IsUnique()
            .HasDatabaseName("idx_edl_project_id");
    }
}
