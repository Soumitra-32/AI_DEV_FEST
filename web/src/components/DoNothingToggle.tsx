"use client";

import { useState } from "react";
import { useLanguage } from "@/components/LangToggle";
import { formatBDT, formatInteger } from "@/lib/i18n";
import MaterialIcon from "@/components/MaterialIcon";

interface DoNothingToggleProps {
  costBdt?: number | null;
  months?: number | null;
  outcome?: string | null;
}

/**
 * Component 5: “Do nothing” neutral option
 * - Collapsed: কিছু না করলে কী হবে? / What if I do nothing?
 * - Expanded: ৬ মাস পরে সঞ্চয় ৳০ থাকবে। এটাও আপনার সিদ্ধান্ত।
 * - Note: সম্পূর্ণ নিরপেক্ষ এবং স্বাভাবিক একটি পথ। কোনো ভয়ভীতি বা জরিমানা নেই।
 * - No fear, no red.
 */
export default function DoNothingToggle({ costBdt, months, outcome }: DoNothingToggleProps) {
  const { lang, tr } = useLanguage();
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState(false);

  const defaultOutcome =
    lang === "bn"
      ? (months && months !== 6
          ? `${formatInteger(months, "bn")} মাস পরে সঞ্চয় ৳০ থাকবে। এটাও আপনার সিদ্ধান্ত।`
          : "৬ মাস পরে সঞ্চয় ৳০ থাকবে। এটাও আপনার সিদ্ধান্ত।")
      : (months && months !== 6
          ? `After ${months} months, savings will be ৳0. This is also your decision.`
          : "After 6 months, savings will be ৳0. This is also your decision.");

  const neutralNote =
    lang === "bn"
      ? "সম্পূর্ণ নিরপেক্ষ এবং স্বাভাবিক একটি পথ। কোনো ভয়ভীতি বা জরিমানা নেই।"
      : "A completely neutral and natural path. No penalties or restrictions apply.";

  const collapsedLabel =
    lang === "bn" ? "কিছু না করলে কী হবে?" : "What if I do nothing?";

  const outcomeText = outcome ?? defaultOutcome;

  if (!open) {
    return (
      <div
        className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-4 md:p-5 flex items-center justify-between cursor-pointer mb-6 hover:border-[#0054A6] transition-colors"
        onClick={() => setOpen(true)}
      >
        <div className="font-serif-bn font-bold text-base md:text-lg text-[#1E1B16]">
          {collapsedLabel}
        </div>
        <MaterialIcon name="expand_more" size={24} className="text-[#6A6355]" />
      </div>
    );
  }

  return (
    <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-5 space-y-3 mb-6">
      <div
        className="flex items-center justify-between border-b border-[#D8CFBB] pb-3 cursor-pointer"
        onClick={() => setOpen(false)}
      >
        <div className="font-serif-bn font-bold text-base md:text-lg text-[#1E1B16]">
          {collapsedLabel}
        </div>
        <MaterialIcon name="expand_less" size={24} className="text-[#6A6355]" />
      </div>

      <p className="text-base font-medium text-[#1E1B16] leading-relaxed font-hind">
        {outcomeText}
      </p>

      {typeof costBdt === "number" && costBdt > 0 && (
        <div className="flex items-baseline justify-between text-sm py-2 border-t border-b border-[#D8CFBB] font-hind">
          <span className="text-[#6A6355]">{tr("common.doNothingCost")}</span>
          <span className="tab-leader" />
          <strong className="font-serif-bn text-base text-[#1E1B16] text-right tabular-nums">
            {formatBDT(costBdt, lang)} {tr("common.taka")}
          </strong>
        </div>
      )}

      <div className="text-xs text-[#6A6355] border-t border-[#D8CFBB] pt-2.5 leading-relaxed font-hind">
        {neutralNote}
      </div>

      {!chosen ? (
        <div className="pt-2 flex items-center gap-3">
          <button
            type="button"
            className="min-h-[48px] px-5 bg-[#0054A6] hover:bg-[#003E7E] text-white text-sm font-medium rounded-[6px] transition-colors"
            onClick={() => setChosen(true)}
          >
            {tr("common.doNothingConfirm")}
          </button>
          <button
            type="button"
            className="min-h-[48px] px-5 bg-[#FFFFFF] border border-[#D8CFBB] text-[#1E1B16] hover:border-[#0054A6] text-sm font-medium rounded-[6px] transition-colors"
            onClick={() => setOpen(false)}
          >
            {tr("common.doNothingDismiss")}
          </button>
        </div>
      ) : (
        <p className="text-xs font-mono text-[#0054A6] pt-2" role="status">
          ✓ {tr("common.doNothingChosen")}
        </p>
      )}
    </div>
  );
}
