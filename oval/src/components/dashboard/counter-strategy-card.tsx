"use client";


interface Reaction {
  platform: string;
  prediction: string;
}

interface CounterStrategyCardProps {
  name: string;
  borderColor: string;
  successRate: number;
  action: string;
  reactions: Reaction[];
  risk: string;
}

export default function CounterStrategyCard({
  name,
  borderColor,
  successRate,
  action,
  reactions,
  risk,
}: CounterStrategyCardProps) {
  return (
    <div
      className="rounded-xl border border-border bg-card p-5 shadow-sm"
      style={{ borderLeftWidth: 3, borderLeftColor: borderColor }}
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold">{name}</h4>
        <span className="text-[10px] text-muted-foreground">
          {successRate}% success
        </span>
      </div>

      <div className="h-1.5 w-full rounded-full bg-gray-100 mb-4">
        <div
          className="h-1.5 rounded-full transition-all"
          style={{
            width: `${successRate}%`,
            backgroundColor: borderColor,
          }}
        />
      </div>

      <p className="text-sm text-foreground mb-3">{action}</p>

      <div className="space-y-1.5 mb-3">
        {reactions.map((r) => (
          <div key={r.platform} className="flex gap-2 text-xs">
            <span className="font-medium text-muted-foreground shrink-0">
              {r.platform}:
            </span>
            <span className="text-muted-foreground">{r.prediction}</span>
          </div>
        ))}
      </div>

      <div className="flex items-start gap-1.5 text-xs text-red-600">
        <span className="font-medium shrink-0">Risk:</span>
        <span>{risk}</span>
      </div>
    </div>
  );
}
