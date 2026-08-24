import { createFileRoute } from "@tanstack/react-router";
import { MapPin } from "lucide-react";
import { useMemo, useState } from "react";

import { DealCard, DealRow } from "@/components/DealCard";
import { DealMap } from "@/components/DealMap";
import { deals } from "@/data/deals";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/near-me")({
  head: () => ({
    meta: [
      { title: "Deals Near Me in Singapore — DealHub" },
      {
        name: "description",
        content:
          "See live promotions plotted on a map around your location, then switch to a list sorted by walking distance.",
      },
      { property: "og:title", content: "Deals Near Me — DealHub" },
      {
        property: "og:description",
        content: "A map-first view of promotions happening close to you right now.",
      },
    ],
  }),
  component: NearMe,
});

function NearMe() {
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"map" | "list">("map");
  const [radius, setRadius] = useState(6);

  const nearby = useMemo(
    () =>
      deals.filter((d) => d.distanceKm <= radius).sort((a, b) => a.distanceKm - b.distanceKm),
    [radius],
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Near me</h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPin className="size-4 text-primary" />
            Marina Bay, Singapore · {nearby.length} deals within {radius} km
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
            Radius
            <input
              type="range"
              min={1}
              max={20}
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="accent-primary"
            />
            <span className="w-10 font-medium text-foreground">{radius} km</span>
          </label>
          <div className="flex rounded-full border border-border bg-card p-1">
            {(["map", "list"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className={cn(
                  "rounded-full px-4 py-1.5 text-sm font-semibold capitalize transition-colors",
                  view === v ? "bg-primary text-primary-foreground" : "text-muted-foreground",
                )}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {view === "map" ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <DealMap
            deals={nearby}
            selectedId={selected}
            onSelect={setSelected}
            className="h-[420px] lg:h-[620px]"
          />
          <div className="surface-panel flex max-h-[620px] flex-col overflow-hidden">
            <div className="border-b border-border p-4">
              <h2 className="font-display text-lg font-bold">Deals near you</h2>
              <p className="text-xs text-muted-foreground">Tap a card to preview on the map</p>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {nearby.map((deal) => (
                <div key={deal.id} onMouseEnter={() => setSelected(deal.id)}>
                  <DealRow deal={deal} />
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {nearby.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      )}
    </div>
  );
}
