import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { money } from "../lib/format";

export interface ValuePoint {
  label: string;
  value: number;
}

export function ValueChart({ data, color = "#34d399" }: { data: ValuePoint[]; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 12 }}
          axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 12 }}
          tickFormatter={(v) => money(v)}
          width={56}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ stroke: "rgba(255,255,255,0.13)" }}
          contentStyle={{
            background: "#1d282d",
            border: "1px solid rgba(255,255,255,0.13)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v) => [money(Number(v)), "value"]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={{ r: 3, fill: color, strokeWidth: 0 }}
          activeDot={{ r: 5, fill: color, strokeWidth: 0 }}
          isAnimationActive
          animationDuration={450}
          animationEasing="ease-out"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
