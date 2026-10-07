import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ForecastChart from "@/components/ForecastChart";
import { LanguageProvider } from "@/components/LangToggle";
import type { DayForecast } from "@/lib/api";

const mockDays: DayForecast[] = [
  {
    date: "2026-10-27",
    predicted_inflow_bdt: 12000,
    predicted_outflow_bdt: 4500,
    predicted_net_bdt: 7500,
    predicted_balance_bdt: 15500,
    is_pressure_day: false,
    pressure_reason: null,
  },
  {
    date: "2026-10-28",
    predicted_inflow_bdt: 2000,
    predicted_outflow_bdt: 18000,
    predicted_net_bdt: -16000,
    predicted_balance_bdt: -500,
    is_pressure_day: true,
    pressure_reason: "below_buffer",
  },
];

describe("ForecastChart", () => {
  it("renders with data and pressure strip", () => {
    const { container } = render(
      <LanguageProvider>
        <ForecastChart days={mockDays} />
      </LanguageProvider>,
    );

    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
    // Pressure days strip should be rendered
    expect(screen.getByText(/টানের দিনসমূহ|Tight days/)).toBeInTheDocument();
  });

  it("shows loading skeleton when isLoading is true", () => {
    render(
      <LanguageProvider>
        <ForecastChart days={[]} isLoading={true} />
      </LanguageProvider>,
    );

    const loader = screen.getByRole("status");
    expect(loader).toBeInTheDocument();
    expect(loader).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText(/হিসাব করা হচ্ছে|Calculating/)).toBeInTheDocument();
  });

  it("shows error state when hasError is true", () => {
    render(
      <LanguageProvider>
        <ForecastChart days={[]} hasError={true} errorMessage="Custom network error" />
      </LanguageProvider>,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(screen.getByText("Custom network error")).toBeInTheDocument();
  });

  it("shows empty state when days array is empty", () => {
    render(
      <LanguageProvider>
        <ForecastChart days={[]} />
      </LanguageProvider>,
    );

    const status = screen.getByRole("status");
    expect(status).toBeInTheDocument();
    expect(
      screen.getByText(/কোনো পূর্বাভাসের তথ্য পাওয়া যায়নি|No forecast data available/),
    ).toBeInTheDocument();
  });

  it("handles single-point series without error", () => {
    const singleDay: DayForecast[] = [
      {
        date: "2026-10-27",
        predicted_inflow_bdt: 5000,
        predicted_outflow_bdt: 2000,
        predicted_net_bdt: 3000,
        predicted_balance_bdt: 8000,
        is_pressure_day: false,
        pressure_reason: null,
      },
    ];

    const { container } = render(
      <LanguageProvider>
        <ForecastChart days={singleDay} />
      </LanguageProvider>,
    );

    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
    // No pressure day strip
    expect(screen.queryByText(/টানের দিনসমূহ|Tight days/)).not.toBeInTheDocument();
  });

  it("handles large-series data (e.g. 60 days)", () => {
    const largeDays: DayForecast[] = Array.from({ length: 60 }, (_, i) => ({
      date: `2026-11-${String((i % 30) + 1).padStart(2, "0")}`,
      predicted_inflow_bdt: 1000 + i * 50,
      predicted_outflow_bdt: 800 + i * 40,
      predicted_net_bdt: 200 + i * 10,
      predicted_balance_bdt: 5000 + i * 100,
      is_pressure_day: i % 15 === 0,
      pressure_reason: (i % 15 === 0 ? "below_buffer" : null) as any,
    }));

    const { container } = render(
      <LanguageProvider>
        <ForecastChart days={largeDays} />
      </LanguageProvider>,
    );

    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });

  it("renders both reason below_buffer and both in pressure reasons", () => {
    const bothReasons: DayForecast[] = [
      {
        date: "2026-10-28",
        predicted_inflow_bdt: 2000,
        predicted_outflow_bdt: 18000,
        predicted_net_bdt: -16000,
        predicted_balance_bdt: -500,
        is_pressure_day: true,
        pressure_reason: "both",
      },
    ];

    render(
      <LanguageProvider>
        <ForecastChart days={bothReasons} />
      </LanguageProvider>,
    );

    expect(screen.getByText(/টানের দিনসমূহ|Tight days/)).toBeInTheDocument();
  });
});
