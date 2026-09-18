using System.Runtime.CompilerServices;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Interfaces;

public interface ILogService
{
    // Endpoint log
    Task LogEndpointAsync(EndpointLog log, CancellationToken cancellationToken = default);

    // Pipeline log
    Task<long> LogPipelineStartAsync(Guid? videoId, Guid? projectId,
        PipelineAsamasi asama, string? traceId = null, string? girdiMetadata = null, CancellationToken cancellationToken = default);
    Task LogPipelineEndAsync(long logId, string? ciktiMetadata = null, CancellationToken cancellationToken = default);
    Task LogPipelineErrorAsync(long logId, Exception ex, CancellationToken cancellationToken = default);

    // Function log
    Task LogFunctionErrorAsync(string errorCode, Exception ex,
        object? input = null, string? traceId = null,
        [CallerMemberName] string methodName = "",
        [CallerFilePath] string filePath = "",
        [CallerLineNumber] int lineNumber = 0,
        CancellationToken cancellationToken = default);
}
