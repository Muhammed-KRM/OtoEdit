using Microsoft.AspNetCore.Mvc;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.Interfaces;

namespace OtoEdit.API.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/chat")]
public class ChatController : ControllerBase
{
    private readonly IChatService _chatService;

    public ChatController(IChatService chatService)
    {
        _chatService = chatService;
    }

    /// <summary>
    /// AI asistana video kurgu komutu veya mesajı gönderir.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(ChatResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> SendMessage(Guid projectId, [FromBody] ChatMessageDto dto, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(dto.Mesaj))
        {
            return BadRequest("Mesaj boş olamaz.");
        }

        var response = await _chatService.SendMessageAsync(projectId, dto.Mesaj, cancellationToken);
        return Ok(response);
    }

    /// <summary>
    /// Projeye ait sohbet geçmişini getirir.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<IActionResult> GetHistory(Guid projectId, CancellationToken cancellationToken)
    {
        var history = await _chatService.GetHistoryAsync(projectId, cancellationToken);
        return Ok(history);
    }

    /// <summary>
    /// AI'ın önerdiği ve onay bekleyen (pending) değişiklikleri EDL'ye uygular (HitL).
    /// </summary>
    [HttpPost("{messageId:guid}/apply")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> ApplyPendingPatch(Guid projectId, Guid messageId, CancellationToken cancellationToken)
    {
        var result = await _chatService.ApplyPendingPatchAsync(messageId, cancellationToken);
        return Ok(result);
    }
}
