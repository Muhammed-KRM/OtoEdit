using FluentAssertions;
using OtoEdit.Business.Helpers;
using Xunit;

namespace OtoEdit.UnitTests.Helpers;

public class HashHelperTests
{
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void ComputeSha256Hash_NullOrEmpty_ReturnsEmptyString(string? input)
    {
        var result = HashHelper.ComputeSha256Hash(input!);
        result.Should().BeEmpty();
    }

    [Fact]
    public void ComputeSha256Hash_ValidString_Returns64CharHex()
    {
        var input = "OtoEdit Video Processing";
        var result = HashHelper.ComputeSha256Hash(input);

        result.Should().NotBeNullOrEmpty();
        result.Length.Should().Be(64);
        result.Should().MatchRegex("^[a-f0-9]{64}$");
    }

    [Fact]
    public void ComputeSha256Hash_SameInput_ReturnsIdenticalHash()
    {
        var input = "cache:project:123";
        var hash1 = HashHelper.ComputeSha256Hash(input);
        var hash2 = HashHelper.ComputeSha256Hash(input);

        hash1.Should().Be(hash2);
    }

    [Fact]
    public void ComputeSha256Hash_DifferentInput_ReturnsDifferentHash()
    {
        var hash1 = HashHelper.ComputeSha256Hash("video_1");
        var hash2 = HashHelper.ComputeSha256Hash("video_2");

        hash1.Should().NotBe(hash2);
    }
}
