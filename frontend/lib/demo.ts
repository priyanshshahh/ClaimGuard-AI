/** Demo theater is opt-in via NEXT_PUBLIC_DEMO_MODE=true */
export const DEMO_MODE =
  process.env.NEXT_PUBLIC_DEMO_MODE === "true" ||
  process.env.NEXT_PUBLIC_DEMO_MODE === "1";
