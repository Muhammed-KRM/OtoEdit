using FluentAssertions;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.DTOs.Project;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Business.Validators;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;
using OtoEdit.Data.Repositories;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class ProjectManagerTests
{
    private readonly Mock<IProjectRepository> _projectRepoMock = new();
    private readonly Mock<IFileStorageService> _fileStorageMock = new();
    private readonly Mock<ICacheService> _cacheMock = new();
    private readonly Mock<ILogService> _logServiceMock = new();
    private readonly Mock<ILogger<ProjectManager>> _loggerMock = new();
    private readonly ProjectCreateValidator _createValidator = new();
    private readonly ProjectUpdateValidator _updateValidator = new();

    private readonly ProjectManager _sut; // System Under Test

    public ProjectManagerTests()
    {
        _sut = new ProjectManager(
            _projectRepoMock.Object,
            _fileStorageMock.Object,
            _cacheMock.Object,
            _createValidator,
            _updateValidator,
            _logServiceMock.Object,
            _loggerMock.Object);
    }

    [Fact]
    public async Task GetByIdAsync_WhenInCache_ShouldReturnCachedWithoutDbCall()
    {
        var projectId = Guid.NewGuid();
        var cachedDto = new ProjectDetailDto
        {
            Id = projectId,
            Ad = "Önbellekteki Proje",
            VideoFormati = VideoFormati.Dikey_9_16,
            Durum = ProjectDurumu.Taslak
        };

        _cacheMock.Setup(c => c.GetAsync<ProjectDetailDto>($"project:{projectId}", It.IsAny<CancellationToken>()))
            .ReturnsAsync(cachedDto);

        var result = await _sut.GetByIdAsync(projectId);

        result.Should().NotBeNull();
        result.Ad.Should().Be("Önbellekteki Proje");
        _projectRepoMock.Verify(r => r.GetProjectWithDetailsAsync(It.IsAny<Guid>(), It.IsAny<bool>()), Times.Never);
    }

    [Fact]
    public async Task GetByIdAsync_WhenNotInCache_AndNotFoundInDb_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();

        _cacheMock.Setup(c => c.GetAsync<ProjectDetailDto>($"project:{projectId}", It.IsAny<CancellationToken>()))
            .ReturnsAsync((ProjectDetailDto?)null);

        _projectRepoMock.Setup(r => r.GetProjectWithDetailsAsync(projectId, true))
            .ReturnsAsync((Project?)null);

        var act = async () => await _sut.GetByIdAsync(projectId);

        await act.Should().ThrowAsync<NotFoundException>()
            .WithMessage("*Proje bulunamadı*");
    }

    [Fact]
    public async Task GetByIdAsync_WhenNotInCache_AndFoundInDb_ShouldCacheAndReturn()
    {
        var projectId = Guid.NewGuid();
        var entity = new Project
        {
            Id = projectId,
            Ad = "Veritabanındaki Proje",
            VideoFormati = VideoFormati.Yatay_16_9,
            Durum = ProjectDurumu.Tamamlandi,
            OlusturmaTarihi = DateTime.UtcNow
        };

        _cacheMock.Setup(c => c.GetAsync<ProjectDetailDto>($"project:{projectId}", It.IsAny<CancellationToken>()))
            .ReturnsAsync((ProjectDetailDto?)null);

        _projectRepoMock.Setup(r => r.GetProjectWithDetailsAsync(projectId, true))
            .ReturnsAsync(entity);

        var result = await _sut.GetByIdAsync(projectId);

        result.Should().NotBeNull();
        result.Id.Should().Be(projectId);
        result.Ad.Should().Be("Veritabanındaki Proje");

        _cacheMock.Verify(c => c.SetAsync(
            $"project:{projectId}",
            It.Is<ProjectDetailDto>(d => d.Id == projectId),
            It.IsAny<TimeSpan?>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task CreateAsync_InvalidDto_ShouldThrowBusinessException()
    {
        var dto = new ProjectCreateDto
        {
            Ad = "", // Boş ad
            VideoFormati = VideoFormati.Dikey_9_16
        };

        var act = async () => await _sut.CreateAsync(dto);

        await act.Should().ThrowAsync<BusinessException>()
            .WithMessage("*Proje adı boş olamaz*");

        _projectRepoMock.Verify(r => r.AddAsync(It.IsAny<Project>()), Times.Never);
    }

    [Fact]
    public async Task CreateAsync_ValidDto_ShouldSaveAndReturnProject()
    {
        var dto = new ProjectCreateDto
        {
            Ad = "Yeni Test Projesi",
            Aciklama = "Otomatik kurgu için",
            VideoFormati = VideoFormati.Dikey_9_16,
            GestureCommandsEnabled = true
        };

        Project? savedProject = null;
        _projectRepoMock.Setup(r => r.AddAsync(It.IsAny<Project>()))
            .ReturnsAsync((Project p) =>
            {
                savedProject = p;
                p.Id = Guid.NewGuid();
                return p;
            });

        _projectRepoMock.Setup(r => r.SaveChangesAsync())
            .ReturnsAsync(1);

        _projectRepoMock.Setup(r => r.GetProjectWithDetailsAsync(It.IsAny<Guid>(), true))
            .ReturnsAsync(() => new Project
            {
                Id = savedProject!.Id,
                Ad = savedProject.Ad,
                VideoFormati = savedProject.VideoFormati,
                Durum = ProjectDurumu.Taslak
            });

        var result = await _sut.CreateAsync(dto);

        result.Should().NotBeNull();
        result.Ad.Should().Be("Yeni Test Projesi");
        _projectRepoMock.Verify(r => r.AddAsync(It.IsAny<Project>()), Times.Once);
        _projectRepoMock.Verify(r => r.SaveChangesAsync(), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_WhenProjectExists_ShouldDeleteStorageAndDbAndCache()
    {
        var projectId = Guid.NewGuid();
        var entity = new Project { Id = projectId, Ad = "Silinecek Proje" };

        _projectRepoMock.Setup(r => r.GetByIdAsync(projectId))
            .ReturnsAsync(entity);

        _projectRepoMock.Setup(r => r.SaveChangesAsync())
            .ReturnsAsync(1);

        await _sut.DeleteAsync(projectId);

        _fileStorageMock.Verify(f => f.DeleteDirectoryAsync($"videos/{projectId}/", It.IsAny<CancellationToken>()), Times.Once);
        _projectRepoMock.Verify(r => r.Delete(entity), Times.Once);
        _projectRepoMock.Verify(r => r.SaveChangesAsync(), Times.Once);
        _cacheMock.Verify(c => c.RemoveAsync($"project:{projectId}", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_WhenProjectNotFound_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();
        _projectRepoMock.Setup(r => r.GetByIdAsync(projectId))
            .ReturnsAsync((Project?)null);

        var act = async () => await _sut.DeleteAsync(projectId);

        await act.Should().ThrowAsync<NotFoundException>();
    }
}
