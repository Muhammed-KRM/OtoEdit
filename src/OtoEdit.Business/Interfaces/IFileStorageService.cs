namespace OtoEdit.Business.Interfaces;

public interface IFileStorageService
{
    Task<string> UploadFileAsync(string objectKey, Stream content, string contentType, CancellationToken cancellationToken = default);
    Task<Stream> DownloadFileAsync(string objectKey, CancellationToken cancellationToken = default);
    Task<string> GetPresignedUrlAsync(string objectKey, TimeSpan expiry, CancellationToken cancellationToken = default);
    Task DeleteFileAsync(string objectKey, CancellationToken cancellationToken = default);
    Task DeleteDirectoryAsync(string prefix, CancellationToken cancellationToken = default);
}
