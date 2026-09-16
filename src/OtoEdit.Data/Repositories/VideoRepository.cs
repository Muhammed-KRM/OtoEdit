using Microsoft.EntityFrameworkCore;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Repositories;

/// <summary>
/// Video varlığına özel repository implementasyonu.
/// </summary>
public class VideoRepository : GenericRepository<Video>, IVideoRepository
{
    public VideoRepository(AppDbContext context) : base(context)
    {
    }

    public async Task<Video?> GetByProjectIdAsync(Guid projectId, bool asNoTracking = true)
    {
        var query = _dbSet
            .Include(v => v.Transcript)
            .AsQueryable();

        if (asNoTracking)
        {
            query = query.AsNoTracking();
        }

        return await query.FirstOrDefaultAsync(v => v.ProjectId == projectId);
    }

    public async Task<bool> UpdateStatusAsync(Guid videoId, VideoIslemDurumu status)
    {
        var video = await _dbSet.FindAsync(videoId);
        if (video == null) return false;

        video.IslemDurumu = status;
        if (status == VideoIslemDurumu.AnalizTamamlandi)
        {
            video.IslemTamamlanmaTarihi = DateTime.UtcNow;
        }

        await _context.SaveChangesAsync();
        return true;
    }
}
