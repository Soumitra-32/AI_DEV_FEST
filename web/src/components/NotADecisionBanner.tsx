"use client";

import { useLanguage } from "@/components/LangToggle";

/**
 * Always-visible banner wherever the consistency signal appears:
 * this is never a lending decision.
 */
export default function NotADecisionBanner() {
  const { tr } = useLanguage();
  return (
    <div className="banner" role="note">
      {tr("banner.notADecision")}
    </div>
  );
}
