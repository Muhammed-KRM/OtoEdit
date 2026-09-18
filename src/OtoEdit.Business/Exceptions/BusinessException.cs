namespace OtoEdit.Business.Exceptions;

/// <summary>
/// İş kuralları ihlal edildiğinde fırlatılan temel exception sınıfı.
/// </summary>
public class BusinessException : Exception
{
    public string? ErrorCode { get; }

    public BusinessException(string message, string? errorCode = null) : base(message)
    {
        ErrorCode = errorCode;
    }

    public BusinessException(string message, Exception innerException, string? errorCode = null) 
        : base(message, innerException)
    {
        ErrorCode = errorCode;
    }
}
