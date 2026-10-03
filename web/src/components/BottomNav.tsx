"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LangToggle";

interface TabDefinition {
  key: string;
  href: string;
  labelEn: string;
  labelBn: string;
  icon: (color: string) => React.ReactNode;
}

const PRIMARY_TABS: TabDefinition[] = [
  {
    key: "home",
    href: "/",
    labelEn: "Home",
    labelBn: "হোম",
    icon: (color) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1V9.5z" />
      </svg>
    ),
  },
  {
    key: "forecast",
    href: "/forecast",
    labelEn: "Forecast",
    labelBn: "পূর্বাভাস",
    icon: (color) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="4" width="18" height="17" rx="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
        <path d="M8 14h.01M12 14h.01M16 14h.01M8 17h.01M12 17h.01" />
      </svg>
    ),
  },
  {
    key: "savings",
    href: "/plan",
    labelEn: "Savings",
    labelBn: "সঞ্চয়",
    icon: (color) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M19 5c-1.5 0-2.8 1.4-3 2-3.5-1.5-11-.3-11 5 0 1.8 0 3 2 4.5V20h4v-2h4v2h4v-4c1-.5 1.5-1 2-2V7.5C20 6.1 19.5 5 19 5z" />
        <path d="M16 11h.01" />
        <path d="M11 5v2" />
      </svg>
    ),
  },
  {
    key: "expense",
    href: "/spending",
    labelEn: "Expense",
    labelBn: "খরচ",
    icon: (color) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 2v20l3-2 3 2 3-2 3 2 3-2 3 2V2l-3 2-3-2-3 2-3-2-3 2-3-2z" />
        <line x1="8" y1="8" x2="16" y2="8" />
        <line x1="8" y1="12" x2="16" y2="12" />
        <line x1="8" y1="16" x2="13" y2="16" />
      </svg>
    ),
  },
  {
    key: "more",
    href: "/tips",
    labelEn: "More",
    labelBn: "আরও",
    icon: (color) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="5" cy="12" r="1.5" />
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="19" cy="12" r="1.5" />
      </svg>
    ),
  },
];

const MORE_MENU = [
  {
    href: "/tips",
    labelEn: "Suggestions",
    labelBn: "পরামর্শ",
    icon: (color: string) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z" />
      </svg>
    ),
  },
  {
    href: "/signal",
    labelEn: "Consistency",
    labelBn: "ধারাবাহিকতা",
    icon: (color: string) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 3v6h6M7 21v-6H1" />
        <path d="M21 9l-7.5-7.5M3 15l7.5 7.5" />
      </svg>
    ),
  },
  {
    href: "/metrics",
    labelEn: "Metrics",
    labelBn: "মেট্রিক্স",
    icon: (color: string) => (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    ),
  },
];

export default function BottomNav() {
  const pathname = usePathname();
  const { lang } = useLanguage();
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

  // Determine active tab index for the 5 slots
  let activeIndex = 0;
  if (pathname === "/") {
    activeIndex = 0;
  } else if (pathname === "/forecast") {
    activeIndex = 1;
  } else if (pathname === "/plan") {
    activeIndex = 2;
  } else if (pathname === "/spending") {
    activeIndex = 3;
  } else if (
    pathname === "/tips" ||
    pathname === "/signal" ||
    pathname === "/metrics" ||
    moreOpen
  ) {
    activeIndex = 4;
  }

  const activeColor = "#0054A6";
  const inactiveColor = "#6A6355";

  return (
    <>
      {/* Backdrop for More sheet */}
      {moreOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#1E1B16]/20 transition-opacity"
          onClick={closeMore}
          aria-hidden="true"
        />
      )}

      {/* More Menu Sheet */}
      {moreOpen && (
        <div
          role="menu"
          aria-label={lang === "bn" ? "আরও মেনু" : "More Menu"}
          className="fixed bottom-[64px] right-4 left-4 sm:left-auto sm:right-[max(1rem,calc((100vw-1140px)/2+20px))] sm:w-64 z-50 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] p-2 space-y-1"
        >
          {MORE_MENU.map((item) => {
            const isItemActive = pathname === item.href;
            const itemColor = isItemActive ? activeColor : inactiveColor;
            return (
              <Link
                key={item.href}
                href={item.href}
                role="menuitem"
                onClick={closeMore}
                className={`min-h-[48px] flex items-center gap-3 px-3 py-2.5 rounded-[6px] no-underline transition-colors active:scale-[0.96] transition-transform duration-[80ms] ${
                  isItemActive
                    ? "bg-[#F1F4F9] text-[#0054A6] font-semibold"
                    : "text-[#1E1B16] hover:bg-[#F1F4F9]"
                }`}
              >
                <div className="w-[24px] h-[24px] flex items-center justify-center shrink-0">
                  {item.icon(itemColor)}
                </div>
                <span className="text-[13px] font-hind leading-tight">
                  {lang === "bn" ? item.labelBn : item.labelEn}
                </span>
              </Link>
            );
          })}
        </div>
      )}

      {/* Fixed 5-tab Bottom Navigation Bar */}
      <nav
        aria-label="Main Navigation"
        className="fixed bottom-0 left-0 right-0 z-40 bg-[#FFFFFF] border-t border-[#D8CFBB] pb-[env(safe-area-inset-bottom)]"
      >
        <div className="max-w-[1140px] mx-auto px-[20px] h-[56px] relative">
          {/* Sliding active indicator: 2px blue horizontal line 8px above the icon */}
          <div
            className="absolute top-0 left-0 h-[2px] w-1/5 pointer-events-none transition-transform duration-[240ms] ease-out z-10"
            style={{
              transform: `translateX(${activeIndex * 100}%)`,
            }}
            aria-hidden="true"
          >
            <div className="w-8 h-[2px] bg-[#0054A6] mx-auto" />
          </div>

          {/* 5 Equally Distributed Tabs */}
          <div className="grid grid-cols-5 h-full relative">
            {PRIMARY_TABS.map((tab, idx) => {
              const isActive = activeIndex === idx;
              const currentColor = isActive ? activeColor : inactiveColor;
              const label = lang === "bn" ? tab.labelBn : tab.labelEn;

              // 5th tab (More) triggers dropdown
              if (tab.key === "more") {
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setMoreOpen((open) => !open)}
                    aria-expanded={moreOpen}
                    aria-haspopup="menu"
                    aria-label={label}
                    className="h-full min-h-[48px] min-w-[48px] w-full flex flex-col items-center justify-center pt-[8px] pb-[6px] no-underline select-none bg-transparent border-0 cursor-pointer p-0 active:scale-[0.96] transition-transform duration-[80ms]"
                  >
                    <div className="w-[24px] h-[24px] flex items-center justify-center">
                      {tab.icon(currentColor)}
                    </div>
                    <span
                      className={`text-[13px] font-hind leading-none mt-[3px] transition-colors ${
                        isActive
                          ? "text-[#0054A6] font-semibold"
                          : "text-[#6A6355] font-normal"
                      }`}
                    >
                      {label}
                    </span>
                  </button>
                );
              }

              return (
                <Link
                  key={tab.key}
                  href={tab.href}
                  aria-label={label}
                  className="h-full min-h-[48px] min-w-[48px] w-full flex flex-col items-center justify-center pt-[8px] pb-[6px] no-underline select-none active:scale-[0.96] transition-transform duration-[80ms]"
                >
                  <div className="w-[24px] h-[24px] flex items-center justify-center">
                    {tab.icon(currentColor)}
                  </div>
                  <span
                    className={`text-[13px] font-hind leading-none mt-[3px] transition-colors ${
                      isActive
                        ? "text-[#0054A6] font-semibold"
                        : "text-[#6A6355] font-normal"
                    }`}
                  >
                    {label}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
    </>
  );
}
