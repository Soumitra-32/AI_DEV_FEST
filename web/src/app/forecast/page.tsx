"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ForecastChart from "@/components/ForecastChart";
import InsightCard from "@/components/InsightCard";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import TopBar from "@/components/TopBar";
import { useLanguage } from "@/components/LangToggle";
import { fetchForecast } from "@/lib/api";
import type { ForecastResponse, PressureReason } from "@/lib/api";
import type { TranslationKey } from "@/lib/i18n";
import { formatBDT, formatInteger } from "@/lib/i18n";

const REASON_KEY: Record<PressureReason, TranslationKey> = {
  negative_net: "forecast.reasonNegativeNet",
  below_buffer: "forecast.reasonBelowBuffer",
  both: "forecast.reasonBoth",
};

export default function ForecastPage() {
  const { lang, tr } = useLanguage();
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    fetchForecast({ horizon_days: 14 })
      .then(setData)
      .catch(() => setError(tr("error.title")));
  }, [tr]);

  useEffect(load, [load]);

  return (
    <>
      <TopBar />
      <main>
        <h1>{tr("forecast.title")}</h1>
        <p>{tr("forecast.subtitle")}</p>
        <NotADecisionBanner />

        {error ? (
          <div className="card">
            <p>{error}</p>
            <button type="button" onClick={load}>
              {tr("error.retry")}
            </button>
          </div>
        ) : null}

        {!data && !error ? <p>{tr("forecast.loading")}</p> : null}

        {data ? (
          <>
            <InsightCard title={tr("forecast.title")} provenance={data.provenance}>
              <ForecastChart days={data.days} />
              <p>
                <strong>{tr("forecast.pressureTitle")}: </strong>
                {data.pressure_days.length === 0 ? (
                  <span className="badge">{tr("forecast.pressureNone")}</span>
                ) : (
                  data.pressure_days.map((date) => {
                    const day = data.days.find((item) => item.date === date);
                    return (
                      <span key={date} className="badge warn">
                        {date} — {tr(REASON_KEY[day?.pressure_reason ?? "both"])}
                      </span>
                    );
                  })
                )}
              </p>
            </InsightCard>

            <div className="card">
              <h2>{tr("forecast.modelAccuracy")}</h2>
              {data.metrics ? (
                <p>
                  {data.metrics.model_name}: MAE{" "}
                  <strong>{formatBDT(data.metrics.mae_bdt, lang)}</strong> ·{" "}
                  {data.metrics.baseline_name}: MAE{" "}
                  <strong>{formatBDT(data.metrics.baseline_mae_bdt, lang)}</strong> ·{" "}
                  <span className="badge">
                    +{data.metrics.improvement_pct}% better
                  </span>
                </p>
              ) : (
                <p className="muted">{tr("forecast.noMetrics")}</p>
              )}
            </div>

            <div className="card">
              <h2>{tr("forecast.table")}</h2>
              <table>
                <thead>
                  <tr>
                    <th>{tr("forecast.days")}</th>
                    <th>{tr("forecast.inflow")}</th>
                    <th>{tr("forecast.outflow")}</th>
                    <th>{tr("forecast.net")}</th>
                    <th>{tr("forecast.balance")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.days.map((day) => (
                    <tr key={day.date}>
                      <td>
                        {day.date}
                        {day.is_pressure_day ? (
                          <span className="badge warn"> {tr("forecast.pressureTitle")}</span>
                        ) : null}
                      </td>
                      <td>{formatBDT(day.predicted_inflow_bdt, lang)}</td>
                      <td>{formatBDT(day.predicted_outflow_bdt, lang)}</td>
                      <td>{formatBDT(day.predicted_net_bdt, lang)}</td>
                      <td>
                        {day.predicted_balance_bdt === null
                          ? "—"
                          : formatBDT(day.predicted_balance_bdt, lang)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p>
              {tr("nav.plan")}:{" "}
              <Link href="/plan">
                {formatInteger(30000, lang)}
              </Link>
            </p>
          </>
        ) : null}
      </main>
    </>
  );
}

