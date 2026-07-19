import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Pin the Turbopack workspace root to this app so Next doesn't infer it from a
  // parent lockfile (silences the "inferred workspace root" warning in the monorepo).
  turbopack: { root: path.join(__dirname) },
};

export default nextConfig;
