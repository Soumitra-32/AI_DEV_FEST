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
          {tr("spending.feeSwitchDesc")}
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

      {/* 1 Oct 2026 Bangladesh Bank Bangla QR Callout */}
      <div className="border-t border-rule pt-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-ink font-serif-bn text-sm">
            {tr("spending.banglaQrTitle")}
          </span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 border border-primaryGreen text-primaryGreen rounded-stamp">
            ০% মার্চেন্ট ফি
          </span>
        </div>
        <p className="text-xs text-ink-muted leading-relaxed font-hind">
          {tr("spending.banglaQrDesc")}
        </p>

        {feeSwitch.bangla_qr_eligible_count ? (
          <div className="p-2.5 bg-paper/40 border border-rule rounded-stamp space-y-1 text-xs">
            <div className="font-medium text-ink font-hind">
              {tr("spending.banglaQrEligible")
                .replace("{count}", String(feeSwitch.bangla_qr_eligible_count))
                .replace(
                  "{volume}",
                  formatBDT(feeSwitch.bangla_qr_eligible_volume_bdt ?? 0, lang)
                )}
            </div>
            <ul className="list-disc list-inside text-ink-muted text-[11px] space-y-0.5 pt-0.5">
              <li>{tr("spending.banglaQrCustomerBenefit")}</li>
              <li>{tr("spending.banglaQrUpayBenefit")}</li>
            </ul>
          </div>
        ) : null}

        {/* Anti-misuse statutory warning banner */}
        <div className="border border-rule bg-paper/30 rounded-stamp p-2.5 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-brickRed font-bold">
            {tr("spending.banglaQrAntiMisuseTitle")}
          </div>
          <p className="text-[11px] text-ink-muted leading-relaxed font-hind">
            {tr("spending.banglaQrAntiMisuseText")}
          </p>
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
