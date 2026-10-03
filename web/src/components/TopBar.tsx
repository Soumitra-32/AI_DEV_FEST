"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import LangToggle, { useLanguage } from "@/components/LangToggle";

export default function TopBar() {
  const { tr } = useLanguage();
  const pathname = usePathname();

  const links = [
    { href: "/", label: tr("nav.home") },
    { href: "/forecast", label: tr("nav.forecast") },
    { href: "/plan", label: tr("nav.plan") },
    { href: "/spending", label: tr("nav.spending") },
    { href: "/tips", label: tr("nav.tips") },
    { href: "/signal", label: tr("nav.signal") },
    { href: "/metrics", label: tr("nav.metrics") },
  ];

  return (
    <header className="border-b border-rule px-4 py-3 bg-surface/70 flex items-center justify-between gap-3 mb-6">
      <div className="flex items-center gap-6">
        <Link
          href="/"
          className="font-serif-bn font-bold text-xl text-ink tracking-tight no-underline hover:text-primaryGreen transition-colors"
        >
          {tr("appName")}
        </Link>
        <nav className="hidden md:flex items-center gap-4 text-xs font-mono tracking-wider">
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`no-underline transition-colors ${
                  isActive
                    ? "font-bold text-primaryGreen border-b-2 border-primaryGreen pb-0.5"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <LangToggle />
    </header>
  );
}