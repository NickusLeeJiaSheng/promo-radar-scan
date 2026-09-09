import type { DbDeal } from "./deals.types";

const API_URL = import.meta.env.VITE_GCF_URL ?? "/api/deals";

export async function fetchDealsFromDb(): Promise<DbDeal[]> {
  const res = await fetch(API_URL);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to fetch deals: ${res.status} — ${body}`);
  }
  return res.json() as Promise<DbDeal[]>;
}
