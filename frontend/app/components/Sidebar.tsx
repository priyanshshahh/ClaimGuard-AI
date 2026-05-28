"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ListChecks,
  Bot,
  BarChart3,
  Settings,
  Play,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/queue", label: "Claims Queue", icon: ListChecks },
  { href: "/studio", label: "Agent Studio", icon: Bot },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 border-r border-[var(--border)] bg-[var(--bg-elevated)] flex flex-col h-screen sticky top-0">
      <div className="p-5 border-b border-[var(--border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-2xl bg-[var(--primary)] flex items-center justify-center">
            <span className="text-white font-bold text-lg tracking-[-1px]">CG</span>
          </div>
          <div>
            <div className="font-semibold text-xl tracking-[-1.25px]">ClaimGuard</div>
            <div className="text-[var(--accent)] text-xs -mt-1 font-medium">AI</div>
          </div>
        </div>
      </div>

      <div className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${isActive ? "active" : ""}`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t border-[var(--border)]">
        <button
          onClick={() => {
            window.location.href = "/?demo=true";
          }}
          className="w-full btn btn-primary text-sm py-2.5"
        >
          <Play size={16} /> Load Pitch Demo
        </button>
        <div className="mt-3 text-[10px] text-center text-[var(--text-muted)] font-mono tracking-widest">
          v2.0 • PITCH READY
        </div>
      </div>
    </div>
  );
}
