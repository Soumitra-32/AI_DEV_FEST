"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";
import { formatBDT, formatDigits } from "@/lib/i18n";
import type { FeeSwitchSuggestion } from "@/lib/api";
import Stamp from "@/components/Stamp";

interface FeeSavingCardProps {
  feeSwitch: FeeSwitchSuggestion;
}

export default function FeeSavingCard({ feeSwitch }: FeeSavingCardProps) {
  const { lang, tr } = useLanguage();

  return (
    <div className="border border-[#D8CFBB] bg-[#F1F4F9] rounded-[6px] p-5 md:p-6 mb-6 space-y-4">
      <div className="flex items-center justify-between text-xs font-mono text-[#6A6355] border-b border-[#D8CFBB] pb-2">
        <span className="uppercase">{tr("spending.feeSwitch")}</span>
        <Stamp variant="blue">{tr("stamp.computed")}</Stamp>
      </div>

      <div className="space-y-1">
        <div className="font-serif-bn text-3xl md:text-4xl font-bold text-[#1E1B16] tracking-tight tabular-nums">
          {formatBDT(feeSwitch.potential_saving_bdt, lang)}{" "}
          <span className="text-sm font-hind font-normal text-[#6A6355]">
            {tr("spending.potentialSaving")} {tr("spending.perMonth")}
          </span>
        </div>
        <p className="text-sm text-[#6A6355] leading-relaxed font-hind">
          {tr("spending.feeSwitchDesc")}
        </p>
        <p className="text-xs text-[#6A6355] font-hind">
          {lang === "bn"
            ? `প্রত্যাশিত ব্যবহারের হার (${formatDigits(feeSwitch.adoption_range || "৩০%–৭০%", lang)}): মাসে আনুমানিক ${formatBDT(Math.round(feeSwitch.potential_saving_bdt * 0.3), lang)} থেকে ${formatBDT(Math.round(feeSwitch.potential_saving_bdt * 0.7), lang)} পর্যন্ত সাশ্রয় হতে পারে।`
            : `Expected adoption range (${feeSwitch.adoption_range || "30%–70%"}): estimated monthly savings between ${formatBDT(Math.round(feeSwitch.potential_saving_bdt * 0.3), lang)} and ${formatBDT(Math.round(feeSwitch.potential_saving_bdt * 0.7), lang)}.`}
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs font-mono">
        <div className="p-2.5 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] space-y-0.5">
          <div className="text-[#6A6355]">{tr("spending.currentFee")}</div>
          <div className="font-bold text-[#1E1B16] text-sm font-serif-bn text-right tabular-nums">
            {formatBDT(feeSwitch.fee_paid_bdt, lang)}
          </div>
        </div>
        <div className="p-2.5 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] space-y-0.5">
          <div className="text-[#6A6355]">{tr("spending.altFee")}</div>
          <div className="font-bold text-[#0054A6] text-sm font-serif-bn text-right tabular-nums">
            {formatBDT(feeSwitch.alternative_fee_bdt, lang)}
          </div>
        </div>
        <div className="p-2.5 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] space-y-0.5 col-span-2 sm:col-span-1">
          <div className="text-[#6A6355]">{tr("spending.adoption")}</div>
          <div className="font-bold text-[#1E1B16] text-sm text-right">
            {formatDigits(feeSwitch.adoption_range, lang)}{" "}
            {lang === "bn" ? "মানুষ" : "of people"}
          </div>
        </div>
      </div>

      {/* 1 Oct 2026 Bangladesh Bank Bangla QR Callout */}
      <div className="border-t border-[#D8CFBB] pt-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-[#1E1B16] font-serif-bn text-sm">
            {tr("spending.banglaQrTitle")}
          </span>
          <Stamp variant="blue">
            {tr("spending.banglaQrNoFee")}
          </Stamp>
        </div>
        <p className="text-xs text-[#6A6355] leading-relaxed font-hind">
          {tr("spending.banglaQrDesc")}
        </p>

        {feeSwitch.bangla_qr_eligible_count ? (
          <div className="p-3 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] space-y-1 text-xs">
            <div className="font-medium text-[#1E1B16] font-hind">
              {tr("spending.banglaQrEligible")
                .replace("{count}", formatDigits(String(feeSwitch.bangla_qr_eligible_count), lang))
                .replace(
                  "{volume}",
                  formatBDT(feeSwitch.bangla_qr_eligible_volume_bdt ?? 0, lang)
                )}
            </div>
            <ul className="list-disc list-inside text-[#6A6355] text-[11px] space-y-0.5 pt-0.5">
              <li>{tr("spending.banglaQrCustomerBenefit")}</li>
              <li>{tr("spending.banglaQrUpayBenefit")}</li>
            </ul>
          </div>
        ) : null}

        {/* Anti-misuse statutory warning banner */}
        <div className="border-l-[3px] border-[#B0431F] border-t border-r border-b border-[#D8CFBB] bg-[#FFFFFF] rounded-[6px] p-3 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#B0431F] font-bold">
            {tr("spending.banglaQrAntiMisuseTitle")}
          </div>
          <p className="text-[11px] text-[#6A6355] leading-relaxed font-hind m-0">
            {tr("spending.banglaQrAntiMisuseText")}
          </p>
        </div>
      </div>

      <div className="pt-2 space-y-2">
        <Link href="/plan" className="block no-underline">
          <button
            type="button"
            className="w-full min-h-[48px] h-12 bg-[#0054A6] hover:bg-[#003E7E] text-white text-[16px] font-medium rounded-[6px] transition-colors cursor-pointer border-0"
          >
            {tr("home.startSavings")}
          </button>
        </Link>
        <div className="text-center pt-1">
          <Link
            href="/forecast"
            className="text-xs font-semibold text-[#0054A6] hover:text-[#003E7E] underline underline-offset-4 decoration-[#0054A6]/60 transition-colors"
          >
            {tr("home.viewDetails")}
          </Link>
        </div>
      </div>
    </div>
  );
}
