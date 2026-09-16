using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class EndpointLogConfiguration : IEntityTypeConfiguration<EndpointLog>
{
    public void Configure(EntityTypeBuilder<EndpointLog> builder)
    {
        builder.ToTable("endpoint_logs");
        builder.HasKey(e => e.Id);

        builder.Property(e => e.Id)
            .HasColumnName("id")
            .UseIdentityAlwaysColumn();

        builder.Property(e => e.TraceId)
            .HasColumnName("trace_id")
            .HasMaxLength(50);

        builder.Property(e => e.Method)
            .HasColumnName("method")
            .HasMaxLength(10)
            .IsRequired();

        builder.Property(e => e.Path)
            .HasColumnName("path")
            .HasMaxLength(500)
            .IsRequired();

        builder.Property(e => e.Query)
            .HasColumnName("query")
            .HasMaxLength(1000);

        builder.Property(e => e.RequestBody)
            .HasColumnName("request_body")
            .HasColumnType("text");

        builder.Property(e => e.ResponseBody)
            .HasColumnName("response_body")
            .HasColumnType("text");

        builder.Property(e => e.StatusCode)
            .HasColumnName("status_code")
            .IsRequired();

        builder.Property(e => e.IpAddress)
            .HasColumnName("ip_address")
            .HasMaxLength(45);

        builder.Property(e => e.UserAgent)
            .HasColumnName("user_agent")
            .HasMaxLength(500);

        builder.Property(e => e.DurationMs)
            .HasColumnName("duration_ms")
            .IsRequired();

        builder.Property(e => e.CreatedAt)
            .HasColumnName("created_at")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        // Indexes
        builder.HasIndex(e => e.CreatedAt)
            .HasDatabaseName("idx_endpoint_logs_created_at")
            .IsDescending();

        builder.HasIndex(e => e.StatusCode)
            .HasDatabaseName("idx_endpoint_logs_status_code");

        builder.HasIndex(e => e.Path)
            .HasDatabaseName("idx_endpoint_logs_path");
    }
}
