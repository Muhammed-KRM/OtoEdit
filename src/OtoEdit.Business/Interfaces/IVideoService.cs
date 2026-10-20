using Microsoft.AspNetCore.Http;
using OtoEdit.Business.DTOs.Video;

namespace OtoEdit.Business.Interfaces;

public interface IVideoService
{
    Task<VideoListDto> UploadVideoAsync(
        Guid projectId, 
        IFormFile file, 
        bool autoJumpcut = true,
        bool autoRetake = true,
        bool autoBroll = true,
        bool autoSubtitles = true,
        CancellationToken cancellationToken = default,
        bool? audioEnhancementEnabled = null,
        bool? gestureCommandsEnabled = null,
        bool autoDirectorEnabled = false,
        bool directToEditor = false);
    Task<VideoDetailDto?> GetVideoByProjectIdAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task DeleteVideoAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task<(Stream FileStream, string ContentType, string FileName)> GetVideoStreamAsync(Guid videoId, CancellationToken cancellationToken = default);
    Task<string> GetVideoUrlAsync(Guid videoId, CancellationToken cancellationToken = default);
    Task TriggerAnalysisAsync(
        Guid projectId,
        bool autoJumpcut = false,
        bool autoRetake = false,
        bool autoBroll = false,
        bool autoSubtitles = true,
        bool audioEnhancement = false,
        bool gestureCommands = false,
        bool autoDirector = false,
        CancellationToken cancellationToken = default);
}
