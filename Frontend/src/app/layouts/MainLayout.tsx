import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { useUserProfile } from "../../hooks/useUserProfile";
import { Button } from "../components/ui/button";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { ModeToggle } from "../components/mode-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  LayoutDashboard,
  BookOpen,
  MessageSquare,
  Trophy,
  TrendingUp,
  Settings,
  GraduationCap,
  LogOut,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Subjects", href: "/dashboard/subjects", icon: BookOpen },
  { name: "AI Tutor", href: "/dashboard/chat", icon: MessageSquare },
  { name: "Quizzes", href: "/quizzes", icon: Trophy },
  { name: "Progress", href: "/dashboard/progress", icon: TrendingUp },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { logout } = useAuth();
  const { data: profile } = useUserProfile();

  // Compute initials from profile (e.g. "John Doe" → "JD")
  const initials = [
    profile?.firstName?.charAt(0) ?? "",
    profile?.lastName?.charAt(0) ?? "",
  ]
    .join("")
    .toUpperCase() || "?";

  const fullName = profile
    ? `${profile.firstName ?? ""} ${profile.lastName ?? ""}`.trim()
    : "Loading…";

  const email = profile?.email ?? "";

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar for desktop */}
      <aside className={`hidden md:fixed md:inset-y-0 md:flex md:flex-col transition-all duration-300 ${
        sidebarCollapsed ? "md:w-20" : "md:w-64"
      }`}>
        <div className="flex flex-col flex-grow bg-sidebar border-r border-sidebar-border">
          {/* Logo - clickable to toggle sidebar */}
          <div className={`flex items-center h-16 border-b border-sidebar-border transition-all duration-300 ${
            sidebarCollapsed ? "justify-center px-3" : "gap-3 px-6"
          }`}>
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shrink-0 cursor-pointer hover:bg-primary/90 active:scale-95 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <GraduationCap className="w-6 h-6 text-primary-foreground" />
            </button>
            {!sidebarCollapsed && (
              <span className="font-semibold leading-tight whitespace-nowrap">
                <span className="block text-lg">GenT</span>
                <span className="block text-xs text-sidebar-foreground/70">AI Tutor</span>
              </span>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                (item.href !== "/dashboard" && location.pathname.startsWith(item.href));
              return (
                <button
                  key={item.name}
                  onClick={() => handleNavigation(item.href)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent"
                  } ${sidebarCollapsed ? "justify-center" : ""}`}
                  title={sidebarCollapsed ? item.name : undefined}
                >
                  <item.icon className="w-5 h-5 shrink-0" />
                  {!sidebarCollapsed && <span>{item.name}</span>}
                </button>
              );
            })}
          </nav>

          {/* Bottom logout button — always visible in sidebar */}
          <div className={`px-3 pb-4 border-t border-sidebar-border pt-4 ${
            sidebarCollapsed ? "flex justify-center" : ""
          }`}>
            <button
              onClick={handleLogout}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-sidebar-foreground hover:bg-destructive/10 hover:text-destructive ${
                sidebarCollapsed ? "justify-center" : ""
              }`}
              title={sidebarCollapsed ? "Log out" : undefined}
            >
              <LogOut className="w-5 h-5 shrink-0" />
              {!sidebarCollapsed && <span>Log out</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="md:hidden">
          <div className="fixed inset-0 z-40 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-sidebar-border flex flex-col">
            <div className="flex items-center justify-between h-16 px-6 border-b border-sidebar-border">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center cursor-pointer hover:bg-primary/90 active:scale-95 transition-all duration-200"
                  title="Close sidebar"
                >
                  <GraduationCap className="w-6 h-6 text-primary-foreground" />
                </button>
                <span className="font-semibold leading-tight">
                  <span className="block text-lg">GenT</span>
                  <span className="block text-xs text-sidebar-foreground/70">AI Tutor</span>
                </span>
              </div>
            </div>
            <nav className="flex-1 px-3 py-4 space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href || 
                  (item.href !== "/dashboard" && location.pathname.startsWith(item.href));
                return (
                  <button
                    key={item.name}
                    onClick={() => {
                      handleNavigation(item.href);
                      setSidebarOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent"
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    <span>{item.name}</span>
                  </button>
                );
              })}
            </nav>
            {/* Mobile sidebar logout button */}
            <div className="px-3 pb-6 border-t border-sidebar-border pt-4">
              <button
                onClick={() => { handleLogout(); setSidebarOpen(false); }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-sidebar-foreground hover:bg-destructive/10 hover:text-destructive"
              >
                <LogOut className="w-5 h-5" />
                <span>Log out</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className={`transition-all duration-300 ${sidebarCollapsed ? "md:pl-20" : "md:pl-64"}`}>
        {/* Top navbar */}
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setSidebarOpen(true)}
              >
                <GraduationCap className="w-5 h-5" />
              </Button>
            </div>

            <div className="flex-1" />

            <div className="flex items-center gap-2">
              <ModeToggle />
              {/* User menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="gap-2">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline">{fullName}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <div className="flex flex-col">
                      <span>{fullName}</span>
                      <span className="text-xs font-normal text-muted-foreground">
                        {email}
                      </span>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => handleNavigation("/dashboard/settings")}>
                    <Settings className="w-4 h-4 mr-2" />
                    Settings
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
