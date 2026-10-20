using Microsoft.AspNetCore.Http;

namespace OtoEdit.Business.DTOs.Video;

public class VideoUploadDto
{
    public IFormFile File { get; set; } = default!;
    public bool AutoJumpcut { get; set; } = true;
    public bool AutoRetake { get; set; } = true;
    public bool AutoBroll { get; set; } = true;
    public bool AutoSubtitles { get; set; } = true;
    public bool? AudioEnhancementEnabled { get; set; }
    public bool? GestureCommandsEnabled { get; set; }
    public bool AutoDirectorEnabled { get; set; } = false;
    public bool DirectToEditor { get; set; } = false;
}
