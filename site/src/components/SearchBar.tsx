import { Search } from "lucide-react";

export function SearchBar({
  value,
  onChange,
  onSubmit,
  placeholder = "Search for deals, restaurants, shops, brands...",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.();
      }}
      className="flex w-full items-center gap-2 rounded-full border border-border bg-card p-2 pl-5 shadow-[var(--shadow-soft)] transition-shadow focus-within:shadow-[var(--shadow-lift)]"
    >
      <Search className="size-5 shrink-0 text-muted-foreground" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label="Search deals"
        className="min-w-0 flex-1 bg-transparent py-2 text-base outline-none placeholder:text-muted-foreground"
      />
      <button
        type="submit"
        className="shrink-0 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.03] active:scale-95"
      >
        Search
      </button>
    </form>
  );
}
