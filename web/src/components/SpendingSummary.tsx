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
    <div className="border border-[#D8CFBB] bg-[#F1F4F9] rounded-[6px] p-5 md:p-6 mb-6 space-y-4">
      <div className="flex items-center justify-between text-xs font-mono text-[#6A6355] border-b border-[#D8CFBB] pb-2">
        <span className="uppercase">
          {tr("spending.summary")} ({formatInteger(windowDays, lang)} {tr("spending.daysUnit")})
        </span>
        <Stamp variant="blue">{tr("stamp.computed")}</Stamp>
      </div>

      <div className="space-y-3 font-hind text-base">
        {/* Row 1: Cash-out count */}
        <div>
          <div className="flex items-baseline justify-between">
            <span className="font-medium text-[#1E1B16]">{tr("spending.cashOutCount")}</span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-lg text-[#1E1B16] text-right tabular-nums">
              {formatInteger(feeSwitch.cash_out_count, lang)} {tr("spending.times")}
            </span>
          </div>
          <div className="text-[12px] text-[#6A6355] -mt-1 pl-1 font-hind">
            {tr("spending.cashOutCountSub")}
          </div>
        </div>

        {/* Row 2: Cash-out volume */}
        <div>
          <div className="flex items-baseline justify-between pt-1">
            <span className="font-medium text-[#1E1B16]">{tr("spending.cashOutVolume")}</span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-lg text-[#1E1B16] text-right tabular-nums">
              {formatBDT(feeSwitch.cash_out_volume_bdt, lang)} {tr("common.taka")}
            </span>
          </div>
          <div className="text-[12px] text-[#6A6355] -mt-1 pl-1 font-hind">
            {tr("spending.cashOutVolumeSub")}
          </div>
        </div>

        {/* Row 3: Fee paid */}
        <div>
          <div className="flex items-baseline justify-between pt-1">
            <span className="font-medium text-[#1E1B16]">{tr("spending.feePaid")}</span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-lg text-[#B0431F] text-right tabular-nums">
              {formatBDT(feeSwitch.fee_paid_bdt, lang)}
            </span>
          </div>
          <div className="text-[12px] text-[#6A6355] -mt-1 pl-1 font-hind">
            {tr("spending.feePaidSub")}
          </div>
        </div>

        {/* Total Accounting Rule: Potential saving */}
        <div className="pt-3 mt-2">
          <div className="border-t border-[#D8CFBB] pt-2.5 pb-2 ledger-double-bottom flex items-baseline justify-between">
            <span className="font-bold text-[#1E1B16] font-serif-bn text-lg">
              {tr("spending.potentialSaving")}
            </span>
            <span className="tab-leader" />
            <span className="font-serif-bn font-bold text-2xl text-[#0054A6] text-right tabular-nums">
              {formatBDT(feeSwitch.potential_saving_bdt, lang)}
            </span>
          </div>
          <div className="text-xs text-[#6A6355] pt-1 text-right font-mono">
            {tr("spending.singleRuleTop")}
          </div>
        </div>
      </div>
    </div>
  );
}
