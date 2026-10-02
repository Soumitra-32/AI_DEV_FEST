"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import DoNothingToggle from "@/components/DoNothingToggle";
import { useLanguage } from "@/components/LangToggle";
import { fetchCreditReadiness } from "@/lib/api";
import type { ConsistencySignalResponse } from "@/lib/api";

const BAND_INDEX: Record<string, number> = {
  Building: 0,
  Steady: 1,
  Strong: 2,
};

export default function SignalPage() {
  const { lang, tr } = useLanguage();
  // Live band from POST /signal; null (offline/error) keeps the static
  // content below, so the page never breaks without the backend.
  const [live, setLive] = useState<ConsistencySignalResponse | null>(null);

  useEffect(() => {
    fetchCreditReadiness(lang)
      .then(setLive)
      .catch(() => setLive(null));
  }, [lang]);

  const activeStep = live ? (BAND_INDEX[live.band] ?? 1) : 1;
  const stepKeys = ["signal.step1", "signal.step2", "signal.step3"] as const;

  const factors = [
    {
      featureBn: "ব্যালেন্স স্থিতিশীলতা",
      featureEn: "Balance Stability",
      direction: "improves",
      weight: 0.35,
      descBn: "আপনার ওয়ালেটের ব্যালেন্স নিয়মিত ইতিবাচক থাকে এবং হঠাৎ শূন্য হয় না।",
      descEn: "Wallet balance remains consistently positive without abrupt zero drops.",
    },
    {
      featureBn: "নিয়মিত সঞ্চয়ের উদ্বৃত্ত",
      featureEn: "Savings Surplus Consistency",
      direction: "improves",
      weight: 0.28,
      descBn: "মাসিক খরচের পর একটি স্থিতিশীল উদ্বৃত্ত ধরে রাখা সম্ভব হচ্ছে।",
      descEn: "Forecasted monthly surplus consistently supports goal progression.",
    },
    {
      featureBn: "ঘন ঘন ক্যাশ-আউট",
      featureEn: "Cash-Out Frequency",
      direction: "weakens",
      weight: 0.22,
      descBn: "বারবার ছোট অংকের ক্যাশ-আউট ফি বাড়ায় ও নগদ স্থিতিশীলতা কমায়।",
      descEn: "Frequent small withdrawals increase fee overhead and diminish liquidity.",
    },
  ];

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider">
            {tr("signal.headerTag")} • {tr("stamp.easyExplain")}
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("signal.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("signal.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Consistency Band Visualization */}
        <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-rule pb-2">
            <span className="text-xs font-mono text-ink-muted uppercase">
              {tr("signal.band")}
            </span>
            <span className="border border-ink-muted rounded-stamp px-2 py-0.5 text-[10px] font-mono">
              {tr("signal.educationalBadge")}
            </span>
          </div>

          <div className="space-y-3 py-2">
            <div className="flex items-baseline justify-between">
              <span className="font-serif-bn font-bold text-2xl md:text-3xl text-ink">
                {live ? live.band : tr("signal.bandSteady")}
              </span>
              <span className="badge success">
                {tr("signal.bandRating")}
              </span>
            </div>

            {/* Stepped Ledger Indicator */}
            <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-2">
              {stepKeys.map((key, idx) => (
                <div
                  key={key}
                  className={
                    idx === activeStep
                      ? "p-2 border-2 border-primaryGreen bg-surface rounded-stamp font-bold text-primaryGreen"
                      : "p-2 border border-rule bg-paper/60 rounded-stamp text-ink-muted"
                  }
                >
                  {tr(key)}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Contributing Factors Ledger */}
        <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4">
          <div className="border-b border-rule pb-2">
            <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
              {tr("signal.factors")}
            </h3>
          </div>

          <div className="divide-y divide-rule font-hind">
            {(live && live.factors.length > 0
              ? live.factors.map((f) => ({
                  title: f.feature,
                  desc: f.plain_language,
                  direction: f.direction,
                  weight: f.magnitude,
                }))
              : factors.map((f) => ({
                  title: lang === "bn" ? f.featureBn : f.featureEn,
                  desc: lang === "bn" ? f.descBn : f.descEn,
                  direction: f.direction,
                  weight: f.weight,
                }))
            ).map((f, idx) => (
              <div key={idx} className="py-3 space-y-1">
                <div className="flex items-baseline justify-between">
                  <span className="font-bold text-sm text-ink">
                    {f.title}
                  </span>
                  <span className="dotted-leader" />
                  <span
                    className={`font-mono text-xs font-bold ${
                      f.direction === "improves" ? "text-primaryGreen" : "text-brickRed"
                    }`}
                  >
                    {f.direction === "improves" ? "+ " : "- "}
                    {f.weight}
                  </span>
                </div>
                <p className="text-xs text-ink-muted leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Educational Guarantee Banner */}
        <div className="bg-surface border border-rule rounded-ledger p-4 text-xs font-mono text-ink-muted space-y-1">
          <div className="font-bold text-ink uppercase">
            {tr("signal.guaranteeTitle")}
          </div>
          <p className="font-hind text-xs leading-relaxed">
            {tr("signal.educationalNote")}
          </p>
        </div>

        <DoNothingToggle />
      </main>
    </>
  );
}
