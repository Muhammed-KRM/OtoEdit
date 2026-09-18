using System.Text.Json;
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class EdlManagerTests : IDisposable
{
    private readonly AppDbContext _dbContext;
    private readonly Mock<ICacheService> _cacheMock = new();
    private readonly Mock<ILogger<EdlManager>> _loggerMock = new();
    private readonly EdlManager _sut;

    public EdlManagerTests()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: $"EdlTestDb_{Guid.NewGuid()}")
            .Options;

        _dbContext = new AppDbContext(options);
        _sut = new EdlManager(_dbContext, _cacheMock.Object, _loggerMock.Object);
    }

    public void Dispose()
    {
        _dbContext.Database.EnsureDeleted();
        _dbContext.Dispose();
    }

    [Fact]
    public async Task GetEdlAsync_WhenInCache_ShouldReturnCached()
    {
        var projectId = Guid.NewGuid();
        var cached = new EdlDto
        {
            ProjectId = projectId,
            Versiyon = 2
        };

        _cacheMock.Setup(c => c.GetAsync<EdlDto>($"edl:{projectId}", It.IsAny<CancellationToken>()))
            .ReturnsAsync(cached);

        var result = await _sut.GetEdlAsync(projectId);

        result.Should().NotBeNull();
        result.Versiyon.Should().Be(2);
    }

    [Fact]
    public async Task GetEdlAsync_WhenNotFound_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();

        _cacheMock.Setup(c => c.GetAsync<EdlDto>($"edl:{projectId}", It.IsAny<CancellationToken>()))
            .ReturnsAsync((EdlDto?)null);

        var act = async () => await _sut.GetEdlAsync(projectId);

        await act.Should().ThrowAsync<NotFoundException>()
            .WithMessage("*EDL bulunamadı*");
    }

    [Fact]
    public async Task CreateOrUpdateAsync_WhenNew_ShouldCreateVersion1()
    {
        var projectId = Guid.NewGuid();
        var jsonDoc = JsonDocument.Parse("{\"cuts\": [{\"start\": 0, \"end\": 5}]}");

        var result = await _sut.CreateOrUpdateAsync(projectId, jsonDoc);

        result.Should().NotBeNull();
        result.ProjectId.Should().Be(projectId);
        result.Versiyon.Should().Be(1);
        result.EdlJson.Should().Contain("\"cuts\"");

        var inDb = await _dbContext.EditDecisionLists.FirstOrDefaultAsync(e => e.ProjectId == projectId);
        inDb.Should().NotBeNull();
        inDb!.Versiyon.Should().Be(1);

        _cacheMock.Verify(c => c.RemoveAsync($"edl:{projectId}", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task CreateOrUpdateAsync_WhenAlreadyExists_ShouldIncrementVersion()
    {
        var projectId = Guid.NewGuid();
        var existing = new EditDecisionList
        {
            ProjectId = projectId,
            EdlJson = "{\"cuts\": []}",
            Versiyon = 1,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _dbContext.EditDecisionLists.Add(existing);
        await _dbContext.SaveChangesAsync();

        var updatedDoc = JsonDocument.Parse("{\"cuts\": [{\"start\": 10, \"end\": 20}]}");

        var result = await _sut.CreateOrUpdateAsync(projectId, updatedDoc);

        result.Versiyon.Should().Be(2);

        var inDb = await _dbContext.EditDecisionLists.FirstOrDefaultAsync(e => e.ProjectId == projectId);
        inDb!.Versiyon.Should().Be(2);
        inDb.EdlJson.Should().Contain("\"start\": 10");
    }

    [Fact]
    public async Task PatchEdlAsync_WhenFound_ShouldMergePropertiesAndIncrementVersion()
    {
        var projectId = Guid.NewGuid();
        var existing = new EditDecisionList
        {
            ProjectId = projectId,
            EdlJson = "{\"aspectRatio\": \"16:9\", \"cuts\": []}",
            Versiyon = 1,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _dbContext.EditDecisionLists.Add(existing);
        await _dbContext.SaveChangesAsync();

        var patchDoc = JsonDocument.Parse("{\"aspectRatio\": \"9:16\", \"subtitleColor\": \"#FFCC00\"}");

        var result = await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        result.Should().NotBeNull();
        result.Versiyon.Should().Be(2);

        var inDb = await _dbContext.EditDecisionLists.FirstOrDefaultAsync(e => e.ProjectId == projectId);
        inDb!.Versiyon.Should().Be(2);
        inDb.EdlJson.Should().Contain("\"aspectRatio\":\"9:16\"");
        inDb.EdlJson.Should().Contain("\"subtitleColor\":\"#FFCC00\"");
    }
}
