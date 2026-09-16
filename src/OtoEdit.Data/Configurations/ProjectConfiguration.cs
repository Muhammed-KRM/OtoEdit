using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class ProjectConfiguration : IEntityTypeConfiguration<Project>
{
    public void Configure(EntityTypeBuilder<Project> builder)
    {
        builder.ToTable("projects");
        builder.HasKey(p => p.Id);

        builder.Property(p => p.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(p => p.Ad)
            .HasColumnName("ad")
            .HasMaxLength(200)
            .IsRequired();

        builder.Property(p => p.Aciklama)
            .HasColumnName("aciklama")
            .HasMaxLength(2000);

        builder.Property(p => p.VideoFormati)
            .HasColumnName("video_formati")
            .IsRequired()
            .HasDefaultValue(0);

        builder.Property(p => p.TemplateId)
            .HasColumnName("template_id");

        builder.Property(p => p.GestureCommandsEnabled)
            .HasColumnName("gesture_commands_enabled")
            .IsRequired()
            .HasDefaultValue(true);

        builder.Property(p => p.AudioEnhancementEnabled)
            .HasColumnName("audio_enhancement_enabled")
            .IsRequired()
            .HasDefaultValue(true);

        builder.Property(p => p.Durum)
            .HasColumnName("durum")
            .IsRequired()
            .HasDefaultValue(0);

        builder.Property(p => p.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        builder.Property(p => p.GuncellemeTarihi)
            .HasColumnName("guncelleme_tarihi")
            .HasColumnType("timestamptz");

        // Indexes
        builder.HasIndex(p => p.Durum)
            .HasDatabaseName("idx_projects_durum");

        builder.HasIndex(p => p.OlusturmaTarihi)
            .HasDatabaseName("idx_projects_olusturma")
            .IsDescending();

        // Relationships
        builder.HasOne(p => p.Template)
            .WithMany(t => t.Projects)
            .HasForeignKey(p => p.TemplateId)
            .OnDelete(DeleteBehavior.SetNull);

        builder.HasOne(p => p.Video)
            .WithOne(v => v.Project)
            .HasForeignKey<Video>(v => v.ProjectId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasOne(p => p.EditDecisionList)
            .WithOne(e => e.Project)
            .HasForeignKey<EditDecisionList>(e => e.ProjectId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasMany(p => p.ChatMessages)
            .WithOne(c => c.Project)
            .HasForeignKey(c => c.ProjectId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasMany(p => p.RenderJobs)
            .WithOne(r => r.Project)
            .HasForeignKey(r => r.ProjectId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
