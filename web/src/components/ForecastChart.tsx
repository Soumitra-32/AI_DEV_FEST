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
import { formatBDT, formatDigits, formatWrittenDate } from "@/lib/i18n";

interface ForecastChartProps {
  days?: DayForecast[];
  isLoading?: boolean;
  hasError?: boolean;
  errorMessage?: string;
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
 * Institutional Khata Forecast Chart:
 * Authentic upay accounting palette: #0054A6 (Inflow), #B0431F (Outflow), #1E1B16 (Balance).
 * Zero gradients, flat zero elevation, #D8CFBB rule lines, 6px radius.
 */
export default function ForecastChart({
  days = [],
  isLoading = false,
  hasError = false,
  errorMessage,
}: ForecastChartProps) {
  const { lang, tr } = useLanguage();

  if (isLoading) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label={tr("forecast.loading")}
        className="w-full h-[320px] p-6 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] flex flex-col items-center justify-center space-y-3"
      >
        <div className="w-12 h-12 border-2 border-[#0054A6] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-mono text-[#6A6355] animate-pulse">
          {tr("forecast.loading")}
        </p>
      </div>
    );
  }

  if (hasError) {
    return (
      <div
        role="alert"
        className="w-full h-[320px] p-6 bg-[#FFFFFF] border-l-[3px] border-[#B0431F] border border-[#D8CFBB] rounded-[6px] flex flex-col items-center justify-center space-y-2 text-center"
      >
        <p className="font-mono text-sm text-[#B0431F]">
          {errorMessage || tr("error.title")}
        </p>
      </div>
    );
  }

  if (days.length === 0) {
    return (
      <div
        role="status"
        className="w-full h-[320px] p-6 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] flex flex-col items-center justify-center space-y-2 text-center"
      >
        <p className="font-mono text-sm text-[#6A6355]">
          {lang === "bn" ? "কোনো পূর্বাভাসের তথ্য পাওয়া যায়নি।" : "No forecast data available."}
        </p>
      </div>
    );
  }

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
      <div style={{ width: "100%", height: 320 }} className="p-3 bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px]">
        <ResponsiveContainer>
          <AreaChart data={points} margin={{ top: 12, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#D8CFBB" />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6A6355" }} />
            <YAxis
              tick={{ fontSize: 12, fill: "#6A6355" }}
              width={64}
              tickFormatter={(val) => formatDigits(String(val), lang)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #D8CFBB",
                borderRadius: "6px",
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
                <span className="text-xs font-mono text-[#1E1B16] uppercase">
                  {seriesName(String(value))}
                </span>
              )}
            />
            {/* Flat fills, NO gradients */}
            <Area
              type="monotone"
              dataKey="inflow"
              stroke="#0054A6"
              fill="#0054A6"
              fillOpacity={0.1}
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="outflow"
              stroke="#B0431F"
              fill="#B0431F"
              fillOpacity={0.1}
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
                    stroke="#FFFFFF"
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

      {/* Pressure Days Strip: 3px brick-red left border, 45° red hatch pattern, 6px radius */}
      {pressureDays.length > 0 && (
        <div className="bg-[#F1F4F9] border-l-[3px] border-[#B0431F] border border-[#D8CFBB] rounded-[6px] p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-[#6A6355]">
            <span className="font-bold">{tr("forecast.pressureTitle")}</span>
            <span className="text-[#B0431F] font-bold">
              {pressureDays.map((d) => formatDigits(d.date.slice(8, 10), lang)).join(" · ")} {lang === "bn" ? "তারিখ" : ""}
            </span>
          </div>

          <div className="h-10 w-full border border-[#D8CFBB] rounded-[6px] diagonal-hatch-pattern flex items-center justify-center">
            <span className="bg-[#FFFFFF] px-3 py-1 border border-[#D8CFBB] rounded-[6px] text-xs font-mono font-bold text-[#B0431F]">
              {pressureDays.map((d) => formatDigits(d.date.slice(8, 10), lang)).join(" · ")} [{tr("forecast.pressureBadge")}]
            </span>
          </div>

          <p className="text-xs text-[#6A6355] leading-relaxed font-hind m-0">
            {pressureDays
              .map((d) => `${formatWrittenDate(d.date, lang)}: ${tr(REASON_KEY[d.pressure_reason ?? "both"])}`)
              .join(" · ")}
          </p>
        </div>
      )}
    </div>
  );
}
