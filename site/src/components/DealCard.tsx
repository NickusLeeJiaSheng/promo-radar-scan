import { Link } from "@tanstack/react-router";
import { ArrowRight, Clock, ExternalLink, Heart, MapPin } from "lucide-react";

import { categoryMap, type Deal } from "@/data/deals";
import { cn } from "@/lib/utils";

type Props = {
  deal: Deal;
  className?: string;
  saved?: boolean;
  onToggleSave?: (id: string) => void;
};

export function DealCard({ deal, className, saved, onToggleSave }: Props) {
  const category = categoryMap[deal.category];
  const hasExternalLink = Boolean(deal.moreInfoUrl);

  // The card is either a full external <a> or an internal router <Link>
  const CardWrapper = hasExternalLink
    ? ({ children, className: cls }: { children: React.ReactNode; className?: string }) => (
        <a
          href={deal.moreInfoUrl}
          target="_blank"
          rel="noreferrer noopener"
          className={cls}
        >
          {children}
        </a>
      )
    : ({ children, className: cls }: { children: React.ReactNode; className?: string }) => (
        <Link to="/deal/$dealId" params={{ dealId: deal.id }} className={cls}>
          {children}
        </Link>
      );

  return (
    <article className={cn("deal-card group flex flex-col overflow-hidden", className)}>
      <div className="relative aspect-[4/3] overflow-hidden bg-secondary">
        {deal.image ? (
          <img
            src={deal.image}
            alt={`${deal.merchant} promotion`}
            loading="lazy"
            width={1024}
            height={768}
            className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="grid size-full place-items-center bg-accent text-5xl">
            {category.emoji}
          </div>
        )}
        <span className="absolute left-3 top-3 rounded-full bg-primary px-3 py-1 font-display text-xs font-bold tracking-wide text-primary-foreground shadow-[var(--shadow-accent)]">
          {deal.offer}
        </span>
        {onToggleSave && (
          <button
            type="button"
            aria-label={saved ? "Remove from saved" : "Save deal"}
            onClick={(e) => {
              e.preventDefault(); // prevent card navigation when clicking heart
              onToggleSave(deal.id);
            }}
            className="absolute right-3 top-3 grid size-8 place-items-center rounded-full border border-border bg-card/90 text-muted-foreground backdrop-blur transition-colors hover:text-primary"
          >
            <Heart className={cn("size-4", saved && "fill-primary text-primary")} />
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {deal.merchant}
          </span>
          <span className="text-base" title={category.label}>
            {category.emoji}
          </span>
        </div>

        <h3 className="font-display text-lg font-bold leading-snug">
          <CardWrapper className="after:absolute after:inset-0">
            {deal.title}
          </CardWrapper>
        </h3>
        <p className="line-clamp-2 text-sm text-muted-foreground">{deal.description}</p>

        <div className="mt-auto space-y-1.5 pt-2 text-sm">
          <p className="flex items-center gap-1.5 text-muted-foreground">
            <MapPin className="size-3.5 text-primary" />
            {deal.location}{deal.distanceKm > 0 ? ` · ${deal.distanceKm} km` : ""}
          </p>
          <p
            className={cn(
              "flex items-center gap-1.5 text-muted-foreground",
              deal.expiresSoon && "font-medium text-primary",
            )}
          >
            <Clock className="size-3.5" />
            {deal.expiresSoon ? deal.expiry : `Ends ${deal.expiry}`}
          </p>
        </div>

        <div className="flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
          <span>Telegram · {deal.scrapedAgo}</span>
          <span className="inline-flex items-center gap-1 font-semibold text-foreground transition-colors group-hover:text-primary">
            View deal
            {hasExternalLink
              ? <ExternalLink className="size-3.5" />
              : <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
            }
          </span>
        </div>
      </div>
    </article>
  );
}

export function DealRow({ deal, distanceKm }: { deal: Deal; distanceKm?: number }) {
  const dist = distanceKm ?? deal.distanceKm;
  const hasExternalLink = Boolean(deal.moreInfoUrl);

  const RowWrapper = hasExternalLink
    ? ({ children, className: cls }: { children: React.ReactNode; className?: string }) => (
        <a href={deal.moreInfoUrl} target="_blank" rel="noreferrer noopener" className={cls}>
          {children}
        </a>
      )
    : ({ children, className: cls }: { children: React.ReactNode; className?: string }) => (
        <Link to="/deal/$dealId" params={{ dealId: deal.id }} className={cls}>
          {children}
        </Link>
      );

  return (
    <RowWrapper className="deal-card flex items-center gap-4 p-3">
      <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-xl bg-accent text-2xl">
        {deal.image ? (
          <img
            src={deal.image}
            alt=""
            loading="lazy"
            className="size-full object-cover"
            width={1024}
            height={768}
          />
        ) : (
          categoryMap[deal.category].emoji
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {deal.merchant}
        </p>
        <p className="truncate font-display text-sm font-bold">{deal.title}</p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {deal.location}
          {dist > 0 ? ` · ${dist} km` : ""}
          {deal.expiry !== "Ongoing" ? ` · Ends ${deal.expiry}` : ""}
        </p>
      </div>
      <span className="shrink-0 rounded-full bg-accent px-2.5 py-1 font-display text-xs font-bold text-accent-foreground">
        {deal.offer}
      </span>
    </RowWrapper>
  );
}
