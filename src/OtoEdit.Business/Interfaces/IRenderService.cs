using OtoEdit.Business.DTOs.Render;

namespace OtoEdit.Business.Interfaces;

public interface IRenderService
{
    Task<RenderStatusDto> RequestRenderAsync(Guid projectId, RenderRequestDto? requestDto = null, CancellationToken cancellationToken = default);
    Task<RenderStatusDto> GetRenderStatusAsync(Guid projectId, Guid renderJobId, CancellationToken cancellationToken = default);
    Task<string> GetDownloadUrlAsync(Guid projectId, Guid renderJobId, CancellationToken cancellationToken = default);
    Task CompleteRenderAsync(Guid renderJobId, string indirmeUrl, CancellationToken cancellationToken = default);
    Task FailRenderAsync(Guid renderJobId, string hataMesaji, CancellationToken cancellationToken = default);
}
