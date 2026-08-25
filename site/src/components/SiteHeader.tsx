import { Link, useNavigate } from "@tanstack/react-router";
import { Heart, MapPin, Search } from "lucide-react";
import { useState } from "react";

const navItems = [
  { to: "/", label: "Discover" },
  { to: "/near-me", label: "Near Me" },
  { to: "/categories", label: "Categories" },
];

export function SiteHeader() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex shrink-0 items-center gap-2">
          <span className="grid size-8 place-items-center rounded-xl bg-primary font-display text-sm font-bold text-primary-foreground">
            D
          </span>
          <span className="font-display text-lg font-bold tracking-tight">DealHub</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              activeOptions={{ exact: item.to === "/" }}
              className="rounded-full px-3.5 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground data-[status=active]:bg-accent data-[status=active]:text-accent-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <form
          className="ml-auto hidden min-w-0 flex-1 items-center gap-2 lg:flex lg:max-w-xs"
          onSubmit={(e) => {
            e.preventDefault();
            navigate({ to: "/search", search: { q } });
          }}
        >
          <label className="flex w-full items-center gap-2 rounded-full border border-border bg-card px-3.5 py-2 text-sm transition-colors focus-within:border-primary">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search deals"
              aria-label="Search deals"
              className="w-full bg-transparent outline-none placeholder:text-muted-foreground"
            />
          </label>
        </form>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          <Link
            to="/saved"
            aria-label="Saved deals"
            className="grid size-9 place-items-center rounded-full border border-border bg-card text-muted-foreground transition-colors hover:text-primary"
          >
            <Heart className="size-4" />
          </Link>
          <span className="hidden items-center gap-1.5 rounded-full border border-border bg-card px-3 py-2 text-sm font-medium sm:flex">
            <MapPin className="size-4 text-primary" />
            Singapore
          </span>
        </div>
      </div>
    </header>
  );
}
