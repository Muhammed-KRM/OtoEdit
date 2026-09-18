using System.Text.Json;
using FluentAssertions;
using OtoEdit.Business.Events;
using OtoEdit.Data.Enums;
using Xunit;

namespace OtoEdit.UnitTests.Events;

public class PipelineEventSerializationTests
{
    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    [Fact]
    public void PipelineStageChangedEvent_DeserializeFromJsonFromPythonWorker()
    {
        var rawJsonFromPython = """
        {
            "projectId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "videoId": "11223344-5566-7788-99aa-bbccddeeff00",
            "asama": "SesIyilestirme",
            "yuzde": 15,
            "mesaj": "Gürültü ve yankı temizleniyor..."
        }
        """;

        var evt = JsonSerializer.Deserialize<PipelineStageChangedEvent>(rawJsonFromPython, _jsonOptions);

        evt.Should().NotBeNull();
        evt!.ProjectId.Should().Be(Guid.Parse("a1b2c3d4-e5f6-7890-abcd-ef1234567890"));
        evt.VideoId.Should().Be(Guid.Parse("11223344-5566-7788-99aa-bbccddeeff00"));
        evt.Asama.Should().Be(PipelineAsamasi.SesIyilestirme);
        evt.Yuzde.Should().Be(15);
        evt.Mesaj.Should().Be("Gürültü ve yankı temizleniyor...");
    }

    [Fact]
    public void VideoUploadedEvent_SerializationMatchesContract()
    {
        var evt = new VideoUploadedEvent
        {
            ProjectId = Guid.NewGuid(),
            VideoId = Guid.NewGuid(),
            DosyaYolu = "videos/proj1/raw.mp4",
            VideoFormati = 1,
            GestureCommandsEnabled = true,
            AudioEnhancementEnabled = true
        };

        var json = JsonSerializer.Serialize(evt, _jsonOptions);
        json.Should().Contain("\"videoFormati\":1");
        json.Should().Contain("\"gestureCommandsEnabled\":true");
        json.Should().Contain("\"dosyaYolu\":\"videos/proj1/raw.mp4\"");

        var deserialized = JsonSerializer.Deserialize<VideoUploadedEvent>(json, _jsonOptions);
        deserialized.Should().BeEquivalentTo(evt);
    }

    [Fact]
    public void AnalysisCompletedEvent_CanParseComplexEdlJson()
    {
        var rawJson = """
        {
            "projectId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "videoId": "11223344-5566-7788-99aa-bbccddeeff00",
            "edlJson": {
                "projectId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "settings": { "targetFormat": "9:16" },
                "cuts": [{"id": "cut_1", "start": 0.0, "end": 2.5, "reason": "silence"}],
                "overlays": [{"id": "text_1", "type": "text", "content": "Abone Ol!"}]
            }
        }
        """;

        var evt = JsonSerializer.Deserialize<AnalysisCompletedEvent>(rawJson, _jsonOptions);

        evt.Should().NotBeNull();
        evt!.EdlJson.Should().NotBeNull();
        evt.EdlJson.RootElement.GetProperty("settings").GetProperty("targetFormat").GetString().Should().Be("9:16");
        evt.EdlJson.RootElement.GetProperty("cuts").GetArrayLength().Should().Be(1);
    }

    [Fact]
    public void PipelineErrorEvent_DeserializeCorrectly()
    {
        var rawJson = """
        {
            "projectId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "videoId": "11223344-5566-7788-99aa-bbccddeeff00",
            "asama": "Analiz",
            "hataMesaji": "MinIO video indirilemedi"
        }
        """;

        var evt = JsonSerializer.Deserialize<PipelineErrorEvent>(rawJson, _jsonOptions);

        evt.Should().NotBeNull();
        evt!.HataMesaji.Should().Be("MinIO video indirilemedi");
    }
}
