"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import type { RankingEntry } from "@/lib/types";

interface Props {
  data: RankingEntry[];
  teamName: string;
}

interface TooltipPayload {
  payload: { rank: number; rank_date: string; total_points: number };
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-muted mb-1">{d.rank_date}</div>
      <div className="text-text font-bold">Rank #{d.rank}</div>
      <div className="text-muted">{d.total_points?.toFixed(1)} pts</div>
    </div>
  );
}

export default function RankingChart({ data, teamName }: Props) {
  if (!data || data.length === 0) {
    return <div className="text-muted text-sm py-8 text-center">No ranking data available</div>;
  }

  const latest = data[data.length - 1]?.rank;
  const earliest = data[0]?.rank;
  const change = latest - earliest;

  return (
    <div>
      <div className="flex items-center gap-6 mb-4">
        <div>
          <div className="text-3xl font-bold text-text">#{latest}</div>
          <div className="text-muted text-sm">Current FIFA Rank</div>
        </div>
        <div>
          <div className={`text-lg font-semibold ${change < 0 ? "text-green-400" : change > 0 ? "text-red-400" : "text-muted"}`}>
            {change < 0 ? `↑ ${Math.abs(change)}` : change > 0 ? `↓ ${change}` : "─"}
          </div>
          <div className="text-muted text-sm">vs. {data[0]?.rank_date?.slice(0, 7)}</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1c2d4a" />
          <XAxis
            dataKey="rank_date"
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(0, 7)}
            interval="preserveStartEnd"
          />
          <YAxis
            reversed
            tick={{ fill: "#64748b", fontSize: 11 }}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => `#${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="rank"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#3b82f6" }}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-muted text-xs text-center mt-1">
        Lower rank = better · {data.length} data points shown
      </p>
    </div>
  );
}
