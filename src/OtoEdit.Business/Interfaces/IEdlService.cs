using System.Text.Json;
using OtoEdit.Business.DTOs.Edl;
using OtoEdit.Data.Entities;

namespace OtoEdit.Business.Interfaces;

public interface IEdlService
{
    Task<EdlDto> GetEdlAsync(Guid projectId, CancellationToken cancellationToken = default);
    Task<EdlPatchResponseDto> PatchEdlAsync(Guid projectId, JsonElement patch, CancellationToken cancellationToken = default);
    Task<EditDecisionList> CreateOrUpdateAsync(Guid projectId, JsonDocument edlJson, CancellationToken cancellationToken = default);
}
