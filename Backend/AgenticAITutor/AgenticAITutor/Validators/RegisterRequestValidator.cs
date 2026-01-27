using AgenticAITutor.Models.DTOs.Auth;
using FluentValidation;

namespace AgenticAITutor.Validators
{
    public class RegisterRequestValidator:AbstractValidator<RegisterRequest>
    {
        public RegisterRequestValidator()
        {
            RuleFor(x => x.FirstName)
                .NotEmpty().WithMessage("First Name Is Required")
                .Length(3, 50).WithMessage("Fisrt Name Must Be Between 3 and 50 Characters");

            RuleFor(x => x.LastName)
                .NotEmpty().WithMessage("Last Name Is Required")
                .Length(3, 50).WithMessage("Last Name Must Be Between 3 and 50 Characters");

            RuleFor(x => x.Email)
                .NotEmpty().WithMessage("Email Is Required")
                .EmailAddress().WithMessage("Invalid Email Format");

            RuleFor(x => x.Password)
                .NotEmpty().WithMessage("Password Is Required")
                .MinimumLength(8).WithMessage("Password Must Be at least 8 Characters ")
                .Matches("[A-Z]").WithMessage("Password Must Contain at least One Uppercase Letter")
                .Matches("[a-z]").WithMessage("Password Must Contain at least One Lowercase Letter")
                .Matches("[0-9]").WithMessage("Password must contain at least one digit");

        }
    }
}
