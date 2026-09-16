using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Repositories;

/// <summary>
/// Proje varlığına özel repository arayüzü.
/// </summary>
public interface IProjectRepository : IRepository<Project>
{
    Task<Project?> GetProjectWithDetailsAsync(Guid id, bool asNoTracking = true);
    Task<(IEnumerable<Project> Items, int TotalCount)> GetProjectsPagedAsync(int pageNumber, int pageSize, bool asNoTracking = true);
    Task<bool> UpdateStatusAsync(Guid id, ProjectDurumu durum);
}
