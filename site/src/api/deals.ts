import type { DbDeal } from "./deals.types";

export async function fetchDealsFromDb(): Promise<DbDeal[]> {
  const res = await fetch("/api/deals");
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to fetch deals: ${res.status} — ${body}`);
  }
  return res.json() as Promise<DbDeal[]>;
}
