"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ForecastChart from "@/components/ForecastChart";
import InsightCard from "@/components/InsightCard";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import TopBar from "@/components/TopBar";
import { useLanguage } from "@/components/LangToggle";
import { fetchForecast } from "@/lib/api";
import type { ForecastResponse } from "@/lib/api";
import { formatBDT, formatDigits } from "@/lib/i18n";

export default function ForecastPage() {
  const { lang, tr } = useLanguage();
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchForecast({ horizon_days: 14 })
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
  }, [load]);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider">
            {tr("forecast.headerTag")} • {tr("stamp.computed")}
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("forecast.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("forecast.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {error && (
          <div className="bg-surface border border-brickRed rounded-ledger p-5 space-y-3">
            <p className="font-mono text-sm text-brickRed">{error}</p>
            <button type="button" onClick={load} className="primary text-xs">
              {tr("error.retry")}
            </button>
          </div>
        )}

        {loading && !error && (
          <div className="bg-surface border border-rule rounded-ledger p-8 text-center">
            <p className="font-mono text-sm text-ink-muted animate-pulse">
              {tr("forecast.loading")}
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Chart Container */}
            <div className="bg-surface border border-rule rounded-ledger p-4 md:p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <h2 className="font-serif-bn font-bold text-xl text-ink m-0">
                  {tr("forecast.title")}
                </h2>
                <span className="text-xs font-mono text-ink-muted uppercase">
                  {tr("stamp.computed")}
                </span>
              </div>
              <ForecastChart days={data.days} />
            </div>

            {/* Model Accuracy Card */}
            <div className="bg-surface border border-rule rounded-ledger p-5 space-y-2">
              <div className="text-xs font-mono text-ink-muted uppercase">
                {tr("forecast.modelAccuracy")}
              </div>
              {data.metrics ? (
                <div className="text-sm font-hind text-ink flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span>
                    {data.metrics.model_name}: MAE{" "}
                    <strong className="font-serif-bn">{formatBDT(data.metrics.mae_bdt, lang)}</strong>
                  </span>
                  <span className="text-rule">·</span>
                  <span>
                    {data.metrics.baseline_name}: MAE{" "}
                    <strong className="font-serif-bn">{formatBDT(data.metrics.baseline_mae_bdt, lang)}</strong>
                  </span>
                  <span className="text-rule">·</span>
                  <span className="badge success">
                    +{data.metrics.improvement_pct}% {tr("metrics.improvement")}
                  </span>
                </div>
              ) : (
                <p className="text-xs font-mono text-ink-muted">{tr("forecast.noMetrics")}</p>
              )}
            </div>

            {/* Day-by-Day Table */}
            <div className="bg-surface border border-rule rounded-ledger p-4 md:p-6 space-y-4">
              <div className="flex items-baseline justify-between border-b border-rule pb-2">
                <h2 className="font-serif-bn font-bold text-xl text-ink m-0">
                  {tr("forecast.table")}
                </h2>
                <span className="text-xs font-mono text-ink-muted uppercase">
                  {tr("forecast.tableSub")}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th>{tr("forecast.days")}</th>
                      <th>{tr("forecast.inflow")}</th>
                      <th>{tr("forecast.outflow")}</th>
                      <th>{tr("forecast.net")}</th>
                      <th>{tr("forecast.balance")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule font-hind">
                    {data.days.map((day) => (
                      <tr
                        key={day.date}
                        className={day.is_pressure_day ? "bg-brickRed/5" : ""}
                      >
                        <td className="font-mono text-xs text-ink whitespace-nowrap">
                          {formatDigits(day.date, lang)}
                          {day.is_pressure_day && (
                            <span className="ml-2 border border-brickRed rounded-stamp px-1.5 py-0.5 text-[10px] text-brickRed font-mono">
                              {tr("forecast.pressureBadge")}
                            </span>
                          )}
                        </td>
                        <td className="font-serif-bn font-bold text-primaryGreen">
                          {formatBDT(day.predicted_inflow_bdt, lang)}
                        </td>
                        <td className="font-serif-bn font-bold text-brickRed">
                          {formatBDT(day.predicted_outflow_bdt, lang)}
                        </td>
                        <td className="font-serif-bn">
                          {formatBDT(day.predicted_net_bdt, lang)}
                        </td>
                        <td className="font-serif-bn font-bold text-ink">
                          {day.predicted_balance_bdt === null
                            ? "—"
                            : formatBDT(day.predicted_balance_bdt, lang)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Top SHAP Drivers */}
            {data.drivers && data.drivers.length > 0 && (
              <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-3">
                <div className="flex items-center justify-between border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                    {tr("forecast.driversTitle")}
                  </h3>
                  <span className="border border-ink-muted rounded-stamp px-2 py-0.5 text-[10px] font-mono">
                    SHAP
                  </span>
                </div>
                <div className="divide-y divide-rule font-hind text-sm">
                  {data.drivers.map((driver, idx) => (
                    <div key={idx} className="py-2.5 flex items-baseline justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="font-bold text-ink">
                          {driver.feature}
                        </div>
                        <div className="text-xs text-ink-muted">
                          {driver.detail || (driver.direction === "increases" ? tr("forecast.increasesOutflow") : tr("forecast.decreasesOutflow"))}
                        </div>
                      </div>
                      <span className="dotted-leader hidden sm:inline-block" />
                      <div className="font-serif-bn font-bold text-sm whitespace-nowrap">
                        <span className={driver.direction === "increases" ? "text-brickRed" : "text-primaryGreen"}>
                          {driver.direction === "increases" ? "+" : "-"}
                          {formatBDT(driver.impact_bdt, lang)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3-Layer Provenance */}
            {data.provenance && (
              <InsightCard provenance={data.provenance} />
            )}

            {/* Next Action Link */}
            <div className="p-4 bg-surface border border-rule rounded-ledger flex items-center justify-between">
              <span className="font-hind text-sm text-ink-muted">
                {tr("forecast.planSavingsPrompt")}
              </span>
              <Link
                href="/plan"
                className="text-sm font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors font-hind"
              >
                {tr("nav.plan")} →
              </Link>
            </div>
          </>
        )}
      </main>
    </>
  );
}
