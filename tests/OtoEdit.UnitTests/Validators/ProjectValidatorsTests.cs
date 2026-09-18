using FluentAssertions;
using OtoEdit.Business.DTOs.Project;
using OtoEdit.Business.Validators;
using OtoEdit.Data.Enums;
using Xunit;

namespace OtoEdit.UnitTests.Validators;

public class ProjectValidatorsTests
{
    private readonly ProjectCreateValidator _createValidator = new();
    private readonly ProjectUpdateValidator _updateValidator = new();

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ProjectCreateValidator_EmptyName_ShouldHaveValidationError(string? name)
    {
        var dto = new ProjectCreateDto
        {
            Ad = name!,
            VideoFormati = VideoFormati.Dikey_9_16
        };

        var result = _createValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == nameof(ProjectCreateDto.Ad));
    }

    [Fact]
    public void ProjectCreateValidator_NameExceeds200Chars_ShouldHaveValidationError()
    {
        var dto = new ProjectCreateDto
        {
            Ad = new string('A', 201),
            VideoFormati = VideoFormati.Yatay_16_9
        };

        var result = _createValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == nameof(ProjectCreateDto.Ad));
    }

    [Fact]
    public void ProjectCreateValidator_DescriptionExceeds2000Chars_ShouldHaveValidationError()
    {
        var dto = new ProjectCreateDto
        {
            Ad = "Geçerli Proje Adı",
            Aciklama = new string('B', 2001),
            VideoFormati = VideoFormati.Kare_1_1
        };

        var result = _createValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == nameof(ProjectCreateDto.Aciklama));
    }

    [Fact]
    public void ProjectCreateValidator_ValidDto_ShouldPassValidation()
    {
        var dto = new ProjectCreateDto
        {
            Ad = "Harika Video Projesi",
            Aciklama = "YouTube Shorts için hazırlandı.",
            VideoFormati = VideoFormati.Dikey_9_16,
            GestureCommandsEnabled = true,
            AudioEnhancementEnabled = true
        };

        var result = _createValidator.Validate(dto);

        result.IsValid.Should().BeTrue();
        result.Errors.Should().BeEmpty();
    }

    [Fact]
    public void ProjectUpdateValidator_EmptyName_ShouldHaveValidationError()
    {
        var dto = new ProjectUpdateDto
        {
            Ad = "",
            VideoFormati = VideoFormati.Yatay_16_9
        };

        var result = _updateValidator.Validate(dto);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == nameof(ProjectUpdateDto.Ad));
    }

    [Fact]
    public void ProjectUpdateValidator_ValidDto_ShouldPassValidation()
    {
        var dto = new ProjectUpdateDto
        {
            Ad = "Güncellenmiş Proje",
            Aciklama = "Yeni açıklama",
            VideoFormati = VideoFormati.Yatay_16_9
        };

        var result = _updateValidator.Validate(dto);

        result.IsValid.Should().BeTrue();
    }
}
