"use client";

import { useLanguage } from "@/components/LangToggle";

export default function NotADecisionBanner() {
  const { tr } = useLanguage();
  return (
    <div
      className="bg-surface border-l-4 border-ink border-t border-r border-b border-rule p-4 space-y-1 rounded-ledger mb-6"
      role="note"
    >
      <div className="text-xs font-mono uppercase tracking-wider text-ink font-bold flex items-center gap-1.5">
        <span>{tr("banner.title")}</span>
      </div>
      <p className="text-sm font-medium text-ink leading-relaxed">
        &ldquo;{tr("banner.notADecision")}&rdquo;
      </p>
    </div>
  );
}
