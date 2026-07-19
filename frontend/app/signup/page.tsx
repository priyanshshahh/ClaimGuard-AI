"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuth } from "../../lib/auth-context";
import { Button, Input, PageHeader } from "../components/ui";

/** Signup page — linked from landing + login. Uses AuthProvider.signUp. */
export default function SignupPage() {
  const { signUp, configured } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!configured) {
      toast.error("Auth is not configured");
      router.push("/dashboard");
      return;
    }
    setBusy(true);
    try {
      await signUp(email, password, orgName || undefined);
      toast.success("Account created", {
        description: "Check email if confirmation is required, then sign in.",
      });
      router.push("/login");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-[var(--bg)]">
      <div className="w-full max-w-md">
        <PageHeader
          title="Create account"
          description="Start a ClaimGuard organization workspace"
        />
        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          <div>
            <label htmlFor="org" className="text-sm font-medium block mb-1">
              Organization name
            </label>
            <Input
              id="org"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Acme Health"
            />
          </div>
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
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <Button type="submit" className="w-full py-2.5" disabled={busy}>
            {busy ? "Creating…" : "Create account"}
          </Button>
          <p className="text-sm text-[var(--text-muted)] text-center">
            Already have an account?{" "}
            <Link href="/login" className="underline hover:text-[var(--text)]">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
