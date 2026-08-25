import { fetchDealsFromDb } from "@/api/deals";
import type { DbDeal } from "@/api/deals.types";
import { type CategoryId, type Deal } from "./deals";

// ── Category normalisation ─────────────────────────────────────────────────────

const CATEGORY_MAP: Record<string, CategoryId> = {
  "food & beverage": "food",
  food: "food",
  dining: "food",
  shopping: "shopping",
  fashion: "shopping",
  beauty: "beauty",
  "health & beauty": "beauty",
  entertainment: "entertainment",
  travel: "travel",
  hotels: "hotels",
  hotel: "hotels",
  electronics: "electronics",
  fitness: "fitness",
  services: "services",
};

function normaliseCategory(raw: string): CategoryId {
  return CATEGORY_MAP[raw.toLowerCase().trim()] ?? "food";
}

// ── Offer label ────────────────────────────────────────────────────────────────

function buildOffer(row: DbDeal): string {
  if (row.discount) return row.discount;
  if (row.price) return row.price;
  return "DEAL";
}

// ── Title ─────────────────────────────────────────────────────────────────────

function buildTitle(row: DbDeal): string {
  const raw = row.offer ?? "";
  const sentence = (raw.split(/[.!?]/)[0] ?? raw).trim();
  return sentence.length > 72 ? sentence.slice(0, 69) + "…" : sentence;
}

// ── Expiry helpers ─────────────────────────────────────────────────────────────

const TODAY = new Date();
TODAY.setHours(0, 0, 0, 0);

function formatExpiry(dateStr: string | null): string {
  if (!dateStr) return "Ongoing";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "Ongoing";
  return d.toLocaleDateString("en-SG", { day: "numeric", month: "short" });
}

function isExpiresSoon(dateStr: string | null): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return false;
  const diffDays = (d.getTime() - TODAY.getTime()) / 86_400_000;
  return diffDays >= 0 && diffDays <= 3;
}

// ── scrapedAgo ────────────────────────────────────────────────────────────────

function scrapedAgo(postedAt: string): string {
  const posted = new Date(postedAt);
  if (isNaN(posted.getTime())) return "recently";
  const diffMs = Date.now() - posted.getTime();
  const diffH = Math.floor(diffMs / 3_600_000);
  if (diffH < 1) return "just now";
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  return `${diffD}d ago`;
}

// ── Map position (deterministic pseudo-random from message_id) ────────────────

function mapPos(id: number): { x: number; y: number } {
  const x = ((id * 137 + 29) % 72) + 10;
  const y = ((id * 97 + 41) % 62) + 15;
  return { x, y };
}

// ── more_info → full URL ───────────────────────────────────────────────────────

function buildMoreInfoUrl(raw: string | null): string | undefined {
  if (!raw) return undefined;
  const clean = raw.replace(/\]\(.*?\)/, "").trim();
  if (!clean) return undefined;
  if (/^https?:\/\//i.test(clean)) return clean;
  return `https://${clean}`;
}

// ── DB row → Deal ─────────────────────────────────────────────────────────────

export function dbRowToDeal(row: DbDeal): Deal {
  // locations is [{name, lat, lng}] — use the first entry for the primary location string
  const firstLoc = row.locations?.[0];
  const locationStr = firstLoc?.name ?? "Singapore";

  const terms = [
    ...(row.restrictions ?? []),
    row.redemption_method ? `Redeem via: ${row.redemption_method}` : null,
    row.promo_code ? `Code: ${row.promo_code}` : null,
  ]
    .filter(Boolean)
    .join(". ");

  const deal: Deal = {
    id: `${row.channel}-${row.message_id}`,
    merchant: row.merchant,
    title: buildTitle(row),
    description: row.offer,
    terms: terms || "T&Cs apply.",
    offer: buildOffer(row),
    category: normaliseCategory(row.category),
    location: locationStr,
    address: locationStr,
    distanceKm: 0,
    expiry: formatExpiry(row.valid_to),
    expiresSoon: isExpiresSoon(row.valid_to),
    scrapedAgo: scrapedAgo(row.posted_at),
    channel: `@${row.channel}`,
    openingHours: row.time ?? "",
    trending: false,
    map: mapPos(row.message_id),
    originalPost: (row.raw_input ?? "").replace(/\*\*/g, "").replace(/@\w+/g, "").trim(),
  };

  const url = buildMoreInfoUrl(row.more_info);
  if (url) deal.moreInfoUrl = url;

  // Use the first geocoded location's coords for distance/map calculations
  // All locations with coords are stored in deal.locations for the map
  const geocodedLocs = (row.locations ?? []).filter(
    (l) => l.lat != null && l.lng != null,
  );
  if (geocodedLocs.length > 0) {
    deal.lat = geocodedLocs[0].lat!;
    deal.lng = geocodedLocs[0].lng!;
  }

  // Attach all locations for multi-pin map rendering
  deal.allLocations = row.locations ?? [];

  return deal;
}

// ── Fetch + parse ─────────────────────────────────────────────────────────────

export async function fetchDeals(): Promise<Deal[]> {
  const rows = await fetchDealsFromDb();

  const deals: Deal[] = [];
  const seen = new Set<string>();

  for (const row of rows) {
    try {
      const deal = dbRowToDeal(row);

      // De-duplicate by merchant + offer in case channels cross-post the same deal
      const key = `${deal.merchant.toLowerCase()}::${deal.offer.toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);

      deals.push(deal);
    } catch {
      // Skip malformed rows
    }
  }

  // Already sorted DESC by posted_at from the DB query
  return deals;
}
