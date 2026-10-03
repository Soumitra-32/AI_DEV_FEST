"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useLanguage } from "@/components/LangToggle";
import { formatBDT, formatInteger } from "@/lib/i18n";

interface DoNothingToggleProps {
  costBdt?: number | null;
  months?: number | null;
  /** Page-specific outcome line. When absent, the horizon-templated default. */
  outcome?: string | null;
}

/**
 * Section 7: "কিছু না করলে কী হবে?" (Do Nothing Option)
 * Both Collapsed & Expanded states matching the ledger design system.
 */
export default function DoNothingToggle({ costBdt, months, outcome }: DoNothingToggleProps) {
  const { lang, tr } = useLanguage();
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState(false);
  // The horizon belongs to the plan being viewed: a 12-month plan must not
  // say "after 6 months". Pages without a horizon keep the legacy text.
  const defaultOutcome =
    months != null && Number.isFinite(months) && months >= 1
      ? (months === 1
          ? tr("common.doNothingOutcome1")
          : tr("common.doNothingOutcomeN").replace("{months}", formatInteger(months, lang)))
      : tr("common.doNothingOutcome");
  const outcomeText = outcome ?? defaultOutcome;

  if (!open) {
    return (
      <div
        className="bg-surface border border-rule rounded-ledger p-4 flex items-center justify-between cursor-pointer mb-6 hover:border-ink transition-colors"
        onClick={() => setOpen(true)}
      >
        <div className="space-y-0.5">
          <div className="font-bold text-base text-ink">
            {tr("common.doNothing")}
          </div>
        </div>
        <ChevronDown className="w-5 h-5 text-ink-muted" strokeWidth={1.5} />
      </div>
    );
  }

  return (
    <div className="bg-surface border border-rule rounded-ledger p-5 space-y-3 mb-6">
      <div
        className="flex items-center justify-between border-b border-rule pb-2 cursor-pointer"
        onClick={() => setOpen(false)}
      >
        <div className="font-serif-bn font-bold text-base text-ink">
          {tr("common.doNothing")}
        </div>
        <ChevronUp className="w-5 h-5 text-ink-muted" strokeWidth={1.5} />
      </div>

      <p className="text-sm font-medium text-ink leading-relaxed">
        {outcomeText}
      </p>

      {typeof costBdt === "number" && (
        <div className="flex items-baseline justify-between text-sm py-1 border-t border-b border-rule">
          <span className="text-ink-muted">{tr("common.doNothingCost")}</span>
          <span className="dotted-leader" />
          <strong className="font-serif-bn text-base text-brickRed">
            {formatBDT(costBdt, lang)}
          </strong>
        </div>
      )}

      <div className="text-xs text-ink-muted border-t border-rule pt-2 leading-relaxed">
        {tr("common.doNothingDisclaimer")}
      </div>

      {!chosen ? (
        <div className="pt-2 flex items-center gap-3">
          <button
            type="button"
            className="primary text-xs"
            onClick={() => setChosen(true)}
          >
            {tr("common.doNothingConfirm")}
          </button>
          <button
            type="button"
            className="text-xs"
            onClick={() => setOpen(false)}
          >
            {tr("common.doNothingDismiss")}
          </button>
        </div>
      ) : (
        <p className="text-xs font-mono text-primaryGreen pt-2" role="status">
          ✓ {tr("common.doNothingChosen")}
        </p>
      )}
    </div>
  );
}
