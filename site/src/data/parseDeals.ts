import { type CategoryId, type Deal } from "./deals";

// ── Raw shape from processed.jsonl ────────────────────────────────────────────

interface RawPrediction {
  merchant: string;
  category: string;
  offer: string;
  price: string | null;
  original_price: string | null;
  discount: string | null;
  valid_from: string | null;
  valid_to: string | null;
  time: string | null;
  locations: string[];
  redemption_method: string | null;
  restrictions: string[];
  promo_code: string | null;
  more_info: string | null;
  // Added by geocode.py
  lat: number | null;
  lng: number | null;
}

interface RawRecord {
  channel: string;
  channel_title: string;
  message_id: number;
  posted_at: string;
  posted_date: string;
  input: string;
  prediction: RawPrediction;
}

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

function buildOffer(p: RawPrediction): string {
  if (p.discount) return p.discount;
  if (p.price) return p.price;
  return "DEAL";
}

// ── Title ─────────────────────────────────────────────────────────────────────

function buildTitle(p: RawPrediction): string {
  // Use first sentence / up to 70 chars of the offer field as the card title
  const raw = p.offer ?? "";
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
  // Simple hash to spread pins across the canvas
  const x = ((id * 137 + 29) % 72) + 10; // 10–82
  const y = ((id * 97 + 41) % 62) + 15; // 15–77
  return { x, y };
}

// ── more_info → full URL ───────────────────────────────────────────────────────

function buildMoreInfoUrl(raw: string | null): string | undefined {
  if (!raw) return undefined;
  // Strip any markdown link junk like "bit.ly/foo](http://bit.ly/foo)"
  const clean = raw.replace(/\]\(.*?\)/, "").trim();
  if (!clean) return undefined;
  // If it already has a protocol, use it as-is
  if (/^https?:\/\//i.test(clean)) return clean;
  return `https://${clean}`;
}

export function rawToDeal(record: RawRecord): Deal {
  const p = record.prediction;
  const location = p.locations.length > 0 ? p.locations[0] : "Singapore";
  const locationStr: string = location ?? "Singapore";

  const terms = [
    ...(p.restrictions ?? []),
    p.redemption_method ? `Redeem via: ${p.redemption_method}` : null,
    p.promo_code ? `Code: ${p.promo_code}` : null,
  ]
    .filter(Boolean)
    .join(". ");

  const deal: Deal = {
    id: `${record.channel}-${record.message_id}`,
    merchant: p.merchant,
    title: buildTitle(p),
    description: p.offer,
    terms: terms || "T&Cs apply.",
    offer: buildOffer(p),
    category: normaliseCategory(p.category),
    location: locationStr,
    address: locationStr,
    distanceKm: 0,
    expiry: formatExpiry(p.valid_to),
    expiresSoon: isExpiresSoon(p.valid_to),
    scrapedAgo: scrapedAgo(record.posted_at),
    channel: `@${record.channel}`,
    openingHours: p.time ?? "",
    trending: false,
    map: mapPos(record.message_id),
    originalPost: record.input.replace(/\*\*/g, "").replace(/@\w+/g, "").trim(),
  };

  const url = buildMoreInfoUrl(p.more_info);
  if (url) deal.moreInfoUrl = url;

  if (p.lat != null) deal.lat = p.lat;
  if (p.lng != null) deal.lng = p.lng;

  return deal;
}

// ── Fetch + parse ─────────────────────────────────────────────────────────────

export async function fetchDeals(): Promise<Deal[]> {
  const res = await fetch("/processed_geo.jsonl");
  if (!res.ok) throw new Error(`Failed to load deals: ${res.status}`);

  const text = await res.text();
  const lines = text.split("\n").filter((l) => l.trim());

  const deals: Deal[] = [];
  const seen = new Set<string>();

  for (const line of lines) {
    try {
      const record = JSON.parse(line) as RawRecord;
      const deal = rawToDeal(record);

      // De-duplicate by merchant + offer in case channels cross-post the same deal
      const key = `${deal.merchant.toLowerCase()}::${deal.offer.toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);

      deals.push(deal);
    } catch {
      // Skip malformed lines
    }
  }

  // Sort newest-first
  return deals.sort(
    (a, b) => new Date(b.scrapedAgo).getTime() - new Date(a.scrapedAgo).getTime(),
  );
}
