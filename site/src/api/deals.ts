import { createServerFn } from "@tanstack/react-start";

import type { DbDeal } from "./deals.types";

export const fetchDealsFromDb = createServerFn({ method: "GET" }).handler(
  async (): Promise<DbDeal[]> => {
    const { queryAllDeals, getSupabaseSignedUrls, toStorageObjectPath } = await import(
      "./deals.server"
    );
    const rows = await queryAllDeals();
    const signed = await getSupabaseSignedUrls(rows.map((r) => r.image_url));

    return rows.map((row) => {
      const key = toStorageObjectPath(row.image_url);
      const signedUrl = key ? signed[key] : undefined;
      if (signedUrl) return { ...row, image_url: signedUrl };
      return row;
    });
  },
);

// Generates a short-lived signed URL for a private Supabase Storage image.
// Called per-card so the URL is always fresh.
export const getSignedImageUrl = createServerFn({ method: "GET" })
  .validator((path: string) => path)
  .handler(async ({ data: storagePath }): Promise<string | null> => {
    if (!storagePath) return null;
    const { getSupabaseSignedUrl } = await import("./deals.server");
    return getSupabaseSignedUrl(storagePath);
  });
