import postgres from "postgres";
import { config } from "dotenv";
import path from "path";

import type { DbDeal } from "./deals.types";

// Cloudflare/production sets DATABASE_URL in the environment; local dev loads repo-root .env.
if (!process.env["DATABASE_URL"]) {
  config({ path: path.resolve(import.meta.dirname, "../../..", ".env") });
}

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
    return await sql<DbDeal[]>`
      SELECT
        channel,
        channel_title,
        message_id,
        posted_at::text,
        posted_date::text,
        raw_input,
        merchant,
        category,
        offer,
        price,
        original_price,
        discount,
        valid_from::text,
        valid_to::text,
        time,
        locations,
        redemption_method,
        restrictions,
        promo_code,
        more_info
      FROM deals
      ORDER BY posted_at DESC
    `;
  } finally {
    await sql.end();
  }
}
