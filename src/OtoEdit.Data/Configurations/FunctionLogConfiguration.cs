using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using OtoEdit.Data.Entities;

namespace OtoEdit.Data.Configurations;

public class FunctionLogConfiguration : IEntityTypeConfiguration<FunctionLog>
{
    public void Configure(EntityTypeBuilder<FunctionLog> builder)
    {
        builder.ToTable("function_logs");
        builder.HasKey(f => f.Id);

        builder.Property(f => f.Id)
            .HasColumnName("id")
            .UseIdentityAlwaysColumn();

        builder.Property(f => f.ErrorCode)
            .HasColumnName("error_code")
            .HasMaxLength(50)
            .IsRequired();

        builder.Property(f => f.ClassName)
            .HasColumnName("class_name")
            .HasMaxLength(200)
            .IsRequired();

        builder.Property(f => f.MethodName)
            .HasColumnName("method_name")
            .HasMaxLength(200)
            .IsRequired();

        builder.Property(f => f.FilePath)
            .HasColumnName("file_path")
            .HasMaxLength(500);

        builder.Property(f => f.LineNumber)
            .HasColumnName("line_number");

        builder.Property(f => f.ErrorMessage)
            .HasColumnName("error_message")
            .HasColumnType("text");

        builder.Property(f => f.StackTrace)
            .HasColumnName("stack_trace")
            .HasColumnType("text");

        builder.Property(f => f.InputType)
            .HasColumnName("input_type")
            .HasMaxLength(200);

        builder.Property(f => f.InputValue)
            .HasColumnName("input_value")
            .HasColumnType("text");

        builder.Property(f => f.TraceId)
            .HasColumnName("trace_id")
            .HasMaxLength(50);

        builder.Property(f => f.Severity)
            .HasColumnName("severity")
            .HasMaxLength(20)
            .IsRequired()
            .HasDefaultValue("Error");

        builder.Property(f => f.CreatedAt)
            .HasColumnName("created_at")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();

        // Indexes
        builder.HasIndex(f => f.CreatedAt)
            .HasDatabaseName("idx_function_logs_created_at")
            .IsDescending();

        builder.HasIndex(f => f.ErrorCode)
            .HasDatabaseName("idx_function_logs_error_code");

        builder.HasIndex(f => f.Severity)
            .HasDatabaseName("idx_function_logs_severity");
    }
}
