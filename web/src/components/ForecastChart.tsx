"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useLanguage } from "@/components/LangToggle";
import type { DayForecast, PressureReason } from "@/lib/api";
import type { TranslationKey } from "@/lib/i18n";
import { formatBDT } from "@/lib/i18n";

interface ForecastChartProps {
  days: DayForecast[];
}

interface ChartPoint {
  label: string;
  inflow: number;
  outflow: number;
  balance: number | null;
  isPressureDay: boolean;
}

const REASON_KEY: Record<PressureReason, TranslationKey> = {
  negative_net: "forecast.reasonNegativeNet",
  below_buffer: "forecast.reasonBelowBuffer",
  both: "forecast.reasonBoth",
};

/**
 * Money in / money out as areas, the running balance as a line, and every
 * pressure day marked with a large amber dot so the month-end squeeze is the
 * first thing the eye lands on.
 */
export default function ForecastChart({ days }: ForecastChartProps) {
  const { lang, tr } = useLanguage();

  const points: ChartPoint[] = days.map((day) => ({
    label: day.date.slice(8, 10),
    inflow: day.predicted_inflow_bdt,
    outflow: day.predicted_outflow_bdt,
    balance: day.predicted_balance_bdt,
    isPressureDay: day.is_pressure_day,
  }));

  const seriesName = (value: string): string =>
    value === "inflow"
      ? tr("forecast.inflow")
      : value === "outflow"
        ? tr("forecast.outflow")
        : tr("forecast.balance");

  return (
    <div>
      <div style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="inflowFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0a6b5b" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#0a6b5b" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="outflowFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a4231f" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#a4231f" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#d7dee8" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} width={64} />
            <Tooltip
              formatter={(value, name) => [
                formatBDT(Number(value), lang),
                seriesName(String(name)),
              ]}
              labelFormatter={(label) => `${tr("forecast.days")} ${label}`}
            />
            <Legend formatter={(value) => seriesName(String(value))} />
            <Area
              type="monotone"
              dataKey="inflow"
              stroke="#0a6b5b"
              fill="url(#inflowFill)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="outflow"
              stroke="#a4231f"
              fill="url(#outflowFill)"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="balance"
              stroke="#10233a"
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, payload } = props as {
                  cx?: number;
                  cy?: number;
                  payload?: ChartPoint;
                };
                const key = `dot-${cx ?? 0}-${cy ?? 0}`;
                if (typeof cx !== "number" || typeof cy !== "number") return <g key={key} />;
                return payload?.isPressureDay ? (
                  <circle key={key} cx={cx} cy={cy} r={6} fill="#8a4b00" stroke="#ffffff" strokeWidth={2} />
                ) : (
                  <circle key={key} cx={cx} cy={cy} r={2} fill="#10233a" />
                );
              }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {days.some((day) => day.is_pressure_day) ? (
        <p className="muted" style={{ fontSize: "0.9rem" }}>
          {days
            .filter((day) => day.is_pressure_day)
            .map(
              (day) =>
                `${day.date} — ${tr(REASON_KEY[day.pressure_reason ?? "both"])}`,
            )
            .join(" · ")}
        </p>
      ) : null}
    </div>
  );
}
