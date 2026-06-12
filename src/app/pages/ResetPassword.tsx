import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { resetPassword } from "../../services/authService";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "../components/ui/input-otp";
import { Label } from "../components/ui/label";

type ResetLocationState = {
  email?: string;
};

export default function ResetPassword() {
  const navigate = useNavigate();
  const location = useLocation();
  const initialEmail = (location.state as ResetLocationState | null)?.email ?? "";

  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState(initialEmail);
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canVerify = useMemo(() => email.trim().length > 0 && /^\d{6}$/.test(otp), [email, otp]);
  const passwordRules = useMemo(() => [
    { label: "At least 8 characters", valid: newPassword.length >= 8 },
    { label: "One uppercase letter", valid: /[A-Z]/.test(newPassword) },
    { label: "One lowercase letter", valid: /[a-z]/.test(newPassword) },
    { label: "One number", valid: /\d/.test(newPassword) },
  ], [newPassword]);
  const isPasswordValid = passwordRules.every((rule) => rule.valid);

  const handleVerify = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Email is required. Please request a reset code again.");
      return;
    }

    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the 6-digit code sent to your email.");
      return;
    }

    setStep(2);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!newPassword) {
      setError("Enter a new password.");
      return;
    }

    if (!isPasswordValid) {
      setError("Your password does not meet the requirements below.");
      return;
    }

    if (!confirmPassword) {
      setError("Confirm your new password.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const message = await resetPassword({
        email: email.trim(),
        otp,
        newPassword,
        confirmNewPassword: confirmPassword,
      });
      toast.success(message || "Password reset successfully. Please sign in.");
      navigate("/login");
    } catch (err: unknown) {
      const rawMessage = err instanceof Error ? err.message : "";
      const message = getFriendlyResetError(rawMessage);
      setError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 px-4 py-10 flex items-center justify-center">
      <Card className="w-full max-w-md border-2 shadow-xl">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary">
            {step === 1 ? (
              <ShieldCheck className="h-7 w-7 text-primary-foreground" />
            ) : (
              <CheckCircle2 className="h-7 w-7 text-primary-foreground" />
            )}
          </div>
          <CardTitle className="text-2xl">Reset Password</CardTitle>
          <CardDescription>
            {step === 1 ? "Verify the code sent to your email." : "Create a new password for your account."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-6 grid grid-cols-2 gap-2">
            <div className={`h-2 rounded-full ${step >= 1 ? "bg-primary" : "bg-muted"}`} />
            <div className={`h-2 rounded-full ${step >= 2 ? "bg-primary" : "bg-muted"}`} />
          </div>

          {step === 1 ? (
            <form onSubmit={handleVerify} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="reset-email">Email</Label>
                <Input
                  id="reset-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  readOnly={Boolean(initialEmail)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="reset-otp">Verification Code</Label>
                <InputOTP id="reset-otp" maxLength={6} value={otp} onChange={setOtp} containerClassName="justify-center">
                  <InputOTPGroup>
                    {Array.from({ length: 6 }).map((_, index) => (
                      <InputOTPSlot key={index} index={index} className="h-11 w-11 text-base" />
                    ))}
                  </InputOTPGroup>
                </InputOTP>
              </div>

              {error && (
                <p role="alert" className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              )}

              <Button type="submit" className="w-full" size="lg" disabled={!canVerify}>
                Verify
              </Button>
            </form>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="new-password">New Password</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="Enter a new password"
                  autoComplete="new-password"
                  disabled={isSubmitting}
                  required
                />
                <div className="grid gap-1 rounded-lg border bg-muted/30 p-3 text-xs">
                  {passwordRules.map((rule) => (
                    <div key={rule.label} className={rule.valid ? "text-green-600" : "text-muted-foreground"}>
                      {rule.valid ? "OK" : "-"} {rule.label}
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-new-password">Confirm Password</Label>
                <Input
                  id="confirm-new-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="Confirm your new password"
                  autoComplete="new-password"
                  disabled={isSubmitting}
                  required
                />
              </div>

              {error && (
                <p role="alert" className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              )}

              <div className="flex flex-col gap-2 sm:flex-row">
                <Button type="button" variant="outline" className="flex-1" onClick={() => setStep(1)} disabled={isSubmitting}>
                  Back
                </Button>
                <Button type="submit" className="flex-1" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Resetting
                    </>
                  ) : (
                    "Reset Password"
                  )}
                </Button>
              </div>
            </form>
          )}

          <Button asChild variant="ghost" className="mt-4 w-full">
            <Link to="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to sign in
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function getFriendlyResetError(message: string): string {
  const normalized = message.toLowerCase();

  if (
    normalized.includes("password") ||
    normalized.includes("uppercase") ||
    normalized.includes("lowercase") ||
    normalized.includes("digit") ||
    normalized.includes("non alphanumeric") ||
    normalized.includes("special")
  ) {
    return "Your password does not meet the requirements below.";
  }

  if (normalized.includes("otp") || normalized.includes("code") || normalized.includes("expired")) {
    return "The verification code is invalid or expired. Please check it and try again.";
  }

  return message || "Unable to reset password. Please try again.";
}
