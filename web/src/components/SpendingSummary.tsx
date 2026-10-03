"use client";

import { useLanguage } from "@/components/LangToggle";
import { formatBDT, formatInteger } from "@/lib/i18n";
import type { FeeSwitchSuggestion } from "@/lib/api";
import Stamp from "@/components/Stamp";

interface SpendingSummaryProps {
  feeSwitch?: FeeSwitchSuggestion | null;
  windowDays?: number;
}

/**
 * Section 5: Ledger Rows with Dotted Leaders & Accounting Rules
 */
export default function SpendingSummary({ feeSwitch, windowDays = 30 }: SpendingSummaryProps) {
  const { lang, tr } = useLanguage();

  if (!feeSwitch) {
    return null;
  }

  return (
    <div className="border-t border-b border-rule bg-surface/50 p-4 md:p-6 mb-6 space-y-4">
      <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
        <span className="uppercase">
          {tr("spending.summary")} ({formatInteger(windowDays, lang)} {tr("spending.daysUnit")})
        </span>
        <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
      </div>

      <div className="space-y-3 font-hind text-base">
        {/* Row 1: Cash-out count */}
        <div>
          <div className="flex items-baseline justify-between">
            <span className="font-medium text-ink">{tr("spending.cashOutCount")}</span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-lg text-ink text-right tabular-nums">
              {formatInteger(feeSwitch.cash_out_count, lang)} {tr("spending.times")}
            </span>
          </div>
          <div className="text-[12px] text-ink-muted -mt-1 pl-1 font-hind">
            {tr("spending.cashOutCountSub")}
          </div>
        </div>

        {/* Row 2: Cash-out volume */}
        <div>
          <div className="flex items-baseline justify-between pt-1">
            <span className="font-medium text-ink">{tr("spending.cashOutVolume")}</span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-lg text-ink text-right tabular-nums">
              {formatBDT(feeSwitch.cash_out_volume_bdt, lang)}
            </span>
          </div>
          <div className="text-[12px] text-ink-muted -mt-1 pl-1 font-hind">
            {tr("spending.cashOutVolumeSub")}
          </div>
        </div>

        {/* Row 3: Fee paid */}
        <div>
          <div className="flex items-baseline justify-between pt-1">
            <span className="font-medium text-ink">{tr("spending.feePaid")}</span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-lg text-brickRed text-right tabular-nums">
              {formatBDT(feeSwitch.fee_paid_bdt, lang)}
            </span>
          </div>
          <div className="text-[12px] text-ink-muted -mt-1 pl-1 font-hind">
            {tr("spending.feePaidSub")}
          </div>
        </div>

        {/* Total Accounting Rule: Potential saving */}
        <div className="pt-3 mt-2">
          <div className="border-t border-rule pt-2 pb-2 ledger-double-bottom flex items-baseline justify-between">
            <span className="font-bold text-ink font-serif-bn text-lg">
              {tr("spending.potentialSaving")}
            </span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-2xl text-primaryGreen text-right tabular-nums">
              {formatBDT(feeSwitch.potential_saving_bdt, lang)}
            </span>
          </div>
          <div className="text-xs text-ink-muted pt-1 text-right font-mono">
            {tr("spending.singleRuleTop")}
          </div>
        </div>
      </div>
    </div>
  );
}
