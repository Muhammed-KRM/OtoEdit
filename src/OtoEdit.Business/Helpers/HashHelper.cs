using System.Security.Cryptography;
using System.Text;

namespace OtoEdit.Business.Helpers;

/// <summary>
/// Cache anahtarları ve dosya/içerik özetleri (SHA256) oluşturma yardımcısı.
/// </summary>
public static class HashHelper
{
    public static string ComputeSha256Hash(string rawData)
    {
        if (string.IsNullOrEmpty(rawData))
            return string.Empty;

        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(rawData));
        var builder = new StringBuilder(bytes.Length * 2);
        foreach (var b in bytes)
        {
            builder.Append(b.ToString("x2"));
        }
        return builder.ToString();
    }
}
