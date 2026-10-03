"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/components/LangToggle";
import type { Provenance } from "@/lib/api";
import Stamp from "@/components/Stamp";
import type { TranslationKey } from "@/lib/i18n";
import { formatBDT, formatDigits, formatInteger } from "@/lib/i18n";

interface InsightCardProps {
  title?: string;
  children?: ReactNode;
  provenance?: Provenance | null;
  fallbackAssumption?: string;
}

/**
 * Section 6: Three-layer Explanation Block & Ledger Insight Card
 * Separates Prediction / Assumption / Explanation with rubber stamps.
 * Pure flat design on #FBF8F1 surface with #D8CFBB rule borders.
 */
function formatProvenanceContent(
  text: string | null | undefined,
  field: "prediction" | "assumption" | "explanation",
  lang: "bn" | "en",
  routeDefault: string,
): string {
  if (!text || !text.trim()) return routeDefault;
  const raw = text.trim();

  // Handle template fallback / internal debug messages
  if (
    raw.includes("fixed template answered") ||
    raw.includes("template path runs") ||
    raw.includes("Intent:") ||
    raw.includes("failed a check") ||
    raw.includes("not_attempted") ||
    raw.includes("no API key is set")
  ) {
    if (field === "prediction") {
      return lang === "bn"
        ? "আপনার নির্ভরযোগ্য খতিয়ান ও লেনদেন তথ্যের ভিত্তিতে এই হিসাবটি তৈরি করা হয়েছে।"
        : "Verified financial guidance calculated directly from your transaction ledger.";
    }
    if (field === "assumption") {
      return lang === "bn"
        ? "আপনার পূর্বের লেনদেন ও ক্যাশ-আউটের নির্ভরযোগ্য তথ্যের ভিত্তিতে হিসাব করা হয়েছে।"
        : "Calculated using verified transaction history and cash flow rules.";
    }
    if (field === "explanation") {
      return lang === "bn"
        ? "পরামর্শের প্রতিটি হিসাব আপনার ব্যক্তিগত লেনদেনের ইতিহাস থেকে সরাসরি সংকলিত।"
        : "Every figure in this recommendation is derived directly from your personal transaction ledger.";
    }
  }

  // In English mode, clean any lingering system debug notes
  if (lang === "en") {
    return raw
      .replace(/\s*\(note:[^)]+\)/gi, "")
      .replace(/^Intent:\s*\w+\.\s*/i, "Topic: Financial Guidance. ");
  }

  // In Bangla mode, translate backend model templates to Bangla
  if (raw.includes("Next") && raw.includes("days from") && raw.includes("net about")) {
    const takaMatch = raw.match(/net about ([\d,]+) taka/i);
    const amountStr = takaMatch ? takaMatch[1] : "";
    return amountStr
      ? `পরবর্তী ১৪ দিনের সম্ভাব্য উদ্বৃত্ত প্রায় ৳${amountStr}।`
      : "পরবর্তী ১৪ দিনের লেনদেনের পূর্বাভাস আপনার নিজস্ব ব্যয়ের ধারা অনুযায়ী হিসাবকৃত।";
  }
  if (raw.includes("14-day mean flow from the trained model")) {
    return "বিগত দিনের ব্যয়ের ধারা ও মডেলের পূর্বাভাস অনুযায়ী ৩ দিনের জরুরি খরচের বাফার রেখে হিসাবকৃত।";
  }
  if (raw.includes("Level from your own trailing-28-day average")) {
    return "বিগত ২৮ দিনের গড় লেনদেন ও সপ্তাহের ব্যয়ের ধরনের ভিত্তিতে হিসাবকৃত।";
  }
  if (raw.includes("Baseline outlook for") || raw.includes("Trailing 7-day average")) {
    return "বিগত ৭ দিনের গড় ব্যয়ের ভিত্তিতে সাধারণ পূর্বাভাস।";
  }
  if (raw.includes("Tightest day is")) {
    return "মাসের শেষ সপ্তাহে সম্ভাব্য ব্যয়ের চাপের দিনগুলোকে হিসেবে রেখে তৈরি।";
  }
  if (raw.includes("No pressure day in this window")) {
    return "এই সময়ে কোনো অতিরিক্ত চাপের দিন নেই — ব্যালেন্স নিরাপদ সীমার উপরে থাকবে।";
  }

  // Plan Service prediction string:
  // e.g. "Feasible: 30,000 in 6 months needs 5,000/month; you can keep about 7,765/month after the buffer."
  const planMatch = raw.match(/([\d,]+)\s+in\s+(\d+)\s+months\s+needs\s+([\d,]+)\/month;\s+you\s+can\s+keep\s+about\s+([\d,]+)\/month\s+after\s+the\s+buffer/i);
  if (planMatch) {
    const [, goal, months, req, keep] = planMatch;
    const isFeas = !raw.toLowerCase().includes("not feasible");
    if (lang === "bn") {
      const verdict = isFeas ? "পরিকল্পনা বাস্তবসম্মত:" : "পরিকল্পনা এখনই সম্ভব নয়:";
      return `${verdict} ${formatDigits(months, "bn")} মাসে ${formatBDT(Number(goal.replace(/,/g, "")), "bn")} জমাতে মাসে ${formatBDT(Number(req.replace(/,/g, "")), "bn")} লাগবে; বাফার বাদে আপনি মাসে ${formatBDT(Number(keep.replace(/,/g, "")), "bn")} রাখতে পারবেন।`;
    } else {
      const verdict = isFeas ? "Feasible:" : "Not feasible as stated:";
      return `${verdict} ৳${goal} in ${months} months needs ৳${req}/month; you can keep about ৳${keep}/month after the buffer.`;
    }
  }

  // Plan
  if (raw.includes("Plan feasible") || raw.includes("Feasible:")) {
    return "পরিকল্পনা বাস্তবসম্মত: নিয়মিত উদ্বৃত্ত থেকে লক্ষ্যটি অর্জন করা সম্ভব।";
  }
  if (raw.includes("Plan not feasible") || raw.includes("Not feasible as stated")) {
    return "বর্তমান উদ্বৃত্ত অনুযায়ী লক্ষ্যটি অর্জন করতে সময়সীমা বা জমার পরিমাণ সমন্বয় করতে হতে পারে।";
  }
  if (raw.includes("Monthly surplus is the 14-day forecast scaled")) {
    return "মাসিক উদ্বৃত্ত ১৪ দিনের পূর্বাভাসের ভিত্তিতে নির্ণীত; ওয়ালেটে নিয়মিত খরচের বাফার রাখা হয়েছে।";
  }
  if (raw.includes("The forecast covers the goal with the safety buffer kept")) {
    return "নিরাপত্তা বাফার অক্ষত রেখেই পূর্বাভাস অনুযায়ী লক্ষ্য পূরণ সম্ভব।";
  }
  if (raw.includes("Pick a trade-off below") || raw.includes("free up monthly cash")) {
    return "নিচে বিকল্প উপায় বেছে নিন, অথবা লক্ষ্য পূরণে মাসিক খরচ কমানোর পরিকল্পনা করুন।";
  }
  if (raw.includes("A goal amount and a horizon")) {
    return "আপনার বার্তা থেকে লক্ষ্য ও সময়সীমা উভয়ের ভিত্তিতে হিসাবকৃত।";
  }
  if (raw.includes("The solver never runs on a guessed number")) {
    return "অনুমান নয়, শুধুমাত্র নিশ্চিত তথ্যের ভিত্তিতে সমাধান তৈরি হয়।";
  }

  // Spending / Anomalies
  if (raw.includes("least typical payments") || raw.includes("ranked against your own history")) {
    return "বিগত ৩০ দিনের লেনদেনের মধ্যে সবচেয়ে ব্যতিক্রমী লেনদেনসমূহ চিহ্নিত করা হয়েছে।";
  }
  if (raw.includes("No payment of your last") || raw.includes("stands out against your own history")) {
    return "বিগত ৩০ দিনে আপনার সাধারণ অভ্যাসের বাইরে কোনো অস্বাভাবিক লেনদেন পাওয়া যায়নি।";
  }
  if (raw.includes("Unusual means far from your own recent pattern")) {
    return "অস্বাভাবিক লেনদেন বলতে আপনার নিয়মিত সময়ের বাইরে বা গড় পরিমাণের চেয়ে বহুগুণ বেশি লেনদেনকে বোঝায়।";
  }
  if (raw.includes("cash-out(s) cost") && raw.includes("switching to")) {
    return "ক্যাশ-আউটে অতিরিক্ত ফি খরচ হচ্ছে; দোকানে সরাসরি বাংলা কিউআরে পেমেন্ট করলে সাশ্রয় সম্ভব।";
  }
  if (raw.includes("No cash-out fee stands out")) {
    return "এই সময়ে অতিরিক্ত ক্যাশ-আউট ফি দেখা যায়নি।";
  }

  // Signal
  if (raw.includes("Your recent behaviour sits in the")) {
    return "আপনার সাম্প্রতিক লেনদেনের অভ্যাস পরবর্তী মাসগুলোতে ধারাবাহিকতার এই স্তরে থাকবে।";
  }
  if (raw.includes("Based only on the transactions you can see")) {
    return "কেবলমাত্র আপনার নিজস্ব দৃশ্যমান লেনদেনের ইতিহাস ও খতিয়ান ডেটার ভিত্তিতে তৈরি।";
  }
  if (raw.includes("This is a reading of your habits")) {
    return "এটি আপনার লেনদেন অভ্যাসের পরিমাপ, কোনো ব্যক্তিগত বিচার বা ঋণ প্রদানের সিদ্ধান্ত নয়।";
  }

  // Fallback: if text is still English in Bangla mode, use route default
  if (/^[A-Za-z0-9\s.,;:'"()\-–—৳/]+$/.test(raw) && routeDefault) {
    return routeDefault;
  }

  return raw.replace(/ঐতিহাসিক/g, "পূর্বের");
}

export default function InsightCard({
  title,
  children,
  provenance,
  fallbackAssumption,
}: InsightCardProps) {
  const { lang, tr } = useLanguage();
  const pathname = usePathname();

  const routeDefaultAssumption =
    pathname === "/forecast"
      ? tr("assumption.forecast")
      : pathname === "/plan"
        ? tr("assumption.plan")
        : pathname === "/spending"
          ? tr("assumption.spending")
          : pathname === "/tips"
            ? tr("assumption.tips")
            : tr("assumption.forecast");

  const effectiveAssumption =
    provenance?.assumption && provenance.assumption.trim().length > 0
      ? provenance.assumption
      : (fallbackAssumption || routeDefaultAssumption);

  const renderedPrediction = provenance
    ? formatDigits(formatProvenanceContent(provenance.prediction, "prediction", lang, ""), lang)
    : "";
  const renderedAssumption = provenance
    ? formatDigits(formatProvenanceContent(effectiveAssumption, "assumption", lang, routeDefaultAssumption), lang)
    : "";
  const renderedExplanation = provenance
    ? formatDigits(formatProvenanceContent(provenance.explanation, "explanation", lang, ""), lang)
    : "";

  return (
    <section className="border border-[#D8CFBB] bg-[#F1F4F9] rounded-[6px] mb-6 overflow-hidden">
      {/* Title & Main Content */}
      {(title || children) && (
        <div className="p-4 md:p-6 space-y-3 bg-[#FFFFFF]">
          {title && (
            <div className="flex items-baseline justify-between border-b border-[#D8CFBB] pb-2">
              <h2 className="font-serif-bn font-bold text-xl text-[#1E1B16] m-0">{title}</h2>
              <Stamp variant="blue">{tr("stamp.verified")}</Stamp>
            </div>
          )}
          {children}
        </div>
      )}

      {/* 3-Layer Explanation Block */}
      {provenance && (
        <div className="border-t border-[#D8CFBB] divide-y divide-[#D8CFBB] bg-[#F1F4F9]">
          {/* Layer 1: Prediction */}
          <div className="p-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-[#0054A6] font-semibold">
                {tr("common.prediction")}
              </span>
              <Stamp variant="blue">{tr("stamp.computed")}</Stamp>
            </div>
            <p className="font-serif-bn text-base md:text-lg font-bold text-[#1E1B16] leading-snug m-0">
              {renderedPrediction}
            </p>
          </div>

          {/* Layer 2: Assumption */}
          <div className="p-4 space-y-1">
            <div className="text-xs font-mono uppercase tracking-wider text-[#6A6355] font-semibold">
              {tr("common.assumption")}
            </div>
            <p className="text-[15px] text-[#1E1B16] leading-relaxed font-hind m-0">
              {renderedAssumption}
            </p>
          </div>

          {/* Layer 3: Explanation */}
          <div className="p-4 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-[#6A6355] font-semibold">
                {tr("common.explanation")}
              </span>
              <Stamp variant="blue">{tr("stamp.easyExplain")}</Stamp>
            </div>
            <p className="text-[15px] text-[#6A6355] leading-relaxed font-hind m-0">
              {renderedExplanation}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
