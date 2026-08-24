import { categories, type CategoryId } from "@/data/deals";
import { cn } from "@/lib/utils";

export type ChipValue = CategoryId | "trending" | "near" | "all";

const leading = [
  { id: "trending" as const, label: "Trending", emoji: "🔥" },
  { id: "near" as const, label: "Near Me", emoji: "📍" },
];

export function CategoryChips({
  value,
  onChange,
}: {
  value: ChipValue;
  onChange: (v: ChipValue) => void;
}) {
  const chips: { id: ChipValue; label: string; emoji: string }[] = [
    { id: "all", label: "All deals", emoji: "✨" },
    ...leading,
    ...categories.map((c) => ({ id: c.id as ChipValue, label: c.label, emoji: c.emoji })),
  ];

  return (
    <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
      {chips.map((chip) => (
        <button
          key={chip.id}
          type="button"
          onClick={() => onChange(chip.id)}
          className={cn(
            "shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200",
            value === chip.id
              ? "border-primary bg-primary text-primary-foreground shadow-[var(--shadow-accent)]"
              : "border-border bg-card text-foreground hover:border-primary/50 hover:bg-accent",
          )}
        >
          <span className="mr-1.5">{chip.emoji}</span>
          {chip.label}
        </button>
      ))}
    </div>
  );
}
