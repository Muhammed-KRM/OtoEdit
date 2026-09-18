using System.Text.Json.Serialization;

namespace OtoEdit.Data.Enums;

/// <summary>
/// Pipeline aşamaları enum'ı.
/// </summary>
[JsonConverter(typeof(JsonStringEnumConverter))]
public enum PipelineAsamasi
{
    SesIyilestirme = 0,
    Stt = 1,
    SessizlikAlgilama = 2,
    KomutAlgilama = 3,
    YuzTakibi = 4,
    Repurposing = 5,
    OneriOlusturma = 6,
    EdlOlusturma = 7,
    Render = 8,
    Tamamlandi = 9
}
