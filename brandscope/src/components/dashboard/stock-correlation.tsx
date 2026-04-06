"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  month: string;
  healthScore: number;
  stockPrice: number;
}

interface StockCorrelationProps {
  data: DataPoint[];
}

export default function StockCorrelation({ data }: StockCorrelationProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <h3 className="text-sm font-semibold mb-4">
        Brand Health vs Stock Price Correlation
      </h3>
      <div className="w-full h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              yAxisId="left"
              domain={[50, 80]}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              tickLine={false}
              axisLine={false}
              label={{
                value: "Health Score",
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 10, fill: "#9ca3af" },
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[70, 170]}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              tickLine={false}
              axisLine={false}
              label={{
                value: "Stock Price (₹)",
                angle: 90,
                position: "insideRight",
                style: { fontSize: 10, fill: "#9ca3af" },
              }}
            />
            <Tooltip
              contentStyle={{
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid #e5e7eb",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11 }}
              iconType="circle"
              iconSize={8}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="healthScore"
              stroke="#534AB7"
              strokeWidth={2}
              dot={{ r: 3, fill: "#534AB7" }}
              name="Health Score"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="stockPrice"
              stroke="#378ADD"
              strokeWidth={2}
              dot={{ r: 3, fill: "#378ADD" }}
              name="Stock Price (₹)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
