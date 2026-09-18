using FluentAssertions;
using OtoEdit.Business.Helpers;
using Xunit;

namespace OtoEdit.UnitTests.Helpers;

public class SensitiveDataMaskerTests
{
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Mask_NullOrEmpty_ReturnsOriginal(string? input)
    {
        var result = SensitiveDataMasker.Mask(input);
        result.Should().Be(input);
    }

    [Fact]
    public void Mask_PasswordInJson_MasksValue()
    {
        var json = "{\"username\": \"admin\", \"password\": \"SuperSecret123!\"}";
        var result = SensitiveDataMasker.Mask(json);

        result.Should().NotContain("SuperSecret123!");
        result.Should().Contain("\"password\": \"***\"");
    }

    [Fact]
    public void Mask_ApiKeyAndTokenInJson_MasksValues()
    {
        var json = "{\"apiKey\": \"KEY-999-XYZ\", \"token\": \"eyJhbGciOi...\"}";
        var result = SensitiveDataMasker.Mask(json);

        result.Should().NotContain("KEY-999-XYZ");
        result.Should().NotContain("eyJhbGciOi...");
        result.Should().Contain("\"apiKey\": \"***\"");
        result.Should().Contain("\"token\": \"***\"");
    }

    [Fact]
    public void Mask_EmailAddresses_MasksEmail()
    {
        var text = "User contact email is john.doe@example.com for notifications.";
        var result = SensitiveDataMasker.Mask(text);

        result.Should().NotContain("john.doe@example.com");
        result.Should().Contain("***@***.***");
    }

    [Fact]
    public void MaskJson_DelegatesToMask()
    {
        var json = "{\"secret\": \"classified_data\"}";
        var result = SensitiveDataMasker.MaskJson(json);

        result.Should().NotContain("classified_data");
        result.Should().Contain("\"secret\": \"***\"");
    }
}
