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
  Brain, BookOpen, BookOpenText, FolderUp, Bot, ClipboardCheck,
  LineChart, MessageSquare, Trophy, Zap, Shield, Clock, Target,
  Upload, ArrowRight, CheckCircle2, Sparkles, X, Loader2, Eye,
  EyeOff, TrendingUp,
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
    { icon: Brain, title: "Personalized Guidance", description: "Receive adaptive support shaped around your pace, strengths, and study goals for a more focused learning journey." },
    { icon: BookOpen, title: "Study Material Intelligence", description: "Turn your notes, PDFs, and course materials into clear summaries, structured insights, and revision-ready content." },
    { icon: MessageSquare, title: "Conversational AI Support", description: "Ask questions naturally, get explanations in context, and keep learning moving with hands-free assistance." },
    { icon: Trophy, title: "Assessment Engine", description: "Generate targeted quizzes from your materials and use instant feedback to reinforce understanding and retention." },
    { icon: LineChart, title: "Progress Visibility", description: "See patterns in performance, topic mastery, and study consistency across subjects and learning sessions." },
    { icon: Sparkles, title: "Context-Aware Learning", description: "Every answer and recommendation is grounded in the subjects and resources you are actively studying." },
  ];

  const benefits = [
    { icon: Zap, text: "Study faster with focused, AI-guided learning support" },
    { icon: Target, text: "Build confidence through adaptive practice and feedback" },
    { icon: Clock, text: "Turn study time into more productive, high-impact sessions" },
    { icon: Shield, text: "Learn in a secure, distraction-free environment" },
  ];

  const howItWorks = [
    { step: 1, icon: BookOpenText, title: "Create Subjects", description: "Organize your coursework into clear learning areas so each topic has its own study context." },
    { step: 2, icon: FolderUp, title: "Upload Materials", description: "Add your PDFs, notes, and presentations to give EduMind AI the context it needs to support your learning." },
    { step: 3, icon: Bot, title: "Ask and Explore", description: "Chat with your learning companion to clarify concepts, review content, and get guidance from your own materials." },
    { step: 4, icon: ClipboardCheck, title: "Assess Understanding", description: "Create quick checks and practice questions that test knowledge and highlight areas to revisit." },
    { step: 5, icon: TrendingUp, title: "Track Growth", description: "Monitor progress, identify trends, and stay motivated with clear performance insights." },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 relative overflow-hidden"
      style={{
        backgroundImage: "linear-gradient(rgba(239, 246, 255, 0.72), rgba(248, 250, 252, 0.88)), url('https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1600&q=80')",
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
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
              EduMind AI
            </span>
            <span className="block text-3xl lg:text-5xl mt-3">Adaptive Learning Companion</span>
          </h1>

          <p className="text-xl lg:text-2xl text-muted-foreground max-w-3xl mx-auto mb-10 leading-relaxed">
            Learn with your own study materials, get tailored AI guidance, and track growth with assessments designed around how you learn.
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
              A simple five-step path from study materials to measurable progress
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
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Intelligent Learning</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Everything you need to learn with clarity, confidence, and context
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
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Why Choose EduMind AI?</h2>
            <p className="text-xl text-blue-50 max-w-2xl mx-auto">
              Built for learners who want smarter studying, better understanding, and clearer momentum
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {[
              { title: "Context-Aware Guidance", body: "Every answer, explanation, and quiz is grounded in your course materials, subjects, and learning goals." },
              { title: "Your Study Materials, Reimagined", body: "Upload your own resources and turn them into organized, actionable learning support instead of static notes." },
              { title: "Instant Feedback", body: "Move from confusion to clarity with immediate explanations, practice checks, and personalized recommendations." },
              { title: "Track Your Growth", body: "Follow your performance across topics, assessments, and sessions with meaningful progress insights." },
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
          <h2 className="text-3xl font-bold mb-4">Ready to learn with more clarity?</h2>
          <p className="text-lg text-blue-50 mb-8">Join learners using AI support to review materials, practice smarter, and track progress.</p>
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
        <DialogContent
          className="sm:max-w-md overflow-hidden rounded-2xl border border-slate-200/70 bg-white/80 shadow-[0_25px_80px_rgba(15,23,42,0.14)]"
          onPointerDownOutside={(e) => e.preventDefault()}
          style={{
            backgroundImage: "linear-gradient(135deg, rgba(255,255,255,0.86), rgba(255,255,255,0.75)), url('https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=1200&q=80')",
            backgroundSize: "cover",
            backgroundPosition: "center top",
          }}
        >
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
            <DialogTitle className="text-center text-2xl font-bold text-slate-900">
              {authTab === "login" ? "Welcome Back" : "Create Account"}
            </DialogTitle>
          </DialogHeader>

          <Tabs value={authTab} onValueChange={(v) => { setAuthTab(v as "login" | "register"); setLoginError(null); setRegisterError(null); }} className="w-full mt-4">
            <TabsList className="grid w-full grid-cols-2 mb-6 bg-slate-100/80 p-1 border border-slate-200/80 backdrop-blur-sm">
              <TabsTrigger value="login" className="data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm data-[state=active]:font-semibold text-slate-600">Login</TabsTrigger>
              <TabsTrigger value="register" className="data-[state=active]:bg-white data-[state=active]:text-primary data-[state=active]:shadow-sm data-[state=active]:font-semibold text-slate-600">Register</TabsTrigger>
            </TabsList>

            {/* ── Login Tab ── */}
            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="modal-login-email" className="text-slate-700 font-semibold">Email</Label>
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
                  <Label htmlFor="modal-login-password" className="text-slate-700 font-semibold">Password</Label>
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

                <Button type="submit" className="w-full shadow-lg shadow-primary/25 ring-1 ring-primary/10 hover:shadow-primary/40" size="lg" disabled={isSubmitting} id="btn-login-submit">
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
                    <Label htmlFor="modal-register-firstname" className="text-slate-700 font-semibold">First Name</Label>
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
                    <Label htmlFor="modal-register-lastname" className="text-slate-700 font-semibold">Last Name</Label>
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
                  <Label htmlFor="modal-register-email" className="text-slate-700 font-semibold">Email</Label>
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
                  <Label htmlFor="modal-register-password" className="text-slate-700 font-semibold">Password</Label>
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
                  <Label htmlFor="modal-register-confirm-password" className="text-slate-700 font-semibold">Confirm Password</Label>
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

                <Button type="submit" className="w-full shadow-lg shadow-primary/25 ring-1 ring-primary/10 hover:shadow-primary/40" size="lg" disabled={isSubmitting} id="btn-register-submit">
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
