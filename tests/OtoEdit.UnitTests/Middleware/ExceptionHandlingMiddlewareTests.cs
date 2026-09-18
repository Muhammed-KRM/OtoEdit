using System.IO;
using System.Net;
using System.Text.Json;
using FluentAssertions;
using FluentValidation;
using FluentValidation.Results;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Moq;
using OtoEdit.API.Middleware;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using Xunit;

namespace OtoEdit.UnitTests.Middleware;

public class ExceptionHandlingMiddlewareTests
{
    private readonly Mock<ILogService> _logServiceMock = new();
    private readonly Mock<ILogger<ExceptionHandlingMiddleware>> _loggerMock = new();

    private DefaultHttpContext CreateHttpContext()
    {
        var context = new DefaultHttpContext();
        context.Response.Body = new MemoryStream();
        return context;
    }

    private static async Task<string> ReadResponseBodyAsync(HttpContext context)
    {
        context.Response.Body.Seek(0, SeekOrigin.Begin);
        using var reader = new StreamReader(context.Response.Body);
        return await reader.ReadToEndAsync();
    }

    [Fact]
    public async Task InvokeAsync_WhenNoException_ShouldCallNext()
    {
        var context = CreateHttpContext();
        var nextCalled = false;
        RequestDelegate next = ctx =>
        {
            nextCalled = true;
            return Task.CompletedTask;
        };

        var middleware = new ExceptionHandlingMiddleware(next, _loggerMock.Object);
        await middleware.InvokeAsync(context, _logServiceMock.Object);

        nextCalled.Should().BeTrue();
        context.Response.StatusCode.Should().Be(StatusCodes.Status200OK);
    }

    [Fact]
    public async Task InvokeAsync_WhenNotFoundException_ShouldReturn404()
    {
        var context = CreateHttpContext();
        RequestDelegate next = ctx => throw new NotFoundException("Entity bulunamadı", Guid.NewGuid());

        var middleware = new ExceptionHandlingMiddleware(next, _loggerMock.Object);
        await middleware.InvokeAsync(context, _logServiceMock.Object);

        context.Response.StatusCode.Should().Be((int)HttpStatusCode.NotFound);
        var body = await ReadResponseBodyAsync(context);
        using var doc = JsonDocument.Parse(body);
        doc.RootElement.GetProperty("title").GetString().Should().Be("Kayıt Bulunamadı");

        _logServiceMock.Verify(l => l.LogFunctionErrorAsync(
            "API_UNHANDLED_ERR",
            It.IsAny<Exception>(),
            It.IsAny<object>(),
            It.IsAny<string>(),
            It.IsAny<string>(),
            It.IsAny<string>(),
            It.IsAny<int>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task InvokeAsync_WhenBusinessException_ShouldReturn400()
    {
        var context = CreateHttpContext();
        RequestDelegate next = ctx => throw new BusinessException("İş kuralı ihlali");

        var middleware = new ExceptionHandlingMiddleware(next, _loggerMock.Object);
        await middleware.InvokeAsync(context, _logServiceMock.Object);

        context.Response.StatusCode.Should().Be((int)HttpStatusCode.BadRequest);
        var body = await ReadResponseBodyAsync(context);
        using var doc = JsonDocument.Parse(body);
        doc.RootElement.GetProperty("title").GetString().Should().Be("İş Kuralı İhlali");
    }

    [Fact]
    public async Task InvokeAsync_WhenValidationException_ShouldReturn400WithErrors()
    {
        var context = CreateHttpContext();
        var failures = new List<ValidationFailure>
        {
            new("Ad", "Proje adı zorunludur")
        };
        RequestDelegate next = ctx => throw new ValidationException(failures);

        var middleware = new ExceptionHandlingMiddleware(next, _loggerMock.Object);
        await middleware.InvokeAsync(context, _logServiceMock.Object);

        context.Response.StatusCode.Should().Be((int)HttpStatusCode.BadRequest);
        var body = await ReadResponseBodyAsync(context);
        using var doc = JsonDocument.Parse(body);
        doc.RootElement.GetProperty("title").GetString().Should().Be("Doğrulama Hatası");
        doc.RootElement.GetProperty("errors").GetArrayLength().Should().Be(1);
    }

    [Fact]
    public async Task InvokeAsync_WhenGeneralException_ShouldReturn500()
    {
        var context = CreateHttpContext();
        RequestDelegate next = ctx => throw new InvalidOperationException("Bilinmeyen kritik hata");

        var middleware = new ExceptionHandlingMiddleware(next, _loggerMock.Object);
        await middleware.InvokeAsync(context, _logServiceMock.Object);

        context.Response.StatusCode.Should().Be((int)HttpStatusCode.InternalServerError);
        var body = await ReadResponseBodyAsync(context);
        using var doc = JsonDocument.Parse(body);
        doc.RootElement.GetProperty("title").GetString().Should().Be("Sunucu Hatası");
        doc.RootElement.GetProperty("detail").GetString().Should().Be("Bilinmeyen kritik hata");
    }
}
