import { useQuery } from "@tanstack/react-query";

import { type CategoryId, type Deal } from "@/data/deals";
import { fetchDeals } from "@/data/parseDeals";

export const DEALS_QUERY_KEY = ["deals"] as const;

export function useDeals() {
  return useQuery<Deal[]>({
    queryKey: DEALS_QUERY_KEY,
    queryFn: fetchDeals,
    staleTime: 5 * 60 * 1000, // treat data as fresh for 5 min
  });
}

// Derived selectors ─────────────────────────────────────────────────────────────

export function filterDeals(deals: Deal[], chip: string): Deal[] {
  if (chip === "all") return deals;
  if (chip === "trending") return deals.filter((d) => d.trending);
  if (chip === "near") return [...deals].sort((a, b) => a.distanceKm - b.distanceKm).slice(0, 6);
  return deals.filter((d) => d.category === (chip as CategoryId));
}
