using Microsoft.AspNetCore.Http;
using OtoEdit.Business.DTOs.Video;

namespace OtoEdit.Business.Interfaces;

public interface IVideoService
{
    Task<VideoListDto> UploadVideoAsync(Guid projectId, IFormFile file, CancellationToken cancellationToken = default);
    Task<VideoDetailDto?> GetVideoByProjectIdAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task DeleteVideoAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task<(Stream FileStream, string ContentType, string FileName)> GetVideoStreamAsync(Guid videoId, CancellationToken cancellationToken = default);
    Task<string> GetVideoUrlAsync(Guid videoId, CancellationToken cancellationToken = default);
}
