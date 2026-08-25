import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

export default defineConfig(({ command }) => ({
  plugins: [
    tsconfigPaths({ projects: ["./tsconfig.json"] }),
    tanstackStart({
      server: { entry: "server" },
    }),
    react(),
    tailwindcss(),
    // Only run the Nitro/Cloudflare bundler during builds
    ...(command === "build"
      ? [
          nitro({
            defaultPreset: "cloudflare-module",
          }),
        ]
      : []),
  ],
}));
