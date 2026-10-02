"use client";

import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";
import DoNothingToggle from "@/components/DoNothingToggle";
import InsightCard from "@/components/InsightCard";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import TopBar from "@/components/TopBar";
import { useLanguage } from "@/components/LangToggle";
import { fetchSavingsPlan } from "@/lib/api";
import type { SavingsPlanResponse, TradeOffAction } from "@/lib/api";
import type { TranslationKey } from "@/lib/i18n";
import { formatBDT, formatDigits, formatInteger } from "@/lib/i18n";

const DEFAULT_GOAL = 30000;
const DEFAULT_MONTHS = 6;

const ACTION_KEY: Record<TradeOffAction, TranslationKey> = {
  reduce: "plan.action.reduce",
  delay: "plan.action.delay",
  switch: "plan.action.switch",
  do_nothing: "plan.action.do_nothing",
};

export default function PlanPage() {
  const { lang, tr } = useLanguage();
  const [goal, setGoal] = useState(String(DEFAULT_GOAL));
  const [months, setMonths] = useState(String(DEFAULT_MONTHS));
  const [plan, setPlan] = useState<SavingsPlanResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const goalBdt = Number(goal);
    const monthsCount = Number(months);

    if (
      !Number.isFinite(goalBdt) ||
      goalBdt <= 0 ||
      !Number.isFinite(monthsCount) ||
      monthsCount < 1
    ) {
      setError(tr("error.title"));
      return;
    }

    setBusy(true);
    setError(null);
    fetchSavingsPlan({ goal_bdt: goalBdt, months: Math.round(monthsCount) })
      .then((body) => {
        setPlan(body);
        setBusy(false);
      })
      .catch(() => {
        setError(tr("error.title"));
        setBusy(false);
      });
  }

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider">
            {tr("plan.headerTag")} • {tr("stamp.computed")}
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("plan.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("plan.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Input Form */}
        <form
          onSubmit={submit}
          className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="goal-input" className="text-xs font-mono uppercase text-ink-muted block">
                {tr("plan.goal")}
              </label>
              <input
                id="goal-input"
                type="number"
                min={500}
                step={500}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="w-full h-12 bg-surface border border-rule rounded-ledger px-4 font-serif-bn text-xl font-bold text-ink focus:outline-none focus:border-ink transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="months-input" className="text-xs font-mono uppercase text-ink-muted block">
                {tr("plan.months")}
              </label>
              <input
                id="months-input"
                type="number"
                min={1}
                max={36}
                value={months}
                onChange={(e) => setMonths(e.target.value)}
                className="w-full h-12 bg-surface border border-rule rounded-ledger px-4 font-mono text-lg text-ink focus:outline-none focus:border-ink transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full h-12 bg-primaryGreen text-white text-[17px] font-medium rounded-ledger hover:opacity-95 transition"
          >
            {busy ? tr("plan.calculating") : tr("plan.submit")}
          </button>
        </form>

        {error && (
          <div className="bg-surface border border-brickRed rounded-ledger p-4 text-brickRed text-sm font-mono">
            {error}
          </div>
        )}

        {/* Plan Results */}
        {plan && (
          <div className="space-y-6">
            {/* Feasibility Hero Card */}
            <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <span className="text-xs font-mono text-ink-muted uppercase">
                  {tr("plan.title")} • {formatInteger(plan.months, lang)} {lang === "bn" ? "মাস" : "months"}
                </span>
                <span
                  className={`border rounded-stamp px-2.5 py-0.5 text-[11px] font-mono uppercase ${
                    plan.feasible
                      ? "border-primaryGreen text-primaryGreen"
                      : "border-brickRed text-brickRed"
                  }`}
                >
                  {plan.feasible ? tr("plan.feasible") : tr("plan.infeasible")}
                </span>
              </div>

              {/* Hero Numbers */}
              <div className="space-y-1">
                <div className="text-xs font-mono text-ink-muted uppercase">
                  {tr("plan.requiredMonthly")}
                </div>
                <div className="font-serif-bn text-4xl md:text-5xl font-bold text-ink tracking-tight">
                  {formatBDT(plan.required_monthly_bdt, lang)}{" "}
                  <span className="text-sm font-hind font-normal text-ink-muted">
                    {tr("spending.perMonth")}
                  </span>
                </div>
              </div>

              {/* Dotted Leader Accounting Breakdown */}
              <div className="space-y-2 pt-3 border-t border-rule font-hind text-sm">
                <div className="flex items-baseline justify-between">
                  <span className="text-ink-muted">{tr("plan.surplus")}</span>
                  <span className="dotted-leader" />
                  <span className="font-serif-bn font-bold text-ink">
                    {formatBDT(plan.forecasted_surplus_bdt, lang)}
                  </span>
                </div>

                <div className="flex items-baseline justify-between">
                  <span className="text-ink-muted">{tr("plan.buffer")}</span>
                  <span className="dotted-leader" />
                  <span className="font-serif-bn font-bold text-ink-muted">
                    - {formatBDT(plan.safety_buffer_bdt, lang)}
                  </span>
                </div>

                <div className="pt-2 mt-2">
                  <div className="border-t border-rule pt-2 pb-2 ledger-double-bottom flex items-baseline justify-between">
                    <span className="font-bold text-ink font-serif-bn text-base">
                      {tr("plan.feasibleMonthly")}
                    </span>
                    <span className="dotted-leader" />
                    <span className="font-serif-bn font-bold text-xl text-primaryGreen">
                      {formatBDT(plan.feasible_monthly_bdt, lang)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Pressure Warning Strip */}
              {plan.pressure_days.length > 0 && (
                <div className="bg-surface border-l-4 border-brickRed border-t border-r border-b border-rule rounded-ledger p-4 space-y-1 mt-4">
                  <div className="text-xs font-mono uppercase tracking-wider text-brickRed font-bold">
                    {tr("spending.warningStripTitle")}
                  </div>
                  <p className="text-xs text-ink-muted leading-relaxed font-hind">
                    {tr("plan.pressureWarning")} (
                    {plan.pressure_days.map((d) => formatDigits(d.slice(8, 10), lang)).join(" · ")} {lang === "bn" ? "তারিখ" : ""}
                    )
                  </p>
                </div>
              )}
            </div>

            {/* Alternative Options (Trade-offs) */}
            {plan.trade_offs.length > 0 && (
              <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4">
                <div className="border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                    {tr("plan.tradeOffs")}
                  </h3>
                </div>

                <div className="divide-y divide-rule font-hind">
                  {plan.trade_offs.map((item, idx) => (
                    <div key={idx} className="py-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-ink">
                          {tr(ACTION_KEY[item.action])}
                        </span>
                        <span className="border border-ink-muted rounded-stamp px-2 py-0.5 text-[10px] font-mono text-ink-muted">
                          {item.action}
                        </span>
                      </div>
                      <p className="text-xs text-ink-muted leading-relaxed">
                        {item.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Arithmetic Trace */}
            {plan.arithmetic.length > 0 && (
              <div className="bg-surface border border-rule rounded-ledger p-5 space-y-2">
                <div className="text-xs font-mono text-ink-muted uppercase border-b border-rule pb-2">
                  {tr("plan.arithmetic")}
                </div>
                <div className="space-y-1 pt-1 font-mono text-xs text-ink-muted">
                  {plan.arithmetic.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <span>•</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3-Layer Provenance */}
            {plan.provenance && (
              <InsightCard provenance={plan.provenance} />
            )}

            {/* Do Nothing Option */}
            <DoNothingToggle costBdt={plan.do_nothing?.estimated_cost_bdt} />

            <div className="p-4 bg-surface border border-rule rounded-ledger flex items-center justify-between">
              <span className="font-hind text-sm text-ink-muted">
                {tr("plan.reviewForecastPrompt")}
              </span>
              <Link
                href="/forecast"
                className="text-sm font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors font-hind"
              >
                {tr("nav.forecast")} →
              </Link>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
