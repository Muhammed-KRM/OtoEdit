namespace OtoEdit.Data.Enums;

/// <summary>
/// Projenin genel yaşam döngüsü durumu.
/// </summary>
public enum ProjectDurumu
{
    /// <summary>
    /// Proje oluşturuldu fakat video henüz yüklenmedi.
    /// </summary>
    Taslak = 0,

    /// <summary>
    /// Ham video başarıyla yüklendi, analiz kuyruğuna gönderildi.
    /// </summary>
    VideoYuklendi = 1,

    /// <summary>
    /// Python Worker analiz pipeline'ını çalıştırıyor.
    /// </summary>
    AnalizEdiliyor = 2,

    /// <summary>
    /// Analiz tamamlandı, ilk taslak EDL hazır ve kullanıcı incelemesine açık.
    /// </summary>
    AnalizTamamlandi = 3,

    /// <summary>
    /// FFmpeg nihai render işlemi devam ediyor.
    /// </summary>
    RenderEdiliyor = 4,

    /// <summary>
    /// Render başarıyla tamamlandı, video indirmeye hazır.
    /// </summary>
    Tamamlandi = 5,

    /// <summary>
    /// Herhangi bir aşamada kritik hata oluştu.
    /// </summary>
    Hata = 99
}
