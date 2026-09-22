using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using Moq;
using OtoEdit.API.Controllers;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.Interfaces;
using Xunit;

namespace OtoEdit.UnitTests.Controllers;

public class ChatControllerTests
{
    private readonly Mock<IChatService> _chatServiceMock = new();
    private readonly ChatController _sut;

    public ChatControllerTests()
    {
        _sut = new ChatController(_chatServiceMock.Object);
    }

    [Fact]
    public async Task SendMessage_WhenMessageIsEmpty_ShouldReturnBadRequest()
    {
        var projectId = Guid.NewGuid();
        var dto = new ChatMessageDto { Mesaj = "   " };

        var result = await _sut.SendMessage(projectId, dto, CancellationToken.None);

        result.Should().BeOfType<BadRequestObjectResult>();
        var badRequest = result as BadRequestObjectResult;
        badRequest!.Value.Should().Be("Mesaj boş olamaz.");
    }

    [Fact]
    public async Task SendMessage_WhenMessageIsValid_ShouldReturnOkWithResponse()
    {
        var projectId = Guid.NewGuid();
        var dto = new ChatMessageDto { Mesaj = "Altyazı ekle" };
        var expectedResponse = new ChatResponseDto
        {
            Id = Guid.NewGuid(),
            Rol = "assistant",
            Mesaj = "Altyazı eklendi",
            PatchDurumu = "clarification"
        };

        _chatServiceMock.Setup(s => s.SendMessageAsync(projectId, dto.Mesaj, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedResponse);

        var result = await _sut.SendMessage(projectId, dto, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(expectedResponse);
    }

    [Fact]
    public async Task GetHistory_ShouldReturnOkWithHistoryList()
    {
        var projectId = Guid.NewGuid();
        var history = new List<ChatMessageHistoryDto>
        {
            new() { Id = Guid.NewGuid(), ProjectId = projectId, Rol = "user", Mesaj = "Merhaba" },
            new() { Id = Guid.NewGuid(), ProjectId = projectId, Rol = "assistant", Mesaj = "Nasıl yardımcı olabilirim?" }
        };

        _chatServiceMock.Setup(s => s.GetHistoryAsync(projectId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(history);

        var result = await _sut.GetHistory(projectId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(history);
    }

    [Fact]
    public async Task ApplyPendingPatch_ShouldReturnOkWithResult()
    {
        var projectId = Guid.NewGuid();
        var messageId = Guid.NewGuid();
        var expectedResult = new OtoEdit.Business.DTOs.Edl.EdlPatchResponseDto
        {
            ProjectId = projectId,
            Versiyon = 2,
            Mesaj = "Patch uygulandı"
        };

        _chatServiceMock.Setup(s => s.ApplyPendingPatchAsync(messageId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedResult);

        var result = await _sut.ApplyPendingPatch(projectId, messageId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(expectedResult);
    }
}
