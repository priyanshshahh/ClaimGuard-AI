"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Menu, X } from "lucide-react";
import { Toaster } from "sonner";
import { useAuth } from "../../lib/auth-context";
import { Sidebar } from "./Sidebar";

// Landing and auth screens render clean marketing chrome (no app sidebar).
const BARE_PATHS = new Set(["/", "/login", "/signup"]);

function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const bare = BARE_PATHS.has(pathname);
  const { orgName, initials, displayName, configured, user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    router.push("/");
  };

  if (bare) {
    return (
      <>
        {children}
        <Toaster position="top-center" richColors closeButton />
      </>
    );
  }

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:bg-[var(--bg-elevated)] focus:px-3 focus:py-2 focus:rounded-lg"
      >
        Skip to content
      </a>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-50 h-full w-64">
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      ) : null}

      <div className="hidden md:block">
        <Sidebar />
      </div>

      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        <header className="h-14 border-b border-[var(--border)] bg-[var(--bg-elevated)] flex items-center px-4 sm:px-6 justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="md:hidden btn btn-ghost p-2"
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((open) => !open)}
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-[var(--primary)] flex items-center justify-center">
                <span className="text-white text-sm font-bold">CG</span>
              </div>
              <span className="font-semibold text-lg tracking-tight">ClaimGuard</span>
              <span className="text-[var(--accent)] font-medium">AI</span>
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
            <span className="hidden sm:inline">{orgName}</span>
            {configured && user ? (
              <button type="button" onClick={() => void handleSignOut()} className="btn btn-ghost text-xs">
                Sign out
              </button>
            ) : configured ? (
              <Link href="/login" className="btn btn-ghost text-xs">
                Sign in
              </Link>
            ) : null}
            <div
              className="w-8 h-8 rounded-full bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] text-xs font-semibold"
              title={displayName}
            >
              {initials}
            </div>
          </div>
        </header>
        <main id="main-content" className="flex-1 p-4 sm:p-6 overflow-auto">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
      <Toaster position="top-center" richColors closeButton />
    </>
  );
}
