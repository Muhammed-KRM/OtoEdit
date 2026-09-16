using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class ChatMessageConfiguration : IEntityTypeConfiguration<ChatMessage>
{
    public void Configure(EntityTypeBuilder<ChatMessage> builder)
    {
        builder.ToTable("chat_messages");
        builder.HasKey(c => c.Id);

        builder.Property(c => c.Id)
            .HasColumnName("id")
            .HasDefaultValueSql("gen_random_uuid()");

        builder.Property(c => c.ProjectId)
            .HasColumnName("project_id")
            .IsRequired();

        builder.Property(c => c.Rol)
            .HasColumnName("rol")
            .HasMaxLength(20)
            .IsRequired();

        builder.Property(c => c.Mesaj)
            .HasColumnName("mesaj")
            .HasColumnType("text")
            .IsRequired();

        builder.Property(c => c.EdlPatch)
            .HasColumnName("edl_patch")
            .HasColumnType("jsonb");

        builder.Property(c => c.OlusturmaTarihi)
            .HasColumnName("olusturma_tarihi")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        // Indexes
        builder.HasIndex(c => c.ProjectId)
            .HasDatabaseName("idx_chat_messages_project_id");

        builder.HasIndex(c => c.OlusturmaTarihi)
            .HasDatabaseName("idx_chat_messages_olusturma");
    }
}
