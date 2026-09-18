using FluentAssertions;
using Microsoft.AspNetCore.Http;
using Moq;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.DTOs.Video;
using OtoEdit.Business.Validators;
using Xunit;

namespace OtoEdit.UnitTests.Validators;

public class OtherValidatorsTests
{
    private readonly VideoUploadValidator _videoUploadValidator = new();
    private readonly ChatMessageValidator _chatMessageValidator = new();

    [Fact]
    public void VideoUploadValidator_NullFile_ShouldHaveValidationError()
    {
        var dto = new VideoUploadDto { File = null! };
        var result = _videoUploadValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == nameof(VideoUploadDto.File));
    }

    [Fact]
    public void VideoUploadValidator_EmptyFile_ShouldHaveValidationError()
    {
        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(0);
        fileMock.Setup(f => f.FileName).Returns("test.mp4");

        var dto = new VideoUploadDto { File = fileMock.Object };
        var result = _videoUploadValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
    }

    [Fact]
    public void VideoUploadValidator_UnsupportedExtension_ShouldHaveValidationError()
    {
        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(1024 * 1024); // 1 MB
        fileMock.Setup(f => f.FileName).Returns("malicious_script.exe");

        var dto = new VideoUploadDto { File = fileMock.Object };
        var result = _videoUploadValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.ErrorMessage.Contains("Desteklenmeyen dosya formatı"));
    }

    [Fact]
    public void VideoUploadValidator_ValidVideo_ShouldPass()
    {
        var fileMock = new Mock<IFormFile>();
        fileMock.Setup(f => f.Length).Returns(50 * 1024 * 1024); // 50 MB
        fileMock.Setup(f => f.FileName).Returns("my_footage.mp4");

        var dto = new VideoUploadDto { File = fileMock.Object };
        var result = _videoUploadValidator.Validate(dto);

        result.IsValid.Should().BeTrue();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ChatMessageValidator_EmptyMessage_ShouldHaveValidationError(string? message)
    {
        var dto = new ChatMessageDto { Mesaj = message! };
        var result = _chatMessageValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == nameof(ChatMessageDto.Mesaj));
    }

    [Fact]
    public void ChatMessageValidator_Exceeds4000Chars_ShouldHaveValidationError()
    {
        var dto = new ChatMessageDto { Mesaj = new string('X', 4001) };
        var result = _chatMessageValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
    }

    [Fact]
    public void ChatMessageValidator_ValidMessage_ShouldPass()
    {
        var dto = new ChatMessageDto { Mesaj = "Videodaki 'eeee' dediğim yerleri keser misin?" };
        var result = _chatMessageValidator.Validate(dto);

        result.IsValid.Should().BeTrue();
    }
}
