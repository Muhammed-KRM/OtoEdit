using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class TemplateConfiguration : IEntityTypeConfiguration<Template>
{
    public void Configure(EntityTypeBuilder<Template> builder)
    {
        builder.ToTable("templates");
        builder.HasKey(t => t.Id);

        builder.Property(t => t.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.Ad)
            .HasColumnName("ad")
            .HasMaxLength(200)
            .IsRequired();

        builder.Property(t => t.Tanim)
            .HasColumnName("tanim")
            .HasMaxLength(1000);

        builder.Property(t => t.VideoFormati)
            .HasColumnName("video_formati")
            .IsRequired();

        builder.Property(t => t.LogoYolu)
            .HasColumnName("logo_yolu")
            .HasMaxLength(500);

        builder.Property(t => t.LogoPozisyonu)
            .HasColumnName("logo_pozisyonu")
            .HasColumnType("jsonb");

        builder.Property(t => t.KonusmaciAdGoster)
            .HasColumnName("konusmaci_ad_goster")
            .IsRequired()
            .HasDefaultValue(false);

        builder.Property(t => t.AltyaziStili)
            .HasColumnName("altyazi_stili")
            .HasMaxLength(50);

        builder.Property(t => t.AltyaziFont)
            .HasColumnName("altyazi_font")
            .HasMaxLength(100);

        builder.Property(t => t.AltyaziRenk)
            .HasColumnName("altyazi_renk")
            .HasMaxLength(20);

        builder.Property(t => t.AktifMi)
            .HasColumnName("aktif_mi")
            .IsRequired()
            .HasDefaultValue(true);

        builder.Property(t => t.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();
    }
}
