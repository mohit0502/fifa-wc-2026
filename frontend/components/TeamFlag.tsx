import Link from "next/link";
import { getFlagUrl } from "@/lib/flags";
import { slugify } from "@/lib/slugify";

interface Props {
  name: string;
  size?: "sm" | "md" | "lg";
  showLink?: boolean;
  truncate?: boolean;
  className?: string;
}

const SIZE = {
  sm:  { img: "w-5 h-3.5", text: "text-sm" },
  md:  { img: "w-7 h-5",   text: "text-base" },
  lg:  { img: "w-10 h-7",  text: "text-lg font-semibold" },
};

export default function TeamFlag({
  name, size = "md", showLink = true, truncate = false, className = "",
}: Props) {
  const flagUrl = getFlagUrl(name, size === "lg" ? 80 : 40);
  const slug = slugify(name);

  const inner = (
    <span className={`flex items-center gap-1.5 min-w-0 ${SIZE[size].text} ${className}`}>
      {flagUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={flagUrl}
          alt={name}
          className={`${SIZE[size].img} object-cover rounded-sm shrink-0`}
          loading="lazy"
        />
      ) : (
        <span className={`${SIZE[size].img} bg-surface2 rounded-sm shrink-0`} />
      )}
      <span className={truncate ? "truncate" : ""}>{name}</span>
    </span>
  );

  if (!showLink) return inner;

  return (
    <Link href={`/team/${slug}`} className="hover:text-accent transition-colors min-w-0 block">
      {inner}
    </Link>
  );
}
