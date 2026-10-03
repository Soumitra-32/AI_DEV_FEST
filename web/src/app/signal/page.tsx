"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import DoNothingToggle from "@/components/DoNothingToggle";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchCreditReadiness } from "@/lib/api";
import type { ConsistencySignalResponse } from "@/lib/api";
import { formatDigits } from "@/lib/i18n";

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
  const bandKey =
    live?.band === "Building"
      ? ("signal.bandBuilding" as const)
      : live?.band === "Strong"
        ? ("signal.bandStrong" as const)
        : ("signal.bandSteady" as const);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider flex items-center gap-2">
            <span>{tr("signal.headerTag")}</span>
            <span>•</span>
            <Stamp variant="muted">{tr("stamp.easyExplain")}</Stamp>
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
        <div className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-rule pb-2">
            <span className="text-xs font-mono text-ink-muted uppercase">
              {tr("signal.band")}
            </span>
            <Stamp variant="muted">{tr("signal.educationalBadge")}</Stamp>
          </div>

          <div className="space-y-3 py-2">
            <div className="flex items-baseline justify-between">
              <span className="font-serif-bn font-bold text-2xl md:text-3xl text-ink">
                {live ? tr(bandKey) : "—"}
              </span>
              <Stamp variant="ink">
                {live
                  ? live.band === "Building"
                    ? tr("signal.bandRatingBuilding")
                    : live.band === "Strong"
                      ? tr("signal.bandRatingStrong")
                      : tr("signal.bandRating")
                  : tr("signal.bandRating")}
              </Stamp>
            </div>

            {/* Stepped Ledger Indicator */}
            {!live && (
              <p className="text-sm font-hind text-ink-muted">
                {tr("signal.unavailable")}
              </p>
            )}
            <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-2">
              {stepKeys.map((key, idx) => (
                <div
                  key={key}
                  className={
                    live && idx === activeStep
                      ? "p-2 border-2 border-primaryGreen bg-surface font-bold text-primaryGreen rounded-none"
                      : "p-2 border border-rule bg-paper/60 text-ink-muted rounded-none"
                  }
                >
                  {tr(key)}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Contributing Factors Ledger */}
        <div className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4">
          <div className="border-b border-rule pb-2 flex items-center justify-between">
            <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
              {tr("signal.factors")}
            </h3>
            <Stamp variant="muted">{tr("signal.logisticRegression")}</Stamp>
          </div>

          <div className="divide-y divide-rule/60 font-hind">
            {live && live.factors.length > 0 ? (
              live.factors.map((f, idx) => (
                <div key={idx} className="py-3 space-y-1">
                  <div className="flex items-baseline justify-between">
                    <span className="font-bold text-sm text-ink text-left">
                      {formatDigits(f.plain_language, lang)}
                    </span>
                    <span className="tab-leader" />
                    <span
                      className={`font-serif-bn text-sm font-bold text-right tabular-nums ${
                        f.direction === "improves" ? "text-primaryGreen" : "text-brickRed"
                      }`}
                    >
                      {f.direction === "improves" ? "+ " : "− "}
                      {f.direction === "improves" ? tr("signal.improves") : tr("signal.weakens")}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-ink-muted leading-relaxed font-hind py-3">
                {tr("signal.unavailable")}
              </p>
            )}
          </div>
        </div>

        {/* Educational Guarantee Banner */}
        <div className="bg-surface/50 border-l-2 border-ink border-t border-r border-b border-rule/60 p-4 text-xs font-mono text-ink-muted space-y-1">
          <div className="font-bold text-ink uppercase">
            {tr("signal.guaranteeTitle")}
          </div>
          <p className="font-hind text-xs leading-relaxed">
            {tr("signal.educationalNote")}
          </p>
        </div>

        <DoNothingToggle
          costBdt={null}
            outcome={
            lang === "bn"
              ? "নিয়মিত মোবাইলে লেনদেন না করলে ধাপ একই থাকবে বা নিচে নামতে পারে।"
              : "Without regular mobile payments, your level will stay or slip down."
          }
        />
      </main>
    </>
  );
}
