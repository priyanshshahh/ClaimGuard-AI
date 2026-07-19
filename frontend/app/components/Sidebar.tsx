"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Home,
  LayoutDashboard,
  ListChecks,
  Bot,
  BarChart3,
  FileText,
  Settings,
  Play,
} from "lucide-react";
import { DEMO_MODE } from "../../lib/demo";
import { apiFetch } from "../../lib/api";
import { toast } from "sonner";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/queue", label: "Claims Queue", icon: ListChecks },
  { href: "/studio", label: "Agent Studio", icon: Bot },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/model-card", label: "Model Card", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();

  const loadDemo = async () => {
    try {
      const data = await apiFetch<{ seeded: number; total_revenue_at_risk: number }>(
        "/api/seed-demo",
        { method: "POST" },
      );
      toast.success(`Demo ready: ${data.seeded} claims`, {
        description: `$${Math.round(data.total_revenue_at_risk).toLocaleString()} at risk`,
      });
      router.push("/queue?mode=treasury");
    } catch {
      toast.error("Could not seed demo claims");
    }
  };

  return (
    <aside className="w-64 border-r border-[var(--border)] bg-[var(--bg-elevated)] flex flex-col h-screen sticky top-0">
      <div className="p-5 border-b border-[var(--border)]">
        <Link href="/dashboard" className="flex items-center gap-2.5" onClick={onNavigate}>
          <div className="w-8 h-8 rounded-2xl bg-[var(--primary)] flex items-center justify-center">
            <span className="text-white font-bold text-lg tracking-[-1px]">CG</span>
          </div>
          <div>
            <div className="font-semibold text-xl tracking-[-1.25px]">ClaimGuard</div>
            <div className="text-[var(--accent)] text-xs -mt-1 font-medium">AI</div>
          </div>
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-1" aria-label="Primary">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`sidebar-link ${isActive ? "active" : ""}`}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--border)] space-y-3">
        {DEMO_MODE ? (
          <button type="button" onClick={loadDemo} className="w-full btn btn-primary text-sm py-2.5">
            <Play size={16} /> Load demo claims
          </button>
        ) : null}
        <div className="text-[10px] text-center text-[var(--text-muted)] font-mono tracking-widest">
          ClaimGuard · v3.1
        </div>
      </div>
    </aside>
  );
}
