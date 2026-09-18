using OtoEdit.Business.DTOs.Project;
using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Interfaces;

public interface IProjectService
{
    Task<IEnumerable<ProjectListDto>> GetAllAsync(CancellationToken cancellationToken = default);
    Task<ProjectDetailDto> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<ProjectDetailDto> CreateAsync(ProjectCreateDto dto, CancellationToken cancellationToken = default);
    Task<ProjectDetailDto> UpdateAsync(Guid id, ProjectUpdateDto dto, CancellationToken cancellationToken = default);
    Task DeleteAsync(Guid id, CancellationToken cancellationToken = default);
    Task UpdateStatusAsync(Guid id, ProjectDurumu durum, CancellationToken cancellationToken = default);
}
