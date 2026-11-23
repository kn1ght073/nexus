"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  User as UserIcon,
  Laptop,
  History,
  Server,
  Database,
  LogOut,
  Hexagon,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import { User } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

interface ClientSidebarProps {
  user: User;
}

export function ClientSidebar({ user }: ClientSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  };

  const navItems = [
    { label: "Account Overview", href: "/client", icon: UserIcon },
    { label: "Devices & Sessions", href: "/client/devices", icon: Laptop },
    { label: "Account Activity", href: "/client/activity", icon: History },
    { label: "Server Information", href: "/client/server", icon: Server },
    { label: "Account Data", href: "/client/data", icon: Database },
  ];

  const isOperator = user.role === "operator" || user.role === "owner";

  return (
    <aside className="w-64 border-r border-white/8 bg-[#090d16] flex flex-col h-screen sticky top-0 shrink-0 z-40">
      {/* Brand Header */}
      <div className="p-4 border-b border-white/8 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 grid place-items-center text-sky-400">
          <Hexagon className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-wider text-white">NEXUS</h1>
          <p className="text-[10px] font-mono text-emerald-400 tracking-wider">CLIENT CONSOLE</p>
        </div>
      </div>

      {/* User Quick Identity Pill */}
      <div className="p-3 border-b border-white/5 bg-white/[0.01]">
        <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-md bg-white/5 border border-white/5">
          <div className="w-7 h-7 rounded-full bg-sky-500/20 text-sky-400 text-xs font-bold grid place-items-center uppercase">
            {user.email.slice(0, 2)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-white truncate">{user.email}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-white/10 text-slate-400">
                ID #{user.id}
              </Badge>
              <span className="text-[10px] text-emerald-400 font-mono">ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-6">
        <div>
          <span className="px-3 text-[10px] font-mono font-semibold text-slate-500 tracking-wider">
            MY SOVEREIGN CLIENT
          </span>
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
                      ? "bg-sky-500/10 text-sky-400 font-semibold border border-sky-500/20"
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

        {/* Operator Switcher (if elevated role) */}
        {isOperator && (
          <div>
            <span className="px-3 text-[10px] font-mono font-semibold text-amber-400/80 tracking-wider">
              ADMINISTRATION
            </span>
            <div className="mt-2">
              <Link
                href="/"
                className="flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium text-amber-300/90 bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  <span>Operator Console</span>
                </div>
                <ExternalLink className="w-3.5 h-3.5 text-amber-400/70" />
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* Footer / Sign Out */}
      <div className="p-3 border-t border-white/8 space-y-2">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-rose-400/90 hover:text-rose-300 hover:bg-rose-500/10 rounded-md transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
