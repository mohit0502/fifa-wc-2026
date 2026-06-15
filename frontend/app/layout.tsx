import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "FIFA World Cup 2026 Analytics",
  description: "Tournament overview, team stats, and player analytics for WC 2026",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-text">
        <Navbar />
        <main className="max-w-screen-xl mx-auto px-4 py-6">{children}</main>
        <footer className="mt-12 py-6 text-center text-muted text-sm border-t border-border">
          WC 2026 Analytics · Data: martj42, FIFA, Fjelstul DB, ELO Ratings
        </footer>
      </body>
    </html>
  );
}
