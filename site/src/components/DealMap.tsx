import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { ExternalLink, Navigation } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

import { categoryMap, type Deal } from "@/data/deals";
import { cn } from "@/lib/utils";

// ── Fix Leaflet's broken default icon paths under Vite ────────────────────────
// Leaflet tries to resolve image URLs relative to leaflet.css which doesn't
// work in bundled environments. We point it at the CDN copies instead.
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)["_getIconUrl"];
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// ── Category-coloured circle markers ─────────────────────────────────────────

const CATEGORY_COLOURS: Record<string, string> = {
  food: "#f97316",
  shopping: "#8b5cf6",
  beauty: "#ec4899",
  entertainment: "#06b6d4",
  travel: "#3b82f6",
  hotels: "#0ea5e9",
  electronics: "#64748b",
  fitness: "#22c55e",
  services: "#a78bfa",
};

function makeIcon(category: string, active: boolean): L.DivIcon {
  const colour = CATEGORY_COLOURS[category] ?? "#f97316";
  const size = active ? 36 : 28;
  const border = active ? 3 : 2;
  return L.divIcon({
    className: "",
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
    html: `
      <div style="
        width:${size}px;height:${size}px;
        border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);
        background:${colour};
        border:${border}px solid white;
        box-shadow:0 2px 6px rgba(0,0,0,.35);
        display:flex;align-items:center;justify-content:center;
      ">
        <span style="transform:rotate(45deg);font-size:${active ? 14 : 11}px;line-height:1">
          ${categoryMap[category as keyof typeof categoryMap]?.emoji ?? "📍"}
        </span>
      </div>`,
  });
}

// ── Helper: pan map to selected deal ─────────────────────────────────────────

function MapFlyTo({
  deals,
  selectedId,
}: {
  deals: Deal[];
  selectedId: string | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (!selectedId) return;
    const deal = deals.find((d) => d.id === selectedId);
    if (deal?.lat != null && deal?.lng != null) {
      map.flyTo([deal.lat, deal.lng], 15, { duration: 0.8 });
    }
  }, [selectedId, deals, map]);
  return null;
}

// ── User location blue dot ────────────────────────────────────────────────────

function UserLocationMarker() {
  const map = useMap();
  const [position, setPosition] = useState<[number, number] | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => setPosition([pos.coords.latitude, pos.coords.longitude]),
      (err) => console.warn("Geolocation error:", err),
      { enableHighAccuracy: true },
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [map]);

  if (!position) return null;

  return (
    <CircleMarker
      center={position}
      radius={8}
      pathOptions={{
        color: "white",
        fillColor: "#3b82f6",
        fillOpacity: 1,
        weight: 2,
      }}
    />
  );
}

function LocateMeButton() {
  const map = useMap();

  const handleLocate = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        map.flyTo([pos.coords.latitude, pos.coords.longitude], 15, {
          duration: 1,
        });
      },
      (err) => console.warn("Geolocation error:", err),
    );
  };

  return (
    <button
      onClick={handleLocate}
      title="Go to my location"
      className="absolute bottom-4 right-4 z-[1000] flex size-9 items-center justify-center rounded-full border border-border bg-background shadow-md transition-colors hover:bg-accent"
    >
      <Navigation className="size-4 text-foreground" />
    </button>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

type Props = {
  deals: Deal[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  className?: string;
  /** Centre of the map — defaults to Singapore CBD */
  center?: [number, number];
  zoom?: number;
};

const SG_CENTRE: [number, number] = [1.3521, 103.8198];

export function DealMap({
  deals,
  selectedId,
  onSelect,
  className,
  center = SG_CENTRE,
  zoom = 12,
}: Props) {
  const mappable = deals.filter((d) => d.lat != null && d.lng != null);
  // Keep a stable ref so MapContainer doesn't remount on re-render
  const centerRef = useRef(center);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-2xl)] border border-border",
        className,
      )}
    >
      {mappable.length === 0 && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-card text-muted-foreground">
          <Navigation className="size-8 opacity-40" />
          <p className="text-sm">No mappable deals in this selection</p>
        </div>
      )}

      <MapContainer
        center={centerRef.current}
        zoom={zoom}
        scrollWheelZoom
        className="size-full"
        // Leaflet needs an explicit pixel height via CSS — the parent div provides it
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapFlyTo deals={deals} selectedId={selectedId} />

        <LocateMeButton />

        <UserLocationMarker />

        {mappable.map((deal) => (
          <Marker
            key={deal.id}
            position={[deal.lat!, deal.lng!]}
            icon={makeIcon(deal.category, deal.id === selectedId)}
            eventHandlers={{
              click: () => onSelect(deal.id === selectedId ? null : deal.id),
            }}
            zIndexOffset={deal.id === selectedId ? 1000 : 0}
          >
            <Popup
              offset={[0, -28]}
              className="deal-map-popup"
              closeButton={false}
            >
              <PopupCard deal={deal} />
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

// ── Popup card ────────────────────────────────────────────────────────────────

function PopupCard({ deal }: { deal: Deal }) {
  const hasExternalLink = Boolean(deal.moreInfoUrl);
  return (
    <div className="w-56 space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {deal.merchant}
      </p>
      <p className="font-display text-sm font-bold leading-snug">{deal.title}</p>
      <p className="text-xs text-muted-foreground">
        📍 {deal.location}
        {deal.expiry !== "Ongoing" && (
          <> &nbsp;·&nbsp; ⏰ Ends {deal.expiry}</>
        )}
      </p>
      <div className="pt-1">
        {hasExternalLink ? (
          <a
            href={deal.moreInfoUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            <ExternalLink className="size-3" />
            View deal
          </a>
        ) : (
          <Link
            to="/deal/$dealId"
            params={{ dealId: deal.id }}
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Navigation className="size-3" />
            View deal
          </Link>
        )}
      </div>
    </div>
  );
}
