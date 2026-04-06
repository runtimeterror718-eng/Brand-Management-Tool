"use client";

interface HeadToHeadProps {
  opponent: string;
  pwWin: number;
  opponentWin: number;
}

export default function HeadToHead({
  opponent,
  pwWin,
  opponentWin,
}: HeadToHeadProps) {
  const total = pwWin + opponentWin;
  const pwPct = total > 0 ? Math.round((pwWin / total) * 100) : 50;
  const opPct = 100 - pwPct;

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between mb-2 text-xs font-semibold">
        <span style={{ color: "#534AB7" }}>PW {pwPct}%</span>
        <span style={{ color: "#1D9E75" }}>
          {opponent} {opPct}%
        </span>
      </div>
      <div className="flex h-5 w-full overflow-hidden rounded-full">
        <div
          className="flex items-center justify-center text-[10px] font-bold text-white transition-all"
          style={{
            width: `${pwPct}%`,
            backgroundColor: "#534AB7",
          }}
        >
          {pwPct > 15 && `${pwPct}%`}
        </div>
        <div
          className="flex items-center justify-center text-[10px] font-bold text-white transition-all"
          style={{
            width: `${opPct}%`,
            backgroundColor: "#1D9E75",
          }}
        >
          {opPct > 15 && `${opPct}%`}
        </div>
      </div>
    </div>
  );
}
