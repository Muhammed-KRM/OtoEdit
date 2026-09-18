using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Minio;
using Minio.DataModel.Args;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.Business.Infrastructure.Storage;

/// <summary>
/// MinIO S3 uyumlu dosya depolama servisi implementasyonu.
/// </summary>
public class MinioFileStorageService : IFileStorageService
{
    private readonly IMinioClient _minioClient;
    private readonly ILogger<MinioFileStorageService> _logger;
    private readonly string _bucketName;

    public MinioFileStorageService(IMinioClient minioClient, IConfiguration configuration, ILogger<MinioFileStorageService> logger)
    {
        _minioClient = minioClient;
        _logger = logger;
        _bucketName = configuration.GetValue<string>("Minio:BucketName") ?? "otoedit";
    }

    private async Task EnsureBucketExistsAsync(CancellationToken cancellationToken)
    {
        var bucketExistsArgs = new BucketExistsArgs().WithBucket(_bucketName);
        bool found = await _minioClient.BucketExistsAsync(bucketExistsArgs, cancellationToken);
        if (!found)
        {
            var makeBucketArgs = new MakeBucketArgs().WithBucket(_bucketName);
            await _minioClient.MakeBucketAsync(makeBucketArgs, cancellationToken);
        }
    }

    public async Task<string> UploadFileAsync(string objectKey, Stream content, string contentType, CancellationToken cancellationToken = default)
    {
        try
        {
            await EnsureBucketExistsAsync(cancellationToken);

            var putObjectArgs = new PutObjectArgs()
                .WithBucket(_bucketName)
                .WithObject(objectKey)
                .WithStreamData(content)
                .WithObjectSize(content.Length)
                .WithContentType(contentType);

            await _minioClient.PutObjectAsync(putObjectArgs, cancellationToken);
            _logger.LogInformation("Dosya MinIO'ya yüklendi: Bucket={Bucket}, ObjectKey={ObjectKey}", _bucketName, objectKey);

            return objectKey;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "MinIO dosya yükleme hatası: ObjectKey={ObjectKey}", objectKey);
            throw;
        }
    }

    public async Task<Stream> DownloadFileAsync(string objectKey, CancellationToken cancellationToken = default)
    {
        try
        {
            var memoryStream = new MemoryStream();
            var getObjectArgs = new GetObjectArgs()
                .WithBucket(_bucketName)
                .WithObject(objectKey)
                .WithCallbackStream(stream =>
                {
                    stream.CopyTo(memoryStream);
                });

            await _minioClient.GetObjectAsync(getObjectArgs, cancellationToken);
            memoryStream.Position = 0;
            return memoryStream;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "MinIO dosya indirme hatası: ObjectKey={ObjectKey}", objectKey);
            throw;
        }
    }

    public async Task<string> GetPresignedUrlAsync(string objectKey, TimeSpan expiry, CancellationToken cancellationToken = default)
    {
        try
        {
            var presignedArgs = new PresignedGetObjectArgs()
                .WithBucket(_bucketName)
                .WithObject(objectKey)
                .WithExpiry((int)expiry.TotalSeconds);

            return await _minioClient.PresignedGetObjectAsync(presignedArgs);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "MinIO presigned URL üretme hatası: ObjectKey={ObjectKey}", objectKey);
            throw;
        }
    }

    public async Task DeleteFileAsync(string objectKey, CancellationToken cancellationToken = default)
    {
        try
        {
            var removeArgs = new RemoveObjectArgs()
                .WithBucket(_bucketName)
                .WithObject(objectKey);

            await _minioClient.RemoveObjectAsync(removeArgs, cancellationToken);
            _logger.LogInformation("MinIO dosya silindi: ObjectKey={ObjectKey}", objectKey);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "MinIO dosya silme hatası: ObjectKey={ObjectKey}", objectKey);
            throw;
        }
    }

    public async Task DeleteDirectoryAsync(string prefix, CancellationToken cancellationToken = default)
    {
        try
        {
            var listArgs = new ListObjectsArgs()
                .WithBucket(_bucketName)
                .WithPrefix(prefix)
                .WithRecursive(true);

            var objectsToRemove = new List<string>();

            await foreach (var item in _minioClient.ListObjectsEnumAsync(listArgs, cancellationToken))
            {
                if (!string.IsNullOrEmpty(item.Key))
                {
                    objectsToRemove.Add(item.Key);
                }
            }

            foreach (var key in objectsToRemove)
            {
                await DeleteFileAsync(key, cancellationToken);
            }

            _logger.LogInformation("MinIO dizin/önek altındaki {Count} dosya temizlendi: Prefix={Prefix}", objectsToRemove.Count, prefix);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "MinIO prefix temizleme sırasında hata oluştu: Prefix={Prefix}", prefix);
        }
    }
}
