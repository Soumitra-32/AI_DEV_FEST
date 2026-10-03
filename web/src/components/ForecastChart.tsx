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
import { formatBDT, formatDigits } from "@/lib/i18n";

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
  below_buffer: "forecast.reasonBelowBuffer",
  both: "forecast.reasonBoth",
};

/**
 * Khata Ledger Forecast Chart:
 * Authentic accounting palette: #1F4D36 (Inflow), #B0431F (Outflow), #1E1B16 (Balance).
 * Background #FBF8F1, Rule lines #D8CFBB, pressure days highlighted with diagonal hatch pattern.
 */
export default function ForecastChart({ days }: ForecastChartProps) {
  const { lang, tr } = useLanguage();

  const points: ChartPoint[] = days.map((day) => ({
    label: formatDigits(day.date.slice(8, 10), lang),
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

  const pressureDays = days.filter((day) => day.is_pressure_day);

  return (
    <div className="space-y-4">
      <div style={{ width: "100%", height: 320 }} className="p-2 bg-surface">
        <ResponsiveContainer>
          <AreaChart data={points} margin={{ top: 12, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="inflowFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1F4D36" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#1F4D36" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="outflowFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#B0431F" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#B0431F" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#D8CFBB" />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6A6355" }} />
            <YAxis
              tick={{ fontSize: 12, fill: "#6A6355" }}
              width={64}
              tickFormatter={(val) => formatDigits(String(val), lang)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#FBF8F1",
                border: "1px solid #D8CFBB",
                borderRadius: "4px",
                fontFamily: "Hind Siliguri, sans-serif",
                color: "#1E1B16",
                boxShadow: "none",
              }}
              formatter={(value, name) => [
                formatBDT(Number(value), lang),
                seriesName(String(name)),
              ]}
              labelFormatter={(label) => `${tr("forecast.days")} ${label}`}
            />
            <Legend
              formatter={(value) => (
                <span className="text-xs font-mono text-ink uppercase">
                  {seriesName(String(value))}
                </span>
              )}
            />
            <Area
              type="monotone"
              dataKey="inflow"
              stroke="#1F4D36"
              fill="url(#inflowFill)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="outflow"
              stroke="#B0431F"
              fill="url(#outflowFill)"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="balance"
              stroke="#1E1B16"
              strokeWidth={2.5}
              dot={(props) => {
                const { cx, cy, payload } = props as {
                  cx?: number;
                  cy?: number;
                  payload?: ChartPoint;
                };
                const key = `dot-${cx ?? 0}-${cy ?? 0}`;
                if (typeof cx !== "number" || typeof cy !== "number") return <g key={key} />;
                return payload?.isPressureDay ? (
                  <circle
                    key={key}
                    cx={cx}
                    cy={cy}
                    r={6}
                    fill="#B0431F"
                    stroke="#FBF8F1"
                    strokeWidth={2}
                  />
                ) : (
                  <circle key={key} cx={cx} cy={cy} r={2} fill="#1E1B16" />
                );
              }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Section 8: Diagonal Hatch Strip for Pressure Days */}
      {pressureDays.length > 0 && (
        <div className="bg-surface border border-rule rounded-ledger p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-ink-muted">
            <span>{tr("forecast.pressureTitle")}</span>
            <span className="text-brickRed font-bold">
              {pressureDays.map((d) => formatDigits(d.date.slice(8, 10), lang)).join(" · ")} {lang === "bn" ? "তারিখ" : ""}
            </span>
          </div>

          <div className="h-10 w-full border border-rule diagonal-hatch-pattern flex items-center justify-center">
            <span className="bg-surface px-2.5 py-0.5 border border-rule text-xs font-mono font-bold text-brickRed">
              {pressureDays.map((d) => formatDigits(d.date.slice(8, 10), lang)).join(" · ")} [{tr("forecast.pressureBadge")}]
            </span>
          </div>

          <p className="text-xs text-ink-muted leading-relaxed font-hind">
            {pressureDays
              .map((d) => `${formatDigits(d.date, lang)}: ${tr(REASON_KEY[d.pressure_reason ?? "both"])}`)
              .join(" · ")}
          </p>
        </div>
      )}
    </div>
  );
}
