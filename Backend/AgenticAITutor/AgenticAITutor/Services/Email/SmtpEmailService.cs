using MailKit.Net.Smtp;
using MailKit.Security;
using MimeKit;

namespace AgenticAITutor.Services
{
    public class SmtpEmailService : IEmailService
    {
        private readonly IConfiguration configuration;
        private readonly ILogger<SmtpEmailService> logger;

        public SmtpEmailService(
            IConfiguration configuration,
            ILogger<SmtpEmailService> logger)
        {
            this.configuration = configuration;
            this.logger = logger;
        }

        public async Task SendPasswordResetEmailAsync(string toEmail, string resetToken)
        {
            var emailConfiguration = configuration.GetSection("EmailConfiguration");
            var smtpServer = GetRequiredSetting(emailConfiguration, "SmtpServer");
            var smtpPort = emailConfiguration.GetValue<int>("SmtpPort");
            var senderName = GetRequiredSetting(emailConfiguration, "SenderName");
            var senderEmail = GetRequiredSetting(emailConfiguration, "SenderEmail");
            var username = GetRequiredSetting(emailConfiguration, "Username");
            var password = GetRequiredSetting(emailConfiguration, "Password");

            if (smtpPort <= 0)
                throw new InvalidOperationException("EmailConfiguration:SmtpPort is invalid.");

            var message = new MimeMessage();
            message.From.Add(new MailboxAddress(senderName, senderEmail));
            message.To.Add(MailboxAddress.Parse(toEmail));
            message.Subject = "Reset your GenT password";
            message.Body = new BodyBuilder
            {
                HtmlBody = BuildPasswordResetEmail(resetToken)
            }.ToMessageBody();

            try
            {
                using var smtpClient = new SmtpClient();
                await smtpClient.ConnectAsync(
                    smtpServer,
                    smtpPort,
                    SecureSocketOptions.StartTls);
                await smtpClient.AuthenticateAsync(username, password);
                await smtpClient.SendAsync(message);
                await smtpClient.DisconnectAsync(true);

                logger.LogInformation("Password reset email sent to {Email}.", toEmail);
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Failed to send password reset email to {Email}.", toEmail);
                throw;
            }
        }

        private static string GetRequiredSetting(
            IConfigurationSection section,
            string key)
        {
            return section[key]
                ?? throw new InvalidOperationException(
                    $"EmailConfiguration:{key} is not configured.");
        }

        private static string BuildPasswordResetEmail(string resetToken)
        {
            var encodedToken = System.Net.WebUtility.HtmlEncode(resetToken);

            return $"""
                <!DOCTYPE html>
                <html lang="en">
                <body style="font-family:Arial,sans-serif;color:#202124;line-height:1.5">
                    <h2>Reset your GenT password</h2>
                    <p>Use the following token to reset your password:</p>
                    <p style="font-size:18px;font-weight:bold;word-break:break-all">
                        {encodedToken}
                    </p>
                    <p>This token expires in 15 minutes.</p>
                    <p>If you did not request a password reset, ignore this email.</p>
                </body>
                </html>
                """;
        }
    }
}
