using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class AssetManagerTests : IDisposable
{
    private readonly AppDbContext _dbContext;
    private readonly Mock<IFileStorageService> _storageMock = new();
    private readonly Mock<ILogger<AssetManager>> _loggerMock = new();
    private readonly AssetManager _sut;

    public AssetManagerTests()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: $"AssetTestDb_{Guid.NewGuid()}")
            .Options;

        _dbContext = new AppDbContext(options);
        _sut = new AssetManager(_dbContext, _storageMock.Object, _loggerMock.Object);
    }

    public void Dispose()
    {
        _dbContext.Database.EnsureDeleted();
        _dbContext.Dispose();
    }

    private static IFormFile CreateMockFile(string fileName, string contentType, byte[] content)
    {
        var stream = new MemoryStream(content);
        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.FileName).Returns(fileName);
        fileMock.Setup(f => f.Length).Returns(content.Length);
        fileMock.Setup(f => f.ContentType).Returns(contentType);
        fileMock.Setup(f => f.OpenReadStream()).Returns(stream);
        return fileMock.Object;
    }

    [Fact]
    public async Task UploadAssetAsync_WhenProjectNotFound_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();
        var file = CreateMockFile("logo.png", "image/png", new byte[] { 1, 2, 3 });

        var act = async () => await _sut.UploadAssetAsync(projectId, file);

        await act.Should().ThrowAsync<NotFoundException>()
            .WithMessage("*Proje bulunamadı*");
    }

    [Fact]
    public async Task UploadAssetAsync_WhenFileIsEmpty_ShouldThrowBusinessException()
    {
        var projectId = Guid.NewGuid();
        _dbContext.Projects.Add(new Project { Id = projectId, Ad = "Test Proje" });
        await _dbContext.SaveChangesAsync();

        var emptyFile = CreateMockFile("empty.png", "image/png", Array.Empty<byte>());

        var act = async () => await _sut.UploadAssetAsync(projectId, emptyFile);

        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*boş olamaz*");
    }

    [Fact]
    public async Task UploadAssetAsync_WhenExtensionInvalid_ShouldThrowBusinessException()
    {
        var projectId = Guid.NewGuid();
        _dbContext.Projects.Add(new Project { Id = projectId, Ad = "Test Proje" });
        await _dbContext.SaveChangesAsync();

        var exeFile = CreateMockFile("virus.exe", "application/x-msdownload", new byte[] { 1, 2 });

        var act = async () => await _sut.UploadAssetAsync(projectId, exeFile);

        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*Geçersiz dosya formatı*");
    }

    [Fact]
    public async Task UploadAssetAsync_ValidImage_ShouldUploadToMinioAndSaveToDb()
    {
        var projectId = Guid.NewGuid();
        _dbContext.Projects.Add(new Project { Id = projectId, Ad = "Asset Projesi" });
        await _dbContext.SaveChangesAsync();

        var content = new byte[] { 0x89, 0x50, 0x4E, 0x47 }; // PNG magic bytes
        var file = CreateMockFile("banner.png", "image/png", content);

        _storageMock.Setup(s => s.UploadFileAsync(It.IsAny<string>(), It.IsAny<Stream>(), "image/png", It.IsAny<CancellationToken>()))
            .ReturnsAsync("assets/banner.png");

        _storageMock.Setup(s => s.GetPresignedUrlAsync(It.IsAny<string>(), It.IsAny<TimeSpan>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync("http://minio:9000/assets/banner.png");

        var result = await _sut.UploadAssetAsync(projectId, file);

        result.Should().NotBeNull();
        result.ProjectId.Should().Be(projectId);
        result.DosyaAdi.Should().Be("banner.png");
        result.MimeTuru.Should().Be("image/png");
        result.Url.Should().Be("http://localhost:9000/assets/banner.png"); // minio -> localhost sanitization

        // Veritabanında kayıt doğrulanmalı
        var savedInDb = await _dbContext.ProjectAssets.FirstOrDefaultAsync(a => a.Id == result.Id);
        savedInDb.Should().NotBeNull();
        savedInDb!.DosyaAdi.Should().Be("banner.png");
        savedInDb.BoyutByte.Should().Be(content.Length);

        // MinIO çağrısı doğrulanmalı
        _storageMock.Verify(s => s.UploadFileAsync(It.IsAny<string>(), It.IsAny<Stream>(), "image/png", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task GetProjectAssetsAsync_ShouldReturnAssetsWithFreshUrls()
    {
        var projectId = Guid.NewGuid();
        _dbContext.ProjectAssets.AddRange(
            new ProjectAsset
            {
                Id = Guid.NewGuid(),
                ProjectId = projectId,
                DosyaAdi = "img1.png",
                StorageKey = "assets/key1.png",
                YuklemeTarihi = DateTime.UtcNow.AddMinutes(-10)
            },
            new ProjectAsset
            {
                Id = Guid.NewGuid(),
                ProjectId = projectId,
                DosyaAdi = "img2.jpg",
                StorageKey = "assets/key2.jpg",
                YuklemeTarihi = DateTime.UtcNow.AddMinutes(-5)
            }
        );
        await _dbContext.SaveChangesAsync();

        _storageMock.Setup(s => s.GetPresignedUrlAsync(It.IsAny<string>(), It.IsAny<TimeSpan>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((string key, TimeSpan _, CancellationToken _) => $"http://localhost:9000/{key}");

        var assets = (await _sut.GetProjectAssetsAsync(projectId)).ToList();

        assets.Should().HaveCount(2);
        assets[0].DosyaAdi.Should().Be("img2.jpg"); // Yeni yüklenen ilk sırada
        assets[1].DosyaAdi.Should().Be("img1.png");
        assets[0].Url.Should().Contain("assets/key2.jpg");
    }

    [Fact]
    public async Task DeleteAssetAsync_ShouldRemoveFromMinioAndDb()
    {
        var projectId = Guid.NewGuid();
        var assetId = Guid.NewGuid();

        _dbContext.ProjectAssets.Add(new ProjectAsset
        {
            Id = assetId,
            ProjectId = projectId,
            DosyaAdi = "to_delete.png",
            StorageKey = "assets/to_delete.png"
        });
        await _dbContext.SaveChangesAsync();

        _storageMock.Setup(s => s.DeleteFileAsync("assets/to_delete.png", It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        await _sut.DeleteAssetAsync(projectId, assetId);

        // MinIO silinmesi doğrulanmalı
        _storageMock.Verify(s => s.DeleteFileAsync("assets/to_delete.png", It.IsAny<CancellationToken>()), Times.Once);

        // DB'den silinmeli
        var inDb = await _dbContext.ProjectAssets.FindAsync(assetId);
        inDb.Should().BeNull();
    }

    [Fact]
    public async Task UploadAssetAsync_RealImageFromDisk_ShouldSucceed()
    {
        var realPath = @"C:\Users\Kursu\Desktop\aristoteles-kimdir-yasami-ve-eserleri_8134_17-46-05.jpg";
        if (!File.Exists(realPath)) return;

        var projectId = Guid.NewGuid();
        _dbContext.Projects.Add(new Project { Id = projectId, Ad = "Real Asset Projesi" });
        await _dbContext.SaveChangesAsync();

        var bytes = await File.ReadAllBytesAsync(realPath);
        var file = CreateMockFile("aristoteles.jpg", "image/jpeg", bytes);

        _storageMock.Setup(s => s.UploadFileAsync(It.IsAny<string>(), It.IsAny<Stream>(), "image/jpeg", It.IsAny<CancellationToken>()))
            .ReturnsAsync("assets/aristoteles.jpg");

        _storageMock.Setup(s => s.GetPresignedUrlAsync(It.IsAny<string>(), It.IsAny<TimeSpan>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync("http://minio:9000/assets/aristoteles.jpg");

        var result = await _sut.UploadAssetAsync(projectId, file);

        result.Should().NotBeNull();
        result.DosyaAdi.Should().Be("aristoteles.jpg");
        result.BoyutByte.Should().Be(bytes.Length);
        result.MimeTuru.Should().Be("image/jpeg");
    }
}
