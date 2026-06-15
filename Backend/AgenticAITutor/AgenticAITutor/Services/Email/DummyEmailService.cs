namespace AgenticAITutor.Services
{
    public class DummyEmailService : IEmailService
    {
        private readonly ILogger<DummyEmailService> logger;

        public DummyEmailService(ILogger<DummyEmailService> logger)
        {
            this.logger = logger;
        }

        public Task SendPasswordResetEmailAsync(string toEmail, string resetToken)
        {
            logger.LogInformation(
                "Dummy password reset email sent to {Email}. Reset token: {ResetToken}",
                toEmail,
                resetToken);

            return Task.CompletedTask;
        }
    }
}
