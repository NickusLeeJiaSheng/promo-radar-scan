import { createFileRoute } from "@tanstack/react-router";
import { Loader2, LocateFixed, MapPin } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { DealCard, DealRow } from "@/components/DealCard";
import { DealMap } from "@/components/DealMap";
import { type Deal } from "@/data/deals";
import { useDeals } from "@/hooks/useDeals";
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

// ── Haversine distance (km) ───────────────────────────────────────────────────

function haversine(
  lat1: number, lng1: number,
  lat2: number, lng2: number,
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Default centre: Singapore CBD
const SG_CENTRE: [number, number] = [1.3521, 103.8198];

// ── Geolocation hook ──────────────────────────────────────────────────────────

type GeoState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ok"; lat: number; lng: number }
  | { status: "error"; message: string };

function useGeolocation() {
  const [state, setState] = useState<GeoState>({ status: "idle" });

  function request() {
    if (!navigator.geolocation) {
      setState({ status: "error", message: "Geolocation not supported by your browser." });
      return;
    }
    setState({ status: "loading" });
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        setState({ status: "ok", lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) =>
        setState({
          status: "error",
          message:
            err.code === 1
              ? "Location access denied. Showing all deals."
              : "Could not get your location. Showing all deals.",
        }),
      { timeout: 10_000, maximumAge: 60_000 },
    );
  }

  return { state, request };
}

// ── Component ─────────────────────────────────────────────────────────────────

function NearMe() {
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"map" | "list">("map");
  const [radius, setRadius] = useState(6);

  const { data: allDeals = [], isLoading: dealsLoading } = useDeals();
  const { state: geo, request: requestGeo } = useGeolocation();

  // Auto-request on mount
  useEffect(() => {
    requestGeo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const userPos: [number, number] =
    geo.status === "ok" ? [geo.lat, geo.lng] : SG_CENTRE;

  // Attach real distances and filter to mappable + within radius
  const dealsWithDist = useMemo<(Deal & { distanceKm: number })[]>(() => {
    return allDeals
      .filter((d): d is Deal & { lat: number; lng: number } =>
        d.lat != null && d.lng != null,
      )
      .map((d) => ({
        ...d,
        distanceKm: parseFloat(
          haversine(userPos[0], userPos[1], d.lat, d.lng).toFixed(1),
        ),
      }));
  }, [allDeals, userPos]);

  const nearby = useMemo(
    () =>
      dealsWithDist
        .filter((d) => d.distanceKm <= radius)
        .sort((a, b) => a.distanceKm - b.distanceKm),
    [dealsWithDist, radius],
  );

  const isLocating = geo.status === "loading" || geo.status === "idle";

  const locationLabel =
    geo.status === "ok"
      ? `Your location · ${nearby.length} deals within ${radius} km`
      : geo.status === "error"
        ? `${geo.message}`
        : "Locating you…";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Near me</h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
            {isLocating ? (
              <Loader2 className="size-4 animate-spin text-primary" />
            ) : (
              <MapPin className="size-4 text-primary" />
            )}
            {locationLabel}
            <button
              type="button"
              onClick={requestGeo}
              disabled={isLocating}
              aria-label="Refresh location"
              className="ml-1 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline disabled:opacity-40"
            >
              <LocateFixed className="size-3" />
              {geo.status === "error" ? "Retry" : "Refresh"}
            </button>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
            Radius
            <input
              type="range"
              min={1}
              max={30}
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
                  view === v
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Mobile radius row (shown only on small screens) ──────────────────── */}
      <div className="mt-3 flex items-center gap-3 sm:hidden">
        <span className="text-sm text-muted-foreground">Radius</span>
        <input
          type="range"
          min={1}
          max={30}
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          className="flex-1 accent-primary"
        />
        <span className="w-12 text-right text-sm font-medium text-foreground">{radius} km</span>
      </div>

      {/* ── Loading skeleton ────────────────────────────────────────────────── */}
      {dealsLoading && (
        <div className="mt-6 flex h-[420px] items-center justify-center rounded-[var(--radius-2xl)] border border-border bg-card lg:h-[620px]">
          <Loader2 className="size-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* ── Map view ────────────────────────────────────────────────────────── */}
      {!dealsLoading && view === "map" && (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <DealMap
            deals={nearby.length > 0 ? nearby : dealsWithDist}
            selectedId={selected}
            onSelect={setSelected}
            center={userPos}
            zoom={geo.status === "ok" ? 13 : 12}
            className="h-[420px] lg:h-[620px]"
          />

          <div className="surface-panel flex max-h-[620px] flex-col overflow-hidden">
            <div className="border-b border-border p-4">
              <h2 className="font-display text-lg font-bold">
                {nearby.length > 0
                  ? `${nearby.length} deal${nearby.length !== 1 ? "s" : ""} within ${radius} km`
                  : "All mapped deals"}
              </h2>
              <p className="text-xs text-muted-foreground">
                Hover a row to highlight it on the map
              </p>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {(nearby.length > 0 ? nearby : dealsWithDist).map((deal) => (
                <div
                  key={deal.id}
                  onMouseEnter={() => setSelected(deal.id)}
                  onMouseLeave={() => setSelected(null)}
                >
                  <DealRow deal={deal} distanceKm={deal.distanceKm} />
                </div>
              ))}
              {dealsWithDist.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No deals have a specific location to map.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── List view ───────────────────────────────────────────────────────── */}
      {!dealsLoading && view === "list" && (
        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {(nearby.length > 0 ? nearby : dealsWithDist).map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
          {dealsWithDist.length === 0 && (
            <p className="col-span-full py-16 text-center text-muted-foreground">
              No deals with a known location.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
