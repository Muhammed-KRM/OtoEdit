using System.Text.Json;
using FluentAssertions;
using MassTransit;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.API.Consumers;
using OtoEdit.API.Hubs;
using OtoEdit.Business.Events;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Entities;
using OtoEdit.Data.Enums;
using Xunit;

namespace OtoEdit.UnitTests.Consumers;

public class AnalysisNotificationConsumerTests
{
    private readonly Mock<IHubContext<PipelineHub>> _hubContextMock = new();
    private readonly Mock<IHubClients> _hubClientsMock = new();
    private readonly Mock<IClientProxy> _clientProxyMock = new();
    private readonly Mock<IEdlService> _edlServiceMock = new();
    private readonly Mock<IProjectService> _projectServiceMock = new();
    private readonly Mock<ILogger<AnalysisNotificationConsumer>> _loggerMock = new();

    private readonly AnalysisNotificationConsumer _sut;

    public AnalysisNotificationConsumerTests()
    {
        _hubContextMock.Setup(h => h.Clients).Returns(_hubClientsMock.Object);
        _hubClientsMock.Setup(c => c.Group(It.IsAny<string>())).Returns(_clientProxyMock.Object);

        _sut = new AnalysisNotificationConsumer(
            _hubContextMock.Object,
            _edlServiceMock.Object,
            _projectServiceMock.Object,
            _loggerMock.Object);
    }

    [Fact]
    public async Task Consume_WhenValidAnalysisCompletedEvent_ShouldSaveEdlUpdateStatusAndNotifySignalR()
    {
        var projectId = Guid.NewGuid();
        var videoId = Guid.NewGuid();
        var jsonDoc = JsonDocument.Parse("{\"cuts\": [], \"settings\": {\"targetFormat\": \"9:16\"}}");

        var eventMessage = new AnalysisCompletedEvent
        {
            ProjectId = projectId,
            VideoId = videoId,
            EdlJson = jsonDoc
        };

        var contextMock = new Mock<ConsumeContext<AnalysisCompletedEvent>>();
        contextMock.Setup(c => c.Message).Returns(eventMessage);

        var savedEdl = new EditDecisionList
        {
            ProjectId = projectId,
            Versiyon = 1
        };

        _edlServiceMock.Setup(e => e.CreateOrUpdateAsync(projectId, jsonDoc, It.IsAny<CancellationToken>()))
            .ReturnsAsync(savedEdl);

        _projectServiceMock.Setup(p => p.UpdateStatusAsync(projectId, ProjectDurumu.AnalizTamamlandi, It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        await _sut.Consume(contextMock.Object);

        _edlServiceMock.Verify(e => e.CreateOrUpdateAsync(projectId, jsonDoc, It.IsAny<CancellationToken>()), Times.Once);
        _projectServiceMock.Verify(p => p.UpdateStatusAsync(projectId, ProjectDurumu.AnalizTamamlandi, It.IsAny<CancellationToken>()), Times.Once);
        _hubClientsMock.Verify(c => c.Group($"project-{projectId}"), Times.Once);
        _clientProxyMock.Verify(c => c.SendCoreAsync(
            "AnalysisCompleted",
            It.IsAny<object[]>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
