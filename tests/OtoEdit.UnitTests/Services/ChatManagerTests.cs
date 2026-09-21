using System.Text.Json;
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Business.Services;
using OtoEdit.Data.Context;
using OtoEdit.Data.Entities;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class ChatManagerTests : IDisposable
{
    private readonly AppDbContext _dbContext;
    private readonly Mock<IChatProvider> _chatProviderMock = new();
    private readonly Mock<IEdlService> _edlServiceMock = new();
    private readonly Mock<ICacheService> _cacheServiceMock = new();
    private readonly Mock<IPexelsService> _pexelsServiceMock = new();
    private readonly Mock<ILogger<ChatManager>> _loggerMock = new();

    private readonly ChatManager _sut;

    public ChatManagerTests()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: $"ChatTestDb_{Guid.NewGuid()}")
            .Options;

        _dbContext = new AppDbContext(options);

        _sut = new ChatManager(
            _dbContext,
            _chatProviderMock.Object,
            _edlServiceMock.Object,
            _cacheServiceMock.Object,
            _pexelsServiceMock.Object,
            _loggerMock.Object);
    }

    public void Dispose()
    {
        _dbContext.Database.EnsureDeleted();
        _dbContext.Dispose();
    }

    [Fact]
    public async Task SendMessageAsync_WhenProjectNotFound_ShouldThrowNotFoundException()
    {
        var projectId = Guid.NewGuid();

        var act = async () => await _sut.SendMessageAsync(projectId, "Selam");

        await act.Should().ThrowAsync<NotFoundException>()
            .WithMessage("*Proje bulunamadı*");
    }

    [Fact]
    public async Task SendMessageAsync_ValidMessage_ShouldSaveMessagesApplyPatchAndClearCache()
    {
        var projectId = Guid.NewGuid();
        var project = new Project
        {
            Id = projectId,
            Ad = "Chat Test Projesi"
        };
        _dbContext.Projects.Add(project);

        var existingEdl = new EditDecisionList
        {
            ProjectId = projectId,
            EdlJson = "{\"cuts\": []}",
            Versiyon = 1
        };
        _dbContext.EditDecisionLists.Add(existingEdl);
        await _dbContext.SaveChangesAsync();

        var patchDoc = JsonDocument.Parse("{\"cuts\": [{\"id\": \"cut_ai_1\", \"start\": 0.0, \"end\": 5.0}]}");
        var aiResult = new ChatResult
        {
            Intent = "command",
            Mesaj = "Girişteki ilk 5 saniyeyi kestim.",
            EdlPatch = patchDoc.RootElement
        };

        _chatProviderMock.Setup(c => c.ProcessCommandAsync(
            "İlk 5 saniyeyi kes",
            It.IsAny<string>(),
            It.IsAny<string?>(),
            It.IsAny<List<ChatHistoryItem>>(),
            It.IsAny<CancellationToken>()))
            .ReturnsAsync(aiResult);

        _edlServiceMock.Setup(e => e.PatchEdlAsync(projectId, It.IsAny<JsonElement>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new EdlPatchResponseDto
            {
                ProjectId = projectId,
                Versiyon = 2,
                Mesaj = "Başarılı"
            });

        var response = await _sut.SendMessageAsync(projectId, "İlk 5 saniyeyi kes");

        response.Should().NotBeNull();
        response.Rol.Should().Be("assistant");
        response.Mesaj.Should().Be("Girişteki ilk 5 saniyeyi kestim.");
        // HitL gereği patch pending durumuna düşmeli ve edlVersiyon null dönmeli
        response.PatchDurumu.Should().Be("pending");
        response.EdlVersiyonYeni.Should().BeNull();

        // Veritabanında hem kullanıcı hem asistan mesajı olmalı
        var messages = await _dbContext.ChatMessages.Where(c => c.ProjectId == projectId).ToListAsync();
        messages.Should().HaveCount(2);
        messages.Should().Contain(m => m.Rol == "user" && m.Mesaj == "İlk 5 saniyeyi kes");
        messages.Should().Contain(m => m.Rol == "assistant" && m.Mesaj == "Girişteki ilk 5 saniyeyi kestim.");

        // Cache silinmiş olmalı
        _cacheServiceMock.Verify(c => c.RemoveAsync($"chat:{projectId}:history", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task SendMessageAsync_WhenImageOverlayGenerated_ShouldEnrichWithPexels()
    {
        var projectId = Guid.NewGuid();
        var project = new Project { Id = projectId, Ad = "Image Test" };
        _dbContext.Projects.Add(project);
        await _dbContext.SaveChangesAsync();

        var patchWithImage = JsonDocument.Parse("{\"overlays\": [{\"id\": \"img_1\", \"type\": \"image\", \"content\": \"cat\"}]}");
        var aiResult = new ChatResult
        {
            Intent = "command",
            Mesaj = "Kedi resmi eklendi.",
            EdlPatch = patchWithImage.RootElement
        };

        _chatProviderMock.Setup(c => c.ProcessCommandAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<string?>(), It.IsAny<List<ChatHistoryItem>>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(aiResult);

        _pexelsServiceMock.Setup(p => p.SearchAndSaveAssetAsync(projectId, "cat", "landscape", It.IsAny<CancellationToken>()))
            .ReturnsAsync($"assets/{projectId}/cat_123.jpg");

        JsonElement? receivedPatch = null;
        _edlServiceMock.Setup(e => e.PatchEdlAsync(projectId, It.IsAny<JsonElement>(), It.IsAny<CancellationToken>()))
            .Callback<Guid, JsonElement, CancellationToken>((_, p, _) => receivedPatch = p)
            .ReturnsAsync(new EdlPatchResponseDto { ProjectId = projectId, Versiyon = 2 });

        await _sut.SendMessageAsync(projectId, "Kedi resmi ekle");

        _pexelsServiceMock.Verify(p => p.SearchAndSaveAssetAsync(projectId, "cat", "landscape", It.IsAny<CancellationToken>()), Times.Once);
        // Patch artık onay bekleyeceği için EdlService.PatchEdlAsync doğrudan çağrılmayacak. HitL pending objesi zenginleşecek.
        var messages = await _dbContext.ChatMessages.Where(c => c.ProjectId == projectId && c.Rol == "assistant").ToListAsync();
        messages.Should().HaveCount(1);
        messages.First().PendingEdlPatch.Should().Contain($"assets/{projectId}/cat_123.jpg");
    }

    [Fact]
    public async Task GetHistoryAsync_ShouldReturnMessagesInChronologicalOrder()
    {
        var projectId = Guid.NewGuid();
        _dbContext.ChatMessages.AddRange(
            new ChatMessage { ProjectId = projectId, Rol = "user", Mesaj = "Mesaj 1", OlusturmaTarihi = DateTime.UtcNow.AddMinutes(-5) },
            new ChatMessage { ProjectId = projectId, Rol = "assistant", Mesaj = "Yanıt 1", OlusturmaTarihi = DateTime.UtcNow.AddMinutes(-4) },
            new ChatMessage { ProjectId = projectId, Rol = "user", Mesaj = "Mesaj 2", OlusturmaTarihi = DateTime.UtcNow.AddMinutes(-1) }
        );
        await _dbContext.SaveChangesAsync();

        var history = (await _sut.GetHistoryAsync(projectId)).ToList();

        history.Should().HaveCount(3);
        history[0].Mesaj.Should().Be("Mesaj 1");
        history[1].Mesaj.Should().Be("Yanıt 1");
        history[2].Mesaj.Should().Be("Mesaj 2");
    }
}
