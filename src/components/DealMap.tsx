import { Link } from "@tanstack/react-router";
import { Navigation, X } from "lucide-react";

import { categoryMap, type Deal } from "@/data/deals";
import { cn } from "@/lib/utils";

type Props = {
  deals: Deal[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  className?: string;
};

/** Stylised city map. Markers are positioned from each deal's map coordinates. */
export function DealMap({ deals, selectedId, onSelect, className }: Props) {
  const selected = deals.find((d) => d.id === selectedId) ?? null;

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-2xl)] border border-border bg-surface",
        className,
      )}
    >
      <svg
        aria-hidden
        className="absolute inset-0 size-full text-border"
        preserveAspectRatio="none"
        viewBox="0 0 100 100"
      >
        <defs>
          <pattern id="blocks" width="9" height="9" patternUnits="userSpaceOnUse">
            <path d="M9 0V9H0" fill="none" stroke="currentColor" strokeWidth="0.3" />
          </pattern>
        </defs>
        <rect width="100" height="100" fill="url(#blocks)" />
        <path
          d="M0 46 L100 38"
          stroke="currentColor"
          strokeWidth="2.4"
          fill="none"
          opacity="0.8"
        />
        <path d="M30 0 L38 100" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.7" />
        <path d="M72 0 L64 100" stroke="currentColor" strokeWidth="1.6" fill="none" opacity="0.6" />
        <path
          d="M0 78 C 25 70, 55 88, 100 74 L100 100 L0 100 Z"
          className="fill-primary/10"
          stroke="none"
        />
      </svg>

      {/* User position */}
      <div
        className="absolute -translate-x-1/2 -translate-y-1/2"
        style={{ left: "48%", top: "50%" }}
      >
        <span className="block size-4 rounded-full border-2 border-card bg-foreground shadow-[var(--shadow-soft)]" />
        <span className="absolute inset-0 -z-10 -m-6 rounded-full bg-foreground/10 blur-md" />
      </div>

      {deals.map((deal) => {
        const active = deal.id === selectedId;
        return (
          <button
            key={deal.id}
            type="button"
            onClick={() => onSelect(active ? null : deal.id)}
            aria-label={`${deal.merchant} — ${deal.title}`}
            className={cn(
              "absolute flex -translate-x-1/2 -translate-y-full items-center gap-1 rounded-full border px-2.5 py-1.5 text-xs font-semibold shadow-[var(--shadow-soft)] transition-all duration-200",
              active
                ? "z-20 scale-110 border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-foreground hover:-translate-y-[110%] hover:border-primary",
            )}
            style={{ left: `${deal.map.x}%`, top: `${deal.map.y}%` }}
          >
            <span>{categoryMap[deal.category].emoji}</span>
            <span className="hidden sm:inline">{deal.offer}</span>
          </button>
        );
      })}

      {selected && (
        <div className="absolute inset-x-4 bottom-4 z-30 mx-auto max-w-sm rounded-[var(--radius-xl)] border border-border bg-card p-4 shadow-[var(--shadow-lift)]">
          <button
            type="button"
            aria-label="Close preview"
            onClick={() => onSelect(null)}
            className="absolute right-3 top-3 text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="size-4" />
          </button>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {selected.merchant}
          </p>
          <p className="mt-1 font-display text-base font-bold">{selected.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            📍 {selected.distanceKm} km away · ⏰{" "}
            {selected.expiresSoon ? selected.expiry : `Ends ${selected.expiry}`}
          </p>
          <Link
            to="/deal/$dealId"
            params={{ dealId: selected.id }}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Navigation className="size-3.5" />
            View deal
          </Link>
        </div>
      )}
    </div>
  );
}
