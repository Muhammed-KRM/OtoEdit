using System.IO;
using System.Text;
using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using OtoEdit.API.Middleware;
using Xunit;

namespace OtoEdit.UnitTests.Middleware;

public class ApiKeyAuthMiddlewareTests
{
    private readonly IConfiguration _configuration;
    private const string ValidApiKey = "SECRET_KEY_TEST_123";

    public ApiKeyAuthMiddlewareTests()
    {
        var inMemorySettings = new Dictionary<string, string?>
        {
            { "ApiKey", ValidApiKey }
        };

        _configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(inMemorySettings)
            .Build();
    }

    [Fact]
    public async Task InvokeAsync_OptionsRequest_ShouldBypassAuth()
    {
        var nextCalled = false;
        RequestDelegate next = (ctx) =>
        {
            nextCalled = true;
            return Task.CompletedTask;
        };

        var middleware = new ApiKeyAuthMiddleware(next);
        var context = new DefaultHttpContext();
        context.Request.Method = "OPTIONS";
        context.Request.Path = "/api/projects";

        await middleware.InvokeAsync(context, _configuration);

        nextCalled.Should().BeTrue();
        context.Response.StatusCode.Should().Be(StatusCodes.Status200OK);
    }

    [Theory]
    [InlineData("/health")]
    [InlineData("/swagger")]
    [InlineData("/swagger/v1/swagger.json")]
    [InlineData("/pipeline-hub")]
    public async Task InvokeAsync_WhitelistedPaths_ShouldBypassAuth(string path)
    {
        var nextCalled = false;
        RequestDelegate next = (ctx) =>
        {
            nextCalled = true;
            return Task.CompletedTask;
        };

        var middleware = new ApiKeyAuthMiddleware(next);
        var context = new DefaultHttpContext();
        context.Request.Method = "GET";
        context.Request.Path = path;

        await middleware.InvokeAsync(context, _configuration);

        nextCalled.Should().BeTrue();
    }

    [Fact]
    public async Task InvokeAsync_MissingApiKey_ShouldReturn401Unauthorized()
    {
        var nextCalled = false;
        RequestDelegate next = (ctx) =>
        {
            nextCalled = true;
            return Task.CompletedTask;
        };

        var middleware = new ApiKeyAuthMiddleware(next);
        var context = new DefaultHttpContext();
        context.Response.Body = new MemoryStream();
        context.Request.Method = "GET";
        context.Request.Path = "/api/projects";

        await middleware.InvokeAsync(context, _configuration);

        nextCalled.Should().BeFalse();
        context.Response.StatusCode.Should().Be(StatusCodes.Status401Unauthorized);

        context.Response.Body.Seek(0, SeekOrigin.Begin);
        using var reader = new StreamReader(context.Response.Body, Encoding.UTF8);
        var responseText = await reader.ReadToEndAsync();
        responseText.Should().Contain("API Key zorunludur");
    }

    [Fact]
    public async Task InvokeAsync_InvalidApiKey_ShouldReturn401Unauthorized()
    {
        var nextCalled = false;
        RequestDelegate next = (ctx) =>
        {
            nextCalled = true;
            return Task.CompletedTask;
        };

        var middleware = new ApiKeyAuthMiddleware(next);
        var context = new DefaultHttpContext();
        context.Response.Body = new MemoryStream();
        context.Request.Method = "GET";
        context.Request.Path = "/api/projects";
        context.Request.Headers["X-API-Key"] = "WRONG_KEY";

        await middleware.InvokeAsync(context, _configuration);

        nextCalled.Should().BeFalse();
        context.Response.StatusCode.Should().Be(StatusCodes.Status401Unauthorized);

        context.Response.Body.Seek(0, SeekOrigin.Begin);
        using var reader = new StreamReader(context.Response.Body, Encoding.UTF8);
        var responseText = await reader.ReadToEndAsync();
        responseText.Should().Contain("Geçersiz API Key");
    }

    [Fact]
    public async Task InvokeAsync_ValidApiKeyInHeader_ShouldCallNext()
    {
        var nextCalled = false;
        RequestDelegate next = (ctx) =>
        {
            nextCalled = true;
            ctx.Response.StatusCode = StatusCodes.Status200OK;
            return Task.CompletedTask;
        };

        var middleware = new ApiKeyAuthMiddleware(next);
        var context = new DefaultHttpContext();
        context.Request.Method = "GET";
        context.Request.Path = "/api/projects";
        context.Request.Headers["X-API-Key"] = ValidApiKey;

        await middleware.InvokeAsync(context, _configuration);

        nextCalled.Should().BeTrue();
        context.Response.StatusCode.Should().Be(StatusCodes.Status200OK);
    }
}
