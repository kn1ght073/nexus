"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Server,
  Network,
  Activity,
  Shield,
  FileText,
  KeyRound,
  Settings,
  Users,
  LogOut,
  Hexagon,
} from "lucide-react";
import { User } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

interface SidebarProps {
  user: User | null;
}

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  };

  const navItems = [
    { label: "Overview", href: "/", icon: LayoutDashboard },
    { label: "Devices & Nodes", href: "/devices", icon: Server },
    { label: "Connections & Relay", href: "/relay", icon: Network },
    { label: "Services & Health", href: "/services", icon: Activity },
  ];

  const secItems = [
    { label: "Security Center", href: "/security", icon: Shield },
    { label: "Audit Logs", href: "/audit", icon: FileText },
    { label: "Sessions & Identity", href: "/sessions", icon: KeyRound },
    ...(user?.role === "owner" || user?.role === "operator"
      ? [{ label: "Operator Management", href: "/operators", icon: Users }]
      : []),
  ];

  const sysItems = [{ label: "Settings", href: "/settings", icon: Settings }];

  return (
    <aside className="w-64 border-r border-white/8 bg-[#090d16] flex flex-col h-screen sticky top-0 shrink-0 z-40">
      {/* Brand Header */}
      <div className="p-4 border-b border-white/8 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 grid place-items-center text-sky-400">
          <Hexagon className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-wider text-white">NEXUS</h1>
          <p className="text-[10px] font-mono text-sky-400 tracking-widest">CONTROL CENTER</p>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-6">
        <div>
          <span className="px-3 text-[10px] font-mono font-semibold text-slate-500 tracking-wider">MAIN</span>
          <div className="mt-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    active
                      ? "bg-sky-500/10 text-sky-400 font-semibold"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>

        <div>
          <span className="px-3 text-[10px] font-mono font-semibold text-slate-500 tracking-wider">SECURITY & ACCESS</span>
          <div className="mt-2 space-y-1">
            {secItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    active
                      ? "bg-sky-500/10 text-sky-400 font-semibold"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>

        <div>
          <span className="px-3 text-[10px] font-mono font-semibold text-slate-500 tracking-wider">SYSTEM</span>
          <div className="mt-2 space-y-1">
            {sysItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    active
                      ? "bg-sky-500/10 text-sky-400 font-semibold"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Operator User Card */}
      <div className="p-3 border-t border-white/8 flex items-center justify-between gap-2 bg-black/20">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-500 grid place-items-center text-white text-[11px] font-bold font-mono shrink-0">
            {user?.email?.slice(0, 2).toUpperCase() || "OP"}
          </div>
          <div className="truncate">
            <p className="text-xs font-medium text-white truncate">{user?.email || "Guest Operator"}</p>
            <Badge variant="outline" className="text-[9px] px-1.5 py-0 uppercase">
              {user?.role || "Unauthenticated"}
            </Badge>
          </div>
        </div>
        {user ? (
          <button
            onClick={handleLogout}
            title="Log out"
            className="p-1.5 text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        ) : (
          <Link href="/login" className="text-xs text-sky-400 font-semibold hover:underline">
            Login
          </Link>
        )}
      </div>
    </aside>
  );
}
