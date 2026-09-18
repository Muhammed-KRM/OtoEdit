using OtoEdit.Business.DTOs.Template;

namespace OtoEdit.Business.Interfaces;

public interface ITemplateService
{
    Task<IEnumerable<TemplateDto>> GetAllAsync(CancellationToken cancellationToken = default);
    Task<TemplateDto> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
}
