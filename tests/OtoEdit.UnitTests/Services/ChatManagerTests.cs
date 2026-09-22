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

    [Fact]
    public async Task SendMessageAsync_WhenAiReturnsClarificationIntent_ShouldSetStatusAndReturnFormFields()
    {
        var projectId = Guid.NewGuid();
        var project = new Project { Id = projectId, Ad = "Clarification Test Projesi" };
        _dbContext.Projects.Add(project);
        await _dbContext.SaveChangesAsync();

        var formFieldsDoc = JsonDocument.Parse("""
        [
            {"id": "content", "type": "text", "label": "Yazı Metni", "defaultValue": "Başlık"},
            {"id": "position", "type": "position", "label": "Ekran Konumu", "defaultValue": "bottom-center"},
            {"id": "color", "type": "color", "label": "Yazı Rengi", "defaultValue": "#FACC15"}
        ]
        """);

        var aiResult = new ChatResult
        {
            Intent = "clarification",
            Mesaj = "Lütfen yazı metni ve rengini seçin.",
            FormFields = formFieldsDoc.RootElement
        };

        _chatProviderMock.Setup(c => c.ProcessCommandAsync(
            "Yazı ekle",
            It.IsAny<string>(),
            It.IsAny<string?>(),
            It.IsAny<List<ChatHistoryItem>>(),
            It.IsAny<CancellationToken>()))
            .ReturnsAsync(aiResult);

        var response = await _sut.SendMessageAsync(projectId, "Yazı ekle");

        response.Should().NotBeNull();
        response.Intent.Should().Be("clarification");
        response.PatchDurumu.Should().Be("clarification");
        response.FormFields.Should().NotBeNull();
        response.FormFields!.Value.GetArrayLength().Should().Be(3);

        // Veritabanında form verisinin EdlPatch alanında saklandığını doğrula
        var savedAssistantMsg = await _dbContext.ChatMessages
            .FirstAsync(c => c.ProjectId == projectId && c.Rol == "assistant");
        savedAssistantMsg.PatchDurumu.Should().Be("clarification");
        savedAssistantMsg.EdlPatch.Should().Contain("position");
        savedAssistantMsg.EdlPatch.Should().Contain("#FACC15");
    }

    [Fact]
    public async Task GetHistoryAsync_WhenClarificationMessageExists_ShouldParseAndReturnFormFields()
    {
        var projectId = Guid.NewGuid();
        var formFieldsJson = """[{"id":"color","type":"color","defaultValue":"#EF4444"}]""";

        _dbContext.ChatMessages.Add(new ChatMessage
        {
            ProjectId = projectId,
            Rol = "assistant",
            Mesaj = "Renk seçin",
            PatchDurumu = "clarification",
            EdlPatch = formFieldsJson,
            OlusturmaTarihi = DateTime.UtcNow
        });
        await _dbContext.SaveChangesAsync();

        var history = (await _sut.GetHistoryAsync(projectId)).ToList();

        history.Should().HaveCount(1);
        history[0].PatchDurumu.Should().Be("clarification");
        history[0].FormFields.Should().NotBeNull();
        history[0].FormFields!.Value.GetArrayLength().Should().Be(1);
        history[0].FormFields!.Value[0].GetProperty("defaultValue").GetString().Should().Be("#EF4444");
    }

    [Fact]
    public async Task ApplyPendingPatchAsync_WhenValidPendingPatch_ShouldApplyToEdlAndMarkApplied()
    {
        var projectId = Guid.NewGuid();
        var messageId = Guid.NewGuid();
        var pendingPatchJson = """{"cuts":[{"id":"cut_test_1","action":"add","start":5.0,"end":10.0}]}""";

        var chatMessage = new ChatMessage
        {
            Id = messageId,
            ProjectId = projectId,
            Rol = "assistant",
            Mesaj = "Kesim önerisi",
            PatchDurumu = "pending",
            PendingEdlPatch = pendingPatchJson,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _dbContext.ChatMessages.Add(chatMessage);
        await _dbContext.SaveChangesAsync();

        _edlServiceMock.Setup(e => e.PatchEdlAsync(projectId, It.IsAny<JsonElement>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new EdlPatchResponseDto
            {
                ProjectId = projectId,
                Versiyon = 2,
                Mesaj = "Patch uygulandı"
            });

        var result = await _sut.ApplyPendingPatchAsync(messageId);

        result.Should().NotBeNull();
        result.Versiyon.Should().Be(2);

        // Veritabanındaki mesajın durumunun applied olduğunu ve pendingPatch'in temizlendiğini doğrula
        var updatedMsg = await _dbContext.ChatMessages.FindAsync(messageId);
        updatedMsg!.PatchDurumu.Should().Be("applied");
        updatedMsg.PendingEdlPatch.Should().BeNull();
        updatedMsg.EdlPatch.Should().Be(pendingPatchJson);

        // EdlService çağrısı doğrulanmalı
        _edlServiceMock.Verify(e => e.PatchEdlAsync(projectId, It.IsAny<JsonElement>(), It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task ApplyPendingPatchAsync_WhenNoPendingPatch_ShouldThrowInvalidOperationException()
    {
        var messageId = Guid.NewGuid();
        var chatMessage = new ChatMessage
        {
            Id = messageId,
            ProjectId = Guid.NewGuid(),
            Rol = "assistant",
            Mesaj = "Bilgilendirme",
            PatchDurumu = "none",
            PendingEdlPatch = null,
            OlusturmaTarihi = DateTime.UtcNow
        };
        _dbContext.ChatMessages.Add(chatMessage);
        await _dbContext.SaveChangesAsync();

        var act = async () => await _sut.ApplyPendingPatchAsync(messageId);

        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*geçerli bir değişiklik yok*");
    }

    [Fact]
    public async Task ApplyPendingPatchAsync_WhenMessageNotFound_ShouldThrowNotFoundException()
    {
        var nonExistentMessageId = Guid.NewGuid();

        var act = async () => await _sut.ApplyPendingPatchAsync(nonExistentMessageId);

        await act.Should().ThrowAsync<NotFoundException>()
            .WithMessage("*Chat mesajı bulunamadı*");
    }
}
