using FluentValidation;
using OtoEdit.Business.DTOs.Project;

namespace OtoEdit.Business.Validators;

public class ProjectCreateValidator : AbstractValidator<ProjectCreateDto>
{
    public ProjectCreateValidator()
    {
        RuleFor(x => x.Ad)
            .NotEmpty().WithMessage("Proje adı boş olamaz.")
            .MaximumLength(200).WithMessage("Proje adı en fazla 200 karakter olabilir.");

        RuleFor(x => x.Aciklama)
            .MaximumLength(2000).WithMessage("Proje açıklaması en fazla 2000 karakter olabilir.");
    }
}

public class ProjectUpdateValidator : AbstractValidator<ProjectUpdateDto>
{
    public ProjectUpdateValidator()
    {
        RuleFor(x => x.Ad)
            .NotEmpty().WithMessage("Proje adı boş olamaz.")
            .MaximumLength(200).WithMessage("Proje adı en fazla 200 karakter olabilir.");

        RuleFor(x => x.Aciklama)
            .MaximumLength(2000).WithMessage("Proje açıklaması en fazla 2000 karakter olabilir.");
    }
}
