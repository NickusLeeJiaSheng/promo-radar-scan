import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { fallback, zodValidator } from "@tanstack/zod-adapter";
import { useMemo, useState } from "react";
import { z } from "zod";

import { DealCard } from "@/components/DealCard";
import { SearchBar } from "@/components/SearchBar";
import { categories, matchesQuery } from "@/data/deals";
import { filterDeals, useDeals } from "@/hooks/useDeals";
import { cn } from "@/lib/utils";

const searchSchema = z.object({
  q: fallback(z.string(), "").default(""),
});

export const Route = createFileRoute("/search")({
  validateSearch: zodValidator(searchSchema),
  head: () => ({
    meta: [
      { title: "Search Deals — DealHub" },
      {
        name: "description",
        content:
          "Search Singapore promotions by merchant, brand, category, location or keyword, then filter by distance, discount and expiry.",
      },
      { property: "og:title", content: "Search Deals — DealHub" },
      {
        property: "og:description",
        content: "Fast search across every promotion collected from Telegram channels.",
      },
    ],
  }),
  component: SearchPage,
});

type SortKey = "newest" | "distance" | "discount" | "expiry";

const sorts: { id: SortKey; label: string }[] = [
  { id: "newest", label: "Newest" },
  { id: "distance", label: "Distance" },
  { id: "discount", label: "Discount" },
  { id: "expiry", label: "Expiring soon" },
];

function discountValue(offer: string) {
  const pct = offer.match(/(\d+)%/);
  if (pct) return Number(pct[1]);
  const dollars = offer.match(/\$(\d+)/);
  if (dollars) return Number(dollars[1]);
  return 25;
}

function SearchPage() {
  const { q } = Route.useSearch();
  const navigate = useNavigate();
  const [input, setInput] = useState(q);
  const [category, setCategory] = useState<string>("all");
  const [sort, setSort] = useState<SortKey>("newest");
  const [maxDistance, setMaxDistance] = useState(20);

  const { data: allDeals = [] } = useDeals();

  const results = useMemo(() => {
    const list = allDeals
      .filter((d) => matchesQuery(d, q))
      .filter((d) => category === "all" || d.category === category)
      .filter((d) => d.distanceKm <= maxDistance);

    return [...list].sort((a, b) => {
      if (sort === "distance") return a.distanceKm - b.distanceKm;
      if (sort === "discount") return discountValue(b.offer) - discountValue(a.offer);
      if (sort === "expiry") return Number(!!b.expiresSoon) - Number(!!a.expiresSoon);
      return 0;
    });
  }, [allDeals, q, category, sort, maxDistance]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold sm:text-4xl">Search</h1>
      <div className="mt-5 max-w-3xl">
        <SearchBar
          value={input}
          onChange={setInput}
          onSubmit={() => navigate({ to: "/search", search: { q: input } })}
          placeholder="Merchant, brand, category, location or keyword..."
        />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium outline-none focus:border-primary"
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
          Within
          <input
            type="range"
            min={1}
            max={20}
            value={maxDistance}
            onChange={(e) => setMaxDistance(Number(e.target.value))}
            className="accent-primary"
          />
          <span className="font-medium text-foreground">{maxDistance} km</span>
        </label>

        <div className="flex flex-wrap gap-1.5">
          {sorts.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSort(s.id)}
              className={cn(
                "rounded-full border px-3.5 py-2 text-sm font-medium transition-colors",
                sort === s.id
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:text-foreground",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <p className="mt-6 text-sm text-muted-foreground">
        {results.length} {results.length === 1 ? "result" : "results"}
        {q ? ` for “${q}”` : ""}
      </p>

      {results.length ? (
        <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {results.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      ) : (
        <div className="surface-panel mt-5 p-14 text-center">
          <p className="font-display text-lg font-bold">No deals match that search</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Try a broader keyword, or widen the distance filter.
          </p>
        </div>
      )}
    </div>
  );
}
