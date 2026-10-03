"use client";

import { usePathname } from "next/navigation";
import { useLanguage } from "@/components/LangToggle";
import type { TranslationKey } from "@/lib/i18n";
import MaterialIcon from "@/components/MaterialIcon";

type BannerRoute = "home" | "forecast" | "plan" | "spending" | "tips" | "signal" | "metrics";

interface NotADecisionBannerProps {
  route?: BannerRoute;
  contextNote?: string;
}

export default function NotADecisionBanner({ route, contextNote }: NotADecisionBannerProps) {
  const { lang, tr } = useLanguage();
  const pathname = usePathname();

  const detectedRoute: BannerRoute =
    route ??
    (pathname === "/forecast"
      ? "forecast"
      : pathname === "/plan"
        ? "plan"
        : pathname === "/spending"
          ? "spending"
          : pathname === "/tips"
            ? "tips"
            : pathname === "/signal"
              ? "signal"
              : pathname === "/metrics"
                ? "metrics"
                : "home");

  const defaultLegal =
    lang === "bn"
      ? "এটি শুধু শিক্ষামূলক ইঙ্গিত, কোনো ঋণ বা আর্থিক সিদ্ধান্ত নয়। আপনার অনুমতি ছাড়া কোনো টাকা সরানো হবে না।"
      : "This is educational guidance only, not a loan or financial decision. No money moves without your permission.";

  const routeKey = `banner.notADecision.${detectedRoute}` as TranslationKey;
  const bannerText = contextNote || (detectedRoute === "home" ? defaultLegal : (tr(routeKey) || defaultLegal));

  return (
    <div
      className="bg-[#F1F4F9] border-l-[3px] border-[#1E1B16] border-t border-r border-b border-[#D8CFBB] rounded-[6px] p-4 mb-6"
      role="note"
    >
      <div className="flex items-start gap-2.5">
        <MaterialIcon name="info" size={20} className="text-[#1E1B16] mt-0.5" />
        <div className="space-y-1">
          <div className="text-xs font-mono uppercase tracking-wider text-[#6A6355] font-bold">
            {tr("banner.title")}
          </div>
          <p className="text-sm font-medium text-[#1E1B16] leading-relaxed font-hind m-0">
            {bannerText}
          </p>
        </div>
      </div>
    </div>
  );
}
