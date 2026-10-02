"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, TrendingUp, Wallet, Receipt, Menu } from "lucide-react";
import { useLanguage } from "@/components/LangToggle";

export default function BottomNav() {
  const pathname = usePathname();
  const { tr } = useLanguage();

  const navItems = [
    { href: "/", label: tr("nav.home"), icon: BookOpen },
    { href: "/forecast", label: tr("nav.forecast"), icon: TrendingUp },
    { href: "/plan", label: tr("nav.plan"), icon: Wallet },
    { href: "/spending", label: tr("nav.spending"), icon: Receipt },
    { href: "/tips", label: tr("nav.more"), icon: Menu },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-rule">
      <div className="max-w-4xl mx-auto grid grid-cols-5 text-center text-xs">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`py-2.5 flex flex-col items-center justify-center transition-colors no-underline ${
                isActive
                  ? "border-t-2 border-primaryGreen text-primaryGreen font-bold"
                  : "border-t-2 border-transparent text-ink-muted hover:text-ink"
              }`}
            >
              <Icon className="w-4 h-4 mb-0.5" strokeWidth={1.5} />
              <span className="text-[11px] font-hind leading-tight">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
