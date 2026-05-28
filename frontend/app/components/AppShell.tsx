"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { Toaster } from "sonner";
import { Sidebar } from "./Sidebar";

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
  return (
    <>
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <header className="h-14 border-b border-[var(--border)] bg-[var(--bg-elevated)] flex items-center px-6 justify-between sticky top-0 z-50">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-[var(--primary)] flex items-center justify-center">
                <span className="text-white text-sm font-bold">CG</span>
              </div>
              <span className="font-semibold text-lg tracking-tight">ClaimGuard</span>
              <span className="text-[var(--accent)] font-medium">AI</span>
            </div>
            <div className="ml-2 px-2 py-0.5 text-[10px] rounded-full bg-[var(--accent)]/10 text-[var(--accent)] font-mono tracking-widest border border-[var(--accent)]/20">
              LIVE DEMO
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
            <span>Regional Health System</span>
            <div className="w-8 h-8 rounded-full bg-[var(--primary)]/10 flex items-center justify-center text-[var(--primary)] text-xs font-semibold">
              JD
            </div>
          </div>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
      <Toaster position="top-center" richColors closeButton />
    </>
  );
}
