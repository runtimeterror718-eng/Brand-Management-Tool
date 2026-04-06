"use client";

interface StatItem {
  label: string;
  value: string | number;
  subtext?: string;
}

interface StatRowProps {
  items: StatItem[];
}

export default function StatRow({ items }: StatRowProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-border bg-card p-5 shadow-sm">
      {items.map((item) => (
        <div key={item.label} className="flex flex-col items-center text-center min-w-[80px]">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            {item.label}
          </span>
          <span className="text-xl font-bold">{item.value}</span>
          {item.subtext && (
            <span className="text-[10px] text-muted-foreground mt-0.5">
              {item.subtext}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
