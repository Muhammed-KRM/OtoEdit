using FluentAssertions;
using MassTransit;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.DTOs.Render;
using OtoEdit.Business.Events;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class RenderManagerTests : IDisposable
{
    private readonly AppDbContext _context;
    private readonly Mock<IPublishEndpoint> _publishEndpointMock = new();
    private readonly Mock<IFileStorageService> _fileStorageMock = new();
    private readonly Mock<ILogger<RenderManager>> _loggerMock = new();
    private readonly RenderManager _sut;

    public RenderManagerTests()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: $"RenderManagerTestDb_{Guid.NewGuid()}")
            .Options;

        _context = new AppDbContext(options);
        _sut = new RenderManager(_context, _publishEndpointMock.Object, _fileStorageMock.Object, _loggerMock.Object);
    }

    public void Dispose()
    {
        _context.Database.EnsureDeleted();
        _context.Dispose();
    }

    [Fact]
    public async Task RequestRenderAsync_WhenProjectNotFound_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();
        var act = async () => await _sut.RequestRenderAsync(projectId);
        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Fact]
    public async Task RequestRenderAsync_WhenEdlMissing_ShouldThrowBusinessException()
    {
        var project = new Project
        {
            Id = Guid.NewGuid(),
            Ad = "Test Project",
            Durum = ProjectDurumu.Taslak
        };
        _context.Projects.Add(project);
        await _context.SaveChangesAsync();

        var act = async () => await _sut.RequestRenderAsync(project.Id);
        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*EDL bulunamadı*");
    }

    [Fact]
    public async Task RequestRenderAsync_WhenValid_ShouldCreateRenderJobAndPublishEvent()
    {
        var projectId = Guid.NewGuid();
        var edlJson = """{"projectId": "111", "cuts": []}""";
        var project = new Project
        {
            Id = projectId,
            Ad = "Valid Project",
            Durum = ProjectDurumu.AnalizTamamlandi,
            EditDecisionList = new EditDecisionList
            {
                Id = Guid.NewGuid(),
                ProjectId = projectId,
                EdlJson = edlJson
            }
        };
        _context.Projects.Add(project);
        await _context.SaveChangesAsync();

        var result = await _sut.RequestRenderAsync(projectId);

        result.Should().NotBeNull();
        result.ProjectId.Should().Be(projectId);
        result.Durum.Should().Be(RenderDurumu.Kuyrukta);

        var savedJob = await _context.RenderJobs.FirstOrDefaultAsync(r => r.ProjectId == projectId);
        savedJob.Should().NotBeNull();
        savedJob!.EdlSnapshot.Should().Be(edlJson);

        var updatedProject = await _context.Projects.FindAsync(projectId);
        updatedProject!.Durum.Should().Be(ProjectDurumu.RenderEdiliyor);

        _publishEndpointMock.Verify(p => p.Publish(
            It.Is<RenderRequestedEvent>(e => e.ProjectId == projectId && e.RenderJobId == savedJob.Id),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task GetRenderStatusAsync_WhenJobExists_ShouldReturnStatus()
    {
        var projectId = Guid.NewGuid();
        var renderJob = new RenderJob
        {
            Id = Guid.NewGuid(),
            ProjectId = projectId,
            EdlSnapshot = "{}",
            Durum = RenderDurumu.RenderEdiliyor,
            BaslangicZamani = DateTime.UtcNow.AddMinutes(-2)
        };
        _context.RenderJobs.Add(renderJob);
        await _context.SaveChangesAsync();

        var result = await _sut.GetRenderStatusAsync(projectId, renderJob.Id);

        result.Should().NotBeNull();
        result.RenderJobId.Should().Be(renderJob.Id);
        result.Durum.Should().Be(RenderDurumu.RenderEdiliyor);
    }

    [Fact]
    public async Task GetDownloadUrlAsync_WhenRenderNotReady_ShouldThrowBusinessException()
    {
        var projectId = Guid.NewGuid();
        var renderJob = new RenderJob
        {
            Id = Guid.NewGuid(),
            ProjectId = projectId,
            EdlSnapshot = "{}",
            Durum = RenderDurumu.Kuyrukta,
            CiktiYolu = null
        };
        _context.RenderJobs.Add(renderJob);
        await _context.SaveChangesAsync();

        var act = async () => await _sut.GetDownloadUrlAsync(projectId, renderJob.Id);
        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*Render çıktısı henüz hazır değil*");
    }

    [Fact]
    public async Task GetDownloadUrlAsync_WhenRenderCompleted_ShouldReturnPresignedUrl()
    {
        var projectId = Guid.NewGuid();
        var renderJob = new RenderJob
        {
            Id = Guid.NewGuid(),
            ProjectId = projectId,
            EdlSnapshot = "{}",
            Durum = RenderDurumu.Tamamlandi,
            CiktiYolu = "renders/test/output.mp4"
        };
        _context.RenderJobs.Add(renderJob);
        await _context.SaveChangesAsync();

        _fileStorageMock.Setup(f => f.GetPresignedUrlAsync("renders/test/output.mp4", It.IsAny<TimeSpan>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync("https://minio.local/presigned/output.mp4");

        var url = await _sut.GetDownloadUrlAsync(projectId, renderJob.Id);

        url.Should().Be("https://minio.local/presigned/output.mp4");
    }

    [Fact]
    public async Task CompleteRenderAsync_ShouldUpdateJobAndProjectToCompleted()
    {
        var projectId = Guid.NewGuid();
        var project = new Project
        {
            Id = projectId,
            Ad = "Render Projesi",
            Durum = ProjectDurumu.RenderEdiliyor
        };
        var renderJob = new RenderJob
        {
            Id = Guid.NewGuid(),
            ProjectId = projectId,
            EdlSnapshot = "{}",
            Durum = RenderDurumu.RenderEdiliyor,
            BaslangicZamani = DateTime.UtcNow.AddSeconds(-30)
        };
        _context.Projects.Add(project);
        _context.RenderJobs.Add(renderJob);
        await _context.SaveChangesAsync();

        await _sut.CompleteRenderAsync(renderJob.Id, "renders/final.mp4");

        var updatedJob = await _context.RenderJobs.FindAsync(renderJob.Id);
        updatedJob!.Durum.Should().Be(RenderDurumu.Tamamlandi);
        updatedJob.CiktiYolu.Should().Be("renders/final.mp4");
        updatedJob.BitisZamani.Should().NotBeNull();
        updatedJob.SureMs.Should().BeGreaterThan(0);

        var updatedProject = await _context.Projects.FindAsync(projectId);
        updatedProject!.Durum.Should().Be(ProjectDurumu.Tamamlandi);
    }
}
