"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ForecastChart from "@/components/ForecastChart";
import InsightCard from "@/components/InsightCard";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import TopBar from "@/components/TopBar";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchForecast } from "@/lib/api";
import type { ForecastResponse } from "@/lib/api";
import { formatBDT, formatDigits, formatModelName, formatFeatureName, formatWrittenDate } from "@/lib/i18n";

export default function ForecastPage() {
  const { lang, tr } = useLanguage();
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Window preset: latest history, or pinned over month-end days 28–31
  // (the demo story) via the server-side as_of parameter.
  const [preset, setPreset] = useState<"latest" | "monthend">("latest");

  const load = useCallback(
    (which: "latest" | "monthend" = "latest") => {
      setLoading(true);
      setError(null);
      setPreset(which);
      fetchForecast({
        horizon_days: 14,
        // Driver explanation sentences follow the UI language.
        language: lang,
        // 06-27 → window Jun 28–Jul 11: covers month-end days 28–31.
        ...(which === "monthend" ? { as_of: "2025-06-27" } : {}),
      })
        .then((res) => {
          setData(res);
          setLoading(false);
        })
        .catch(() => {
          setError(tr("error.title"));
          setLoading(false);
        });
    },
    [lang, tr],
  );

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider flex items-center gap-2">
            <span>{tr("forecast.headerTag")}</span>
            <span>•</span>
            <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
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
          <div className="bg-surface/50 border-l-2 border-brickRed border-t border-b border-r border-rule p-5 space-y-3">
            <p className="font-mono text-sm text-brickRed">{error}</p>
            <button type="button" onClick={() => load(preset)} className="primary text-xs">
              {tr("error.retry")}
            </button>
          </div>
        )}

        {loading && !error && (
          <div className="bg-surface/50 border-t border-b border-rule p-8 text-center">
            <p className="font-mono text-sm text-ink-muted animate-pulse">
              {tr("forecast.loading")}
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Window preset buttons */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => load("latest")}
                disabled={loading}
                className={`min-h-[44px] px-3.5 py-1.5 border rounded-[6px] text-xs font-hind transition-colors cursor-pointer ${
                  preset === "latest"
                    ? "border-[#0054A6] text-[#0054A6] font-bold bg-[#FFFFFF]"
                    : "border-[#D8CFBB] text-[#6A6355] bg-[#F1F4F9] hover:border-[#1E1B16]"
                }`}
              >
                {tr("forecast.latestPreset")}
              </button>
              <button
                type="button"
                onClick={() => load("monthend")}
                disabled={loading}
                className={`min-h-[44px] px-3.5 py-1.5 border rounded-[6px] text-xs font-hind transition-colors cursor-pointer ${
                  preset === "monthend"
                    ? "border-[#0054A6] text-[#0054A6] font-bold bg-[#FFFFFF]"
                    : "border-[#D8CFBB] text-[#6A6355] bg-[#F1F4F9] hover:border-[#1E1B16]"
                }`}
              >
                {tr("forecast.monthEndPreset")}
              </button>
            </div>

            {/* Chart Ledger Section (no outer rounded card box) */}
            <div className="bg-surface/50 border-t border-b border-rule p-4 md:p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <h2 className="font-serif-bn font-bold text-xl text-ink m-0">
                  {tr("forecast.title")}
                </h2>
                <div className="flex items-center gap-2">
                  <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
                  <Stamp variant="ink">
                    {data.net_source === "anchor"
                      ? tr("forecast.netSourceAnchor")
                      : data.net_source === "difference"
                        ? tr("forecast.netSourceDifference")
                        : tr("forecast.netSourceModel")}
                  </Stamp>
                </div>
              </div>
              <ForecastChart days={data.days} />
            </div>

            {/* Model Accuracy Ledger Section */}
            <div className="bg-surface/50 border-t border-b border-rule p-5 space-y-2">
              <div className="text-xs font-mono text-ink-muted uppercase">
                {tr("forecast.modelAccuracy")}
              </div>
              {data.metrics ? (
                <div className="text-sm font-hind text-ink flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span>
                    {formatModelName(data.metrics.model_name, lang)}: {tr("metrics.maeLong")}{" "}
                    <strong className="font-serif-bn tabular-nums">{formatBDT(data.metrics.mae_bdt, lang)}</strong>{" "}
                    {tr("common.taka")}
                  </span>
                  <span className="text-rule">·</span>
                  <span>
                    {formatModelName(data.metrics.baseline_name, lang)}: {tr("metrics.maeLong")}{" "}
                    <strong className="font-serif-bn tabular-nums">{formatBDT(data.metrics.baseline_mae_bdt, lang)}</strong>{" "}
                    {tr("common.taka")}
                  </span>
                  <span className="text-rule">·</span>
                  <Stamp variant="ink">
                    +{formatDigits(String(data.metrics.improvement_pct), lang)}% {tr("metrics.improvement")}
                  </Stamp>
                  {data.metrics.net_mae_bdt != null && (
                    <>
                      <span className="text-rule">·</span>
                      <span>
                        {tr("metrics.net")}: MAE{" "}
                        <strong className="font-serif-bn tabular-nums">
                          {formatBDT(data.metrics.net_mae_bdt, lang)}
                        </strong>
                        {data.metrics.net_baseline_name
                          ? ` vs ${formatModelName(data.metrics.net_baseline_name, lang)}`
                          : ""}
                        {data.metrics.net_improvement_pct != null
                          ? ` (+${formatDigits(String(data.metrics.net_improvement_pct), lang)}%)`
                          : ""}
                      </span>
                    </>
                  )}
                </div>
              ) : (
                <p className="text-xs font-mono text-ink-muted">{tr("forecast.noMetrics")}</p>
              )}
            </div>

            {/* Day-by-Day Table (strict column alignment: numbers right-aligned, text left) */}
            <div className="bg-surface/50 border-t border-b border-rule p-4 md:p-6 space-y-4">
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
                    <tr className="border-b border-rule text-xs font-mono text-ink-muted uppercase">
                      <th className="py-2.5 text-left">{tr("forecast.days")}</th>
                      <th className="py-2.5 text-right">{tr("forecast.inflow")}</th>
                      <th className="py-2.5 text-right">{tr("forecast.outflow")}</th>
                      <th className="py-2.5 text-right">{tr("forecast.net")}</th>
                      <th className="py-2.5 text-right">{tr("forecast.balance")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule font-hind">
                    {data.days.map((day) => (
                      <tr
                        key={day.date}
                        className={day.is_pressure_day ? "bg-brickRed/5" : ""}
                      >
                        <td className="py-2 font-mono text-xs text-ink whitespace-nowrap text-left">
                          {formatWrittenDate(day.date, lang)}
                          {day.is_pressure_day && (
                            <span className="ml-2 inline-block">
                              <Stamp variant="warn">{tr("forecast.pressureBadge")}</Stamp>
                            </span>
                          )}
                        </td>
                        <td className="py-2 font-serif-bn font-bold text-[#0054A6] text-right tabular-nums">
                          {formatBDT(day.predicted_inflow_bdt, lang)}
                        </td>
                        <td className="py-2 font-serif-bn font-bold text-brickRed text-right tabular-nums">
                          {formatBDT(day.predicted_outflow_bdt, lang)}
                        </td>
                        <td className="py-2 font-serif-bn text-right tabular-nums">
                          {formatBDT(day.predicted_net_bdt, lang)}
                        </td>
                        <td className="py-2 font-serif-bn font-bold text-ink text-right tabular-nums">
                          {day.predicted_balance_bdt === null
                            ? "—"
                            : formatBDT(day.predicted_balance_bdt, lang)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-rule ledger-double-bottom text-xs font-mono text-ink-muted">
                      <td colSpan={5} className="py-2 text-right">
                        {formatDigits(String(data.days.length), lang)} {lang === "bn" ? "দিনের হিসাব অন্তর্ভুক্ত" : "days analyzed in total"}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Top SHAP Drivers */}
            {data.drivers && data.drivers.length > 0 && (
              <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-5 md:p-6 space-y-3">
                <div className="flex items-center justify-between border-b border-[#D8CFBB] pb-2">
                  <h3 className="font-serif-bn font-bold text-lg text-[#1E1B16] m-0">
                    {tr("forecast.driversTitle")}
                  </h3>
                  <Stamp variant="blue">{tr("forecast.driversBadge")}</Stamp>
                </div>
                <div className="divide-y divide-[#D8CFBB] font-hind text-sm">
                  {data.drivers.map((driver, idx) => (
                    <div key={idx} className="py-2.5 flex items-baseline justify-between gap-2">
                      <div className="space-y-0.5 text-left">
                        <div className="font-bold text-[#1E1B16]">
                          {formatFeatureName(driver.feature, lang)}
                        </div>
                        <div className="text-xs text-[#6A6355]">
                          {driver.detail || (driver.direction === "increases" ? tr("forecast.increasesOutflow") : tr("forecast.decreasesOutflow"))}
                        </div>
                      </div>
                      <span className="tab-leader hidden sm:inline-block" />
                      <div className="font-serif-bn font-bold text-sm whitespace-nowrap text-right tabular-nums">
                        <span className={driver.direction === "increases" ? "text-brickRed" : "text-[#0054A6]"}>
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
            <div className="p-4 bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] flex items-center justify-between">
              <span className="font-hind text-sm text-[#6A6355]">
                {tr("forecast.planSavingsPrompt")}
              </span>
              <Link
                href="/plan"
                className="text-sm font-semibold text-[#0054A6] hover:text-[#003E7E] underline underline-offset-4 decoration-[#0054A6]/60 transition-colors font-hind"
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
