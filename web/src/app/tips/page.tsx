"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import InsightCard from "@/components/InsightCard";
import DoNothingToggle from "@/components/DoNothingToggle";
import { useLanguage } from "@/components/LangToggle";
import { fetchExplain } from "@/lib/api";
import type { ExplainResponse } from "@/lib/api";

const CURATED_TIPS = [
  {
    titleBn: "ঘন ঘন ছোট ক্যাশ-আউট কমান",
    titleEn: "Consolidate Frequent Small Cash-Outs",
    descBn:
      "আপনি মাসে ৫ বার গড়ে ৳৩,৫০০ করে ক্যাশ-আউট করেন। বারবার ক্যাশ-আউট না করে একবার বা দুইবারে প্রয়োজনমতো তুললে প্রতি মাসে আনুমানিক ৳৩২০ ফি সাশ্রয় সম্ভব।",
    descEn:
      "You currently cash out ~5 times/month averaging ৳3,500. Consolidating into 1-2 withdrawals or paying merchants directly can save ~৳320 in monthly fees.",
    tagBn: "ফি সাশ্রয়",
    tagEn: "Fee Saving",
    stampKey: "tips.stampRule" as const,
  },
  {
    titleBn: "২৮–৩১ তারিখের জন্য অগ্রিম বাফার রাখুন",
    titleEn: "Maintain Month-End Cash Buffer for Days 28–31",
    descBn:
      "মাসের শেষ সপ্তাহে আপনার দোকানের বিল ও ক্যাশ খরচের চাপ বেশি থাকে। মাসের ১৫ তারিখ থেকেই দৈনিক ৳৫০ আলাদা রাখলে মাস শেষে টানাটানি পড়বে না।",
    descEn:
      "Outflows spike near month-end due to rent and utility schedules. Retaining a small safety buffer earlier prevents emergency borrowing.",
    tagBn: "ক্যাশ-ফ্লো",
    tagEn: "Cash Flow",
    stampKey: "tips.stampForecast" as const,
  },
  {
    titleBn: "সঞ্চয়ের বাস্তবসম্মত লক্ষ্য নির্ধারণ",
    titleEn: "Set a Realistic Surplus-Matched Goal",
    descBn:
      "আপনার বর্তমান মাসিক উদ্বৃত্ত থেকে সেফটি বাফার বাদ দিলে প্রতি মাসে ৳৫,০০০ সঞ্চয় করা সম্ভব। ৬ মাসে ৳৩০,০০০ লক্ষ্য আপনার স্বাভাবিক উপার্জনের সাথে মানানসই।",
    descEn:
      "After retaining a safety buffer, your forecasted monthly surplus supports ৳5,000/month. The ৳30,000 in 6 months goal fits your profile.",
    tagBn: "সঞ্চয়",
    tagEn: "Savings",
    stampKey: "tips.stampPlan" as const,
  },
];

export default function TipsPage() {
  const { lang, tr } = useLanguage();
  const [explainRes, setExplainRes] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchExplain({
      message: lang === "bn" ? "আমার ক্যাশ খরচ ও সঞ্চয়ের পরামর্শ দিন" : "Give me tips for savings and cash flow",
      language: lang,
    })
      .then((res) => {
        if (!cancelled) {
          setExplainRes(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [lang]);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider">
            {tr("tips.headerTag")} • {tr("stamp.easyExplain")}
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("tips.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("tips.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Live Assistant Response if available */}
        {loading && (
          <div className="bg-surface border border-rule rounded-ledger p-6 text-center">
            <p className="font-mono text-sm text-ink-muted animate-pulse">
              {tr("tips.loading")}
            </p>
          </div>
        )}

        {explainRes && (
          <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-rule pb-2">
              <span className="text-xs font-mono uppercase text-primaryGreen font-bold">
                {tr("tips.coachAdvice")}
              </span>
              <span className="border border-ink-muted rounded-stamp px-2 py-0.5 text-[10px] font-mono">
                {explainRes.source}
              </span>
            </div>

            <p className="font-serif-bn text-base md:text-lg font-bold text-ink leading-snug">
              {lang === "bn" ? explainRes.answer_bn : explainRes.answer_en}
            </p>

            {((lang === "bn" ? explainRes.bullets_bn : explainRes.bullets_en) || []).length > 0 && (
              <ul className="space-y-1.5 pt-2 border-t border-rule font-hind text-sm text-ink-muted list-disc list-inside">
                {(lang === "bn" ? explainRes.bullets_bn : explainRes.bullets_en).map((bullet, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {bullet}
                  </li>
                ))}
              </ul>
            )}

            {explainRes.provenance && (
              <InsightCard provenance={explainRes.provenance} />
            )}
          </div>
        )}

        {/* Curated Khata Advice Cards */}
        <div className="space-y-4">
          <div className="border-b border-rule pb-2">
            <h2 className="font-serif-bn font-bold text-xl text-ink m-0">
              {tr("tips.coreGuidance")}
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {CURATED_TIPS.map((tip, idx) => (
              <div
                key={idx}
                className="bg-surface border border-rule rounded-ledger p-5 space-y-2.5"
              >
                <div className="flex items-center justify-between border-b border-rule pb-2">
                  <span className="border border-primaryGreen rounded-stamp px-2 py-0.5 text-[10px] font-mono text-primaryGreen uppercase font-bold">
                    {lang === "bn" ? tip.tagBn : tip.tagEn}
                  </span>
                  <span className="text-xs font-mono text-ink-muted">
                    [{tr(tip.stampKey)}]
                  </span>
                </div>

                <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                  {lang === "bn" ? tip.titleBn : tip.titleEn}
                </h3>

                <p className="text-sm text-ink-muted leading-relaxed font-hind">
                  {lang === "bn" ? tip.descBn : tip.descEn}
                </p>
              </div>
            ))}
          </div>
        </div>

        <DoNothingToggle />
      </main>
    </>
  );
}
