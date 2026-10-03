"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import DoNothingToggle from "@/components/DoNothingToggle";
import VoiceInput from "@/components/VoiceInput";
import SuggestionChips from "@/components/SuggestionChips";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchHealth, fetchIdentity, fetchParseGoal } from "@/lib/api";
import type { HealthResponse, IdentityResponse } from "@/lib/api";
import { formatInteger } from "@/lib/i18n";

type Status = "checking" | "ok" | "unreachable";

function StatusCard() {
  const { lang, tr } = useLanguage();
  const [status, setStatus] = useState<Status>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [identity, setIdentity] = useState<IdentityResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((body) => {
        if (cancelled) return;
        setHealth(body);
        setStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("unreachable");
      });

    fetchIdentity().then(
      (body) => {
        if (!cancelled) setIdentity(body);
      },
      () => undefined,
    );

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 mb-6 space-y-4">
      <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
        <span className="uppercase">{tr("status.title")}</span>
        <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
      </div>

      {status === "checking" && (
        <p className="text-sm font-mono text-ink-muted animate-pulse">
          {tr("status.checking")}
        </p>
      )}

      {status === "unreachable" && (
        <div className="space-y-2">
          <span className="badge danger">{tr("status.apiUnreachable")}</span>
          <p className="text-xs text-ink-muted font-hind">{tr("status.apiHint")}</p>
        </div>
      )}

      {status === "ok" && health && (
        <div className="space-y-3 font-hind text-sm">
          <div className="flex items-center gap-2">
            <span className="badge success">{tr("status.apiReachable")}</span>
            <span className="text-xs font-mono text-ink-muted">
              {tr("status.serviceVersion")}: {health.version}
            </span>
            {health.status === "degraded" && (
              <span className="badge warn">{tr("status.degraded")}</span>
            )}
          </div>

          <div className="space-y-2 pt-2 border-t border-rule font-hind">
            <div className="flex items-baseline justify-between">
              <span className="text-ink-muted">{tr("status.database")}</span>
              <span className="tab-leader" />
              <strong className="font-mono text-ink text-right">
                {health.database.available ? tr("status.databaseReady") : tr("status.databaseMissing")}
              </strong>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-ink-muted">{tr("status.users")}</span>
              <span className="tab-leader" />
              <strong className="font-serif-bn text-ink text-right tabular-nums">
                {formatInteger(health.database.users, lang)}
              </strong>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-ink-muted">{tr("status.transactions")}</span>
              <span className="tab-leader" />
              <strong className="font-serif-bn text-ink text-right tabular-nums">
                {formatInteger(health.database.transactions, lang)}
              </strong>
            </div>
          </div>

          {identity && (
            <div className="pt-2 border-t border-rule text-xs font-mono text-ink flex flex-wrap items-center justify-between gap-2">
              <div>
                <span>{tr("identity.title")}: </span>
                <strong className="text-base font-serif-bn">
                  {lang === "bn" ? identity.name_bn || identity.user_id : identity.name_en || identity.user_id}
                </strong>
              </div>
              <span className="text-ink-muted">
                {identity.persona} · {identity.district} · {identity.income_band}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function GoalConfirm({
  text,
  initialGoal,
  initialMonths,
  onCancel,
}: {
  text: string;
  initialGoal: number | null;
  initialMonths: number | null;
  onCancel: () => void;
}) {
  const { lang, tr } = useLanguage();
  const router = useRouter();
  const [goal, setGoal] = useState(initialGoal && initialGoal > 0 ? String(Math.round(initialGoal)) : "");
  const [months, setMonths] = useState(initialMonths && initialMonths >= 1 ? String(initialMonths) : "");
  // Never substitute: the plan computes only what the user confirms here.
  const ready = Number(goal) > 0 && Number(months) >= 1;
  return (
    <div className="border border-rule p-4 space-y-3 bg-paper/60">
      <p className="text-sm font-hind text-ink">
        <span className="text-ink-muted">{tr("voice.heard")} </span>
        <strong>{text}</strong>
      </p>
      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1 text-sm font-hind text-ink">
          <span className="text-ink-muted">{tr("plan.goal")}</span>
          <input
            type="number"
            min={1}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            className="w-full border border-rule px-2 py-1.5 bg-surface text-ink rounded-none"
          />
        </label>
        <label className="space-y-1 text-sm font-hind text-ink">
          <span className="text-ink-muted">{tr("plan.months")}</span>
          <input
            type="number"
            min={1}
            max={36}
            value={months}
            onChange={(e) => setMonths(e.target.value)}
            className="w-full border border-rule px-2 py-1.5 bg-surface text-ink rounded-none"
          />
        </label>
      </div>
      {!ready && <p className="text-sm font-hind text-ink-muted">{tr("voice.needBoth")}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!ready}
          onClick={() => ready && router.push(`/plan?goal=${Number(goal)}&months=${Number(months)}&prompt=${encodeURIComponent(text)}`)}
          className="px-4 py-1.5 bg-primaryGreen text-paper text-sm font-hind disabled:opacity-40 rounded-none"
        >
          {tr("voice.confirm")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-1.5 border border-rule text-sm font-hind text-ink rounded-none"
        >
          {tr("voice.retry")}
        </button>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { lang, tr } = useLanguage();
  const router = useRouter();
  // Parsed goal awaiting user confirmation. Nothing routes to /plan until
  // the user confirms explicit numbers — no silent 30000/6 defaults (GAP-10).
  const [pending, setPending] = useState<{ text: string; goal: number | null; months: number | null } | null>(null);

  return (
    <>
      <TopBar />
      {/* Real ledger margin rule on left (হাশিয়া - hashia) */}
      <main className="space-y-6 border-l-2 border-rule/80 pl-4 md:pl-6 ml-1">
        {/* Top Ledger Header */}
        <header className="border-t-2 border-b border-rule pt-4 pb-6 space-y-3">
          <div className="flex flex-col md:flex-row md:items-baseline justify-between gap-2">
            <span className="text-xs font-mono tracking-widest text-ink-muted uppercase">
              {tr("subTitle")}
            </span>
            <span className="text-xs font-mono text-ink-muted">
              {tr("subTitleBadge")}
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold font-serif-bn text-ink tracking-tight">
            {tr("appName")}
          </h1>
          <p className="text-base text-ink-muted max-w-3xl leading-relaxed font-hind">
            {tr("tagline")}
          </p>
        </header>

        {/* Section 9: Voice & Search Input Pair */}
        <section className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4">
          <VoiceInput
            onSubmitText={(text) => {
              fetchParseGoal(text)
                .then((parsed) => {
                  setPending({
                    text,
                    goal: parsed.goal_bdt && parsed.goal_bdt > 0 ? parsed.goal_bdt : null,
                    months: parsed.months ?? null,
                  });
                })
                .catch(() => {
                  setPending({ text, goal: null, months: null });
                });
            }}
          />
          {pending && (
            <GoalConfirm
              key={`${pending.text}|${pending.goal}|${pending.months}`}
              text={pending.text}
              initialGoal={pending.goal}
              initialMonths={pending.months}
              onCancel={() => setPending(null)}
            />
          )}
          <SuggestionChips
            onSelectQuery={(q) => {
              router.push(`/plan?goal=30000&months=6&prompt=${encodeURIComponent(q)}`);
            }}
          />
        </section>

        {/* Live System Status */}
        <StatusCard />

        {/* Core Navigation Ledger Grid (ruled cells, no cards) */}
        <div className="border-t border-b border-rule grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:gap-px bg-rule">
          {/* Cell 1: Forecast */}
          <div className="bg-surface p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.forecast")}</span>
              <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
            </div>
            <h3 className="font-serif-bn text-xl font-bold text-ink">
              {tr("forecast.title")}
            </h3>
            <p className="text-sm text-ink-muted font-hind leading-relaxed">
              {tr("forecast.subtitle")}
            </p>
            <div className="pt-2">
              <Link
                href="/forecast"
                className="text-sm font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors"
              >
                {tr("home.viewDetails")} →
              </Link>
            </div>
          </div>

          {/* Cell 2: Savings Plan */}
          <div className="bg-surface p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.plan")}</span>
              <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
            </div>
            <h3 className="font-serif-bn text-xl font-bold text-ink">
              {tr("plan.title")}
            </h3>
            <p className="text-sm text-ink-muted font-hind leading-relaxed">
              {tr("plan.subtitle")}
            </p>
            <div className="pt-2">
              <Link
                href="/plan"
                className="text-sm font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors"
              >
                {tr("home.startSavings")} →
              </Link>
            </div>
          </div>

          {/* Cell 3: Spending Companion */}
          <div className="bg-surface p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.spending")}</span>
              <Stamp variant="muted">{tr("stamp.computed")}</Stamp>
            </div>
            <h3 className="font-serif-bn text-xl font-bold text-ink">
              {tr("spending.title")}
            </h3>
            <p className="text-sm text-ink-muted font-hind leading-relaxed">
              {tr("spending.subtitle")}
            </p>
            <div className="pt-2">
              <Link
                href="/spending"
                className="text-sm font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors"
              >
                {tr("home.viewDetails")} →
              </Link>
            </div>
          </div>

          {/* Cell 4: Tips */}
          <div className="bg-surface p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.tips")}</span>
              <Stamp variant="muted">[{tr("stamp.easyExplain")}]</Stamp>
            </div>
            <h3 className="font-serif-bn text-xl font-bold text-ink">
              {tr("tips.title")}
            </h3>
            <p className="text-sm text-ink-muted font-hind leading-relaxed">
              {tr("tips.subtitle")}
            </p>
            <div className="pt-2">
              <Link
                href="/tips"
                className="text-sm font-semibold text-primaryGreen underline underline-offset-4 decoration-primaryGreen/60 hover:text-ink transition-colors"
              >
                {tr("home.viewDetails")} →
              </Link>
            </div>
          </div>
        </div>

        {/* Section 10: Legal & Non-decision Banner */}
        <NotADecisionBanner />

        {/* Section 7: Do Nothing Option */}
        <DoNothingToggle />

        {/* Footer */}
        <footer className="border-t border-rule pt-6 pb-12 flex flex-col sm:flex-row items-center justify-between text-xs text-ink-muted gap-2 font-mono">
          <span>{tr("footer.ledgerSystem")}</span>
          <span className="font-bold text-ink">{tr("footer.demoDisclaimer")}</span>
        </footer>
      </main>
    </>
  );
}
