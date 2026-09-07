/**
 * functions/index.js
 * Google Cloud Function — HTTP endpoint that serves deal data.
 *
 * GET /deals
 *   → queries Neon DB for all deals
 *   → generates Supabase signed URLs for private bucket images
 *   → returns JSON array of DbDeal objects
 *
 * Environment variables (set via GCF console or --set-env-vars in CI):
 *   DATABASE_URL          — Neon PostgreSQL connection string
 *   SUPABASE_URL          — Supabase project URL
 *   SUPABASE_SERVICE_KEY  — Supabase service role key (kept server-side only)
 *   SUPABASE_BUCKET       — Supabase storage bucket name
 *   ALLOWED_ORIGIN        — Your GitHub Pages URL, e.g. https://nicokusleejiasheng.github.io
 */

import { http } from "@google-cloud/functions-framework";
import postgres from "postgres";
import { createClient } from "@supabase/supabase-js";
import { config } from "dotenv";
import { fileURLToPath } from "url";
import { resolve, dirname } from "path";

// Load .env from the repo root (one level up from functions/) when running locally
const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "..", ".env") });

// ── Config ────────────────────────────────────────────────────────────────────

const DATABASE_URL    = process.env.DATABASE_URL;
const SUPABASE_URL    = process.env.SUPABASE_URL;
const SUPABASE_KEY    = process.env.SUPABASE_SERVICE_KEY;
const SUPABASE_BUCKET = process.env.SUPABASE_BUCKET ?? "deal-images";
const ALLOWED_ORIGIN  = process.env.ALLOWED_ORIGIN ?? "*";

const SIGNED_URL_EXPIRY = 60 * 60; // 1 hour

// ── Postgres connection (reused across warm invocations) ──────────────────────

let _sql;
function getDb() {
  if (!DATABASE_URL) throw new Error("DATABASE_URL is not set");
  if (!_sql) {
    _sql = postgres(DATABASE_URL, {
      ssl: "require",
      max: 3,
      idle_timeout: 20,
      connection: { application_name: "promo-radar-gcf" },
    });
  }
  return _sql;
}

// ── Supabase client ───────────────────────────────────────────────────────────

let _supabase;
function getSupabase() {
  if (!SUPABASE_URL || !SUPABASE_KEY) throw new Error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set");
  if (!_supabase) _supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
  return _supabase;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Decode BYTEA-as-hex string (\\x6869…) returned by postgres.js */
function decodeImageUrl(raw) {
  if (raw == null) return null;
  if (raw instanceof Uint8Array) return new TextDecoder().decode(raw);
  const s = String(raw).trim();
  if (/^\\x[0-9a-f]+$/i.test(s) && s.length % 2 === 0) {
    return Buffer.from(s.slice(2), "hex").toString("utf8");
  }
  return s || null;
}

/** Extract storage object path from a URL or plain key */
function toStoragePath(raw) {
  const decoded = decodeImageUrl(raw);
  if (!decoded) return null;
  const v = decoded.trim();
  const match = v.match(/\/storage\/v1\/object\/(?:public|sign)\/[^/]+\/(.+?)(?:\?|$)/);
  if (match?.[1]) return decodeURIComponent(match[1]);
  if (/^https?:\/\//i.test(v)) return null;
  return v.replace(/^\//, "") || null;
}

/** Bulk-generate signed URLs; returns { storagePath → signedUrl } */
async function getSignedUrls(imageUrls) {
  const paths = [...new Set(imageUrls.map(toStoragePath).filter(Boolean))];
  if (paths.length === 0) return {};
  const { data, error } = await getSupabase()
    .storage.from(SUPABASE_BUCKET)
    .createSignedUrls(paths, SIGNED_URL_EXPIRY);
  if (error || !data) {
    console.error("Supabase createSignedUrls failed:", error?.message ?? "no data");
    return {};
  }
  const out = {};
  data.forEach((item, i) => {
    const key = toStoragePath(item.path) ?? paths[i];
    if (item.signedUrl && key) {
      out[key] = item.signedUrl;
      out[paths[i]] = item.signedUrl;
    }
  });
  return out;
}

// ── Cloud Function ────────────────────────────────────────────────────────────

http("deals", async (req, res) => {
  // CORS headers
  res.set("Access-Control-Allow-Origin", ALLOWED_ORIGIN);
  res.set("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.set("Access-Control-Allow-Headers", "Content-Type");
  res.set("Cache-Control", "public, max-age=300"); // 5-min CDN cache

  if (req.method === "OPTIONS") {
    res.status(204).send("");
    return;
  }

  if (req.method !== "GET") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }

  try {
    const sql = getDb();

    const rows = await sql`
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

    // Decode BYTEA image_url values
    const decoded = rows.map((row) => ({
      ...row,
      image_url: decodeImageUrl(row.image_url),
    }));

    // Replace storage paths with signed URLs
    const signed = await getSignedUrls(decoded.map((r) => r.image_url));
    const result = decoded.map((row) => {
      const path = toStoragePath(row.image_url);
      const signedUrl = path ? signed[path] : undefined;
      return signedUrl ? { ...row, image_url: signedUrl } : row;
    });

    res.status(200).json(result);
  } catch (err) {
    console.error("GCF /deals error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});
