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

    [Fact]
    public async Task PatchEdlAsync_WithCaseInsensitivePropertyNames_ShouldMatchAndModifyCorrectly()
    {
        var projectId = Guid.NewGuid();
        var initialEdlJson = """
        {
            "cuts": [
                {"id": "cut_1", "start": 0.0, "end": 5.0, "reason": "silence"}
            ],
            "overlays": [
                {"id": "ov_1", "type": "text", "content": "Orijinal Başlık", "position": "center"}
            ],
            "settings": {"resolution": "1080p"}
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

        // Büyük / küçük harf karışık JSON patch (Cuts, OVERLAYS, ID, ACTION vb.)
        var patchDoc = JsonDocument.Parse("""
        {
            "Cuts": [
                {"ID": "cut_1", "ACTION": "remove"},
                {"id": "cut_2", "start": 10.0, "end": 15.0}
            ],
            "OverLAYS": [
                {"Id": "ov_1", "Action": "update", "Content": "Güncellenmiş Başlık", "color": "#FACC15"}
            ],
            "SETTINGS": {"resolution": "4k"}
        }
        """);

        var result = await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        result.Versiyon.Should().Be(2);

        var updatedInDb = await _dbContext.EditDecisionLists.FirstAsync(e => e.ProjectId == projectId);
        var updatedJson = updatedInDb.EdlJson;

        // cut_1 silinmiş olmalı
        updatedJson.Should().NotContain("cut_1");
        // cut_2 eklenmiş olmalı
        updatedJson.Should().Contain("cut_2");
        // ov_1 güncellenmiş olmalı
        updatedJson.Should().Contain("ov_1");
        updatedJson.Should().Contain("Güncellenmiş Başlık");
        updatedJson.Should().Contain("#FACC15");
        // settings güncellenmiş olmalı
        updatedJson.Should().Contain("\"resolution\":\"4k\"");
    }

    [Fact]
    public async Task PatchEdlAsync_WhenUpdatingOverlayTrackId_ShouldUpdateTrackIdCorrectly()
    {
        var projectId = Guid.NewGuid();
        var initialEdlJson = """
        {
            "cuts": [],
            "overlays": [
                {"id": "ov_text_1", "type": "text", "content": "Alt Yazı", "trackId": 1},
                {"id": "ov_img_2", "type": "image", "content": "Logo", "trackId": 2}
            ],
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

        // ov_text_1'i öne getir (trackId 1 -> 3)
        var patchDoc = JsonDocument.Parse("""
        {
            "overlays": [
                {"id": "ov_text_1", "action": "update", "trackId": 3}
            ]
        }
        """);

        var result = await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        result.Versiyon.Should().Be(2);

        var updatedInDb = await _dbContext.EditDecisionLists.FirstAsync(e => e.ProjectId == projectId);
        var updatedJson = updatedInDb.EdlJson;

        updatedJson.Should().Contain("ov_text_1");
        updatedJson.Should().Contain("\"trackId\":3");
        updatedJson.Should().Contain("ov_img_2");
        updatedJson.Should().Contain("\"trackId\":2");
    }

    [Fact]
    public async Task PatchEdlAsync_WhenUpdatingOverlayExitAnimationAndFont_ShouldUpdateCorrectly()
    {
        var projectId = Guid.NewGuid();
        var initialEdlJson = """
        {
            "projectId": "11111111-1111-1111-1111-111111111111",
            "cuts": [],
            "overlays": [
                {"id": "ov_text_1", "type": "text", "content": "Başlık", "font": "Inter", "animation": "fade", "exitAnimation": "fade"}
            ],
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
                {
                    "id": "ov_text_1",
                    "action": "update",
                    "font": "Bebas Neue",
                    "animation": "pop-up",
                    "exitAnimation": "scale-out"
                }
            ]
        }
        """);

        var result = await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        result.Versiyon.Should().Be(2);

        var updatedInDb = await _dbContext.EditDecisionLists.FirstAsync(e => e.ProjectId == projectId);
        var updatedJson = updatedInDb.EdlJson;

        updatedJson.Should().Contain("ov_text_1");
        updatedJson.Should().Contain("Bebas Neue");
        updatedJson.Should().Contain("scale-out");
        updatedJson.Should().Contain("pop-up");
    }

    [Fact]
    public async Task PatchEdlAsync_WhenMergingClipsByRemovingMultipleCuts_ShouldRemoveAllSpecifiedCuts()
    {
        var projectId = Guid.NewGuid();
        var initialEdlJson = """
        {
            "projectId": "11111111-1111-1111-1111-111111111111",
            "cuts": [
                {"id": "cut_gap_1", "start": 5.0, "end": 7.0, "reason": "silence"},
                {"id": "cut_gap_2", "start": 12.0, "end": 14.0, "reason": "silence"},
                {"id": "cut_keep_outside", "start": 50.0, "end": 55.0, "reason": "silence"}
            ],
            "overlays": [],
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

        // Kurguda [0-20] aralığındaki 3 klip seçilip 'Birleştir' dendiğinde aradaki 2 cut kaldırılır
        var patchDoc = JsonDocument.Parse("""
        {
            "cuts": [
                {"id": "cut_gap_1", "action": "remove"},
                {"id": "cut_gap_2", "action": "remove"}
            ]
        }
        """);

        var result = await _sut.PatchEdlAsync(projectId, patchDoc.RootElement);

        result.Versiyon.Should().Be(2);

        var updatedInDb = await _dbContext.EditDecisionLists.FirstAsync(e => e.ProjectId == projectId);
        var updatedJson = updatedInDb.EdlJson;

        updatedJson.Should().NotContain("cut_gap_1");
        updatedJson.Should().NotContain("cut_gap_2");
        updatedJson.Should().Contain("cut_keep_outside");
    }
}


