import { render } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, expect, it } from "vitest";
import ForecastChart from "@/components/ForecastChart";
import SavingsPlanForm from "@/components/SavingsPlanForm";
import LangToggle, { LanguageProvider } from "@/components/LangToggle";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";

expect.extend(toHaveNoViolations);

describe("Accessibility (jest-axe) audits on critical components", () => {
  it("ForecastChart has no critical or serious accessibility violations", async () => {
    const { container } = render(
      <LanguageProvider>
        <ForecastChart
          days={[
            {
              date: "2026-10-27",
              predicted_inflow_bdt: 12000,
              predicted_outflow_bdt: 4500,
              predicted_net_bdt: 7500,
              predicted_balance_bdt: 15500,
              is_pressure_day: false,
              pressure_reason: null,
            },
          ]}
        />
      </LanguageProvider>,
    );

    const results = await axe(container);
    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(criticalOrSerious).toHaveLength(0);
  });

  it("SavingsPlanForm has no critical or serious accessibility violations", async () => {
    const { container } = render(
      <LanguageProvider>
        <SavingsPlanForm />
      </LanguageProvider>,
    );

    const results = await axe(container);
    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(criticalOrSerious).toHaveLength(0);
  });

  it("LangToggle has no critical or serious accessibility violations", async () => {
    const { container } = render(
      <LanguageProvider>
        <LangToggle />
      </LanguageProvider>,
    );

    const results = await axe(container);
    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(criticalOrSerious).toHaveLength(0);
  });

  it("TopBar has no critical or serious accessibility violations", async () => {
    const { container } = render(
      <LanguageProvider>
        <TopBar />
      </LanguageProvider>,
    );

    const results = await axe(container);
    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(criticalOrSerious).toHaveLength(0);
  });

  it("NotADecisionBanner has no critical or serious accessibility violations", async () => {
    const { container } = render(
      <LanguageProvider>
        <NotADecisionBanner />
      </LanguageProvider>,
    );

    const results = await axe(container);
    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(criticalOrSerious).toHaveLength(0);
  });
});
