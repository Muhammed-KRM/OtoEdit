using FluentAssertions;
using MassTransit;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.API.Consumers;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;
using Xunit;

namespace OtoEdit.UnitTests.Consumers;

public class RenderNotificationConsumerTests
{
    private readonly Mock<IHubContext<PipelineHub>> _hubContextMock = new();
    private readonly Mock<IHubClients> _hubClientsMock = new();
    private readonly Mock<IClientProxy> _clientProxyMock = new();
    private readonly Mock<IRenderService> _renderServiceMock = new();
    private readonly Mock<ILogger<RenderNotificationConsumer>> _loggerMock = new();

    private readonly RenderNotificationConsumer _sut;

    public RenderNotificationConsumerTests()
    {
        _hubContextMock.Setup(h => h.Clients).Returns(_hubClientsMock.Object);
        _hubClientsMock.Setup(c => c.Group(It.IsAny<string>())).Returns(_clientProxyMock.Object);

        _sut = new RenderNotificationConsumer(
            _hubContextMock.Object,
            _renderServiceMock.Object,
            _loggerMock.Object);
    }

    [Fact]
    public async Task Consume_WhenRenderCompletedEvent_ShouldCompleteJobAndNotifySignalR()
    {
        var renderJobId = Guid.NewGuid();
        var projectId = Guid.NewGuid();
        var downloadUrl = "s3://otoedit/renders/job1.mp4";

        var eventMessage = new RenderCompletedEvent
        {
            RenderJobId = renderJobId,
            ProjectId = projectId,
            IndirmeUrl = downloadUrl
        };

        var contextMock = new Mock<ConsumeContext<RenderCompletedEvent>>();
        contextMock.Setup(c => c.Message).Returns(eventMessage);

        _renderServiceMock.Setup(r => r.CompleteRenderAsync(renderJobId, downloadUrl, It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        await _sut.Consume(contextMock.Object);

        _renderServiceMock.Verify(r => r.CompleteRenderAsync(renderJobId, downloadUrl, It.IsAny<CancellationToken>()), Times.Once);
        _hubClientsMock.Verify(c => c.Group($"project-{projectId}"), Times.Once);
        _clientProxyMock.Verify(c => c.SendCoreAsync(
            "RenderCompleted",
            It.IsAny<object[]>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
