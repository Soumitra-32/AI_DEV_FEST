"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import DoNothingToggle from "@/components/DoNothingToggle";
import InsightCard from "@/components/InsightCard";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import TopBar from "@/components/TopBar";
import Stamp from "@/components/Stamp";
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

const ACTION_LABEL: Record<TradeOffAction, { bn: string; en: string }> = {
  reduce: { bn: "খরচ কমানো", en: "Reduce" },
  delay: { bn: "সময় বাড়ানো", en: "Delay" },
  switch: { bn: "চ্যানেল বদল", en: "Switch" },
  do_nothing: { bn: "কিছু না করা", en: "Do Nothing" },
};

function formatTradeOffDescription(desc: string, lang: "bn" | "en"): string {
  if (lang === "en" || !desc) return desc;
  if (desc.includes("already fits") || desc.includes("fits in")) {
    return desc.includes("no extra time")
      ? "লক্ষ্যটি বর্তমান মেয়াদেই অর্জন সম্ভব — বাড়তি সময়ের প্রয়োজন নেই।"
      : "বর্তমান মাসিক উদ্বৃত্তেই পুরো সঞ্চয় লক্ষ্যটি পূরণ করা সম্ভব।";
  }
  if (desc.includes("Free up") || desc.includes("spending cut")) {
    return "মাসে অপ্রয়োজনীয় খরচ (যেমন: অতিরিক্ত ক্যাশ-আউট) কমিয়ে লক্ষ্যটি অর্জন করা সম্ভব।";
  }
  if (desc.includes("Keep") && desc.includes("months")) {
    return desc.includes("aim for")
      ? "সময় ঠিক রেখে মাসিক উদ্বৃত্তের সাথে সামঞ্জস্য রেখে সঞ্চয়ের লক্ষ্য কিছুটা কমান।"
      : "লক্ষ্য ও সময়সীমা সমন্বয় করে সঞ্চয় বাস্তবায়ন করুন।";
  }
  if (desc.includes("Change nothing and keep paying")) {
    return "কোনো পরিবর্তন না করলে প্রতি মাসে ক্যাশ-আউট ফি বাবদ অপচয় হতে থাকবে।";
  }
  return desc;
}

function formatArithmeticStep(step: string, lang: "bn" | "en"): string {
  if (lang === "en" || !step) return step;
  if (step.includes("required monthly")) {
    return formatDigits(
      step.replace("required monthly =", "প্রয়োজনীয় মাসিক সঞ্চয় ="),
      "bn"
    );
  }
  if (step.includes("safety buffer")) {
    return formatDigits(
      step
        .replace("safety buffer =", "জরুরি খরচের বাফার =")
        .replace("day(s) of typical outflow =", "দিনের নিয়মিত খরচ ="),
      "bn"
    );
  }
  if (step.includes("feasible monthly")) {
    return formatDigits(
      step
        .replace("feasible monthly = surplus", "সম্ভাব্য মাসিক সঞ্চয় = উদ্বৃত্ত")
        .replace("- buffer", "- বাফার"),
      "bn"
    );
  }
  if (step === "feasible") {
    return "পরিকল্পনাটি বর্তমান উদ্বৃত্তে বাস্তবসম্মত ও টেকসই।";
  }
  if (step.includes("not feasible")) {
    return "জরুরি বাফার বাদ দিয়ে বর্তমান উদ্বৃত্তে এই সময়ে সম্পন্ন করা সম্ভব নয়।";
  }
  return formatDigits(step, "bn");
}

function PlanContent() {
  const { lang, tr } = useLanguage();
  const searchParams = useSearchParams();
  // Voice (and suggestion chips) arrive via ?goal=&months=&prompt= from the
  // home page. Read them once for the initial form values; the prompt also
  // triggers one automatic calculation below.
  const [goal, setGoal] = useState(
    () => searchParams.get("goal") ?? String(DEFAULT_GOAL),
  );
  const [months, setMonths] = useState(
    () => searchParams.get("months") ?? String(DEFAULT_MONTHS),
  );
  const [plan, setPlan] = useState<SavingsPlanResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Key of the last voice handoff already handled. Same-route navigation
  // (home → plan → home → plan) does NOT remount this component, so a
  // run-once ref would swallow every handoff after the first and the page
  // would keep showing stale/default values (GAP-10 voice carry bug).
  const lastHandoff = useRef<string | null>(null);

  function runPlan(goalBdt: number, monthsCount: number) {
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

    runPlan(goalBdt, monthsCount);
  }

  // Voice handoff: landing with ?goal=&months=&prompt= means the user spoke
  // (or confirmed numbers on the home page), so the form takes those values
  // and calculates immediately. Keyed on the full query string, so a second
  // voice handoff to the same route re-syncs instead of showing stale values.
  useEffect(() => {
    const prompt = searchParams.get("prompt");
    if (!prompt) return;
    const key = `${searchParams.get("goal")}|${searchParams.get("months")}|${prompt}`;
    if (lastHandoff.current === key) return;
    lastHandoff.current = key;
    const goalParam = searchParams.get("goal");
    const monthsParam = searchParams.get("months");
    if (goalParam !== null) setGoal(goalParam);
    if (monthsParam !== null) setMonths(monthsParam);
    const goalBdt = Number(goalParam ?? goal);
    const monthsCount = Number(monthsParam ?? months);
    if (
      Number.isFinite(goalBdt) &&
      goalBdt > 0 &&
      Number.isFinite(monthsCount) &&
      monthsCount >= 1
    ) {
      runPlan(goalBdt, monthsCount);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider flex items-center gap-2">
            <span>{tr("plan.headerTag")}</span>
            <span>•</span>
            <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("plan.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("plan.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Input Form Ledger Section */}
        <form
          onSubmit={submit}
          className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4"
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
                className="w-full h-12 bg-surface border border-rule px-4 font-serif-bn text-xl font-bold text-ink focus:outline-none focus:border-ink transition-colors rounded-none"
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
                className="w-full h-12 bg-surface border border-rule px-4 font-mono text-lg text-ink focus:outline-none focus:border-ink transition-colors rounded-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full h-12 bg-primaryGreen text-white text-[17px] font-medium rounded-none hover:opacity-95 transition"
          >
            {busy ? tr("plan.calculating") : tr("plan.submit")}
          </button>
        </form>

        {error && (
          <div className="bg-surface/50 border-l-2 border-brickRed border-t border-b border-r border-rule p-4 text-brickRed text-sm font-mono">
            {error}
          </div>
        )}

        {/* Plan Results */}
        {plan && (
          <div className="space-y-6">
            {/* Feasibility Hero Section (no outer rounded card) */}
            <div className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-2">
                <span className="text-xs font-mono text-ink-muted uppercase">
                  {tr("plan.title")} • {formatInteger(plan.months, lang)} {lang === "bn" ? "মাস" : "months"}
                </span>
                <Stamp variant={plan.feasible ? "ink" : "warn"}>
                  {plan.feasible ? tr("plan.feasible") : tr("plan.infeasible")}
                </Stamp>
              </div>

              {/* Hero Numbers */}
              <div className="space-y-1">
                <div className="text-xs font-mono text-ink-muted uppercase">
                  {tr("plan.requiredMonthly")}
                </div>
                <div className="font-serif-bn text-4xl md:text-5xl font-bold text-ink tracking-tight tabular-nums">
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
                  <span className="tab-leader" />
                  <span className="font-serif-bn font-bold text-ink text-right tabular-nums">
                    {formatBDT(plan.forecasted_surplus_bdt, lang)}
                  </span>
                </div>

                <div className="flex items-baseline justify-between">
                  <span className="text-ink-muted">{tr("plan.buffer")}</span>
                  <span className="tab-leader" />
                  <span className="font-serif-bn font-bold text-ink-muted text-right tabular-nums">
                    - {formatBDT(plan.safety_buffer_bdt, lang)}
                  </span>
                </div>

                <div className="pt-2 mt-2">
                  <div className="border-t border-rule pt-2 pb-2 ledger-double-bottom flex items-baseline justify-between">
                    <span className="font-bold text-ink font-serif-bn text-base">
                      {tr("plan.feasibleMonthly")}
                    </span>
                    <span className="tab-leader" />
                    <span className="font-serif-bn font-bold text-xl text-primaryGreen text-right tabular-nums">
                      {formatBDT(plan.feasible_monthly_bdt, lang)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Pressure Warning Strip */}
              {plan.pressure_days.length > 0 && (
                <div className="bg-surface/50 border-l-2 border-brickRed border-t border-r border-b border-rule/60 p-4 space-y-1 mt-4">
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
              <div className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4">
                <div className="border-b border-rule pb-2">
                  <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                    {tr("plan.tradeOffs")}
                  </h3>
                </div>

                <div className="divide-y divide-rule/60 font-hind">
                  {plan.trade_offs.map((item, idx) => (
                    <div key={idx} className="py-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-ink">
                          {tr(ACTION_KEY[item.action])}
                        </span>
                        <Stamp variant="muted">
                          {ACTION_LABEL[item.action]?.[lang] ?? item.action}
                        </Stamp>
                      </div>
                      <p className="text-xs text-ink-muted leading-relaxed">
                        {formatTradeOffDescription(item.description, lang)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Arithmetic Trace */}
            {plan.arithmetic.length > 0 && (
              <div className="bg-surface/50 border-t border-b border-rule p-5 space-y-2">
                <div className="text-xs font-mono text-ink-muted uppercase border-b border-rule pb-2">
                  {tr("plan.arithmetic")}
                </div>
                <div className="space-y-1 pt-1 font-mono text-xs text-ink-muted">
                  {plan.arithmetic.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <span>•</span>
                      <span>{formatArithmeticStep(step, lang)}</span>
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
            <DoNothingToggle
              costBdt={plan.do_nothing?.estimated_cost_bdt ?? (plan.required_monthly_bdt * plan.months)}
              months={plan.months}
              outcome={plan.do_nothing?.description}
            />

            <div className="p-4 bg-surface/50 border-t border-b border-rule flex items-center justify-between">
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

export default function PlanPage() {
  return (
    <Suspense
      fallback={
        <div className="bg-surface/50 border-t border-b border-rule p-8 text-center">
          <p className="font-mono text-sm text-ink-muted animate-pulse">...</p>
        </div>
      }
    >
      <PlanContent />
    </Suspense>
  );
}
