using System.Net;
using System.Text;
using FluentAssertions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using Moq.Protected;
using OtoEdit.Business.Infrastructure.AI;
using OtoEdit.Business.Interfaces;
using Xunit;

namespace OtoEdit.UnitTests.Services;

public class PexelsServiceTests
{
    private readonly Mock<IFileStorageService> _fileStorageMock = new();
    private readonly Mock<ILogger<PexelsService>> _loggerMock = new();

    private class FakeHttpMessageHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _handler;

        public FakeHttpMessageHandler(Func<HttpRequestMessage, HttpResponseMessage> handler)
        {
            _handler = handler;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            return Task.FromResult(_handler(request));
        }
    }

    [Fact]
    public async Task SearchPhotoUrlAsync_WhenApiKeyMissing_ShouldReturnNull()
    {
        var config = new ConfigurationBuilder().Build();
        var httpClient = new HttpClient(new FakeHttpMessageHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)));
        var sut = new PexelsService(httpClient, _fileStorageMock.Object, config, _loggerMock.Object);

        var result = await sut.SearchPhotoUrlAsync("cat");

        result.Should().BeNull();
    }

    [Fact]
    public async Task SearchPhotoUrlAsync_WhenPhotosFound_ShouldReturnLargeUrl()
    {
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { { "Pexels:ApiKey", "test_key_123" } })
            .Build();

        var jsonResponse = """
        {
            "photos": [
                {
                    "id": 12345,
                    "src": {
                        "large": "https://images.pexels.com/photos/12345/pexels-photo-12345.jpeg",
                        "original": "https://images.pexels.com/photos/12345/original.jpeg"
                    }
                }
            ]
        }
        """;

        var fakeHandler = new FakeHttpMessageHandler(req => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(jsonResponse, Encoding.UTF8, "application/json")
        });

        var httpClient = new HttpClient(fakeHandler);
        var sut = new PexelsService(httpClient, _fileStorageMock.Object, config, _loggerMock.Object);

        var result = await sut.SearchPhotoUrlAsync("cat");

        result.Should().Be("https://images.pexels.com/photos/12345/pexels-photo-12345.jpeg");
    }

    [Fact]
    public async Task SearchAndSaveAssetAsync_WhenSuccessful_ShouldUploadToStorageAndReturnKey()
    {
        var projectId = Guid.NewGuid();
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { { "Pexels:ApiKey", "test_key_123" } })
            .Build();

        var jsonResponse = """
        {
            "photos": [
                {
                    "id": 888,
                    "src": {
                        "large": "https://images.pexels.com/cat.jpg"
                    }
                }
            ]
        }
        """;

        var fakeHandler = new FakeHttpMessageHandler(req =>
        {
            if (req.RequestUri!.ToString().Contains("api.pexels.com"))
            {
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(jsonResponse, Encoding.UTF8, "application/json")
                };
            }

            // Image download response
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new ByteArrayContent(new byte[] { 0xFF, 0xD8, 0xFF, 0xE0 })
            };
        });

        var httpClient = new HttpClient(fakeHandler);
        var sut = new PexelsService(httpClient, _fileStorageMock.Object, config, _loggerMock.Object);

        var result = await sut.SearchAndSaveAssetAsync(projectId, "cute cat");

        result.Should().NotBeNull();
        result.Should().StartWith($"assets/{projectId}/");
        result.Should().EndWith(".jpg");

        _fileStorageMock.Verify(f => f.UploadFileAsync(
            It.Is<string>(k => k.StartsWith($"assets/{projectId}/")),
            It.IsAny<Stream>(),
            "image/jpeg",
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
