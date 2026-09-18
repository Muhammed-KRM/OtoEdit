using Microsoft.EntityFrameworkCore;
using OtoEdit.Business.DTOs.Template;
using OtoEdit.Business.Exceptions;
using OtoEdit.Business.Interfaces;
using OtoEdit.Data.Context;

namespace OtoEdit.Business.Services;

/// <summary>
/// Video şablonları iş mantığı implementasyonu.
/// </summary>
public class TemplateManager : ITemplateService
{
    private readonly AppDbContext _context;

    public TemplateManager(AppDbContext context)
    {
        _context = context;
    }

    public async Task<IEnumerable<TemplateDto>> GetAllAsync(CancellationToken cancellationToken = default)
    {
        var templates = await _context.Templates
            .Where(t => t.AktifMi)
            .AsNoTracking()
            .ToListAsync(cancellationToken);

        return templates.Select(t => new TemplateDto
        {
            Id = t.Id,
            Ad = t.Ad,
            Tanim = t.Tanim,
            VideoFormati = t.VideoFormati,
            LogoYolu = t.LogoYolu,
            LogoPozisyonu = t.LogoPozisyonu,
            KonusmaciAdGoster = t.KonusmaciAdGoster,
            AltyaziStili = t.AltyaziStili,
            AltyaziFont = t.AltyaziFont,
            AltyaziRenk = t.AltyaziRenk,
            AktifMi = t.AktifMi
        });
    }

    public async Task<TemplateDto> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var t = await _context.Templates
            .AsNoTracking()
            .FirstOrDefaultAsync(x => x.Id == id, cancellationToken);

        if (t == null)
        {
            throw new NotFoundException("Şablon bulunamadı", id);
        }

        return new TemplateDto
        {
            Id = t.Id,
            Ad = t.Ad,
            Tanim = t.Tanim,
            VideoFormati = t.VideoFormati,
            LogoYolu = t.LogoYolu,
            LogoPozisyonu = t.LogoPozisyonu,
            KonusmaciAdGoster = t.KonusmaciAdGoster,
            AltyaziStili = t.AltyaziStili,
            AltyaziFont = t.AltyaziFont,
            AltyaziRenk = t.AltyaziRenk,
            AktifMi = t.AktifMi
        };
    }
}
