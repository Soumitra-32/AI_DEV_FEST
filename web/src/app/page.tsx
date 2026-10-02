"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import DoNothingToggle from "@/components/DoNothingToggle";
import VoiceInput from "@/components/VoiceInput";
import SuggestionChips from "@/components/SuggestionChips";
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
    <div className="bg-surface border border-rule rounded-ledger p-5 md:p-6 mb-6 space-y-4">
      <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
        <span className="uppercase">{tr("status.title")}</span>
        <span className="border border-ink-muted rounded-stamp px-2 py-0.5 text-[11px]">
          {tr("stamp.computed")}
        </span>
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
              <span className="dotted-leader" />
              <strong className="font-mono text-ink">
                {health.database.available ? tr("status.databaseReady") : tr("status.databaseMissing")}
              </strong>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-ink-muted">{tr("status.users")}</span>
              <span className="dotted-leader" />
              <strong className="font-serif-bn text-ink">
                {formatInteger(health.database.users, lang)}
              </strong>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-ink-muted">{tr("status.transactions")}</span>
              <span className="dotted-leader" />
              <strong className="font-serif-bn text-ink">
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

export default function HomePage() {
  const { lang, tr } = useLanguage();
  const router = useRouter();

  return (
    <>
      <TopBar />
      <main className="space-y-6">
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
        <section className="bg-surface border border-rule rounded-ledger p-5 md:p-6 space-y-4">
          <VoiceInput
            onSubmitText={(text) => {
              // Speech carries the numbers: parse them first so the plan page
              // computes what was SAID, not the hardcoded defaults. Missing
              // halves keep the defaults; parse failures do too (never block).
              fetchParseGoal(text)
                .then((parsed) => {
                  const goal =
                    parsed.goal_bdt && parsed.goal_bdt > 0
                      ? Math.round(parsed.goal_bdt)
                      : 30000;
                  const months = parsed.months ?? 6;
                  router.push(
                    `/plan?goal=${goal}&months=${months}&prompt=${encodeURIComponent(text)}`,
                  );
                })
                .catch(() => {
                  router.push(
                    `/plan?goal=30000&months=6&prompt=${encodeURIComponent(text)}`,
                  );
                });
            }}
          />
          <SuggestionChips
            onSelectQuery={(q) => {
              router.push(`/plan?goal=30000&months=6&prompt=${encodeURIComponent(q)}`);
            }}
          />
        </section>

        {/* Live System Status Card */}
        <StatusCard />

        {/* Core Navigation Ledger Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Card 1: Forecast */}
          <div className="bg-surface border border-rule rounded-ledger p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.forecast")}</span>
              <span className="border border-ink-muted rounded-stamp px-1.5 py-0.5 text-[10px]">
                {tr("stamp.computed")}
              </span>
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

          {/* Card 2: Savings Plan */}
          <div className="bg-surface border border-rule rounded-ledger p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.plan")}</span>
              <span className="border border-ink-muted rounded-stamp px-1.5 py-0.5 text-[10px]">
                {tr("stamp.computed")}
              </span>
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

          {/* Card 3: Spending Companion */}
          <div className="bg-surface border border-rule rounded-ledger p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.spending")}</span>
              <span className="border border-ink-muted rounded-stamp px-1.5 py-0.5 text-[10px]">
                {tr("stamp.computed")}
              </span>
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

          {/* Card 4: Tips */}
          <div className="bg-surface border border-rule rounded-ledger p-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-ink-muted border-b border-rule pb-2">
              <span className="uppercase">{tr("nav.tips")}</span>
              <span className="border border-ink-muted rounded-stamp px-1.5 py-0.5 text-[10px]">
                [{tr("stamp.easyExplain")}]
              </span>
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
