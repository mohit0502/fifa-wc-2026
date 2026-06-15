"use client";

// Position → pitch row (0 = GK end, 4 = attacking end) and column bucket
// Rows are rendered bottom-to-top so GK is at the bottom of the pitch visual.

export interface LineupPlayer {
  pos: string;
  name: string;
  short_name: string;
  injury: string | null;
}

interface Props {
  players: LineupPlayer[];
  formation: string;
  status: "predicted" | "confirmed";
  onPlayerClick?: (player: LineupPlayer) => void;
  selectedName?: string;
}

// Map RotoWire position codes → broad tier
function tier(pos: string): "GK" | "DEF" | "DM" | "MID" | "AM" | "FW" {
  const p = pos.toUpperCase();
  if (p === "GK") return "GK";
  if (p.startsWith("D") && !p.includes("M")) return "DEF"; // DL, DC, DR, D
  if (p === "DMC" || p === "DML" || p === "DMR" || p === "DM") return "DM";
  if (p.startsWith("AM")) return "AM";
  if (p.startsWith("FW") || p === "ST" || p === "CF" || p === "SS") return "FW";
  if (p.startsWith("M")) return "MID"; // ML, MC, MR
  return "MID";
}

const TIER_ORDER: Array<"GK" | "DEF" | "DM" | "MID" | "AM" | "FW"> = [
  "FW", "AM", "MID", "DM", "DEF", "GK",
];

const TIER_LABEL: Record<string, string> = {
  GK: "GK", DEF: "DEF", DM: "DM", MID: "MID", AM: "AM", FW: "FW",
};

const TIER_BG: Record<string, string> = {
  GK:  "#ca8a04",   // amber
  DEF: "#1d4ed8",   // blue
  DM:  "#0f766e",   // teal
  MID: "#15803d",   // green
  AM:  "#7e22ce",   // purple
  FW:  "#dc2626",   // red
};

// Shorten long names for display on pitch
function shortName(player: LineupPlayer): string {
  const n = player.short_name || player.name;
  // Already short
  if (n.length <= 14) return n;
  // Take last name only
  const parts = n.split(" ");
  return parts[parts.length - 1];
}

export default function PitchXI({ players, formation, status, onPlayerClick, selectedName }: Props) {
  // Group players into tiers
  const groups: Record<string, LineupPlayer[]> = {};
  for (const p of players) {
    const t = tier(p.pos);
    if (!groups[t]) groups[t] = [];
    groups[t].push(p);
  }

  // Rows to render (only non-empty tiers, in top-down order FW→GK)
  const rows = TIER_ORDER.filter((t) => groups[t]?.length > 0);

  return (
    <div className="w-full">
      {/* Status badge + formation */}
      <div className="flex items-center gap-3 mb-4">
        <span
          className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide ${
            status === "confirmed"
              ? "bg-green-500/20 text-green-400 border border-green-500/40"
              : "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40"
          }`}
        >
          {status === "confirmed" ? "✓ Confirmed XI" : "⏳ Predicted XI"}
        </span>
        <span className="text-muted text-sm font-mono">{formation}</span>
        <span className="text-muted text-xs ml-auto">Source: RotoWire</span>
      </div>

      {/* Pitch */}
      <div
        className="relative w-full rounded-xl overflow-hidden"
        style={{
          background: "linear-gradient(180deg, #166534 0%, #15803d 50%, #166534 100%)",
          minHeight: 480,
        }}
      >
        {/* Pitch markings */}
        <PitchMarkings />

        {/* Player rows */}
        <div className="relative z-10 flex flex-col justify-around h-full py-4" style={{ minHeight: 480 }}>
          {rows.map((t) => (
            <div key={t} className="flex justify-around items-center px-4 py-1">
              {groups[t].map((p, i) => (
                <PlayerDot
                  key={i}
                  player={p}
                  tierColor={TIER_BG[t]}
                  isSelected={selectedName === p.name}
                  onClick={onPlayerClick ? () => onPlayerClick(p) : undefined}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-4 justify-center">
        {TIER_ORDER.filter((t) => groups[t]?.length > 0).map((t) => (
          <div key={t} className="flex items-center gap-1.5 text-xs">
            <span
              className="w-3 h-3 rounded-full shrink-0"
              style={{ background: TIER_BG[t] }}
            />
            <span className="text-muted">{TIER_LABEL[t]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlayerDot({
  player,
  tierColor,
  isSelected,
  onClick,
}: {
  player: LineupPlayer;
  tierColor: string;
  isSelected?: boolean;
  onClick?: () => void;
}) {
  const name = shortName(player);
  const hasInjury = !!player.injury;
  return (
    <div
      className="flex flex-col items-center gap-1 group relative"
      onClick={onClick}
      style={{ cursor: onClick ? "pointer" : "default" }}
    >
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold text-white shadow-lg border-2 transition-transform group-hover:scale-110 ${
          isSelected
            ? "border-white scale-110 ring-2 ring-white ring-offset-2 ring-offset-green-700"
            : "border-white/30"
        }`}
        style={{ background: hasInjury ? "#991b1b" : tierColor }}
        title={`${player.name}${hasInjury ? ` (${player.injury})` : ""}`}
      >
        {player.pos.slice(0, 2)}
      </div>
      <span
        className={`text-xs font-medium text-center leading-tight max-w-[70px] truncate drop-shadow-sm ${
          isSelected ? "text-yellow-300 font-bold" : "text-white"
        }`}
      >
        {name}
      </span>
      {hasInjury && (
        <span className="text-xs font-bold text-red-300 leading-none">
          {player.injury}
        </span>
      )}
    </div>
  );
}

function PitchMarkings() {
  return (
    <svg
      className="absolute inset-0 w-full h-full opacity-20"
      viewBox="0 0 400 560"
      preserveAspectRatio="none"
      fill="none"
      stroke="white"
      strokeWidth="2"
    >
      {/* Outer boundary */}
      <rect x="10" y="10" width="380" height="540" />
      {/* Centre line */}
      <line x1="10" y1="280" x2="390" y2="280" />
      {/* Centre circle */}
      <circle cx="200" cy="280" r="50" />
      <circle cx="200" cy="280" r="3" fill="white" />
      {/* Top penalty area */}
      <rect x="95" y="10" width="210" height="90" />
      {/* Top goal area */}
      <rect x="145" y="10" width="110" height="35" />
      {/* Top goal */}
      <rect x="165" y="5" width="70" height="10" fill="white" opacity="0.3" />
      {/* Bottom penalty area */}
      <rect x="95" y="460" width="210" height="90" />
      {/* Bottom goal area */}
      <rect x="145" y="515" width="110" height="35" />
      {/* Bottom goal */}
      <rect x="165" y="545" width="70" height="10" fill="white" opacity="0.3" />
      {/* Penalty spots */}
      <circle cx="200" cy="80" r="3" fill="white" />
      <circle cx="200" cy="480" r="3" fill="white" />
    </svg>
  );
}
