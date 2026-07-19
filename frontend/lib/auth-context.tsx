"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createClient, type Session, type User } from "@supabase/supabase-js";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  orgName: string;
  displayName: string;
  initials: string;
  loading: boolean;
  configured: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, orgName?: string) => Promise<void>;
  signOut: (onDone?: () => void) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

function makeClient() {
  if (!supabaseUrl || !supabaseAnon) return null;
  return createClient(supabaseUrl, supabaseAnon);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const client = useMemo(() => makeClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(Boolean(client));

  useEffect(() => {
    // No client → nothing to load; `loading` already initializes to false via useState(Boolean(client)).
    if (!client) return;
    client.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (data.session?.access_token) {
        localStorage.setItem("cg_access_token", data.session.access_token);
      }
      setLoading(false);
    });
    const { data: sub } = client.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      if (next?.access_token) {
        localStorage.setItem("cg_access_token", next.access_token);
      } else {
        localStorage.removeItem("cg_access_token");
      }
    });
    return () => sub.subscription.unsubscribe();
  }, [client]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!client) throw new Error("Supabase is not configured");
      const { error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw error;
    },
    [client],
  );

  const signUp = useCallback(
    async (email: string, password: string, orgName?: string) => {
      if (!client) throw new Error("Supabase is not configured");
      const { error } = await client.auth.signUp({
        email,
        password,
        options: { data: { org_name: orgName || "My Organization" } },
      });
      if (error) throw error;
    },
    [client],
  );

  const signOut = useCallback(
    async (onDone?: () => void) => {
      if (client) {
        await client.auth.signOut();
      }
      localStorage.removeItem("cg_access_token");
      onDone?.();
    },
    [client],
  );

  const user = session?.user ?? null;
  const displayName =
    (user?.user_metadata?.display_name as string) ||
    user?.email?.split("@")[0] ||
    "Guest";
  const orgName =
    (user?.user_metadata?.org_name as string) ||
    (user ? "Your organization" : "Local session");
  const initials = displayName
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const value: AuthContextValue = {
    user,
    session,
    orgName,
    displayName,
    initials: initials || "CG",
    loading,
    configured: Boolean(client),
    signIn,
    signUp,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
