"use client";

import { usePathname } from "next/navigation";
import { useLanguage } from "@/components/LangToggle";
import type { TranslationKey } from "@/lib/i18n";

type BannerRoute = "home" | "forecast" | "plan" | "spending" | "tips" | "signal" | "metrics";

interface NotADecisionBannerProps {
  route?: BannerRoute;
  contextNote?: string;
}

export default function NotADecisionBanner({ route, contextNote }: NotADecisionBannerProps) {
  const { tr } = useLanguage();
  const pathname = usePathname();

  // Determine route key from prop or current pathname
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

  const routeKey = `banner.notADecision.${detectedRoute}` as TranslationKey;
  const bannerText = contextNote || tr(routeKey) || tr("banner.notADecision");

  return (
    <div
      className="bg-surface/50 border-l-2 border-ink border-t border-r border-b border-rule/60 p-4 space-y-1 mb-6"
      role="note"
    >
      <div className="text-xs font-mono uppercase tracking-wider text-ink font-bold flex items-center gap-1.5">
        <span>{tr("banner.title")}</span>
      </div>
      <p className="text-sm font-medium text-ink leading-relaxed font-hind">
        &ldquo;{bannerText}&rdquo;
      </p>
    </div>
  );
}
