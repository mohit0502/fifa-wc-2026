"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import type { TeamMeta } from "@/lib/types";
import { getFlagUrl } from "@/lib/flags";

export default function Navbar() {
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const [teams, setTeams] = useState<TeamMeta[]>([]);
  const [filtered, setFiltered] = useState<TeamMeta[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/data/teams_meta.json")
      .then((r) => r.json())
      .then(setTeams)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (query.length < 1) { setFiltered([]); setOpen(false); return; }
    const q = query.toLowerCase();
    const res = teams.filter((t) => t.name.toLowerCase().includes(q)).slice(0, 8);
    setFiltered(res);
    setOpen(res.length > 0);
  }, [query, teams]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const nav = [
    { href: "/", label: "Tournament" },
    { href: "/players", label: "Players" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-surface border-b border-border backdrop-blur-md">
      <div className="max-w-screen-xl mx-auto px-4 h-14 flex items-center gap-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <span className="text-gold font-bold text-lg tracking-wide">WC</span>
          <span className="text-text font-bold text-lg tracking-wide">2026</span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {nav.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                pathname === n.href
                  ? "bg-accent/20 text-accent"
                  : "text-muted hover:text-text hover:bg-surface2"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Team search */}
        <div ref={ref} className="relative w-56">
          <input
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-1.5 text-sm text-text placeholder-muted focus:outline-none focus:border-accent"
            placeholder="Search team…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {open && (
            <div className="absolute top-full mt-1 left-0 right-0 bg-surface border border-border rounded-lg shadow-xl overflow-hidden z-50">
              {filtered.map((t) => (
                <Link
                  key={t.slug}
                  href={`/team/${t.slug}`}
                  onClick={() => { setQuery(""); setOpen(false); }}
                  className="flex items-center gap-2 px-3 py-2 hover:bg-surface2 transition-colors text-sm"
                >
                  {getFlagUrl(t.name) && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={getFlagUrl(t.name)} alt={t.name} className="w-6 h-4 object-cover rounded-sm" />
                  )}
                  <span className="text-text">{t.name}</span>
                  <span className="ml-auto text-muted text-xs">{t.group}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
