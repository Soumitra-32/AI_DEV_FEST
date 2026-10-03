"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

interface SuggestionItem {
  labelBn: string;
  labelEn: string;
  href: string;
}

const SUGGESTIONS: SuggestionItem[] = [
  {
    labelBn: "আমার খরচ দেখাও",
    labelEn: "Show my spending",
    href: "/spending",
  },
  {
    labelBn: "আমার সঞ্চয় পরিকল্পনা দেখাও",
    labelEn: "Show my savings plan",
    href: "/plan",
  },
  {
    labelBn: "আগামী ১৪ দিনের পূর্বাভাস দেখাও",
    labelEn: "Show 14-day cash forecast",
    href: "/forecast",
  },
];

interface SuggestionChipsProps {
  onSelectQuery?: (query: string, href: string) => void;
}

export default function SuggestionChips({ onSelectQuery }: SuggestionChipsProps) {
  const { lang, tr } = useLanguage();

  return (
    <div className="space-y-2 pt-3 border-t border-[#D8CFBB]">
      <span className="text-xs font-mono uppercase text-[#6A6355] block">
        {tr("voice.suggestedTitle")}
      </span>
      <div className="flex flex-wrap items-center gap-x-5 md:gap-x-8 gap-y-2">
        {SUGGESTIONS.map((item, idx) => {
          const label = lang === "bn" ? item.labelBn : item.labelEn;
          return (
            <span key={item.href} className="inline-flex items-center gap-x-5 md:gap-x-8">
              <Link
                href={item.href}
                onClick={() => onSelectQuery?.(label, item.href)}
                className="min-h-[48px] inline-flex items-center text-[#0054A6] hover:text-[#003E7E] underline underline-offset-4 decoration-[#0054A6] transition-colors text-sm font-medium font-hind select-none"
              >
                {label}
              </Link>
              {idx < SUGGESTIONS.length - 1 && (
                <span className="text-[#D8CFBB] select-none" aria-hidden="true">
                  /
                </span>
              )}
            </span>
          );
        })}
      </div>
    </div>
  );
}
