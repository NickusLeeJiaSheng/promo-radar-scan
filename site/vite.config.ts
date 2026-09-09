import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import path from "path";
import { config as loadDotenv } from "dotenv";
import postgres from "postgres";

// Load repo-root .env at config time so DATABASE_URL is available in the plugin
loadDotenv({ path: path.resolve(__dirname, "../.env") });

// ── Vite plugin: serve /api/deals from Neon DB during dev ─────────────────────
function dealsApiPlugin() {
  return {
    name: "deals-api",
    configureServer(server: import("vite").ViteDevServer) {
      server.middlewares.use("/api/deals", async (_req, res) => {
        const url = process.env["DATABASE_URL"];
        if (!url) {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "DATABASE_URL not set" }));
          return;
        }
        const sql = postgres(url, { ssl: "require", max: 2 });
        try {
          const rows = await sql`
            SELECT
              d.channel, d.channel_title, d.message_id,
              d.posted_at::text, d.posted_date::text,
              d.raw_input, d.merchant, d.category, d.offer,
              d.price, d.original_price, d.discount,
              d.valid_from::text, d.valid_to::text,
              d.time, d.locations, d.redemption_method,
              d.restrictions, d.promo_code, d.more_info,
              r.image_url
            FROM deals d
            LEFT JOIN raw_messages r
              ON r.channel = d.channel AND r.message_id = d.message_id
            ORDER BY d.posted_at DESC
          `;
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(rows));
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e);
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: msg }));
        } finally {
          await sql.end();
        }
      });
    },
  };
}

export default defineConfig({
  // Load .env from the repo root (one level up from site/)
  envDir: path.resolve(__dirname, ".."),
  base: "/promo-radar-scan/",
  plugins: [
    TanStackRouterVite({ autoCodeSplitting: true }),
    react(),
    tailwindcss(),
    tsconfigPaths({ projects: ["./tsconfig.json"] }),
    dealsApiPlugin(),
  ],
  build: {
    outDir: "dist",
    rollupOptions: {
      input: "./index.html",
    },
  },
});
