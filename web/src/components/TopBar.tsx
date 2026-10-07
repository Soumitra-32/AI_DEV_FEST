"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import LangToggle, { useLanguage } from "@/components/LangToggle";
import MaterialIcon from "@/components/MaterialIcon";

export default function TopBar() {
  const { lang, tr } = useLanguage();
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: tr("nav.home"), icon: "home" },
    { href: "/forecast", label: tr("nav.forecast"), icon: "calendar_month" },
    { href: "/plan", label: tr("nav.plan"), icon: "savings" },
    { href: "/spending", label: tr("nav.spending"), icon: "receipt_long" },
    { href: "/tips", label: tr("nav.tips"), icon: "lightbulb" },
    {
      href: "/signal",
      label: tr("nav.signal"),
      customIcon: (
        <svg
          width="19"
          height="19"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M17 3v6h6M7 21v-6H1" />
          <path d="M21 9l-7.5-7.5M3 15l7.5 7.5" />
        </svg>
      ),
    },
    { href: "/metrics", label: tr("nav.metrics"), icon: "bar_chart" },
  ];

  return (
    <header className="border-b border-[#D8CFBB] bg-[#FFFFFF] mb-6">
      {/* Demo Mode Strip */}
      <div className="bg-[#F1F4F9] border-b border-[#D8CFBB] px-4 py-1.5 flex flex-wrap items-center justify-between gap-2 text-xs font-hind text-[#6A6355]">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-[#0054A6]" />
          <span className="font-semibold text-[#1E1B16]">
            {lang === "bn" ? "ডেমো মোড" : "DEMO MODE"}
          </span>
          <span>—</span>
          <span>
            {lang === "bn"
              ? "সিন্থেটিক লেনদেন ডেটা ব্যবহৃত হচ্ছে"
              : "Using synthetic transaction data"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono">
          <span>{lang === "bn" ? "দৃশ্যপট:" : "Scenario:"}</span>
          <select
            aria-label="Demo Scenario"
            className="bg-white border border-[#D8CFBB] text-[#1E1B16] rounded px-1.5 py-0.5 text-xs font-sans focus:outline-none focus:border-[#0054A6]"
            defaultValue="healthy"
            onChange={(e) => {
              const val = e.target.value;
              if (val === "monthend") {
                window.location.href = "/forecast";
              } else if (val === "fees") {
                window.location.href = "/tips";
              } else if (val === "unusual") {
                window.location.href = "/spending";
              } else {
                window.location.href = "/";
              }
            }}
          >
            <option value="healthy">{lang === "bn" ? "স্বাভাবিক ক্যাশ-ফ্লো" : "Healthy cash flow"}</option>
            <option value="monthend">{lang === "bn" ? "মাস শেষের চাপ (২৮-৩১)" : "Month-end pressure"}</option>
            <option value="fees">{lang === "bn" ? "অতিরিক্ত ক্যাশ-আউট ফি" : "High avoidable fees"}</option>
            <option value="unusual">{lang === "bn" ? "অস্বাভাবিক লেনদেন" : "Unusual transaction"}</option>
          </select>
        </div>
      </div>

      {/* Upper header bar */}
      <div className="px-4 py-3 flex items-center justify-between gap-4">
        {/* Brand: "সঞ্চয় Copilot" with a 3px upay-blue vertical bar */}
        <Link
          href="/"
          className="flex items-center gap-2.5 no-underline group focus-visible:outline-none"
        >
          <div className="w-[3px] h-6 bg-[#0054A6] shrink-0" />
          <div className="flex flex-col">
            <span className="font-serif-bn font-bold text-xl md:text-2xl text-[#1E1B16] tracking-tight group-hover:text-[#0054A6] transition-colors">
              {tr("appName")}
            </span>
            <span className="text-[11px] font-hind text-[#6A6355] -mt-1 hidden sm:inline">
              institutional digital khata · upay
            </span>
          </div>
        </Link>

        {/* Language switch: plain text “বাংলা · EN” with 2px upay-blue underline on active */}
        <LangToggle />
      </div>

      {/* Main nav: 7 items, text-first, top border 2px upay-blue on active */}
      <nav
        aria-label="Main Navigation"
        className="flex items-center overflow-x-auto border-t border-[#D8CFBB] scrollbar-none px-2 md:px-4 bg-[#F1F4F9]"
      >
        <div className="flex items-center gap-1 md:gap-2 min-w-max">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`min-h-[48px] px-3 py-2.5 flex items-center gap-2 text-sm font-hind no-underline transition-colors ${
                  isActive
                    ? "border-t-2 border-[#0054A6] text-[#0054A6] font-bold bg-[#FFFFFF]"
                    : "border-t-2 border-transparent text-[#6A6355] hover:text-[#1E1B16] hover:border-[#D8CFBB]"
                }`}
              >
                {item.customIcon ? (
                  <span className={`inline-flex items-center shrink-0 ${isActive ? "text-[#0054A6]" : "text-[#6A6355]"}`}>
                    {item.customIcon}
                  </span>
                ) : (
                  <MaterialIcon
                    name={item.icon || "info"}
                    size={19}
                    className={isActive ? "text-[#0054A6]" : "text-[#6A6355]"}
                  />
                )}
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}