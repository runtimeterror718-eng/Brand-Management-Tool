"use client";

interface SectionDividerProps {
  title?: string;
}

export default function SectionDivider({ title }: SectionDividerProps) {
  if (!title) {
    return <hr className="border-t border-border my-6" />;
  }

  return (
    <div className="relative my-6">
      <hr className="border-t border-border" />
      <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
        {title}
      </span>
    </div>
  );
}
