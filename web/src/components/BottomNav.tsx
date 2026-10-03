"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Lightbulb,
  Menu,
  Receipt,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";
import { useLanguage } from "@/components/LangToggle";

const PRIMARY_TABS = [
  { href: "/", key: "nav.home", icon: BookOpen },
  { href: "/forecast", key: "nav.forecast", icon: TrendingUp },
  { href: "/plan", key: "nav.plan", icon: Wallet },
  { href: "/spending", key: "nav.spending", icon: Receipt },
] as const;

const MORE_TABS = [
  { href: "/tips", key: "nav.tips", icon: Lightbulb },
  { href: "/signal", key: "nav.signal", icon: Activity },
  { href: "/metrics", key: "nav.metrics", icon: BarChart3 },
] as const;

export default function BottomNav() {
  const pathname = usePathname();
  const { tr } = useLanguage();
  const [moreOpen, setMoreOpen] = useState(false);

  const closeMore = useCallback(() => setMoreOpen(false), []);

  // Close the sheet on navigation and on Escape so it never traps the user.
  useEffect(() => {
    closeMore();
  }, [pathname, closeMore]);

  useEffect(() => {
    if (!moreOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMore();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [moreOpen, closeMore]);

  const moreActive = MORE_TABS.some((item) => pathname === item.href);

  const tabClass = (isActive: boolean) =>
    `py-2.5 flex flex-col items-center justify-center transition-colors no-underline ${
      isActive
        ? "border-t-2 border-primaryGreen text-primaryGreen font-bold"
        : "border-t-2 border-transparent text-ink-muted hover:text-ink"
    }`;

  return (
    <>
      {moreOpen && (
        <div
          className="fixed inset-0 z-40 bg-ink/40"
          onClick={closeMore}
          aria-hidden="true"
        />
      )}

      {moreOpen && (
        <div
          role="menu"
          aria-label={tr("nav.more")}
          className="fixed bottom-16 left-4 right-4 z-50 bg-surface border border-rule rounded-ledger p-2 space-y-1 shadow-lg"
        >
          {MORE_TABS.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                role="menuitem"
                onClick={closeMore}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-stamp no-underline transition-colors ${
                  isActive
                    ? "bg-primaryGreen/10 text-primaryGreen font-bold"
                    : "text-ink hover:bg-paper"
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" strokeWidth={1.5} />
                <span className="text-sm font-hind">{tr(item.key)}</span>
              </Link>
            );
          })}
        </div>
      )}

      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-rule">
        <div className="max-w-4xl mx-auto grid grid-cols-5 text-center text-xs">
          {PRIMARY_TABS.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className={tabClass(isActive)}>
                <Icon className="w-4 h-4 mb-0.5" strokeWidth={1.5} />
                <span className="text-[11px] font-hind leading-tight">{tr(item.key)}</span>
              </Link>
            );
          })}

          <button
            type="button"
            onClick={() => setMoreOpen((open) => !open)}
            aria-expanded={moreOpen}
            aria-haspopup="menu"
            aria-label={tr("nav.more")}
            className={tabClass(moreActive || moreOpen)}
          >
            {moreOpen ? (
              <X className="w-4 h-4 mb-0.5" strokeWidth={1.5} />
            ) : (
              <Menu className="w-4 h-4 mb-0.5" strokeWidth={1.5} />
            )}
            <span className="text-[11px] font-hind leading-tight">{tr("nav.more")}</span>
          </button>
        </div>
      </nav>
    </>
  );
}
