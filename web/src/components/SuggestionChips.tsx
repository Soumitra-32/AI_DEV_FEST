"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

interface SuggestionChipsProps {
  onSelectQuery?: (query: string) => void;
}

export default function SuggestionChips({ onSelectQuery }: SuggestionChipsProps) {
  const { lang, tr } = useLanguage();

  const suggestions = [
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
      labelBn: "আগামী ১৪ দিন দেখাও",
      labelEn: "See the next 14 days",
      href: "/forecast",
    },
    {
      labelBn: "৬ মাসে ৳৩০,০০০ জমাতে চাই",
      labelEn: "Save ৳30,000 in 6 months",
      href: "/plan?goal=30000&months=6",
      isQuery: true,
      queryBn: "৬ মাসে ৳৩০,০০০ জমাতে চাই",
      queryEn: "Save ৳30,000 in 6 months",
    },
  ];

  return (
    <div className="space-y-2 pt-2 border-t border-rule">
      <span className="text-xs font-mono uppercase text-ink-muted block">
        {tr("voice.suggestedTitle")}
      </span>
      <div className="flex flex-wrap items-center gap-x-4 md:gap-x-6 gap-y-2 text-sm font-medium">
        {suggestions.map((item, idx) => {
          const label = lang === "bn" ? item.labelBn : item.labelEn;
          const query = lang === "bn" ? item.queryBn : item.queryEn;
          return (
            <span key={item.labelBn} className="inline-flex items-center gap-x-4 md:gap-x-6">
              {item.isQuery && onSelectQuery ? (
                <button
                  type="button"
                  onClick={() => onSelectQuery(query ?? label)}
                  className="bg-transparent border-0 p-0 text-primaryGreen underline underline-offset-4 decoration-primaryGreen/50 hover:text-ink cursor-pointer text-sm font-medium font-hind"
                >
                  {label}
                </button>
              ) : (
                <Link
                  href={item.href}
                  className="text-primaryGreen underline underline-offset-4 decoration-primaryGreen/50 hover:text-ink transition-colors font-hind"
                >
                  {label}
                </Link>
              )}
              {idx < suggestions.length - 1 && (
                <span className="text-rule select-none">/</span>
              )}
            </span>
          );
        })}
      </div>
    </div>
  );
}
