using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class VideoConfiguration : IEntityTypeConfiguration<Video>
{
    public void Configure(EntityTypeBuilder<Video> builder)
    {
        builder.ToTable("videos");
        builder.HasKey(v => v.Id);

        builder.Property(v => v.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(v => v.ProjectId)
            .HasColumnName("project_id")
            .IsRequired();

        builder.Property(v => v.Baslik)
            .HasColumnName("baslik")
            .HasMaxLength(300)
            .IsRequired();

        builder.Property(v => v.DosyaYolu)
            .HasColumnName("dosya_yolu")
            .HasMaxLength(500)
            .IsRequired();

        builder.Property(v => v.TemizSesYolu)
            .HasColumnName("temiz_ses_yolu")
            .HasMaxLength(500);

        builder.Property(v => v.Sure)
            .HasColumnName("sure")
            .HasColumnType("interval");

        builder.Property(v => v.DosyaBoyutu)
            .HasColumnName("dosya_boyutu")
            .HasColumnType("bigint")
            .IsRequired()
            .HasDefaultValue(0L);

        builder.Property(v => v.IslemDurumu)
            .HasColumnName("islem_durumu")
            .IsRequired()
            .HasDefaultValue(0);

        builder.Property(v => v.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        builder.Property(v => v.IslemTamamlanmaTarihi)
            .HasColumnName("islem_tamamlanma_tarihi")
            .HasColumnType("timestamptz");

        // Indexes
        builder.HasIndex(v => v.ProjectId)
            .IsUnique()
            .HasDatabaseName("idx_videos_project_id");

        builder.HasIndex(v => v.IslemDurumu)
            .HasDatabaseName("idx_videos_durum");

        // Relationships
        builder.HasOne(v => v.Transcript)
            .WithOne(t => t.Video)
            .HasForeignKey<VideoTranscript>(t => t.VideoId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
