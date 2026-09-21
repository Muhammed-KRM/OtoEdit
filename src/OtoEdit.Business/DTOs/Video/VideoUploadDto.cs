using Microsoft.AspNetCore.Http;

namespace OtoEdit.Business.DTOs.Video;

public class VideoUploadDto
{
    public IFormFile File { get; set; } = default!;
    public bool AutoJumpcut { get; set; } = true;
    public bool AutoRetake { get; set; } = true;
    public bool AutoBroll { get; set; } = true;
    public bool AutoSubtitles { get; set; } = false;
}
