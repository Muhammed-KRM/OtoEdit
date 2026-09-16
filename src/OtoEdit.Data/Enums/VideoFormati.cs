namespace OtoEdit.Data.Enums;

/// <summary>
/// Çıktı video en-boy oranı formatı.
/// </summary>
public enum VideoFormati
{
    /// <summary>
    /// 16:9 — YouTube, TV ve masaüstü standart yatay video
    /// </summary>
    Yatay_16_9 = 0,

    /// <summary>
    /// 9:16 — Instagram Reels, YouTube Shorts, TikTok dikey video
    /// </summary>
    Dikey_9_16 = 1,

    /// <summary>
    /// 1:1 — Instagram Post, kare video
    /// </summary>
    Kare_1_1 = 2
}
