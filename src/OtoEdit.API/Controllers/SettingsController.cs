using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/settings")]
public class SettingsController : ControllerBase
{
    private readonly IAiProviderSettingsService _settingsService;

    public SettingsController(IAiProviderSettingsService settingsService)
    {
        _settingsService = settingsService;
    }

    /// <summary>
    /// Mevcut AI sağlayıcı (Antigravity / OpenRouter) ayarlarını döner.
    /// </summary>
    [HttpGet("ai-provider")]
    [ProducesResponseType(typeof(AiProviderSettingsDto), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAiProviderSettings(CancellationToken cancellationToken)
    {
        var settings = await _settingsService.GetSettingsAsync(cancellationToken);
        return Ok(settings);
    }

    /// <summary>
    /// Aktif AI sağlayıcısını ve API yapılandırmasını günceller.
    /// </summary>
    [HttpPost("ai-provider")]
    [ProducesResponseType(typeof(AiProviderSettingsDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> UpdateAiProviderSettings([FromBody] AiProviderSettingsDto dto, CancellationToken cancellationToken)
    {
        if (dto == null)
        {
            return BadRequest("Ayar parametreleri boş olamaz.");
        }

        var updated = await _settingsService.UpdateSettingsAsync(dto, cancellationToken);
        return Ok(updated);
    }

    /// <summary>
    /// Belirtilen AI sağlayıcısına canlı bağlantı testi yapar.
    /// </summary>
    [HttpPost("ai-provider/test")]
    [ProducesResponseType(typeof(TestConnectionResultDto), StatusCodes.Status200OK)]
    public async Task<IActionResult> TestAiProvider([FromBody] TestProviderRequest request, CancellationToken cancellationToken)
    {
        var result = await _settingsService.TestConnectionAsync(request?.Provider ?? "openrouter", cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// OpenRouter veya Antigravity üzerinden erişilebilir tüm modelleri listeler.
    /// </summary>
    [HttpGet("ai-provider/models")]
    [ProducesResponseType(typeof(List<ModelOptionDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAiModels([FromQuery] string provider = "openrouter", CancellationToken cancellationToken = default)
    {
        var models = await _settingsService.GetAvailableModelsAsync(provider, cancellationToken);
        return Ok(models);
    }
}

public class TestProviderRequest
{
    public string Provider { get; set; } = "openrouter";
}
