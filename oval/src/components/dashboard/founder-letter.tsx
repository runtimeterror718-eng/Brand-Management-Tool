"use client";

interface FounderLetterProps {
  label: string;
  body: string;
}

export default function FounderLetter({ label, body }: FounderLetterProps) {
  return (
    <div
      className="rounded-xl border border-border bg-card p-5 shadow-sm"
      style={{ borderLeftWidth: 3, borderLeftColor: "#534AB7" }}
    >
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p className="font-serif italic text-[13px] leading-[1.8] text-muted-foreground">
        {body}
      </p>
    </div>
  );
}
