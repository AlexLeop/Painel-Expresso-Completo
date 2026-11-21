import { authStorage } from "./auth";

function prefix(): string | null {
  const session = authStorage.getSession<{ user?: Record<string, unknown> }>();
  const user = session?.user;
  if (!user?.id) return null;
  return "nevesgo:cache:v2:" + [
    user.id, user.operator_id, user.company_id, user.store_id, user.role,
  ].map(value => encodeURIComponent(String(value ?? ""))).join(":") + ":";
}

export const sessionCache = {
  getItem(key: string): string | null {
    const scope = prefix();
    return scope ? localStorage.getItem(scope + key) : null;
  },
  setItem(key: string, value: string): void {
    const scope = prefix();
    if (scope) localStorage.setItem(scope + key, value);
  },
};

export function clearBusinessCache(): void {
  try {
    const legacy = new Set([
      "machine_admin_dailies", "machine_admin_manual_entries",
      "nevesgo:credit_log", "nevesgo:company_configs",
    ]);
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith("nevesgo:cache:") || legacy.has(key)) localStorage.removeItem(key);
    }
  } catch {
    // Authentication must still end when browser storage is unavailable.
  }
}
