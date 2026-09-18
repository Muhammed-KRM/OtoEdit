namespace OtoEdit.Business.Exceptions;

/// <summary>
/// İstenen varlık bulunamadığında (HTTP 404) fırlatılan exception.
/// </summary>
public class NotFoundException : BusinessException
{
    public string EntityName { get; }
    public object Key { get; }

    public NotFoundException(string entityName, object key)
        : base($"{entityName} ({key}) bulunamadı.", "NOT_FOUND")
    {
        EntityName = entityName;
        Key = key;
    }
}
