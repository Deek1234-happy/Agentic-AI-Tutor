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

        private static string BuildPasswordResetEmail(string otp)
        {
            return $"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                  <meta charset="UTF-8" />
                  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                  <title>Reset your GenT password</title>
                </head>
                <body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
                  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f8;padding:40px 0;">
                    <tr>
                      <td align="center">
                        <table width="480" cellpadding="0" cellspacing="0"
                               style="background-color:#ffffff;border-radius:12px;overflow:hidden;
                                      box-shadow:0 4px 20px rgba(0,0,0,0.08);">

                          <!-- Header -->
                          <tr>
                            <td align="center"
                                style="background:linear-gradient(135deg,#4f46e5,#7c3aed);
                                       padding:32px 40px;">
                              <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;
                                         letter-spacing:-0.5px;">
                                🔑 Password Reset
                              </h1>
                            </td>
                          </tr>

                          <!-- Body -->
                          <tr>
                            <td style="padding:40px 48px 32px;">
                              <p style="margin:0 0 16px;color:#374151;font-size:16px;line-height:1.6;">
                                Hi there,
                              </p>
                              <p style="margin:0 0 28px;color:#374151;font-size:16px;line-height:1.6;">
                                We received a request to reset your <strong>GenT</strong> account password.
                                Enter the 6-digit code below to continue:
                              </p>

                              <!-- OTP box -->
                              <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                  <td align="center"
                                      style="background-color:#f0edff;border:2px dashed #7c3aed;
                                             border-radius:10px;padding:24px 16px;">
                                    <span style="font-size:42px;font-weight:800;letter-spacing:12px;
                                                 color:#4f46e5;font-family:'Courier New',Courier,monospace;">
                                      {otp}
                                    </span>
                                  </td>
                                </tr>
                              </table>

                              <p style="margin:24px 0 0;color:#6b7280;font-size:14px;line-height:1.6;
                                         text-align:center;">
                                ⏳ This code expires in <strong>15 minutes</strong>.
                              </p>

                              <hr style="border:none;border-top:1px solid #e5e7eb;margin:32px 0;" />

                              <p style="margin:0;color:#9ca3af;font-size:13px;line-height:1.6;">
                                If you did not request a password reset, you can safely ignore this
                                email — your account will not be affected.
                              </p>
                            </td>
                          </tr>

                          <!-- Footer -->
                          <tr>
                            <td align="center"
                                style="background-color:#f9fafb;padding:20px 40px;
                                       border-top:1px solid #e5e7eb;">
                              <p style="margin:0;color:#9ca3af;font-size:12px;">
                                © {DateTime.UtcNow.Year} GenT · All rights reserved.
                              </p>
                            </td>
                          </tr>

                        </table>
                      </td>
                    </tr>
                  </table>
                </body>
                </html>
                """;
        }
    }
}

