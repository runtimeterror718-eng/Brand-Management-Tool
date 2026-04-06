"use client";

interface PlatformData {
  platform: string;
  color: string;
  bgTint: string;
  sentiment: string;
  quote: string;
  stat: string;
}

interface PlatformSplitProps {
  platforms: PlatformData[];
}

export default function PlatformSplit({ platforms }: PlatformSplitProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {platforms.map((p) => (
        <div
          key={p.platform}
          className="rounded-xl border border-border p-5 shadow-sm"
          style={{ backgroundColor: p.bgTint }}
        >
          <span
            className="inline-block text-[10px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: p.color }}
          >
            {p.platform}
          </span>
          <p className="text-2xl font-bold mb-2" style={{ color: p.color }}>
            {p.sentiment}
          </p>
          <p className="text-sm italic text-muted-foreground leading-relaxed mb-3">
            &ldquo;{p.quote}&rdquo;
          </p>
          <p className="text-xs text-muted-foreground">{p.stat}</p>
        </div>
      ))}
    </div>
  );
}
