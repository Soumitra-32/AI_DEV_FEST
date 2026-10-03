"use client";

import { useLanguage } from "@/components/LangToggle";

interface NotADecisionBannerProps {
  contextNote?: string;
}

export default function NotADecisionBanner({ contextNote }: NotADecisionBannerProps) {
  const { tr } = useLanguage();
  return (
    <div
      className="bg-surface/50 border-l-2 border-ink border-t border-r border-b border-rule/60 p-4 space-y-1 mb-6"
      role="note"
    >
      <div className="text-xs font-mono uppercase tracking-wider text-ink font-bold flex items-center gap-1.5">
        <span>{tr("banner.title")}</span>
      </div>
      <p className="text-sm font-medium text-ink leading-relaxed font-hind">
        &ldquo;{contextNote || tr("banner.notADecision")}&rdquo;
      </p>
    </div>
  );
}
