"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import DoNothingToggle from "@/components/DoNothingToggle";
import InsightCard from "@/components/InsightCard";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import SavingsPlanForm from "@/components/SavingsPlanForm";
import TopBar from "@/components/TopBar";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchSavingsPlan, trackEvent } from "@/lib/api";
import type { SavingsPlanResponse, TradeOffAction } from "@/lib/api";
import { FeedbackWidget } from "@/components/FeedbackWidget";
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
  reduce: { bn: "লক্ষ্য কমান", en: "Lower the target" },
  delay: { bn: "সময়সীমা বাড়ান", en: "Extend the timeline" },
  switch: { bn: "QR ব্যবহার করুন", en: "Switch to QR" },
  do_nothing: { bn: "কিছু পরিবর্তন করব না", en: "Keep as is" },
};

function formatDoNothingOutcome(desc: string | null | undefined, lang: "bn" | "en"): string {
  if (!desc) return "";
  const m = desc.match(/After\s+(\d+)\s+months?\s+you\s+have\s*৳?0\s+saved\s+and\s+paid\s+about\s*৳?([\d,]+)/i);
  if (m) {
    const fee = formatBDT(Number(m[2].replace(/,/g, "")), lang);
    const taka = lang === "bn" ? "টাকা" : "taka";
    return lang === "bn"
      ? `কোনো পরিবর্তন না করলে ${formatDigits(m[1], lang)} মাসে সঞ্চয়ের পরিমাণ হবে ৳০ এবং ফি বাবদ ব্যয় হবে প্রায় ${fee} ${taka}।`
      : `If you make no changes, after ${m[1]} months you will have ৳0 saved and pay about ${fee} ${taka} in fees.`;
  }
  return lang === "bn" ? formatDigits(desc, lang) : desc;
}

function formatTradeOffDescription(desc: string, lang: "bn" | "en"): string {
  if (!desc) return "";

  // 1. Keep months, aim for goal
  const m1 = desc.match(/Keep\s+(\d+)\s+months,\s*aim\s+for\s*৳?([\d,]+)/i);
  if (m1) {
    const goalStr = formatBDT(Number(m1[2].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `${formatDigits(m1[1], "bn")} মাস সময় ঠিক রেখে লক্ষ্য ${goalStr} নির্ধারণ করুন (হাতে থাকা টাকায় যতটুকু হয়)।`
      : `Keep ${m1[1]} months, aim for ${goalStr} (what your extra money allows).`;
  }

  // 2. Keep target, extend months
  const m2 = desc.match(/Keep\s*৳?([\d,]+)\s+target,\s*extend\s+to\s*(\d+)\s+months/i);
  if (m2) {
    const goalStr = formatBDT(Number(m2[1].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `লক্ষ্য ${goalStr} ঠিক রেখে সময় ${formatDigits(m2[2], "bn")} মাস পর্যন্ত বাড়ান।`
      : `Keep the ${goalStr} goal, take ${m2[2]} months instead.`;
  }

  // 3. Free up cuts
  const m3 = desc.match(/Free\s+up\s*৳?([\d,]+)\/month/i);
  if (m3) {
    const amt = formatBDT(Number(m3[1].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `খরচ বা ক্যাশ-আউট ফি থেকে মাসে ${amt} বাঁচিয়ে সঞ্চয়ে যোগ করুন।`
      : `Save ${amt} a month from spending or cash-out fees and add it to savings.`;
  }

  // 4. Avoid fees
  const m4 = desc.match(/Avoid\s+up\s+to\s*৳?([\d,]+)\/month\s+in\s+cash-out\s+fees/i);
  if (m4) {
    const amt = formatBDT(Number(m4[1].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `ক্যাশ-আউটের ফি থেকে প্রতি মাসে ${amt} পর্যন্ত বাঁচিয়ে ঘাটতি পূরণ করুন।`
      : `Save up to ${amt} a month in cash-out fees to close the gap.`;
  }

  // 5. Do nothing
  const m5 = desc.match(/After\s+(\d+)\s+months\s+you\s+have\s*৳?0\s+saved\s+and\s+paid\s+about\s*৳?([\d,]+)/i);
  if (m5) {
    const fee = formatBDT(Number(m5[2].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `কোনো সঞ্চয় হবে না। ${formatDigits(m5[1], "bn")} মাস পর সঞ্চয় ৳০ থাকবে এবং প্রায় ${fee} ক্যাশ-আউট ফি চলে যাবে।`
      : `You will save nothing. After ${m5[1]} months you will have ৳0 saved and pay about ${fee} in cash-out fees.`;
  }

  if (desc.includes("already fits") || desc.includes("fits in")) {
    return lang === "bn"
      ? "লক্ষ্যটি বর্তমান মেয়াদেই পূরণ হবে — বাড়তি সময় লাগবে না।"
      : "This goal fits your current timeline — no extra time needed.";
  }
  if (desc.includes("Free up") || desc.includes("spending cut")) {
    return lang === "bn"
      ? "মাসে অপ্রয়োজনীয় খরচ কমিয়ে লক্ষ্যটি পূরণ করা সম্ভব।"
      : "You can reach the goal by cutting unneeded spending each month.";
  }
  if (desc.includes("Change nothing and keep paying")) {
    return lang === "bn"
      ? "কোনো পরিবর্তন না করলে প্রতি মাসে ক্যাশ-আউট ফি বাবদ টাকা যেতেই থাকবে।"
      : "If nothing changes, cash-out fees will keep eating your money every month.";
  }
  return lang === "bn" ? formatDigits(desc, lang) : desc;
}

function formatArithmeticStep(step: string, lang: "bn" | "en"): string {
  if (!step) return step;
  if (step.includes("required monthly")) {
    return formatDigits(
      step.replace("required monthly =", lang === "bn" ? "প্রয়োজনীয় মাসিক সঞ্চয় =" : "Required monthly savings ="),
      lang,
    );
  }
  if (step.includes("safety buffer")) {
    return formatDigits(
      step
        .replace("safety buffer =", lang === "bn" ? "সংরক্ষিত নিরাপত্তা বাফার =" : "Safety buffer =")
        .replace("day(s) of typical outflow =", lang === "bn" ? "দিনের স্বাভাবিক খরচ =" : "days of typical outflow ="),
      lang,
    );
  }
  if (step.includes("feasible monthly")) {
    return formatDigits(
      step
        .replace("feasible monthly = surplus", lang === "bn" ? "সম্ভাব্য মাসিক সঞ্চয় = মাসিক উদ্বৃত্ত" : "Achievable monthly savings = surplus")
        .replace("- buffer", lang === "bn" ? "- বাফার" : "- buffer"),
      lang,
    );
  }
  if (step === "feasible") {
    return lang === "bn" ? "এই পরিকল্পনা বর্তমান উদ্বৃত্তে বাস্তবায়নযোগ্য।" : "This plan is achievable with your current surplus.";
  }
  if (step.includes("not feasible")) {
    return lang === "bn"
      ? "নিরাপত্তা বাফার বজায় রেখে বর্তমান উদ্বৃত্তে এই লক্ষ্য অর্জন সম্ভব নয়।"
      : "After preserving the safety buffer, this goal cannot be met within the timeline.";
  }
  return lang === "bn" ? formatDigits(step, lang) : step;
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

  useEffect(() => {
    trackEvent("savings_plan_viewed", { feature: "savings_plan" });
  }, []);

  function runPlan(goalBdt: number, monthsCount: number) {
    setBusy(true);
    setError(null);
    fetchSavingsPlan({ goal_bdt: goalBdt, months: Math.round(monthsCount) })
      .then((body) => {
        setPlan(body);
        setBusy(false);
        trackEvent("savings_plan_created", {
          feature: "savings_plan",
          properties: { goal_bdt: goalBdt, months: Math.round(monthsCount) },
        });
      })
      .catch(() => {
        setError(tr("error.title"));
        setBusy(false);
      });
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

        <SavingsPlanForm
          initialGoal={goal}
          initialMonths={months}
          busy={busy}
          error={error}
          onSubmit={({ goal_bdt, months: m }) => {
            setGoal(String(goal_bdt));
            setMonths(String(m));
            runPlan(goal_bdt, m);
          }}
        />

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
                  {formatBDT(plan.required_monthly_bdt, lang)} {tr("common.taka")}{" "}
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
                    <span className="font-serif-bn font-bold text-xl text-[#0054A6] text-right tabular-nums">
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
              outcome={formatDoNothingOutcome(plan.do_nothing?.description, lang) || undefined}
            />

            {/* Feedback Loop */}
            <FeedbackWidget feature="savings_plan" language={lang} />

            <div className="p-4 bg-surface/50 border-t border-b border-rule flex items-center justify-between">
              <span className="font-hind text-sm text-ink-muted">
                {tr("plan.reviewForecastPrompt")}
              </span>
              <Link
                href="/forecast"
                className="text-sm font-semibold text-[#0054A6] hover:text-[#003E7E] underline underline-offset-4 decoration-[#0054A6]/60 transition-colors font-hind"
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
