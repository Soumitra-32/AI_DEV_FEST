"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";
import { formatBDT } from "@/lib/i18n";
import type { FeeSwitchSuggestion } from "@/lib/api";

interface FeeSavingCardProps {
  feeSwitch: FeeSwitchSuggestion;
}

export default function FeeSavingCard({ feeSwitch }: FeeSavingCardProps) {
  const { lang, tr } = useLanguage();

  return (
    <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 mb-6 space-y-4">
      <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
        <span className="uppercase">{tr("spending.feeSwitch")}</span>
        <span className="border border-ink-muted rounded-stamp px-2 py-0.5 text-[11px]">
          {tr("stamp.computed")}
        </span>
      </div>

      <div className="space-y-1">
        <div className="font-serif-bn text-3xl md:text-4xl font-bold text-ink tracking-tight">
          {formatBDT(feeSwitch.potential_saving_bdt, lang)}{" "}
          <span className="text-sm font-hind font-normal text-ink-muted">
            {tr("spending.potentialSaving")} {tr("spending.perMonth")}
          </span>
        </div>
        <p className="text-sm text-ink-muted leading-relaxed font-hind">
          {lang === "bn"
            ? `এজেন্ট ক্যাশ-আউটের বদলে ${feeSwitch.alternative_channel === "app_transfer" ? "অ্যাপ ট্রান্সফার বা মার্চেন্ট পেমেন্ট" : feeSwitch.alternative_channel} ব্যবহার করলে আপনার বাড়তি ফি বাঁচবে।`
            : `Switching from agent cash-out to ${feeSwitch.alternative_channel} can avoid transaction fees.`}
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs font-mono">
        <div className="p-2.5 bg-paper/60 border border-rule rounded-stamp space-y-0.5">
          <div className="text-ink-muted">{tr("spending.currentFee")}</div>
          <div className="font-bold text-ink text-sm font-serif-bn">
            {formatBDT(feeSwitch.fee_paid_bdt, lang)}
          </div>
        </div>
        <div className="p-2.5 bg-paper/60 border border-rule rounded-stamp space-y-0.5">
          <div className="text-ink-muted">{tr("spending.altFee")}</div>
          <div className="font-bold text-primaryGreen text-sm font-serif-bn">
            {formatBDT(feeSwitch.alternative_fee_bdt, lang)}
          </div>
        </div>
        <div className="p-2.5 bg-paper/60 border border-rule rounded-stamp space-y-0.5 col-span-2 sm:col-span-1">
          <div className="text-ink-muted">{tr("spending.adoption")}</div>
          <div className="font-bold text-ink text-sm">
            {feeSwitch.adoption_range}
          </div>
        </div>
      </div>

      <div className="pt-2 space-y-2">
        <Link href="/plan" className="block no-underline">
          <button
            type="button"
            className="w-full h-12 bg-primaryGreen text-white text-[17px] font-medium rounded-ledger hover:opacity-95 transition"
          >
            {tr("home.startSavings")}
          </button>
        </Link>
        <div className="text-center pt-1">
          <Link
            href="/forecast"
            className="text-xs font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors"
          >
            {tr("home.viewDetails")}
          </Link>
        </div>
      </div>
    </div>
  );
}
