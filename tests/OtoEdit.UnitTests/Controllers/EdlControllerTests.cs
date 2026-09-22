using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using Moq;
using OtoEdit.API.Controllers;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Business.Interfaces;
using Xunit;

namespace OtoEdit.UnitTests.Controllers;

public class EdlControllerTests
{
    private readonly Mock<IEdlService> _edlServiceMock = new();
    private readonly EdlController _sut;

    public EdlControllerTests()
    {
        _sut = new EdlController(_edlServiceMock.Object);
    }

    [Fact]
    public async Task GetEdl_ShouldReturnOkWithEdl()
    {
        var projectId = Guid.NewGuid();
        var edlJsonDoc = JsonDocument.Parse("""{"cuts": [], "overlays": []}""");
        var edlDto = new EdlDto
        {
            ProjectId = projectId,
            Versiyon = 1,
            Edl = edlJsonDoc.RootElement
        };

        _edlServiceMock.Setup(s => s.GetEdlAsync(projectId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(edlDto);

        var result = await _sut.GetEdl(projectId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(edlDto);
    }

    [Fact]
    public async Task PatchEdl_ShouldReturnOkWithPatchResponse()
    {
        var projectId = Guid.NewGuid();
        var patchDoc = JsonDocument.Parse("""{"cuts": []}""");
        var expectedResponse = new EdlPatchResponseDto
        {
            ProjectId = projectId,
            Versiyon = 2,
            Mesaj = "Güncellendi"
        };

        _edlServiceMock.Setup(s => s.PatchEdlAsync(projectId, It.IsAny<JsonElement>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedResponse);

        var result = await _sut.PatchEdl(projectId, patchDoc.RootElement, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(expectedResponse);
    }

    [Fact]
    public async Task UndoEdl_ShouldReturnOkWithRevertedEdl()
    {
        var projectId = Guid.NewGuid();
        var edlJsonDoc = JsonDocument.Parse("""{"cuts": [], "overlays": []}""");
        var revertedEdl = new EdlDto
        {
            ProjectId = projectId,
            Versiyon = 1,
            Edl = edlJsonDoc.RootElement
        };

        _edlServiceMock.Setup(s => s.UndoAsync(projectId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(revertedEdl);

        var result = await _sut.UndoEdl(projectId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(revertedEdl);
    }

    [Fact]
    public async Task RedoEdl_ShouldReturnOkWithRestoredEdl()
    {
        var projectId = Guid.NewGuid();
        var edlJsonDoc = JsonDocument.Parse("""{"cuts": [], "overlays": []}""");
        var restoredEdl = new EdlDto
        {
            ProjectId = projectId,
            Versiyon = 2,
            Edl = edlJsonDoc.RootElement
        };

        _edlServiceMock.Setup(s => s.RedoAsync(projectId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(restoredEdl);

        var result = await _sut.RedoEdl(projectId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(restoredEdl);
    }
}
