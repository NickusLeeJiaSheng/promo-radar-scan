import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft, Clock, ExternalLink, Heart, MapPin, Ruler, Send } from "lucide-react";
import { useState } from "react";

import { DealCard } from "@/components/DealCard";
import { DealMap } from "@/components/DealMap";
import { categoryMap, deals, getDeal } from "@/data/deals";
import { useSavedDeals } from "@/hooks/useSavedDeals";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/deal/$dealId")({
  loader: ({ params }) => {
    const deal = getDeal(params.dealId);
    if (!deal) throw notFound();
    return { deal };
  },
  head: ({ loaderData }) => {
    if (!loaderData) {
      return {
        meta: [{ title: "Deal not found — DealHub" }, { name: "robots", content: "noindex" }],
      };
    }
    const { deal } = loaderData;
    const title = `${deal.title} at ${deal.merchant} — DealHub`;
    const description = `${deal.offer} · ${deal.location}. ${deal.description}`;
    return {
      meta: [
        { title },
        { name: "description", content: description.slice(0, 155) },
        { property: "og:title", content: title },
        { property: "og:description", content: description.slice(0, 155) },
      ],
    };
  },
  component: DealDetail,
});

function DealDetail() {
  const { deal } = Route.useLoaderData();
  const { isSaved, toggle } = useSavedDeals();
  const [selected, setSelected] = useState<string | null>(deal.id);
  const category = categoryMap[deal.category];
  const related = deals.filter((d) => d.category === deal.category && d.id !== deal.id).slice(0, 4);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to deals
      </Link>

      <div className="mt-5 overflow-hidden rounded-[var(--radius-3xl)] border border-border bg-card shadow-[var(--shadow-soft)]">
        <div className="relative aspect-[16/9] bg-accent">
          {deal.image ? (
            <img
              src={deal.image}
              alt={`${deal.merchant} promotion`}
              width={1024}
              height={768}
              className="size-full object-cover"
            />
          ) : (
            <div className="grid size-full place-items-center text-7xl">{category.emoji}</div>
          )}
          <span className="absolute left-5 top-5 rounded-full bg-primary px-4 py-1.5 font-display text-sm font-bold text-primary-foreground shadow-[var(--shadow-accent)]">
            {deal.offer}
          </span>
        </div>

        <div className="p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                {deal.merchant} · {category.label}
              </p>
              <h1 className="mt-2 text-3xl font-bold sm:text-4xl">{deal.title}</h1>
            </div>
            <button
              type="button"
              onClick={() => toggle(deal.id)}
              className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-semibold transition-colors hover:border-primary"
            >
              <Heart
                className={cn("size-4", isSaved(deal.id) && "fill-primary text-primary")}
              />
              {isSaved(deal.id) ? "Saved" : "Save"}
            </button>
          </div>

          <p className="mt-4 max-w-2xl text-pretty text-muted-foreground">{deal.description}</p>

          <dl className="mt-6 grid gap-3 sm:grid-cols-3">
            <Fact icon={<MapPin className="size-4 text-primary" />} label="Location" value={deal.location} />
            <Fact icon={<Ruler className="size-4 text-primary" />} label="Distance" value={`${deal.distanceKm} km away`} />
            <Fact
              icon={<Clock className="size-4 text-primary" />}
              label="Expires"
              value={deal.expiresSoon ? deal.expiry : `Ends ${deal.expiry}`}
            />
          </dl>

          <a
            href="https://t.me/"
            target="_blank"
            rel="noreferrer noopener"
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 font-semibold text-primary-foreground shadow-[var(--shadow-accent)] transition-transform hover:scale-[1.02] active:scale-95"
          >
            View original promotion
            <ExternalLink className="size-4" />
          </a>
        </div>
      </div>

      <section className="surface-panel mt-6 p-6 sm:p-8">
        <h2 className="text-xl font-bold">Location</h2>
        <p className="mt-1 text-sm text-muted-foreground">{deal.address}</p>
        {deal.openingHours && (
          <p className="mt-1 text-sm text-muted-foreground">Opening hours · {deal.openingHours}</p>
        )}
        <DealMap
          deals={[deal]}
          selectedId={selected}
          onSelect={setSelected}
          className="mt-5 h-[320px]"
        />
      </section>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <section className="surface-panel p-6">
          <h2 className="text-xl font-bold">Terms & conditions</h2>
          <p className="mt-2 text-sm text-muted-foreground">{deal.terms}</p>
        </section>
        <section className="surface-panel p-6">
          <h2 className="flex items-center gap-2 text-xl font-bold">
            <Send className="size-4 text-primary" />
            Source
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Telegram {deal.channel} · scraped {deal.scrapedAgo}
          </p>
          <p className="mt-3 rounded-[var(--radius-lg)] bg-surface p-4 text-sm italic text-muted-foreground">
            “{deal.originalPost}”
          </p>
        </section>
      </div>

      {related.length > 0 && (
        <section className="mt-12">
          <h2 className="text-2xl font-bold">More {category.label.toLowerCase()} deals</h2>
          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {related.map((d) => (
              <DealCard key={d.id} deal={d} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Fact({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-4">
      <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </dt>
      <dd className="mt-1 font-display font-bold">{value}</dd>
    </div>
  );
}
