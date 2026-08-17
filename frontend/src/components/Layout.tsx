import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  Flame,
  LayoutDashboard,
  Briefcase,
  Send,
  Mail,
  SlidersHorizontal,
  Settings as SettingsIcon,
  User as UserIcon,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { useAuth } from "../lib/auth";
import { ThemeToggle } from "./ThemeToggle";

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "Jobs", icon: Briefcase },
  { to: "/applications", label: "Applications", icon: Send },
  { to: "/emails", label: "Emails", icon: Mail },
  { to: "/rules", label: "Rules", icon: SlidersHorizontal },
  { to: "/profile", label: "Profile", icon: UserIcon },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();

  return (
    <>
      <div className="flex items-center gap-2 px-6 py-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
          <Flame className="h-5 w-5" />
        </div>
        <span className="text-lg font-semibold text-slate-900">Flames</span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors sm:py-2",
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3">
        <div className="mb-2 flex items-center justify-between px-1">
          <span className="text-xs font-medium text-slate-400">Theme</span>
          <ThemeToggle />
        </div>
        <div className="flex items-center gap-3 rounded-lg px-3 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700">
            {(user?.first_name?.[0] ?? user?.email[0] ?? "?").toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-900">
              {user?.first_name ? `${user.first_name} ${user.last_name ?? ""}`.trim() : user?.email}
            </p>
            <p className="truncate text-xs text-slate-400">{user?.role}</p>
          </div>
          <button
            onClick={() => void logout()}
            className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            title="Log out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );
}

export function Layout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Desktop sidebar — permanent, hidden below lg */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
        <SidebarContent />
      </aside>

      {/* Mobile off-canvas drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside className="relative flex h-full w-72 max-w-[85vw] flex-col bg-white shadow-xl">
            <button
              onClick={() => setMobileNavOpen(false)}
              className="absolute right-3 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarContent onNavigate={() => setMobileNavOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex flex-1 items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-600 text-white">
              <Flame className="h-3.5 w-3.5" />
            </div>
            <span className="text-base font-semibold text-slate-900">Flames</span>
          </div>
          <ThemeToggle />
        </header>

        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
