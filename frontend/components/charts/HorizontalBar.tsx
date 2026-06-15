"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";

interface DataItem {
  label: string;
  value: number;
  color?: string;
}

interface Props {
  data: DataItem[];
  valueLabel?: string;
  height?: number;
  color?: string;
}

export default function HorizontalBar({
  data, valueLabel = "Value", height = 300, color = "#3b82f6",
}: Props) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 120, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1c2d4a" horizontal={false} />
        <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          width={116}
        />
        <Tooltip
          contentStyle={{
            background: "#0e1628",
            border: "1px solid #1c2d4a",
            borderRadius: "8px",
            color: "#e2e8f0",
            fontSize: 12,
          }}
          formatter={(v: number) => [v, valueLabel]}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color ?? color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
