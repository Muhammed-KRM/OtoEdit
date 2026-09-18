using System.Text.Json;
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class EdlManagerPatchTests : IDisposable
{
    private readonly AppDbContext _dbContext;
    private readonly Mock<ICacheService> _cacheMock = new();
    private readonly Mock<ILogger<EdlManager>> _loggerMock = new();
    private readonly EdlManager _sut;

    public EdlManagerPatchTests()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: $"EdlPatchTestDb_{Guid.NewGuid()}")
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
    public async Task PatchEdlAsync_AddAndRemoveCuts_ShouldCorrectlyModifyArray()
    {
        var projectId = Guid.NewGuid();
        var initialEdlJson = """
        {
            "projectId": "11111111-1111-1111-1111-111111111111",
            "cuts": [
                {"id": "cut_old_1", "start": 0.0, "end": 5.0, "reason": "silence"},
                {"id": "cut_keep_2", "start": 10.0, "end": 15.0, "reason": "silence"}
            ],
            "overlays": [],
            "settings": {"targetFormat": "16:9"}
        }
        """;

        var edl = new EditDecisionList
        {
            ProjectId = projectId,
            EdlJson = initialEdlJson,
            Versiyon = 1,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _dbContext.EditDecisionLists.Add(edl);
        await _dbContext.SaveChangesAsync();

        var patchDoc = JsonDocument.Parse("""
        {
            "cuts": [
                {"id": "cut_old_1", "action": "remove"},
                {"id": "cut_new_3", "start": 20.0, "end": 25.0, "reason": "user_command"}
            ],
            "settings": {"targetFormat": "9:16"}
        }
        """);

        var response = await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        response.Versiyon.Should().Be(2);

        var updatedInDb = await _dbContext.EditDecisionLists.FirstAsync(e => e.ProjectId == projectId);
        updatedInDb.EdlJson.Should().NotContain("cut_old_1");
        updatedInDb.EdlJson.Should().Contain("cut_keep_2");
        updatedInDb.EdlJson.Should().Contain("cut_new_3");
        updatedInDb.EdlJson.Should().Contain("\"targetFormat\":\"9:16\"");
    }

    [Fact]
    public async Task PatchEdlAsync_AddOverlay_ShouldAppendToOverlaysArray()
    {
        var projectId = Guid.NewGuid();
        var initialEdlJson = """
        {
            "cuts": [],
            "overlays": [{"id": "text_1", "type": "text", "content": "Eski Başlık"}],
            "settings": {}
        }
        """;

        var edl = new EditDecisionList
        {
            ProjectId = projectId,
            EdlJson = initialEdlJson,
            Versiyon = 1,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _dbContext.EditDecisionLists.Add(edl);
        await _dbContext.SaveChangesAsync();

        var patchDoc = JsonDocument.Parse("""
        {
            "overlays": [
                {"id": "img_2", "type": "image", "content": "cat", "timestamp": 45.0}
            ]
        }
        """);

        await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        var updatedInDb = await _dbContext.EditDecisionLists.FirstAsync(e => e.ProjectId == projectId);
        updatedInDb.EdlJson.Should().Contain("text_1");
        updatedInDb.EdlJson.Should().Contain("img_2");
        updatedInDb.EdlJson.Should().Contain("\"content\":\"cat\"");
    }
}
