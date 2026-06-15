import { useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import {
  Brain, BookOpen, LineChart, MessageSquare, Trophy, Zap,
  Shield, Clock, Target, Upload, ArrowRight, CheckCircle2,
  Sparkles, X, Loader2, Eye, EyeOff,
} from "lucide-react";
import { login, register } from "../../services/authService";
import { useAuth } from "../../context/AuthContext";

// ─── Form state shapes ────────────────────────────────────────────────────────

interface LoginForm {
  email: string;
  password: string;
}

interface RegisterForm {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Welcome() {
  const navigate = useNavigate();
  const { setSession } = useAuth();

  // ── Form state ──────────────────────────────────────────────────────────────
  const [loginForm, setLoginForm] = useState<LoginForm>({ email: "", password: "" });
  const [registerForm, setRegisterForm] = useState<RegisterForm>({
    firstName: "", lastName: "", email: "", password: "", confirmPassword: "",
  });

  // ── UI state ────────────────────────────────────────────────────────────────
  const [showAuthModal, setShowAuthModal]   = useState(false);
  const [authTab, setAuthTab]               = useState<"login" | "register">("login");
  const [isSubmitting, setIsSubmitting]     = useState(false);
  const [loginError, setLoginError]         = useState<string | null>(null);
  const [registerError, setRegisterError]   = useState<string | null>(null);
  const [showLoginPwd, setShowLoginPwd]     = useState(false);
  const [showRegPwd, setShowRegPwd]         = useState(false);
  const [showRegConfirmPwd, setShowRegConfirmPwd] = useState(false);

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const openAuthModal = (tab: "login" | "register") => {
    setLoginError(null);
    setRegisterError(null);
    setAuthTab(tab);
    setShowAuthModal(true);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);

    if (!loginForm.email || !loginForm.password) {
      setLoginError("Please fill in all fields.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await login({ email: loginForm.email, password: loginForm.password });
      setSession({
        userId: response.userId,
        email: response.email ?? "",
        token: response.token ?? "",
        expiresIn: response.expiresIn,
      });
      toast.success(response.message ?? "Welcome back!");
      setShowAuthModal(false);
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed. Please try again.";
      setLoginError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterError(null);

    const { firstName, lastName, email, password, confirmPassword } = registerForm;

    if (!firstName || !lastName || !email || !password || !confirmPassword) {
      setRegisterError("Please fill in all fields.");
      return;
    }
    if (password !== confirmPassword) {
      setRegisterError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await register({ firstName, lastName, email, password });
      setSession({
        userId: response.userId,
        email: response.email ?? "",
        token: response.token ?? "",
        expiresIn: response.expiresIn,
      });
      toast.success(response.message ?? "Account created! Welcome aboard.");
      setShowAuthModal(false);
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed. Please try again.";
      setRegisterError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Static data ─────────────────────────────────────────────────────────────

  const features = [
    { icon: Brain, title: "AI-Powered Tutoring", description: "Get personalized learning assistance with our advanced AI tutor that adapts to your learning style and provides instant answers." },
    { icon: BookOpen, title: "Smart Document Analysis", description: "Upload your study materials and let AI analyze, summarize, and create custom learning content from your documents." },
    { icon: MessageSquare, title: "Interactive Chat", description: "Ask questions anytime with speech-to-text and text-to-speech capabilities for a truly hands-free learning experience." },
    { icon: Trophy, title: "Intelligent Quizzes", description: "AI-generated quizzes tailored to your documents with instant feedback, detailed explanations, and performance tracking." },
    { icon: LineChart, title: "Progress Analytics", description: "Track your learning progress with detailed insights, performance metrics, and visual analytics across all subjects." },
    { icon: Sparkles, title: "Context-Aware Learning", description: "Every interaction is contextualized to your selected subjects and documents for maximum relevance and efficiency." },
  ];

  const benefits = [
    { icon: Zap, text: "Learn 3x faster with personalized AI assistance" },
    { icon: Target, text: "Achieve your academic goals efficiently" },
    { icon: Clock, text: "Study smarter, not harder with AI insights" },
    { icon: Shield, text: "Secure and private learning environment" },
  ];

  const howItWorks = [
    { step: 1, icon: BookOpen, title: "Create Subjects", description: "Organize your learning by creating subjects for each course or topic you're studying." },
    { step: 2, icon: Upload, title: "Upload Documents", description: "Add your study materials - PDFs, notes, presentations - to each subject for AI analysis." },
    { step: 3, icon: MessageSquare, title: "Chat with AI Tutor", description: "Select a subject and documents, then chat with AI to get answers, explanations, and insights." },
    { step: 4, icon: Trophy, title: "Take AI Quizzes", description: "Generate quizzes from your documents to test your knowledge and reinforce learning." },
    { step: 5, icon: LineChart, title: "Track Progress", description: "Monitor your performance, quiz scores, and learning trends with detailed analytics." },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-12 lg:py-20">
        <div className="text-center mb-16 lg:mb-20">
          <div className="flex justify-center mb-8">
            <div className="relative">
              <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full" />
              <div className="relative bg-gradient-to-br from-primary to-blue-600 p-6 rounded-3xl shadow-2xl">
                <Brain className="w-20 h-20 text-white" />
              </div>
            </div>
          </div>

          <h1 className="text-5xl lg:text-7xl font-extrabold text-foreground mb-6 leading-tight">
            <span className="bg-gradient-to-r from-primary via-blue-600 to-indigo-600 bg-clip-text text-transparent block">
              GenT
            </span>
            <span className="block text-3xl lg:text-5xl mt-3">AI Tutor</span>
          </h1>

          <p className="text-xl lg:text-2xl text-muted-foreground max-w-3xl mx-auto mb-10 leading-relaxed">
            Your intelligent learning companion. Master any subject with AI-powered tutoring,
            adaptive quizzes, and comprehensive progress tracking—all from your own study materials.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button size="lg" className="text-lg px-8 py-6 h-auto" onClick={() => openAuthModal("register")}>
              Get Started Free
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button size="lg" variant="outline" className="text-lg px-8 py-6 h-auto" onClick={() => {
              document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });
            }}>
              See How It Works
            </Button>
          </div>
        </div>

        {/* Benefits */}
        <div className="bg-gradient-to-r from-primary/10 via-blue-500/10 to-indigo-500/10 rounded-3xl p-8 lg:p-12 mb-20 border border-primary/20">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {benefits.map((benefit, index) => (
              <div key={index} className="flex items-start gap-4">
                <div className="bg-primary/20 p-3 rounded-xl shrink-0">
                  <benefit.icon className="w-6 h-6 text-primary" />
                </div>
                <p className="text-foreground font-medium pt-2">{benefit.text}</p>
              </div>
            ))}
          </div>
        </div>

        {/* How It Works */}
        <div id="how-it-works" className="mb-20 scroll-mt-20">
          <div className="text-center mb-12">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">How It Works</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Five simple steps to transform your learning experience
            </p>
          </div>

          <div className="relative">
            <div className="hidden lg:block absolute top-24 left-0 right-0 h-1">
              <div className="max-w-5xl mx-auto h-full">
                <div className="h-full bg-gradient-to-r from-primary via-blue-500 to-indigo-500 rounded-full opacity-20" />
              </div>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-8 relative">
              {howItWorks.map((item, index) => (
                <div key={index} className="relative">
                  <Card className="border-2 hover:border-primary/50 transition-all hover:shadow-xl h-full">
                    <CardContent className="pt-6 text-center">
                      <div className="relative inline-block mb-4">
                        <div className="absolute inset-0 bg-primary/10 blur-xl rounded-full" />
                        <div className="relative bg-gradient-to-br from-primary to-blue-600 text-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-lg">
                          <item.icon className="w-8 h-8" />
                        </div>
                        <div className="absolute -top-2 -right-2 bg-white border-2 border-primary w-8 h-8 rounded-full flex items-center justify-center font-bold text-primary shadow-sm">
                          {item.step}
                        </div>
                      </div>
                      <h3 className="font-bold text-lg mb-2">{item.title}</h3>
                      <p className="text-muted-foreground text-sm leading-relaxed">{item.description}</p>
                    </CardContent>
                  </Card>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="mb-20">
          <div className="text-center mb-12">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Powerful Features</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Everything you need for effective, AI-enhanced learning
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="border-2 hover:border-primary/50 transition-all hover:shadow-xl group">
                <CardHeader>
                  <div className="bg-gradient-to-br from-primary/20 to-blue-500/20 w-14 h-14 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <feature.icon className="w-7 h-7 text-primary" />
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                  <CardDescription className="text-base leading-relaxed">{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>

        {/* Why Choose */}
        <div className="bg-gradient-to-br from-primary to-blue-600 rounded-3xl p-8 lg:p-16 mb-20 text-white shadow-2xl">
          <div className="text-center mb-12">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Why Choose GenT?</h2>
            <p className="text-xl text-blue-50 max-w-2xl mx-auto">
              Built for modern learners who demand more from their study tools
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {[
              { title: "Context-Aware AI", body: "Every conversation and quiz is tailored to your specific documents and subjects for maximum relevance." },
              { title: "Your Materials, Your Way", body: "Learn from your own notes and resources. No generic content—just personalized insights." },
              { title: "Instant Feedback", body: "Get immediate answers, explanations, and quiz results. No waiting, just learning." },
              { title: "Track Your Growth", body: "Comprehensive analytics show your progress across subjects, quizzes, and study sessions." },
            ].map((item, i) => (
              <div key={i} className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
                <CheckCircle2 className="w-8 h-8 mb-4" />
                <h3 className="font-bold text-xl mb-2">{item.title}</h3>
                <p className="text-blue-50">{item.body}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="max-w-2xl mx-auto text-center bg-gradient-to-br from-primary to-blue-600 rounded-3xl p-12 text-white shadow-2xl">
          <h2 className="text-3xl font-bold mb-4">Ready to Transform Your Learning?</h2>
          <p className="text-lg text-blue-50 mb-8">Join thousands of students already learning smarter with AI</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" variant="secondary" className="text-lg px-8 py-6 h-auto" onClick={() => openAuthModal("register")}>
              Create Free Account
            </Button>
            <Button size="lg" variant="outline" className="text-lg px-8 py-6 h-auto bg-white/10 text-white border-white/30 hover:bg-white/20" onClick={() => openAuthModal("login")}>
              Sign In
            </Button>
          </div>
          <p className="text-sm text-blue-100 mt-6">No credit card required • Free forever</p>
        </div>
      </div>

      {/* ── Auth Modal ─────────────────────────────────────────────────────────── */}
      <Dialog open={showAuthModal} onOpenChange={setShowAuthModal}>
        <DialogContent className="sm:max-w-md" onPointerDownOutside={(e) => e.preventDefault()}>
          <button
            onClick={() => setShowAuthModal(false)}
            className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </button>

          <DialogHeader>
            <div className="flex justify-center mb-4">
              <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center">
                <Brain className="w-8 h-8 text-primary-foreground" />
              </div>
            </div>
            <DialogTitle className="text-center text-2xl">
              {authTab === "login" ? "Welcome Back" : "Create Account"}
            </DialogTitle>
          </DialogHeader>

          <Tabs value={authTab} onValueChange={(v) => { setAuthTab(v as "login" | "register"); setLoginError(null); setRegisterError(null); }} className="w-full mt-4">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="login">Login</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>

            {/* ── Login Tab ── */}
            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="modal-login-email">Email</Label>
                  <Input
                    id="modal-login-email"
                    type="email"
                    placeholder="Enter your email"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    required
                    disabled={isSubmitting}
                    autoComplete="email"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modal-login-password">Password</Label>
                  <div className="relative">
                    <Input
                      id="modal-login-password"
                      type={showLoginPwd ? "text" : "password"}
                      placeholder="Enter your password"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                      required
                      disabled={isSubmitting}
                      autoComplete="current-password"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setShowLoginPwd((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showLoginPwd ? "Hide password" : "Show password"}
                    >
                      {showLoginPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {loginError && (
                  <p role="alert" className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                    {loginError}
                  </p>
                )}

                <Button type="submit" className="w-full" size="lg" disabled={isSubmitting} id="btn-login-submit">
                  {isSubmitting ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Signing in…</>
                  ) : (
                    "Sign In"
                  )}
                </Button>

                <div className="text-center">
                  <button type="button" className="text-sm text-primary hover:underline" onClick={() => navigate("/forgot-password")}>
                    Forgot password?
                  </button>
                </div>
              </form>
            </TabsContent>

            {/* ── Register Tab ── */}
            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="modal-register-firstname">First Name</Label>
                    <Input
                      id="modal-register-firstname"
                      type="text"
                      placeholder="First name"
                      value={registerForm.firstName}
                      onChange={(e) => setRegisterForm({ ...registerForm, firstName: e.target.value })}
                      required
                      disabled={isSubmitting}
                      autoComplete="given-name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="modal-register-lastname">Last Name</Label>
                    <Input
                      id="modal-register-lastname"
                      type="text"
                      placeholder="Last name"
                      value={registerForm.lastName}
                      onChange={(e) => setRegisterForm({ ...registerForm, lastName: e.target.value })}
                      required
                      disabled={isSubmitting}
                      autoComplete="family-name"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modal-register-email">Email</Label>
                  <Input
                    id="modal-register-email"
                    type="email"
                    placeholder="Enter your email"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                    required
                    disabled={isSubmitting}
                    autoComplete="email"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modal-register-password">Password</Label>
                  <div className="relative">
                    <Input
                      id="modal-register-password"
                      type={showRegPwd ? "text" : "password"}
                      placeholder="Create a password"
                      value={registerForm.password}
                      onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                      required
                      disabled={isSubmitting}
                      autoComplete="new-password"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setShowRegPwd((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showRegPwd ? "Hide password" : "Show password"}
                    >
                      {showRegPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modal-register-confirm-password">Confirm Password</Label>
                  <div className="relative">
                    <Input
                      id="modal-register-confirm-password"
                      type={showRegConfirmPwd ? "text" : "password"}
                      placeholder="Confirm your password"
                      value={registerForm.confirmPassword}
                      onChange={(e) => setRegisterForm({ ...registerForm, confirmPassword: e.target.value })}
                      required
                      disabled={isSubmitting}
                      autoComplete="new-password"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={() => setShowRegConfirmPwd((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showRegConfirmPwd ? "Hide confirm password" : "Show confirm password"}
                    >
                      {showRegConfirmPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {registerError && (
                  <p role="alert" className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                    {registerError}
                  </p>
                )}

                <Button type="submit" className="w-full" size="lg" disabled={isSubmitting} id="btn-register-submit">
                  {isSubmitting ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Creating account…</>
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>

          <p className="text-center text-xs text-muted-foreground mt-4">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}
