import postgres from "postgres";
import { createClient } from "@supabase/supabase-js";
import { config } from "dotenv";
import path from "path";

import type { DbDeal } from "./deals.types";

// dotenv does not override vars already in the environment. Always load so
// local `vite dev` still picks up SUPABASE_BUCKET when DATABASE_URL is exported.
config({ path: path.resolve(import.meta.dirname, "../../..", ".env") });

function getDb() {
  const url = process.env["DATABASE_URL"];
  if (!url) throw new Error("DATABASE_URL is not set");
  // Pass ssl as an option rather than relying on the query string,
  // which postgres.js may not parse correctly
  return postgres(url, { ssl: "require", max: 5, connection: { application_name: "promo-radar-scan" } });
}

export async function queryAllDeals(): Promise<DbDeal[]> {
  const sql = getDb();
  try {
    const rows = await sql<DbDeal[]>`
      SELECT
        d.channel,
        d.channel_title,
        d.message_id,
        d.posted_at::text,
        d.posted_date::text,
        d.raw_input,
        d.merchant,
        d.category,
        d.offer,
        d.price,
        d.original_price,
        d.discount,
        d.valid_from::text,
        d.valid_to::text,
        d.time,
        d.locations,
        d.redemption_method,
        d.restrictions,
        d.promo_code,
        d.more_info,
        r.image_url AS image_url
      FROM deals d
      LEFT JOIN raw_messages r
        ON r.channel = d.channel AND r.message_id = d.message_id
      ORDER BY d.posted_at DESC
    `;
    return rows.map((row) => ({
      ...row,
      image_url: decodeImageUrlValue(row.image_url),
    }));
  } finally {
    await sql.end();
  }
}

// ── Supabase signed URL ────────────────────────────────────────────────────────

function getSupabaseClient() {
  const url = process.env["SUPABASE_URL"];
  const key = process.env["SUPABASE_SERVICE_KEY"];  // service role key — server only
  if (!url || !key) throw new Error("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set");
  return createClient(url, key);
}

const SUPABASE_BUCKET = process.env["SUPABASE_BUCKET"] ?? "deal-images";
const SIGNED_URL_EXPIRY_SECONDS = 60 * 60; // 1 hour

/** Decode BYTEA-as-text (`\\x6869…`) or a Buffer from postgres.js. */
function decodeImageUrlValue(raw: unknown): string | null {
  if (raw == null) return null;
  if (typeof raw !== "string") {
    if (raw instanceof Uint8Array) return new TextDecoder().decode(raw);
    return String(raw);
  }
  const trimmed = raw.trim();
  if (/^\\x[0-9a-f]+$/i.test(trimmed)) {
    const bytes = trimmed.slice(2);
    if (bytes.length % 2 === 0) {
      return Buffer.from(bytes, "hex").toString("utf8");
    }
  }
  return trimmed;
}

/** Object key in the bucket, e.g. "sgfooddeals/4908.jpg". Accepts a key or a public/signed Storage URL. */
export function toStorageObjectPath(raw: unknown): string | null {
  const decoded = decodeImageUrlValue(raw);
  if (!decoded) return null;
  const value = decoded.trim();
  if (!value) return null;

  const fromUrl = value.match(
    /\/storage\/v1\/object\/(?:public|sign)\/[^/]+\/(.+?)(?:\?|$)/,
  );
  if (fromUrl?.[1]) return decodeURIComponent(fromUrl[1]);

  if (/^https?:\/\//i.test(value)) return null;
  return value.replace(/^\//, "");
}

export async function getSupabaseSignedUrl(storagePath: string): Promise<string | null> {
  const key = toStorageObjectPath(storagePath);
  if (!key) return null;
  const urls = await getSupabaseSignedUrls([key]);
  return urls[key] ?? null;
}

export async function getSupabaseSignedUrls(
  storagePaths: string[],
): Promise<Record<string, string>> {
  const unique = [...new Set(storagePaths.map((p) => toStorageObjectPath(p)).filter((p): p is string => Boolean(p)))];
  if (unique.length === 0) return {};

  try {
    const supabase = getSupabaseClient();
    const { data, error } = await supabase.storage
      .from(SUPABASE_BUCKET)
      .createSignedUrls(unique, SIGNED_URL_EXPIRY_SECONDS);
    if (error || !data) {
      console.error("Supabase createSignedUrls failed:", error?.message ?? "no data");
      return {};
    }

    const out: Record<string, string> = {};
    data.forEach((item, i) => {
      const key = toStorageObjectPath(item.path) ?? unique[i];
      if (item.error) {
        console.error("Supabase signed URL error for", unique[i], item.error);
      }
      if (item.signedUrl && key) {
        out[key] = item.signedUrl;
        out[unique[i]!] = item.signedUrl;
      }
    });
    return out;
  } catch (err) {
    console.error("Supabase createSignedUrls threw:", err);
    return {};
  }
}
