using OtoEdit.Data.Enums;

namespace OtoEdit.Business.Exceptions;

/// <summary>
/// Pipeline aşamalarında karşılaşılan işleme ve analiz hataları için fırlatılan exception.
/// </summary>
public class PipelineException : BusinessException
{
    public PipelineAsamasi? Asama { get; }
    public Guid? VideoId { get; }

    public PipelineException(string message, PipelineAsamasi? asama = null, Guid? videoId = null, Exception? innerException = null)
        : base(message, innerException!, "PIPELINE_ERROR")
    {
        Asama = asama;
        VideoId = videoId;
    }
}
