using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class VideoTranscriptConfiguration : IEntityTypeConfiguration<VideoTranscript>
{
    public void Configure(EntityTypeBuilder<VideoTranscript> builder)
    {
        builder.ToTable("video_transcripts");
        builder.HasKey(t => t.Id);

        builder.Property(t => t.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.VideoId)
            .HasColumnName("video_id")
            .IsRequired();

        builder.Property(t => t.HamMetin)
            .HasColumnName("ham_metin")
            .HasColumnType("text")
            .IsRequired();

        builder.Property(t => t.ZamanDamgalari)
            .HasColumnName("zaman_damgalari")
            .HasColumnType("jsonb");

        builder.Property(t => t.Dil)
            .HasColumnName("dil")
            .HasMaxLength(10)
            .IsRequired()
            .HasDefaultValue("tr");

        builder.Property(t => t.KelimeSayisi)
            .HasColumnName("kelime_sayisi")
            .IsRequired()
            .HasDefaultValue(0);

        builder.Property(t => t.SttModel)
            .HasColumnName("stt_model")
            .HasMaxLength(50)
            .IsRequired();

        builder.Property(t => t.SttSuresiMs)
            .HasColumnName("stt_suresi_ms")
            .IsRequired()
            .HasDefaultValue(0);

        builder.Property(t => t.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        // Indexes
        builder.HasIndex(t => t.VideoId)
            .IsUnique()
            .HasDatabaseName("idx_video_transcripts_video_id");
    }
}
