import type { DbLocation } from "@/api/deals.types";

export type CategoryId =
  | "food"
  | "shopping"
  | "beauty"
  | "entertainment"
  | "travel"
  | "hotels"
  | "electronics"
  | "fitness"
  | "services";

export type Category = {
  id: CategoryId;
  label: string;
  emoji: string;
};

export const categories: Category[] = [
  { id: "food", label: "Food & Dining", emoji: "🍔" },
  { id: "shopping", label: "Shopping", emoji: "🛍" },
  { id: "beauty", label: "Beauty", emoji: "💄" },
  { id: "entertainment", label: "Entertainment", emoji: "🎮" },
  { id: "travel", label: "Travel", emoji: "✈️" },
  { id: "hotels", label: "Hotels", emoji: "🏨" },
  { id: "electronics", label: "Electronics", emoji: "🎧" },
  { id: "fitness", label: "Fitness", emoji: "🏋️" },
  { id: "services", label: "Services", emoji: "🧰" },
];

export const categoryMap = Object.fromEntries(
  categories.map((c) => [c.id, c]),
) as Record<CategoryId, Category>;

export type Deal = {
  id: string;
  merchant: string;
  title: string;
  description: string;
  terms: string;
  restrictions?: string[];
  offer: string;
  category: CategoryId;
  image?: string;
  location: string;
  address: string;
  distanceKm: number;
  expiry: string;
  expiresSoon?: boolean;
  scrapedAgo: string;
  channel: string;
  openingHours?: string;
  trending?: boolean;
  // Position on the stylised map, in percent
  map: { x: number; y: number };
  originalPost: string;
  moreInfoUrl?: string;
  // Primary coordinates (first geocoded location — used for distance/near-me)
  lat?: number;
  lng?: number;
  // All locations with their individual coordinates (for multi-pin map rendering)
  allLocations?: DbLocation[];
  // Supabase Storage path — use getSignedImageUrl() server fn to get a temporary URL
  imagePath?: string;
};

export function matchesQuery(deal: Deal, query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [
    deal.merchant,
    deal.title,
    deal.description,
    deal.location,
    deal.offer,
    categoryMap[deal.category].label,
  ]
    .join(" ")
    .toLowerCase()
    .includes(q);
}
