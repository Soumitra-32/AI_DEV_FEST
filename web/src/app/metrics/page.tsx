"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchMetrics } from "@/lib/api";
import type { MetricsResponse, ModelMetric, FairnessRow } from "@/lib/api";
import { formatBDT, formatDigits, formatInteger, formatModelName, formatPersona, formatDistrict } from "@/lib/i18n";

export default function MetricsPage() {
  const { lang, tr } = useLanguage();
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchMetrics()
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Backend metric ids (mae_bdt, auc, precision…) never print raw.
  const formatFairnessMetric = (metric: string) => {
    const m = metric.toLowerCase();
    if (m.includes("mae")) return tr("metrics.maeLong");
    if (m.includes("rmse")) return tr("metrics.rmse");
    if (m.includes("auc")) return tr("metrics.auc");
    if (m.includes("precision")) return tr("metrics.precision");
    if (m.includes("recall")) return tr("metrics.recall");
    if (m === "f1") return tr("metrics.f1");
    return metric;
  };

  // Counts are said as "25 out of 100", never a bare 25.05% or 0.8375.
  const formatOutOf100 = (val: number) => {
    const n = val > 1 ? Math.round(val) : Math.round(val * 100);
    return lang === "bn"
      ? `${tr("metrics.outOf100")} ${formatDigits(String(n), lang)}টি`
      : `${n} ${tr("metrics.outOf100")}`;
  };

  const formatMetricVal = (metric: string, val: number) => {    if (metric.includes("bdt")) {
      return formatBDT(val, lang);
    }
    if (
      metric.includes("pct") ||
      metric === "precision" ||
      metric === "recall" ||
      metric === "auc" ||
      metric === "f1"
    ) {
      return formatOutOf100(val);
    }
    return formatDigits(val.toFixed(2), lang);
  };

  const getFlowLabel = (idx: number) => {
    if (idx === 0 || idx === 1) return tr("metrics.inflow");
    if (idx === 2 || idx === 3) return tr("metrics.outflow");
    return tr("metrics.net");
  };

  const maeForecastRows = (data?.forecast || []).filter((f) => f.metric === "mae_bdt");

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider flex items-center gap-2">
            <span>{tr("metrics.headerTag")}</span>
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("metrics.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("metrics.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {loading && (
          <div className="bg-surface/50 border-t border-b border-rule p-8 text-center">
            <p className="font-mono text-sm text-ink-muted animate-pulse">
              {tr("metrics.loading")}
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-surface/50 border-l-2 border-brickRed border-t border-b border-r border-rule p-5 space-y-2">
            <p className="font-mono text-sm text-brickRed">{tr("error.title")}</p>
          </div>
        )}

        {data && !loading && (
          <div className="space-y-8">
            {/* ------------------------------------------------------------- */}
            {/* EVIDENCE LAYER 1: Model Evaluation & Offline Accuracy          */}
            {/* ------------------------------------------------------------- */}
            <section className="space-y-4">
              <div className="border-b-2 border-[#0054A6] pb-2 flex items-baseline justify-between">
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-[#0054A6] font-bold">
                    {lang === "bn" ? "প্রমাণ স্তর ১ • অফলাইন মূল্যায়ন" : "Evidence Layer 1 • Offline Benchmarks"}
                  </div>
                  <h2 className="font-serif-bn font-bold text-2xl text-[#1E1B16] m-0">
                    {lang === "bn" ? "মডেল মূল্যায়ন ও অ্যালগরিদমিক নির্ভুলতা" : "Model Evaluation & Offline Accuracy"}
                  </h2>
                </div>
                <Stamp variant="blue">{lang === "bn" ? "মেশিন লার্নিং" : "ML Models"}</Stamp>
              </div>

              {/* Forecast Model Evaluation */}
              <div className="bg-surface-block/40 border border-rule rounded-[6px] p-5 md:p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-xl text-ink m-0">
                    {tr("metrics.forecast")}
                  </h3>
                  <Stamp variant="blue">{tr("metrics.forecastBadge")}</Stamp>
                </div>

                <div className="space-y-4 font-hind text-sm">
                  {maeForecastRows.map((row, idx) => (
                    <div key={idx} className="border-b border-rule/60 pb-3 space-y-1.5 last:border-b-0 last:pb-0">
                      <div className="flex items-baseline justify-between text-xs font-mono text-ink-muted uppercase">
                        <span>{getFlowLabel(idx * 2)}</span>
                        <span>{row.baseline_name ? `vs ${formatModelName(row.baseline_name, lang)}` : ""}</span>
                      </div>
                      <div className="flex items-baseline justify-between">
                        <span className="text-ink-muted">
                          {formatModelName(row.model_name, lang)}
                        </span>
                        <span className="tab-leader" />
                        <strong className="font-serif-bn text-ink text-base text-right tabular-nums">
                          {tr("metrics.maeLong")} {formatBDT(row.value, lang)} {tr("common.taka")}
                        </strong>
                      </div>

                      {row.baseline_value !== null && row.baseline_value !== undefined && (
                        <div className="flex items-baseline justify-between">
                          <span className="text-ink-muted">
                            {formatModelName(row.baseline_name, lang)}
                          </span>
                          <span className="tab-leader" />
                          <strong className="font-serif-bn text-ink-muted text-base text-right tabular-nums">
                            {tr("metrics.maeLong")} {formatBDT(row.baseline_value, lang)} {tr("common.taka")}
                          </strong>
                        </div>
                      )}

                      {row.improvement_pct !== null && row.improvement_pct !== undefined && (
                        <div className="pt-1 flex items-baseline justify-between">
                          <span className="font-bold text-ink font-serif-bn">
                            {tr("metrics.improvement")}
                          </span>
                          <span className="tab-leader" />
                          <span
                            className={`font-serif-bn font-bold text-lg text-right tabular-nums ${
                              row.improvement_pct >= 0 ? "text-[#0054A6]" : "text-brickRed"
                            }`}
                          >
                            {row.improvement_pct >= 0 ? "+" : ""}
                            {formatDigits(row.improvement_pct.toFixed(1), lang)}%
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Anomaly Detection Model Specs */}
              <div className="bg-surface-block/40 border border-rule rounded-[6px] p-5 md:p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                    {tr("metrics.anomaly")}
                  </h3>
                  <Stamp variant="muted">{tr("metrics.anomalyBadge")}</Stamp>
                </div>
                <p className="text-xs text-ink-muted font-hind leading-relaxed">
                  {tr("metrics.anomalyDesc")}
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 font-mono text-xs">
                  {data.anomaly.map((anom, idx) => (
                    <div
                      key={idx}
                      className="border border-rule rounded-[6px] p-2.5 bg-surface-white space-y-1"
                    >
                      <div className="text-[10px] text-ink-muted uppercase">
                        {anom.metric === "precision"
                          ? tr("metrics.precision")
                          : anom.metric === "recall"
                          ? tr("metrics.recall")
                          : anom.metric === "f1"
                          ? tr("metrics.f1")
                          : anom.metric === "auc"
                          ? tr("metrics.auc")
                          : anom.metric}
                      </div>
                      <div className="font-serif-bn font-bold text-base text-ink text-right tabular-nums">
                        {formatMetricVal(anom.metric, anom.value)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Consistency Model Specs */}
              <div className="bg-surface-block/40 border border-rule rounded-[6px] p-5 md:p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                    {tr("metrics.signal")}
                  </h3>
                  <Stamp variant="muted">{tr("signal.logisticRegression")}</Stamp>
                </div>

                {data.signal.filter((s) => s.metric === "auc").map((sig, idx) => (
                  <div key={idx} className="space-y-2 font-hind text-sm">
                    <div className="flex items-baseline justify-between">
                      <span className="text-ink-muted">
                        {tr("metrics.auc")} ({formatModelName(sig.model_name, lang)})
                      </span>
                      <span className="tab-leader" />
                      <strong className="font-serif-bn text-ink text-base text-right tabular-nums">
                        {formatDigits(sig.value.toFixed(4), lang)}
                      </strong>
                    </div>
                    {sig.baseline_value !== null && sig.baseline_value !== undefined && (
                      <div className="flex items-baseline justify-between">
                        <span className="text-ink-muted">
                          {tr("metrics.baseline")} ({formatModelName(sig.baseline_name, lang)})
                        </span>
                        <span className="tab-leader" />
                        <strong className="font-serif-bn text-ink-muted text-base text-right tabular-nums">
                          {formatDigits(sig.baseline_value.toFixed(4), lang)}
                        </strong>
                      </div>
                    )}
                    {sig.improvement_pct !== null && sig.improvement_pct !== undefined && (
                      <div className="pt-1 flex items-baseline justify-between">
                        <span className="font-bold text-ink font-serif-bn">
                          {tr("metrics.improvement")}
                        </span>
                        <span className="tab-leader" />
                        <span className="font-serif-bn font-bold text-lg text-[#0054A6] text-right tabular-nums">
                          +{formatDigits(sig.improvement_pct.toFixed(1), lang)}%
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Fairness Audit Ledger Table */}
              <div className="bg-surface-block/40 border border-rule rounded-[6px] p-4 md:p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-xl text-ink m-0">
                    {tr("metrics.fairnessTable")}
                  </h3>
                  <span className="text-xs font-mono text-ink-muted">
                    {formatDigits(String(data.fairness.length), lang)} {lang === "bn" ? "টি অডিট রো" : "audit rows"}
                  </span>
                </div>
                <p className="text-xs text-ink-muted font-hind leading-relaxed">
                  {tr("metrics.fairnessDesc")}
                </p>

                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-rule text-[11px] font-mono text-ink-muted uppercase">
                        <th className="py-2 pr-3 text-left">{tr("metrics.dimension")}</th>
                        <th className="py-2 pr-3 text-left">{tr("metrics.group")}</th>
                        <th className="py-2 pr-3 text-left">{tr("metrics.metric")}</th>
                        <th className="py-2 pr-3 text-right">{tr("metrics.value")}</th>
                        <th className="py-2 text-right">{tr("metrics.gap")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-rule/60 font-hind text-xs">
                      {data.fairness.slice(0, 15).map((row, idx) => (
                        <tr key={idx} className="hover:bg-surface-block/50">
                          <td className="py-2 pr-3 font-mono text-ink-muted capitalize text-left">
                            {row.dimension === "persona"
                              ? (lang === "bn" ? "পেশা" : "Persona")
                              : row.dimension === "district"
                              ? (lang === "bn" ? "জেলা" : "District")
                              : (lang === "bn" ? "আয়ের স্তর" : "Income")}
                          </td>
                          <td className="py-2 pr-3 font-bold text-ink capitalize text-left">
                            {row.dimension === "persona"
                              ? formatPersona(row.group, lang)
                              : row.dimension === "district"
                              ? formatDistrict(row.group, lang)
                              : formatDigits(row.group, lang)}
                          </td>
                          <td className="py-2 pr-3 font-mono text-ink-muted text-[11px] text-left">
                            {formatFairnessMetric(row.metric)}
                          </td>
                          <td className="py-2 pr-3 font-serif-bn font-bold text-ink text-right tabular-nums">
                            {formatMetricVal(row.metric, row.value)}
                          </td>
                          <td className="py-2 text-right font-serif-bn font-bold tabular-nums">
                            <span
                              className={
                                row.relative_gap_pct >= 0 ? "text-[#0054A6]" : "text-brickRed"
                              }
                            >
                              {row.relative_gap_pct >= 0 ? "+" : ""}
                              {formatDigits(row.relative_gap_pct.toFixed(2), lang)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {data.fairness.length > 15 && (
                  <div className="text-center pt-2 border-t border-rule text-xs font-mono text-ink-muted">
                    {lang === "bn"
                      ? `... আরও ${formatDigits(String(data.fairness.length - 15), lang)} টি পরিমাপ অন্তর্ভুক্ত`
                      : `... and ${data.fairness.length - 15} more audited slices`}
                  </div>
                )}
                <div className="border-t border-rule/60 pt-3">
                  <p className="text-xs text-ink-muted leading-relaxed font-hind italic">
                    {tr("metrics.institutionalCaveat")}
                  </p>
                </div>
              </div>
            </section>

            {/* ------------------------------------------------------------- */}
            {/* EVIDENCE LAYER 2: Product Interaction Data & Customer Impact    */}
            {/* ------------------------------------------------------------- */}
            <section className="space-y-4">
              <div className="border-b-2 border-[#0054A6] pb-2 flex items-baseline justify-between">
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-[#0054A6] font-bold">
                    {lang === "bn" ? "প্রমাণ স্তর ২ • লাইভ টেলিমেট্রি" : "Evidence Layer 2 • Live Telemetry"}
                  </div>
                  <h2 className="font-serif-bn font-bold text-2xl text-[#1E1B16] m-0">
                    {lang === "bn" ? "গ্রাহক ব্যবহারের বাস্তব প্রভাব ও পরিমাপ" : "Product Interaction Data & Customer Impact"}
                  </h2>
                </div>
                <Stamp variant="blue">{lang === "bn" ? "বাস্তব ব্যবহার" : "Product Telemetry"}</Stamp>
              </div>

              <div className="bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] p-5 md:p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#D8CFBB] pb-3">
                  <div>
                    <h3 className="font-serif-bn font-bold text-lg text-[#1E1B16] m-0">
                      {lang === "bn" ? "প্রকৃত ব্যবহারের খতিয়ান" : "Interaction Ledger"}
                    </h3>
                    <p className="text-xs text-[#6A6355] font-hind m-0">
                      {lang === "bn"
                        ? "অথেনটিকেটেড ব্যবহারকারীর সরাসরি কার্যকলাপ থেকে পরিমাপকৃত • কোনো কাল্পনিক পরিসংখ্যান নেই"
                        : "Calculated strictly from authenticated user interaction events — Zero fabrication"}
                    </p>
                  </div>
                  <span className="text-[11px] font-mono text-[#0054A6] px-2 py-1 bg-[#F1F4F9] rounded border border-[#D8CFBB]">
                    {data.customer_impact?.has_data
                      ? (lang === "bn" ? "ডেটা উপলব্ধ" : "Data Available")
                      : (lang === "bn" ? "কোনো ডেটা নেই" : "No Data")}
                  </span>
                </div>

                {data.customer_impact && data.customer_impact.has_data ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-1">
                    {/* Feedback Count & Helpful Rate */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "মতামত ও সহায়কতার হার" : "Feedback & Helpful Rate"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {data.customer_impact.helpful_feedback_rate_pct !== null
                          ? `${formatDigits(data.customer_impact.helpful_feedback_rate_pct.toFixed(1), lang)}%`
                          : "—"}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {formatInteger(data.customer_impact.helpful_responses, lang)}/
                        {formatInteger(data.customer_impact.total_feedback, lang)}{" "}
                        {lang === "bn" ? "সহায়ক" : "helpful"}
                      </div>
                    </div>

                    {/* Understanding Rate */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "পরামর্শ বোঝার হার" : "Understanding Rate"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {data.customer_impact.understanding_rate_pct !== null
                          ? `${formatDigits(data.customer_impact.understanding_rate_pct.toFixed(1), lang)}%`
                          : "—"}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {formatInteger(data.customer_impact.understood_count, lang)}/
                        {formatInteger(data.customer_impact.understanding_responses, lang)}{" "}
                        {lang === "bn" ? "বুঝেছেন" : "understood"}
                      </div>
                    </div>

                    {/* Recommendations Shown & Accepted */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "পরামর্শ গ্রহণ" : "Recommendations Accepted"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {formatInteger(data.customer_impact.recommendations_accepted, lang)}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "প্রদর্শিত:" : "Shown:"}{" "}
                        {formatInteger(data.customer_impact.recommendations_shown, lang)}{" "}
                        ({data.customer_impact.recommendation_acceptance_rate_pct !== null
                          ? `${formatDigits(data.customer_impact.recommendation_acceptance_rate_pct.toFixed(1), lang)}%`
                          : "—"})
                      </div>
                    </div>

                    {/* Actions Completed & Completion Rate */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "পদক্ষেপ সম্পন্ন" : "Actions Completed"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#0054A6] tabular-nums">
                        {formatInteger(data.customer_impact.actions_completed, lang)}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "সম্পন্নের হার:" : "Completion:"}{" "}
                        {data.customer_impact.action_completion_rate_pct !== null
                          ? `${formatDigits(data.customer_impact.action_completion_rate_pct.toFixed(1), lang)}%`
                          : "—"}
                      </div>
                    </div>

                    {/* Savings Plans Created */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "সঞ্চয় পরিকল্পনা তৈরি" : "Savings Plans Created"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {formatInteger(data.customer_impact.savings_plans_created, lang)}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {formatInteger(data.customer_impact.savings_plans_viewed, lang)}{" "}
                        {lang === "bn" ? "বার দর্শন" : "views"}
                      </div>
                    </div>

                    {/* Forecast Views */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "পূর্বাভাস দর্শন" : "Forecast Views"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {formatInteger(data.customer_impact.forecast_views, lang)}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "১৪ দিনের ক্যাশ-ফ্লো" : "14-day cash flow"}
                      </div>
                    </div>

                    {/* Anomaly Views */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "ব্যয় অসঙ্গতি দর্শন" : "Anomaly Views"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {formatInteger(data.customer_impact.anomaly_views, lang)}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "অস্বাভাবিক লেনদেন চেক" : "High-fee & flagged items"}
                      </div>
                    </div>

                    {/* Copilot Usage */}
                    <div className="border border-[#D8CFBB] rounded-[6px] p-3.5 bg-[#F1F4F9] space-y-1">
                      <div className="text-[11px] font-mono uppercase text-[#6A6355]">
                        {lang === "bn" ? "কপাইলট ব্যবহার" : "Copilot Interactions"}
                      </div>
                      <div className="font-serif-bn font-bold text-xl text-[#1E1B16] tabular-nums">
                        {formatInteger(data.customer_impact.copilot_usage, lang)}
                      </div>
                      <div className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "আর্থিক প্রশ্ন ও লক্ষ্য পার্স" : "Goal queries resolved"}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Zero-Data Empty State */
                  <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-8 text-center space-y-2.5">
                    <div className="w-10 h-10 mx-auto rounded-full bg-[#FFFFFF] border border-[#D8CFBB] flex items-center justify-center text-[#6A6355]">
                      <span className="font-mono text-sm">Ø</span>
                    </div>
                    <h4 className="font-serif-bn font-bold text-lg text-[#1E1B16] m-0">
                      {lang === "bn" ? "কোনো ইন্টারঅ্যাকশন ডেটা এখনো সংগৃহীত হয়নি" : "No interaction data collected yet"}
                    </h4>
                    <p className="text-xs text-[#6A6355] font-hind max-w-md mx-auto leading-relaxed">
                      {lang === "bn"
                        ? "বাস্তব ব্যবহারকারীরা যখন বিভিন্ন পরামর্শ গ্রহণ করবেন, সম্পন্ন করবেন এবং মতামত দেবেন—তখন এই মেট্রিকগুলো স্বয়ংক্রিয়ভাবে লাইভ আপডেট হবে।"
                        : "Customer impact metrics update in real time as authenticated users interact with recommendations and submit feedback."}
                    </p>
                    <div className="pt-1">
                      <span className="text-[11px] font-mono text-[#0054A6] uppercase tracking-wider">
                        {lang === "bn" ? "• শূন্য পরিসংখ্যান নীতি (Zero Fabrication Policy)" : "• Zero Fabrication Enforced"}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* ------------------------------------------------------------- */}
            {/* EVIDENCE LAYER 3: Simulation & Policy Context                 */}
            {/* ------------------------------------------------------------- */}
            <section className="space-y-4">
              <div className="border-b-2 border-[#0054A6] pb-2 flex items-baseline justify-between">
                <div>
                  <div className="text-xs font-mono uppercase tracking-wider text-[#0054A6] font-bold">
                    {lang === "bn" ? "প্রমাণ স্তর ৩ • নীতিগত সিমুলেশন" : "Evidence Layer 3 • Policy Simulation"}
                  </div>
                  <h2 className="font-serif-bn font-bold text-2xl text-[#1E1B16] m-0">
                    {lang === "bn" ? "সিমুলেশন ও নীতিগত প্রেক্ষাপট (কাউন্টারফ্যাকচুয়াল)" : "Simulation & Policy Context (Counterfactual)"}
                  </h2>
                </div>
                <Stamp variant="muted">{lang === "bn" ? "সিমুলেশন" : "Simulation"}</Stamp>
              </div>

              {data.impact && data.impact.length > 0 && (
                <div className="bg-surface-block/40 border border-rule rounded-[6px] p-5 md:p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-rule pb-2">
                    <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                      {tr("metrics.impactTitle")}
                    </h3>
                    <Stamp variant="muted">{lang === "bn" ? "ফলাফল" : "Outcome"}</Stamp>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                    {data.impact
                      .filter((imp) => imp.metric === "avg_potential_fee_saving_bdt_per_month" || imp.metric === "observed_shortfall_days_per_month" || imp.metric === "requests")
                      .map((imp, idx) => (
                        <div key={idx} className="border border-rule rounded-[6px] p-3 bg-surface-white space-y-1">
                          <div className="text-[10px] text-ink-muted uppercase">
                            {imp.metric === "avg_potential_fee_saving_bdt_per_month"
                              ? (lang === "bn" ? "মাসে বাঁচতে পারে এমন ফি" : "Fee you could save a month")
                              : imp.metric === "observed_shortfall_days_per_month"
                              ? (lang === "bn" ? "মাসে টানের দিন" : "Tight days a month")
                              : (lang === "bn" ? "উত্তর দেওয়া প্রশ্ন" : "Questions answered")}
                          </div>
                          <div className="font-serif-bn font-bold text-base text-ink text-right tabular-nums">
                            {imp.metric.includes("bdt")
                              ? <>{formatBDT(imp.value, lang)} {tr("common.taka")}</>
                              : imp.metric === "observed_shortfall_days_per_month"
                              ? <>{formatDigits(imp.value.toFixed(1), lang)} {tr("spending.daysUnit")}</>
                              : <>{formatInteger(Math.round(imp.value), lang)} {tr("metrics.requestsUnit")}</>}
                          </div>
                        </div>
                      ))}
                  </div>

                  {/* Macroeconomic Context Line (1 Oct 2026 Bangladesh Bank Reform) */}
                  <div className="border-t border-rule/60 pt-3">
                    <p className="text-xs text-ink-muted leading-relaxed font-hind">
                      {tr("metrics.macroContext")}
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Notes & Caveats */}
            {data.notes && data.notes.length > 0 && (
              <div className="border-t border-rule pt-4 space-y-2">
                <h4 className="text-xs font-mono text-ink-muted uppercase tracking-wider">
                  {tr("metrics.notesTitle")}
                </h4>
                <ul className="space-y-1 text-xs text-ink-muted font-hind list-disc list-inside leading-relaxed">
                  {data.notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </>
  );
}
