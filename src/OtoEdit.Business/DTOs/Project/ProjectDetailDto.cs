using OtoEdit.Business.DTOs.Render;
using OtoEdit.Business.DTOs.Video;
using OtoEdit.Data.Enums;

namespace OtoEdit.Business.DTOs.Project;

public record ProjectDetailDto
{
    public Guid Id { get; init; }
    public string Ad { get; init; } = string.Empty;
    public string? Aciklama { get; init; }
    public VideoFormati VideoFormati { get; init; }
    public Guid? TemplateId { get; init; }
    public string? TemplateAd { get; init; }
    public bool GestureCommandsEnabled { get; init; }
    public bool AudioEnhancementEnabled { get; init; }
    public ProjectDurumu Durum { get; init; }
    public DateTime OlusturmaTarihi { get; init; }
    public DateTime? GuncellemeTarihi { get; init; }
    public VideoDetailDto? Video { get; init; }
    public int? EdlVersiyon { get; init; }
    public int ChatMesajSayisi { get; init; }
    public RenderStatusDto? SonRender { get; init; }
}
