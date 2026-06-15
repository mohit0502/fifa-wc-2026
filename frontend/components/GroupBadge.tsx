import { GROUP_COLORS } from "@/lib/groups";

interface Props {
  group: string; // e.g. "Group A" or just "A"
  size?: "sm" | "md";
}

export default function GroupBadge({ group, size = "md" }: Props) {
  const letter = group.replace("Group ", "").trim();
  const color = GROUP_COLORS[letter] ?? "#64748b";

  return (
    <span
      className={`inline-flex items-center font-bold rounded-full uppercase tracking-wider ${
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs"
      }`}
      style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}
    >
      {size === "sm" ? letter : `Group ${letter}`}
    </span>
  );
}
