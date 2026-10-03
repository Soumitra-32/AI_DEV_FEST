"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LangToggle";
import MaterialIcon from "@/components/MaterialIcon";

const PRIMARY_TABS = [
  { href: "/", key: "nav.home", icon: "home" },
  { href: "/forecast", key: "nav.forecast", icon: "calendar_month" },
  { href: "/plan", key: "nav.plan", icon: "savings" },
  { href: "/spending", key: "nav.spending", icon: "receipt_long" },
] as const;

const MORE_TABS = [
  { href: "/tips", key: "nav.tips", icon: "lightbulb" },
  { href: "/signal", key: "nav.signal", icon: "swap_horiz" },
  { href: "/metrics", key: "nav.metrics", icon: "bar_chart" },
] as const;

export default function BottomNav() {
  const pathname = usePathname();
  const { tr } = useLanguage();
  const [moreOpen, setMoreOpen] = useState(false);

  const closeMore = useCallback(() => setMoreOpen(false), []);

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
    `min-h-[48px] py-2 flex flex-col items-center justify-center transition-colors no-underline ${
      isActive
        ? "border-t-2 border-[#0054A6] text-[#0054A6] font-bold bg-[#FFFFFF]"
        : "border-t-2 border-transparent text-[#6A6355] hover:text-[#1E1B16]"
    }`;

  return (
    <>
      {moreOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#1E1B16]/30"
          onClick={closeMore}
          aria-hidden="true"
        />
      )}

      {moreOpen && (
        <div
          role="menu"
          aria-label={tr("nav.more")}
          className="fixed bottom-14 left-4 right-4 z-50 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] p-2 space-y-1"
        >
          {MORE_TABS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                role="menuitem"
                onClick={closeMore}
                className={`min-h-[48px] flex items-center gap-3 px-3 py-2.5 rounded-[6px] no-underline transition-colors ${
                  isActive
                    ? "bg-[#F1F4F9] text-[#0054A6] font-bold"
                    : "text-[#1E1B16] hover:bg-[#F1F4F9]"
                }`}
              >
                <MaterialIcon
                  name={item.icon}
                  size={20}
                  className={isActive ? "text-[#0054A6]" : "text-[#6A6355]"}
                />
                <span className="text-sm font-hind">{tr(item.key)}</span>
              </Link>
            );
          })}
        </div>
      )}

      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#FFFFFF] border-t border-[#D8CFBB]">
        <div className="max-w-4xl mx-auto grid grid-cols-5 text-center text-xs">
          {PRIMARY_TABS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className={tabClass(isActive)}>
                <MaterialIcon
                  name={item.icon}
                  size={20}
                  className={`mb-0.5 ${isActive ? "text-[#0054A6]" : "text-[#6A6355]"}`}
                />
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
            <MaterialIcon
              name={moreOpen ? "close" : "more_horiz"}
              size={20}
              className={`mb-0.5 ${moreActive || moreOpen ? "text-[#0054A6]" : "text-[#6A6355]"}`}
            />
            <span className="text-[11px] font-hind leading-tight">{tr("nav.more")}</span>
          </button>
        </div>
      </nav>
    </>
  );
}
