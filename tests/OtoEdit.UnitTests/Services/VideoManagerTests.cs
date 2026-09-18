using System.IO;
using System.Text;
using FluentAssertions;
using MassTransit;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.Events;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;
using OtoEdit.Data.Repositories;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class VideoManagerTests
{
    private readonly Mock<IVideoRepository> _videoRepoMock = new();
    private readonly Mock<IProjectRepository> _projectRepoMock = new();
    private readonly Mock<IFileStorageService> _fileStorageMock = new();
    private readonly Mock<IPublishEndpoint> _publishEndpointMock = new();
    private readonly Mock<ILogService> _logServiceMock = new();
    private readonly Mock<ILogger<VideoManager>> _loggerMock = new();

    private readonly VideoManager _sut;

    public VideoManagerTests()
    {
        _sut = new VideoManager(
            _videoRepoMock.Object,
            _projectRepoMock.Object,
            _fileStorageMock.Object,
            _publishEndpointMock.Object,
            _logServiceMock.Object,
            _loggerMock.Object);
    }

    [Fact]
    public async Task UploadVideoAsync_WhenProjectNotFound_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();
        _projectRepoMock.Setup(r => r.GetByIdAsync(projectId))
            .ReturnsAsync((Project?)null);

        var fileMock = new Mock<IFormFile>();

        var act = async () => await _sut.UploadVideoAsync(projectId, fileMock.Object);

        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Fact]
    public async Task UploadVideoAsync_WhenFileEmpty_ShouldThrowBusinessException()
    {
        var projectId = Guid.NewGuid();
        _projectRepoMock.Setup(r => r.GetByIdAsync(projectId))
            .ReturnsAsync(new Project { Id = projectId });

        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(0);

        var act = async () => await _sut.UploadVideoAsync(projectId, fileMock.Object);

        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*Video dosyası boş olamaz*");
    }

    [Fact]
    public async Task UploadVideoAsync_WhenExtensionNotAllowed_ShouldThrowBusinessException()
    {
        var projectId = Guid.NewGuid();
        _projectRepoMock.Setup(r => r.GetByIdAsync(projectId))
            .ReturnsAsync(new Project { Id = projectId });

        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(1024);
        fileMock.Setup(f => f.FileName).Returns("document.pdf");

        var act = async () => await _sut.UploadVideoAsync(projectId, fileMock.Object);

        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*Geçersiz video formatı*");
    }

    [Fact]
    public async Task UploadVideoAsync_ValidVideo_ShouldUploadAndPublishEvent()
    {
        var projectId = Guid.NewGuid();
        var project = new Project
        {
            Id = projectId,
            VideoFormati = VideoFormati.Dikey_9_16,
            GestureCommandsEnabled = true,
            AudioEnhancementEnabled = true
        };

        _projectRepoMock.Setup(r => r.GetByIdAsync(projectId))
            .ReturnsAsync(project);

        var fileMock = new Mock<IFormFile>();
        var content = "dummy video binary stream content";
        var stream = new MemoryStream(Encoding.UTF8.GetBytes(content));
        fileMock.Setup(f => f.Length).Returns(stream.Length);
        fileMock.Setup(f => f.FileName).Returns("camera_raw.mp4");
        fileMock.Setup(f => f.ContentType).Returns("video/mp4");
        fileMock.Setup(f => f.OpenReadStream()).Returns(stream);

        _videoRepoMock.Setup(r => r.AddAsync(It.IsAny<Video>()))
            .ReturnsAsync((Video v) => v);
        _videoRepoMock.Setup(r => r.SaveChangesAsync())
            .ReturnsAsync(1);
        _projectRepoMock.Setup(r => r.UpdateStatusAsync(projectId, ProjectDurumu.AnalizEdiliyor))
            .ReturnsAsync(true);

        var result = await _sut.UploadVideoAsync(projectId, fileMock.Object);

        result.Should().NotBeNull();
        result.ProjectId.Should().Be(projectId);
        result.Baslik.Should().Be("camera_raw");
        result.IslemDurumu.Should().Be(VideoIslemDurumu.Bekliyor);

        _fileStorageMock.Verify(f => f.UploadFileAsync(
            It.Is<string>(s => s.StartsWith($"videos/{projectId}/")),
            It.IsAny<Stream>(),
            "video/mp4",
            It.IsAny<CancellationToken>()), Times.Once);

        _videoRepoMock.Verify(r => r.AddAsync(It.IsAny<Video>()), Times.Once);
        _projectRepoMock.Verify(r => r.UpdateStatusAsync(projectId, ProjectDurumu.AnalizEdiliyor), Times.Once);

        _publishEndpointMock.Verify(p => p.Publish(
            It.Is<VideoUploadedEvent>(e => e.ProjectId == projectId && e.VideoFormati == (int)VideoFormati.Dikey_9_16),
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
