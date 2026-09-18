using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Interfaces;

public interface IPipelineNotificationService
{
    Task NotifyAnalysisProgressAsync(Guid projectId, PipelineAsamasi asama, int yuzde, string? mesaj, CancellationToken cancellationToken = default);
    Task NotifyAnalysisCompletedAsync(Guid projectId, int edlVersiyon, CancellationToken cancellationToken = default);
    Task NotifyRenderProgressAsync(Guid projectId, Guid renderJobId, int yuzde, CancellationToken cancellationToken = default);
    Task NotifyRenderCompletedAsync(Guid projectId, Guid renderJobId, string indirmeUrl, CancellationToken cancellationToken = default);
    Task NotifyPipelineErrorAsync(Guid projectId, Guid? videoId, string asama, string hataMesaji, CancellationToken cancellationToken = default);
}
