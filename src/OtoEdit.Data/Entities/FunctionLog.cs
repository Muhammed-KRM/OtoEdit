namespace OtoEdit.Data.Entities;

/// <summary>
/// Fonksiyon seviyesinde hata ve istisna log varlığı.
/// </summary>
public class FunctionLog
{
    public long Id { get; set; }
    public string ErrorCode { get; set; } = string.Empty;
    public string ClassName { get; set; } = string.Empty;
    public string MethodName { get; set; } = string.Empty;
    public string? FilePath { get; set; }
    public int LineNumber { get; set; }
    public string? ErrorMessage { get; set; }
    public string? StackTrace { get; set; }
    public string? InputType { get; set; }
    public string? InputValue { get; set; }
    public string? TraceId { get; set; }
    public string Severity { get; set; } = "Error";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
