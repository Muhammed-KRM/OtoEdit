using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using OtoEdit.API.Controllers;
using OtoEdit.Business.DTOs.Asset;
using OtoEdit.Business.Interfaces;
using Xunit;

namespace OtoEdit.UnitTests.Controllers;

public class AssetsControllerTests
{
    private readonly Mock<IAssetService> _assetServiceMock = new();
    private readonly AssetsController _sut;

    public AssetsControllerTests()
    {
        _sut = new AssetsController(_assetServiceMock.Object);
    }

    [Fact]
    public async Task UploadAsset_WhenFileNullOrEmpty_ShouldReturnBadRequest()
    {
        var projectId = Guid.NewGuid();
        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(0);

        var result = await _sut.UploadAsset(projectId, fileMock.Object, CancellationToken.None);

        result.Should().BeOfType<BadRequestObjectResult>();
        var badRequest = result as BadRequestObjectResult;
        badRequest!.Value.Should().Be("Yüklenecek medya dosyası boş olamaz.");
    }

    [Fact]
    public async Task UploadAsset_WhenFileValid_ShouldReturnCreatedWithDto()
    {
        var projectId = Guid.NewGuid();
        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(1024);
        fileMock.Setup(f => f.FileName).Returns("photo.jpg");

        var expectedDto = new ProjectAssetDto
        {
            Id = Guid.NewGuid(),
            ProjectId = projectId,
            DosyaAdi = "photo.jpg",
            Url = "http://localhost:9000/assets/photo.jpg"
        };

        _assetServiceMock.Setup(s => s.UploadAssetAsync(projectId, fileMock.Object, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedDto);

        var result = await _sut.UploadAsset(projectId, fileMock.Object, CancellationToken.None);

        result.Should().BeOfType<ObjectResult>();
        var objResult = result as ObjectResult;
        objResult!.StatusCode.Should().Be(StatusCodes.Status201Created);
        objResult.Value.Should().BeEquivalentTo(expectedDto);
    }

    [Fact]
    public async Task GetAssets_ShouldReturnOkWithList()
    {
        var projectId = Guid.NewGuid();
        var expectedList = new List<ProjectAssetDto>
        {
            new() { Id = Guid.NewGuid(), ProjectId = projectId, DosyaAdi = "img1.png" },
            new() { Id = Guid.NewGuid(), ProjectId = projectId, DosyaAdi = "img2.png" }
        };

        _assetServiceMock.Setup(s => s.GetProjectAssetsAsync(projectId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedList);

        var result = await _sut.GetAssets(projectId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(expectedList);
    }

    [Fact]
    public async Task DeleteAsset_ShouldReturnNoContent()
    {
        var projectId = Guid.NewGuid();
        var assetId = Guid.NewGuid();

        _assetServiceMock.Setup(s => s.DeleteAssetAsync(projectId, assetId, It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _sut.DeleteAsset(projectId, assetId, CancellationToken.None);

        result.Should().BeOfType<NoContentResult>();
    }
}
