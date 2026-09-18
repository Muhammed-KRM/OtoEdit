using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.DTOs.Template;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class TemplatesController : ControllerBase
{
    private readonly ITemplateService _templateService;

    public TemplatesController(ITemplateService templateService)
    {
        _templateService = templateService;
    }

    /// <summary>
    /// Sistemde tanımlı tüm video şablonlarını (Yatay, Reels, Kare vb.) listeler.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<TemplateDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAll(CancellationToken cancellationToken)
    {
        var templates = await _templateService.GetAllAsync(cancellationToken);
        return Ok(templates);
    }

    /// <summary>
    /// Belirtilen şablonun detaylarını getirir.
    /// </summary>
    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(TemplateDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(Guid id, CancellationToken cancellationToken)
    {
        var template = await _templateService.GetByIdAsync(id, cancellationToken);
        return Ok(template);
    }
}
