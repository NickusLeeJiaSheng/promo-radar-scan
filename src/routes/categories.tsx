import { createFileRoute, Link } from "@tanstack/react-router";

import { DealCard } from "@/components/DealCard";
import { categories, deals } from "@/data/deals";

export const Route = createFileRoute("/categories")({
  head: () => ({
    meta: [
      { title: "Browse Deal Categories — DealHub" },
      {
        name: "description",
        content:
          "Browse Singapore promotions by category: food and dining, shopping, beauty, entertainment, travel, hotels, electronics, fitness and services.",
      },
      { property: "og:title", content: "Browse Deal Categories — DealHub" },
      {
        property: "og:description",
        content: "Every Telegram promotion, organised into clean browsable categories.",
      },
    ],
  }),
  component: Categories,
});

function Categories() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold sm:text-4xl">Categories</h1>
      <p className="mt-2 max-w-xl text-muted-foreground">
        Pick a category to jump straight into the promotions that matter to you.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((category) => {
          const count = deals.filter((d) => d.category === category.id).length;
          return (
            <Link
              key={category.id}
              to="/search"
              search={{ q: category.label }}
              className="deal-card group flex items-center gap-4 p-5"
            >
              <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-accent text-2xl transition-transform duration-300 group-hover:scale-110">
                {category.emoji}
              </span>
              <span className="min-w-0">
                <span className="block font-display text-lg font-bold">{category.label}</span>
                <span className="block text-sm text-muted-foreground">
                  {count} live {count === 1 ? "deal" : "deals"}
                </span>
              </span>
            </Link>
          );
        })}
      </div>

      <h2 className="mt-14 text-2xl font-bold">Popular right now</h2>
      <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {deals
          .filter((d) => d.trending)
          .map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
      </div>
    </div>
  );
}
