"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuth } from "../../lib/auth-context";
import { Button, Input, PageHeader } from "../components/ui";

export default function LoginPage() {
  const { signIn, configured } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!configured) {
      toast.error("Auth is not configured", {
        description: "Set NEXT_PUBLIC_SUPABASE_URL and ANON_KEY, or use local demo mode.",
      });
      router.push("/dashboard");
      return;
    }
    setBusy(true);
    try {
      await signIn(email, password);
      toast.success("Signed in");
      router.push("/dashboard");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-[var(--bg)]">
      <div className="w-full max-w-md">
        <PageHeader title="Sign in" description="Access your ClaimGuard workspace" />
        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          <div>
            <label htmlFor="email" className="text-sm font-medium block mb-1">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="password" className="text-sm font-medium block mb-1">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <Button type="submit" className="w-full py-2.5" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-sm text-[var(--text-muted)] text-center">
            No account?{" "}
            <Link href="/signup" className="underline hover:text-[var(--text)]">
              Create one
            </Link>
          </p>
          {!configured ? (
            <p className="text-xs text-[var(--text-muted)] text-center">
              Supabase not configured — continue to{" "}
              <Link href="/dashboard" className="underline">
                dashboard
              </Link>{" "}
              for local use.
            </p>
          ) : null}
        </form>
      </div>
    </div>
  );
}
