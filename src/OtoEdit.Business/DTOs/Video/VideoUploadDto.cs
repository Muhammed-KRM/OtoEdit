using Microsoft.AspNetCore.Http;

namespace OtoEdit.Business.DTOs.Video;

public class VideoUploadDto
{
    public IFormFile File { get; set; } = default!;
}
