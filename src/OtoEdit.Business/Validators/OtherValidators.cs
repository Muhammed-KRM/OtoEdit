using FluentValidation;
using Microsoft.AspNetCore.Http;
using OtoEdit.Business.DTOs.Chat;
using OtoEdit.Business.DTOs.Video;

namespace OtoEdit.Business.Validators;

public class VideoUploadValidator : AbstractValidator<VideoUploadDto>
{
    private static readonly string[] AllowedExtensions = [".mp4", ".mkv", ".avi", ".mov", ".webm"];
    private const long MaxFileSizeInBytes = 2147483648; // 2 GB

    public VideoUploadValidator()
    {
        RuleFor(x => x.File)
            .NotNull().WithMessage("Video dosyası seçilmelidir.")
            .Must(file => file != null && file.Length > 0).WithMessage("Yüklenen dosya boş olamaz.")
            .Must(file => file != null && file.Length <= MaxFileSizeInBytes)
                .WithMessage("Dosya boyutu en fazla 2GB olabilir.")
            .Must(file => file != null && AllowedExtensions.Contains(Path.GetExtension(file.FileName).ToLowerInvariant()))
                .WithMessage("Desteklenmeyen dosya formatı. İzin verilen uzantılar: .mp4, .mkv, .avi, .mov, .webm");
    }
}

public class ChatMessageValidator : AbstractValidator<ChatMessageDto>
{
    public ChatMessageValidator()
    {
        RuleFor(x => x.Mesaj)
            .NotEmpty().WithMessage("Mesaj boş olamaz.")
            .MaximumLength(4000).WithMessage("Mesaj en fazla 4000 karakter olabilir.");
    }
}
