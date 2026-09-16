using Microsoft.EntityFrameworkCore;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Repositories;

/// <summary>
/// Proje varlığına özel repository implementasyonu.
/// </summary>
public class ProjectRepository : GenericRepository<Project>, IProjectRepository
{
    public ProjectRepository(AppDbContext context) : base(context)
    {
    }

    public async Task<Project?> GetProjectWithDetailsAsync(Guid id, bool asNoTracking = true)
    {
        var query = _dbSet
            .Include(p => p.Video)
                .ThenInclude(v => v!.Transcript)
            .Include(p => p.Template)
            .Include(p => p.EditDecisionList)
            .Include(p => p.RenderJobs)
            .AsQueryable();

        if (asNoTracking)
        {
            query = query.AsNoTracking();
        }

        return await query.FirstOrDefaultAsync(p => p.Id == id);
    }

    public async Task<(IEnumerable<Project> Items, int TotalCount)> GetProjectsPagedAsync(
        int pageNumber, int pageSize, bool asNoTracking = true)
    {
        var query = _dbSet
            .Include(p => p.Video)
            .Include(p => p.Template)
            .OrderByDescending(p => p.OlusturmaTarihi)
            .AsQueryable();

        if (asNoTracking)
        {
            query = query.AsNoTracking();
        }

        var totalCount = await query.CountAsync();
        var items = await query
            .Skip((pageNumber - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return (items, totalCount);
    }

    public async Task<bool> UpdateStatusAsync(Guid id, ProjectDurumu durum)
    {
        var project = await _dbSet.FindAsync(id);
        if (project == null) return false;

        project.Durum = durum;
        project.GuncellemeTarihi = DateTime.UtcNow;
        await _context.SaveChangesAsync();
        return true;
    }
}
