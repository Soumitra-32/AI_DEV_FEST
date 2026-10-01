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
import { formatBDT } from "@/lib/i18n";

/** The demo goal from the plan's story: ৳30,000 in 6 months. */
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
    // the solver owns the maths; the client only rejects a nonsense goal
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
      <main>
        <h1>{tr("plan.title")}</h1>
        <p>{tr("plan.subtitle")}</p>
        <NotADecisionBanner />
        <PlanForm
          goal={goal}
          months={months}
          busy={busy}
          onGoal={setGoal}
          onMonths={setMonths}
          onSubmit={submit}
        />
        {error ? <p className="banner">{error}</p> : null}
        {busy ? <p>{tr("plan.calculating")}</p> : null}
        {plan ? <PlanResult plan={plan} /> : null}
      </main>
    </>
  );
interface PlanFormProps {
  goal: string;
  months: string;
  busy: boolean;
  onGoal: (value: string) => void;
  onMonths: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function PlanForm({ goal, months, busy, onGoal, onMonths, onSubmit }: PlanFormProps) {
  const { tr } = useLanguage();
  return (
    <form className="card" onSubmit={onSubmit}>
      <p>
        <label htmlFor="goal">
          {tr("plan.goal")}
          <br />
          <input
            id="goal"
            type="number"
            min={1}
            step={500}
            value={goal}
            onChange={(event) => onGoal(event.target.value)}
            style={{ font: "inherit", padding: "8px", width: "12rem" }}
          />
        </label>
      </p>
      <p>
        <label htmlFor="months">
          {tr("plan.months")}
          <br />
          <input
            id="months"
            type="number"
            min={1}
            max={60}
            value={months}
            onChange={(event) => onMonths(event.target.value)}
            style={{ font: "inherit", padding: "8px", width: "8rem" }}
          />
        </label>
      </p>
      <button type="submit" className="primary" disabled={busy}>
        {tr("plan.submit")}
      </button>
    </form>
  );
}

function PlanResult({ plan }: { plan: SavingsPlanResponse }) {
  const { lang, tr } = useLanguage();
  return (
    <>
      <InsightCard title={tr("plan.title")} provenance={plan.provenance}>
        <p>
          <span className={plan.feasible ? "badge" : "badge warn"}>
            {plan.feasible ? tr("plan.feasible") : tr("plan.infeasible")}
          </span>
        </p>
        <table>
          <tbody>
            <tr>
              <th>{tr("plan.requiredMonthly")}</th>
              <td>
                <strong>{formatBDT(plan.required_monthly_bdt, lang)}</strong>
              </td>
            </tr>
            <tr>
              <th>{tr("plan.feasibleMonthly")}</th>
              <td>
                <strong>{formatBDT(plan.feasible_monthly_bdt, lang)}</strong>
              </td>
            </tr>
            <tr>
              <th>{tr("plan.surplus")}</th>
              <td>{formatBDT(plan.forecasted_surplus_bdt, lang)}</td>
            </tr>
            <tr>
              <th>{tr("plan.buffer")}</th>
              <td>{formatBDT(plan.safety_buffer_bdt, lang)}</td>
            </tr>
          </tbody>
        </table>
      </InsightCard>

      <div className="card">
        <h2>{tr("plan.arithmetic")}</h2>
        <ol>
          {plan.arithmetic.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      </div>

      {plan.pressure_days.length > 0 ? (
        <p className="banner">
          {tr("plan.pressureWarning")} ({plan.pressure_days.join(", ")})
        </p>
      ) : null}

      <div className="card">
        <h2>{tr("plan.tradeOffs")}</h2>
        <ul>
          {plan.trade_offs.map((option) => (
            <li key={`${option.action}-${option.title}`}>
              <strong>{tr(ACTION_KEY[option.action])}</strong> — {option.title}
              {option.monthly_amount_bdt !== null ? (
                <span className="muted">
                  {" "}
                  ({formatBDT(option.monthly_amount_bdt, lang)}
                  {option.months !== null ? ` × ${option.months}` : ""})
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </div>

      <DoNothingToggle costBdt={plan.do_nothing.estimated_cost_bdt} />

      <p>
        <Link href="/forecast">{tr("nav.forecast")}</Link>
      </p>
    </>
  );
}
}

