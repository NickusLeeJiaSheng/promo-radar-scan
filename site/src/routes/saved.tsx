import { createFileRoute, Link } from "@tanstack/react-router";
import { Heart } from "lucide-react";

import { DealCard } from "@/components/DealCard";
import { useDeals } from "@/hooks/useDeals";
import { useSavedDeals } from "@/hooks/useSavedDeals";

export const Route = createFileRoute("/saved")({
  head: () => ({
    meta: [
      { title: "Saved Deals — DealHub" },
      {
        name: "description",
        content: "Your shortlist of saved Singapore promotions, kept in one place until they expire.",
      },
      { property: "og:title", content: "Saved Deals — DealHub" },
      { property: "og:description", content: "Your shortlisted promotions on DealHub." },
    ],
  }),
  component: Saved,
});

function Saved() {
  const { saved, isSaved, toggle } = useSavedDeals();
  const { data: allDeals = [] } = useDeals();
  const items = allDeals.filter((d) => saved.includes(d.id));

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold sm:text-4xl">Saved deals</h1>
      <p className="mt-2 text-muted-foreground">
        {items.length ? `${items.length} deals shortlisted.` : "Nothing saved yet."}
      </p>

      {items.length ? (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((deal) => (
            <DealCard key={deal.id} deal={deal} saved={isSaved(deal.id)} onToggleSave={toggle} />
          ))}
        </div>
      ) : (
        <div className="surface-panel mt-8 flex flex-col items-center gap-3 p-14 text-center">
          <span className="grid size-14 place-items-center rounded-2xl bg-accent">
            <Heart className="size-6 text-primary" />
          </span>
          <p className="font-display text-lg font-bold">Tap the heart on any deal</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            Saved deals stay on this device so you can check them before they expire.
          </p>
          <Link
            to="/"
            className="mt-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
          >
            Discover deals
          </Link>
        </div>
      )}
    </div>
  );
}
