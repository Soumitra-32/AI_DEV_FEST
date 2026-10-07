"use client";

import { useCallback, useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import SpendingSummary from "@/components/SpendingSummary";
import FeeSavingCard from "@/components/FeeSavingCard";
import AnomalyCard from "@/components/AnomalyCard";
import InsightCard from "@/components/InsightCard";
import DoNothingToggle from "@/components/DoNothingToggle";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchAnomalies, trackEvent } from "@/lib/api";
import type { AnomalyResponse } from "@/lib/api";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { formatBDT } from "@/lib/i18n";

export default function SpendingPage() {
  const { lang, tr } = useLanguage();
  const [data, setData] = useState<AnomalyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchAnomalies({ window_days: 30, limit: 20 })
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setError(tr("error.title"));
        setLoading(false);
      });
  }, [tr]);

  useEffect(() => {
    load();
    trackEvent("anomaly_viewed", { feature: "spending" });
  }, [load]);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        {/* Header */}
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-[#0054A6] uppercase tracking-wider flex items-center gap-2">
            <span>{tr("spending.headerTag")}</span>
            <span>•</span>
            <Stamp variant="blue">{tr("stamp.computed")}</Stamp>
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-[#1E1B16] tracking-tight">
            {tr("spending.title")}
          </h1>
          <p className="text-base text-[#6A6355] leading-relaxed font-hind">
            {tr("spending.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Warning strip */}
        <div className="bg-[#F1F4F9] border-l-[3px] border-[#B0431F] border border-[#D8CFBB] rounded-[6px] p-4 space-y-1">
          <div className="text-xs font-mono uppercase tracking-wider text-[#B0431F] font-bold">
            {tr("spending.warningStripTitle")}
          </div>
          <p className="text-sm font-medium text-[#1E1B16] leading-relaxed font-hind m-0">
            {tr("spending.warningStripText")}
          </p>
        </div>

        {error && (
          <div className="bg-surface/50 border-l-2 border-brickRed border-t border-b border-r border-rule p-5 space-y-3">
            <p className="font-mono text-sm text-brickRed">{error}</p>
            <button type="button" onClick={load} className="text-xs primary">
              {tr("error.retry")}
            </button>
          </div>
        )}

        {loading && !error && (
          <div className="bg-surface/50 border-t border-b border-rule p-8 text-center">
            <p className="font-mono text-sm text-ink-muted animate-pulse">
              {tr("spending.loading")}
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Ledger Overview Rows */}
            <SpendingSummary feeSwitch={data.fee_switch} windowDays={data.window_days} />

            {/* Fee Switch Opportunity */}
            {data.fee_switch && <FeeSavingCard feeSwitch={data.fee_switch} />}

            {/* Anomalies Ruled Section */}
            <div className="space-y-4">
              <div className="flex items-baseline justify-between border-b border-rule pb-2">
                <h2 className="font-serif-bn font-bold text-xl text-ink">
                  {tr("spending.anomalies")}
                </h2>
                <span className="text-xs font-mono text-ink-muted">
                  {data.items.length} {tr("spending.anomalies")}
                </span>
              </div>

              {data.items.length === 0 ? (
                <div className="bg-surface/50 border-t border-b border-rule p-6 text-center text-sm text-ink-muted font-hind">
                  {tr("spending.anomaliesNone")}
                </div>
              ) : (
                <div className="border-t border-b border-rule bg-surface/30 divide-y divide-rule/60">
                  {data.items.map((item) => (
                    <AnomalyCard key={item.transaction_id} item={item} />
                  ))}
                </div>
              )}
            </div>

            {/* 3-Layer Provenance */}
            {data.provenance && (
              <InsightCard provenance={data.provenance} />
            )}

            {/* Feedback Loop */}
            <FeedbackWidget feature="spending" language={lang} />

            {/* Do Nothing Consent */}
            <DoNothingToggle
              costBdt={data.fee_switch?.potential_saving_bdt}
              outcome={
                data.fee_switch
                  ? tr("spending.doNothingOutcome").replace(
                      "{fee}",
                      formatBDT(data.fee_switch.potential_saving_bdt, lang),
                    )
                  : null
              }
            />
          </>
        )}
      </main>
    </>
  );
}
