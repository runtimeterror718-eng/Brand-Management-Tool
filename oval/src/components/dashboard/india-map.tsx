"use client";

import { useState, memo } from "react";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber } from "@/lib/utils";

const GEO_URL = "/india-states.json";

// Map state names to our state codes
const STATE_NAME_TO_CODE: Record<string, string> = {
  "Rajasthan": "RJ", "Maharashtra": "MH", "Delhi": "DL", "NCT of Delhi": "DL",
  "Uttar Pradesh": "UP", "Karnataka": "KA", "Tamil Nadu": "TN",
  "Gujarat": "GJ", "Madhya Pradesh": "MP", "West Bengal": "WB",
  "Bihar": "BR", "Telangana": "TG", "Andhra Pradesh": "AP",
  "Kerala": "KL", "Punjab": "PB", "Haryana": "HR",
  "Jammu & Kashmir": "JK", "Jammu and Kashmir": "JK",
  "Himachal Pradesh": "HP", "Uttarakhand": "UK",
  "Jharkhand": "JH", "Odisha": "OR", "Chhattisgarh": "CG",
  "Assam": "AS", "Goa": "GA", "Arunachal Pradesh": "AR",
  "Manipur": "MN", "Meghalaya": "ML", "Mizoram": "MZ",
  "Nagaland": "NL", "Sikkim": "SK", "Tripura": "TR",
  "Ladakh": "LA", "Chandigarh": "CH", "Puducherry": "PY",
  "Dadra and Nagar Haveli and Daman and Diu": "DD",
  "Lakshadweep": "LD", "Andaman and Nicobar Islands": "AN",
};

// State centroids for bubble markers
const STATE_CENTROIDS: Record<string, [number, number]> = {
  RJ: [74.2, 26.9], MH: [75.7, 19.7], DL: [77.1, 28.7],
  UP: [80.9, 26.8], KA: [75.7, 15.3], TN: [78.7, 11.1],
  GJ: [71.6, 22.3], MP: [78.7, 23.5], WB: [87.9, 22.6],
  BR: [85.3, 25.6], TG: [79.0, 18.1], AP: [79.7, 15.9],
  KL: [76.3, 10.9], PB: [75.3, 31.1], HR: [76.1, 29.1],
  JK: [74.8, 33.8], HP: [77.2, 31.1], UK: [79.1, 30.1],
  JH: [85.3, 23.6], OR: [84.0, 20.9], CG: [82.0, 21.3],
  AS: [92.9, 26.2], GA: [74.0, 15.3],
};

function getNegColor(negPct: number): string {
  if (negPct >= 40) return "#E24B4A";
  if (negPct >= 25) return "#BA7517";
  if (negPct >= 10) return "#F59E0B";
  return "#639922";
}

function getStateFill(stateCode: string, geoDataMap: Map<string, any>): string {
  const data = geoDataMap.get(stateCode);
  if (!data) return "var(--muted)";
  const negPct = data.negative_pct || 0;
  if (negPct >= 40) return "#E24B4A30";
  if (negPct >= 25) return "#BA751730";
  if (negPct >= 10) return "#F59E0B20";
  return "#63992220";
}

interface IndiaMapProps {
  className?: string;
}

function IndiaMapInner({ className }: IndiaMapProps) {
  const { data: apiData } = useLiveData<any>("/api/geo", null);
  const geoData: any[] = apiData?.data || [];
  const [hovered, setHovered] = useState<any>(null);

  // Build lookup map
  const geoDataMap = new Map<string, any>();
  for (const row of geoData) {
    geoDataMap.set(row.state_code, row);
  }

  // Build markers for states with data
  const markers = geoData
    .filter((row) => STATE_CENTROIDS[row.state_code])
    .map((row) => ({
      code: row.state_code,
      state: row.state,
      coordinates: STATE_CENTROIDS[row.state_code] as [number, number],
      total: row.total_mentions || 0,
      negative: row.negative_mentions || 0,
      negPct: row.negative_pct || 0,
      topIssue: row.top_issue || "",
    }));

  return (
    <div className={className}>
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Geographic Distribution</h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">Mention concentration across Indian states</p>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#639922]" /> Safe</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#BA7517]" /> Warning</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#E24B4A]" /> Critical</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Map */}
          <div className="lg:col-span-2 relative">
            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ scale: 1000, center: [82, 22] }}
              width={500}
              height={480}
              style={{ width: "100%", height: "auto" }}
            >
              <Geographies geography={GEO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const stateName = geo.properties.ST_NM || geo.properties.NAME_1 || "";
                    const stateCode = STATE_NAME_TO_CODE[stateName] || "";
                    const fill = getStateFill(stateCode, geoDataMap);

                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={fill}
                        stroke="var(--border)"
                        strokeWidth={0.5}
                        style={{
                          default: { outline: "none" },
                          hover: { fill: "#534AB730", outline: "none", cursor: "pointer" },
                          pressed: { outline: "none" },
                        }}
                      />
                    );
                  })
                }
              </Geographies>

              {/* Bubble markers for states with data */}
              {markers.map((marker) => {
                const r = Math.max(4, Math.min(14, Math.sqrt(marker.total) * 2));
                const color = getNegColor(marker.negPct);

                return (
                  <Marker
                    key={marker.code}
                    coordinates={marker.coordinates}
                    onMouseEnter={() => setHovered(marker)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <circle r={r} fill={color} opacity={0.8} stroke="white" strokeWidth={1.5} className="cursor-pointer" />
                    <text textAnchor="middle" y={r + 12} className="fill-foreground" style={{ fontSize: 8, fontWeight: 600 }}>
                      {marker.code}
                    </text>
                  </Marker>
                );
              })}
            </ComposableMap>

            {/* Tooltip */}
            {hovered && (
              <div className="absolute top-4 right-4 bg-card border border-border rounded-xl p-3 shadow-lg z-10 min-w-[200px]">
                <p className="font-semibold text-sm">{hovered.state}</p>
                <div className="mt-1.5 space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total mentions</span>
                    <span className="font-medium">{hovered.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Negative</span>
                    <span className="font-semibold" style={{ color: getNegColor(hovered.negPct) }}>
                      {hovered.negative} ({hovered.negPct}%)
                    </span>
                  </div>
                  {hovered.topIssue && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Top issue</span>
                      <span className="font-medium text-right">{hovered.topIssue}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* State list */}
          <div>
            <h4 className="text-xs font-semibold mb-2">Top States by Mentions</h4>
            <div className="space-y-1.5 max-h-[380px] overflow-y-auto">
              {geoData
                .sort((a: any, b: any) => (b.total_mentions || 0) - (a.total_mentions || 0))
                .slice(0, 12)
                .map((row: any, i: number) => {
                  const negPct = row.negative_pct || 0;
                  const color = getNegColor(negPct);
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs p-2 rounded-lg border border-border hover:bg-muted/50 cursor-pointer transition-colors"
                      onMouseEnter={() => {
                        const marker = markers.find((m) => m.code === row.state_code);
                        if (marker) setHovered(marker);
                      }}
                      onMouseLeave={() => setHovered(null)}
                    >
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      <span className="font-medium flex-1 truncate">{row.state || row.state_code}</span>
                      <span className="text-muted-foreground">{row.total_mentions}</span>
                      <span className="font-semibold tabular-nums" style={{ color }}>{negPct}%</span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const IndiaMap = memo(IndiaMapInner);
export default IndiaMap;
