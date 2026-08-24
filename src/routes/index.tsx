import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Sparkles, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";

import { CategoryChips, type ChipValue } from "@/components/CategoryChips";
import { DealCard } from "@/components/DealCard";
import { SearchBar } from "@/components/SearchBar";
import { deals } from "@/data/deals";
import { useSavedDeals } from "@/hooks/useSavedDeals";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DealHub — Discover the best deals around you in Singapore" },
      {
        name: "description",
        content:
          "DealHub turns Telegram promo channels into clean, searchable, location-aware deal cards. Find discounts near you across food, shopping, beauty and travel.",
      },
      { property: "og:title", content: "DealHub — Deal discovery for Singapore" },
      {
        property: "og:description",
        content:
          "Promotions from Telegram channels, organised into a location-aware deal discovery feed.",
      },
    ],
  }),
  component: Home,
});

function Home() {
  const [query, setQuery] = useState("");
  const [chip, setChip] = useState<ChipValue>("all");
  const navigate = useNavigate();
  const { isSaved, toggle } = useSavedDeals();

  const trending = useMemo(() => deals.filter((d) => d.trending), []);
  const filtered = useMemo(() => {
    if (chip === "all") return deals;
    if (chip === "trending") return deals.filter((d) => d.trending);
    if (chip === "near") return [...deals].sort((a, b) => a.distanceKm - b.distanceKm).slice(0, 6);
    return deals.filter((d) => d.category === chip);
  }, [chip]);

  return (
    <div className="mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8 lg:pt-16">
      <section className="mx-auto max-w-3xl text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-medium text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" />
          {deals.length} live promotions collected from Telegram channels
        </span>
        <h1 className="mt-5 text-balance text-4xl font-bold leading-[1.05] sm:text-5xl lg:text-6xl">
          Discover the best deals around you.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-pretty text-base text-muted-foreground sm:text-lg">
          We read the messy promo channels so you don't have to — every offer cleaned up,
          mapped and checked for expiry.
        </p>

        <div className="mt-7">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSubmit={() => navigate({ to: "/search", search: { q: query } })}
          />
        </div>
      </section>

      <section className="mt-8">
        <CategoryChips value={chip} onChange={setChip} />
      </section>

      <section className="mt-14">
        <div className="flex items-end justify-between gap-4">
          <h2 className="flex items-center gap-2 text-2xl font-bold">
            <TrendingUp className="size-5 text-primary" />
            Trending deals
          </h2>
          <Link
            to="/categories"
            className="text-sm font-semibold text-primary hover:underline"
          >
            Browse categories
          </Link>
        </div>
        <div className="no-scrollbar -mx-4 mt-5 flex snap-x snap-mandatory gap-5 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
          {trending.map((deal) => (
            <DealCard
              key={deal.id}
              deal={deal}
              saved={isSaved(deal.id)}
              onToggleSave={toggle}
              className="w-[290px] shrink-0 snap-start"
            />
          ))}
        </div>
      </section>

      <section className="mt-14">
        <h2 className="text-2xl font-bold">
          {chip === "near" ? "Closest to you" : "Fresh from the channels"}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {filtered.length} deals · sorted by what's newest and still valid
        </p>
        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((deal) => (
            <DealCard
              key={deal.id}
              deal={deal}
              saved={isSaved(deal.id)}
              onToggleSave={toggle}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
