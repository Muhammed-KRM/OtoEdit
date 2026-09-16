using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Data.Repositories;

/// <summary>
/// Video varlığına özel repository arayüzü.
/// </summary>
public interface IVideoRepository : IRepository<Video>
{
    Task<Video?> GetByProjectIdAsync(Guid projectId, bool asNoTracking = true);
    Task<bool> UpdateStatusAsync(Guid videoId, VideoIslemDurumu status);
}
