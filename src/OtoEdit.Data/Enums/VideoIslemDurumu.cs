namespace OtoEdit.Data.Enums;

/// <summary>
/// Videonun Python Worker analiz pipeline'ındaki anlık durumu.
/// </summary>
public enum VideoIslemDurumu
{
    Bekliyor = 0,
    SesIyilestirmeBasladi = 1,
    SttBasladi = 2,
    SttTamamlandi = 3,
    SessizlikAlgilamaBasladi = 4,
    KomutAlgilamaBasladi = 5,
    YuzTakibiBasladi = 6,
    AnalizTamamlandi = 7,
    Hata = 99
}
