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
import MaterialIcon from "@/components/MaterialIcon";
import { useLanguage } from "@/components/LangToggle";
import { fetchAnomalies, fetchHealth, fetchIdentity, fetchParseGoal } from "@/lib/api";
import type { HealthResponse, IdentityResponse } from "@/lib/api";
import { formatBDT, formatDistrict, formatIncomeBand, formatInteger, formatPersona } from "@/lib/i18n";

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
    <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-4 md:p-5 space-y-3">
      <div className="flex items-center justify-between text-xs font-mono text-[#6A6355] border-b border-[#D8CFBB] pb-2">
        <span className="uppercase">{tr("status.title")}</span>
        <Stamp variant="blue">{tr("stamp.computed")}</Stamp>
      </div>

      {status === "checking" && (
        <p className="text-sm font-mono text-[#6A6355] animate-pulse">
          {tr("status.checking")}
        </p>
      )}

      {status === "unreachable" && (
        <div className="space-y-1">
          <span className="badge danger">{tr("status.apiUnreachable")}</span>
          <p className="text-xs text-[#6A6355] font-hind">{tr("status.apiHint")}</p>
        </div>
      )}

      {status === "ok" && health && (
        <div className="space-y-2.5 font-hind text-sm">
          <div className="flex items-center gap-2">
            <span className="badge success">{tr("status.apiReachable")}</span>
            {health.status === "degraded" && (
              <span className="badge warn">{tr("status.degraded")}</span>
            )}
          </div>

          <div className="space-y-1.5 pt-1.5 border-t border-[#D8CFBB] font-hind">
            <div className="flex items-baseline justify-between">
              <span className="text-[#6A6355]">{tr("status.database")}</span>
              <span className="tab-leader" />
              <strong className="font-mono text-[#1E1B16] text-right">
                {health.database.available ? tr("status.databaseReady") : tr("status.databaseMissing")}
              </strong>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-[#6A6355]">{tr("status.users")}</span>
              <span className="tab-leader" />
              <strong className="font-serif-bn text-[#1E1B16] text-right tabular-nums">
                {formatInteger(health.database.users, lang)}
              </strong>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-[#6A6355]">{tr("status.transactions")}</span>
              <span className="tab-leader" />
              <strong className="font-serif-bn text-[#1E1B16] text-right tabular-nums">
                {formatInteger(health.database.transactions, lang)}
              </strong>
            </div>
          </div>

          {identity && (
            <div className="pt-2 border-t border-[#D8CFBB] text-xs font-mono text-[#1E1B16] flex flex-wrap items-center justify-between gap-2">
              <div>
                <span>{tr("identity.title")}: </span>
                <strong className="text-sm font-serif-bn">
                  {lang === "bn" ? identity.name_bn || identity.user_id : identity.name_en || identity.user_id}
                </strong>
              </div>
              <span className="text-[#6A6355]">
                {formatPersona(identity.persona, lang)} · {formatDistrict(identity.district, lang)} · {formatIncomeBand(identity.income_band, lang)}
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
  const { tr } = useLanguage();
  const router = useRouter();
  const [goal, setGoal] = useState(initialGoal && initialGoal > 0 ? String(Math.round(initialGoal)) : "");
  const [months, setMonths] = useState(initialMonths && initialMonths >= 1 ? String(initialMonths) : "");
  const ready = Number(goal) > 0 && Number(months) >= 1;

  return (
    <div className="border border-[#D8CFBB] rounded-[6px] p-4 space-y-3 bg-[#F1F4F9]">
      <p className="text-sm font-hind text-[#1E1B16]">
        <span className="text-[#6A6355]">{tr("voice.heard")} </span>
        <strong>{text}</strong>
      </p>
      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1 text-sm font-hind text-[#1E1B16]">
          <span className="text-[#6A6355]">{tr("plan.goal")}</span>
          <input
            type="number"
            min={1}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            className="w-full border border-[#D8CFBB] px-3 py-2 bg-[#FFFFFF] text-[#1E1B16] rounded-[6px] focus:outline-none focus:border-[#0054A6]"
          />
        </label>
        <label className="space-y-1 text-sm font-hind text-[#1E1B16]">
          <span className="text-[#6A6355]">{tr("plan.months")}</span>
          <input
            type="number"
            min={1}
            max={36}
            value={months}
            onChange={(e) => setMonths(e.target.value)}
            className="w-full border border-[#D8CFBB] px-3 py-2 bg-[#FFFFFF] text-[#1E1B16] rounded-[6px] focus:outline-none focus:border-[#0054A6]"
          />
        </label>
      </div>
      {!ready && <p className="text-sm font-hind text-[#6A6355]">{tr("voice.needBoth")}</p>}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          disabled={!ready}
          onClick={() => ready && router.push(`/plan?goal=${Number(goal)}&months=${Number(months)}&prompt=${encodeURIComponent(text)}`)}
          className="min-h-[48px] px-5 bg-[#0054A6] hover:bg-[#003E7E] text-white text-sm font-medium rounded-[6px] disabled:opacity-40 transition-colors"
        >
          {tr("voice.confirm")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-[48px] px-5 bg-[#FFFFFF] border border-[#D8CFBB] text-sm font-medium text-[#1E1B16] hover:border-[#0054A6] rounded-[6px] transition-colors"
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
  const [pending, setPending] = useState<{ text: string; goal: number | null; months: number | null } | null>(null);
  const [homeFeeSaving, setHomeFeeSaving] = useState<number | null>(null);

  useEffect(() => {
    fetchAnomalies({ window_days: 30, limit: 1 })
      .then((res) => {
        if (res.fee_switch?.potential_saving_bdt) {
          setHomeFeeSaving(res.fee_switch.potential_saving_bdt);
        }
      })
      .catch(() => undefined);
  }, []);

  return (
    <>
      <TopBar />

      <main className="space-y-6 md:space-y-8">
        {/* Hero Section: Institutional Header */}
        <header className="border-b border-[#D8CFBB] pb-6 space-y-3">
          <div className="text-xs font-mono text-[#0054A6] tracking-wider uppercase flex items-center gap-2">
            <span>{tr("subTitle")}</span>
            <span>•</span>
            <Stamp variant="blue">{tr("subTitleBadge")}</Stamp>
          </div>
          <h1 className="text-3xl md:text-5xl font-bold font-serif-bn text-[#1E1B16] tracking-tight">
            {tr("appName")}
          </h1>
          <p className="text-base md:text-lg text-[#6A6355] max-w-3xl leading-relaxed font-hind">
            {tr("tagline")}
          </p>
        </header>

        {/* Component 1: Quick input (Input + 56px square Mic + Underlined Suggestion Links) */}
        <section className="bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] p-5 md:p-6 space-y-4">
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

        {/* Component 2: Ledger snapshot */}
        <section className="bg-[#FFFFFF] border border-[#D8CFBB] rounded-[6px] p-5 md:p-6 space-y-4">
          <div className="flex items-center justify-between text-xs font-mono text-[#6A6355] border-b border-[#D8CFBB] pb-2">
            <h2 className="font-serif-bn font-bold text-lg md:text-xl text-[#1E1B16] m-0">
              {lang === "bn" ? "এই মাসের খতিয়ান সারসংক্ষেপ" : "This Month's Ledger Summary"}
            </h2>
            <Stamp variant="blue">{tr("stamp.computed")}</Stamp>
          </div>

          <div className="space-y-3 font-hind text-base">
            {/* Row 1: Total income */}
            <div className="flex items-baseline justify-between">
              <span className="font-medium text-[#1E1B16]">
                {lang === "bn" ? "মোট আয় (নগদ ও ব্যাংক ট্রান্সফার)" : "Total Income (Cash & Bank Transfer)"}
              </span>
              <span className="tab-leader" />
              <span className="font-serif-bn font-bold text-lg text-[#1E1B16] text-right tabular-nums">
                {lang === "bn" ? "৳২২,০০০" : "৳22,000"}
              </span>
            </div>

            {/* Row 2: Regular shop expenses */}
            <div className="flex items-baseline justify-between pt-1">
              <span className="font-medium text-[#1E1B16]">
                {lang === "bn" ? "দোকানের নিয়মিত খরচ ও বিল" : "Regular Shop Expenses & Bills"}
              </span>
              <span className="tab-leader" />
              <span className="font-serif-bn font-bold text-lg text-[#1E1B16] text-right tabular-nums">
                {lang === "bn" ? "৳৫,০০০" : "৳5,000"}
              </span>
            </div>

            {/* Row 3: Fee saving potential */}
            <div className="flex items-baseline justify-between pt-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-[#1E1B16]">
                  {lang === "bn" ? "ফি সাশ্রয় সম্ভাবনা" : "Potential Fee Savings"}
                </span>
                <Stamp variant="blue">
                  {lang === "bn" ? "সিস্টেম হিসাব করেছে" : "Calculated by System"}
                </Stamp>
              </div>
              <span className="tab-leader" />
              <span className="font-serif-bn font-bold text-lg text-[#0054A6] text-right tabular-nums">
                {lang === "bn" ? "+ ৳৩২০" : "+ ৳320"}
              </span>
            </div>

            {/* Accounting double rule: top/bottom 1px #D8CFBB, height 4px */}
            <div className="ledger-double-rule my-3" />

            {/* Total: Remaining potential surplus */}
            <div className="flex items-baseline justify-between pt-1">
              <span className="font-bold text-[#1E1B16] font-serif-bn text-lg md:text-xl">
                {lang === "bn" ? "অবশিষ্ট সম্ভাব্য উদ্বৃত্ত" : "Remaining Potential Surplus"}
              </span>
              <span className="tab-leader" />
              <span className="font-serif-bn font-bold text-2xl md:text-3xl text-[#0054A6] text-right tabular-nums">
                {lang === "bn" ? "৳১৭,৩২০" : "৳17,320"}
              </span>
            </div>
          </div>
        </section>

        {/* Component 3: Pressure-day marker */}
        <section className="space-y-3">
          <div className="flex items-center justify-between border-b border-[#D8CFBB] pb-2">
            <h2 className="font-serif-bn font-bold text-lg md:text-xl text-[#1E1B16] m-0 flex items-center gap-2">
              <MaterialIcon name="calendar_month" size={20} className="text-[#B0431F]" />
              <span>{lang === "bn" ? "টানের দিনসমূহ ও আসন্ন প্রদেয়" : "Upcoming Pressure Days & Dues"}</span>
            </h2>
            <span className="text-xs font-mono text-[#B0431F] font-bold">
              {lang === "bn" ? "সতর্কতা" : "Notice"}
            </span>
          </div>

          <div className="space-y-3">
            {/* Pressure Row 1: 28 March */}
            <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] pressure-marker overflow-hidden flex items-center justify-between p-3.5 md:p-4">
              <div className="flex items-center gap-3">
                <div className="w-2.5 self-stretch -my-3.5 -ml-3.5 mr-1 hatch-pattern-left border-r border-[#D8CFBB]" />
                <div>
                  <div className="font-serif-bn font-bold text-base text-[#1E1B16]">
                    {lang === "bn" ? "২৮ মার্চ — মহাজনের বকেয়া" : "28 March — Wholesaler Due"}
                  </div>
                  <div className="text-xs font-hind text-[#6A6355]">
                    {lang === "bn" ? "মাসের শেষ সপ্তাহের পাইকারি পণ্যের হিসাব" : "Wholesale inventory settlement"}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-right">
                <span className="font-serif-bn font-bold text-lg text-[#1E1B16] tabular-nums">
                  {lang === "bn" ? "৳৩,৫০০" : "৳3,500"}
                </span>
                <span className="badge pressure">
                  {lang === "bn" ? "চাপের দিন" : "Pressure Day"}
                </span>
              </div>
            </div>

            {/* Pressure Row 2: 29 March */}
            <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] pressure-marker overflow-hidden flex items-center justify-between p-3.5 md:p-4">
              <div className="flex items-center gap-3">
                <div className="w-2.5 self-stretch -my-3.5 -ml-3.5 mr-1 hatch-pattern-left border-r border-[#D8CFBB]" />
                <div>
                  <div className="font-serif-bn font-bold text-base text-[#1E1B16]">
                    {lang === "bn" ? "২৯ মার্চ — দোকান ঘরভাড়া" : "29 March — Shop Rent"}
                  </div>
                  <div className="text-xs font-hind text-[#6A6355]">
                    {lang === "bn" ? "মাসিক দোকান ভাড়া বাবদ নির্ধারিত নগদ অর্থ" : "Scheduled monthly shop space rent"}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-right">
                <span className="font-serif-bn font-bold text-lg text-[#1E1B16] tabular-nums">
                  {lang === "bn" ? "৳২,৮০০" : "৳2,800"}
                </span>
                <span className="badge pressure">
                  {lang === "bn" ? "চাপের দিন" : "Pressure Day"}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Component 4: Three-layer explanation */}
        <section className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-5 md:p-6 space-y-4">
          <div className="border-b border-[#D8CFBB] pb-2 flex items-center justify-between">
            <h2 className="font-serif-bn font-bold text-lg text-[#1E1B16] m-0">
              {lang === "bn" ? "হিসাব ও পূর্বাভাসের তিন স্তর" : "Three-Layer Analysis"}
            </h2>
            <Stamp variant="blue">{tr("stamp.easyExplain")}</Stamp>
          </div>

          <div className="divide-y divide-[#D8CFBB] text-sm font-hind">
            {/* Layer 1: Prediction */}
            <div className="py-3 first:pt-0 space-y-1">
              <div className="text-xs font-mono uppercase tracking-wider text-[#0054A6] font-bold">
                {lang === "bn" ? "পূর্বাভাস" : "Prediction"}
              </div>
              <p className="text-base font-medium text-[#1E1B16] leading-relaxed m-0 font-serif-bn">
                {lang === "bn"
                  ? "২৮–৩১ তারিখে আপনার খরচ বেশি হতে পারে।"
                  : "Your expenses may be higher on days 28–31."}
              </p>
            </div>

            {/* Layer 2: Assumed */}
            <div className="py-3 space-y-1">
              <div className="text-xs font-mono uppercase tracking-wider text-[#6A6355] font-bold">
                {lang === "bn" ? "ধরে নেওয়া হয়েছে" : "Assumed"}
              </div>
              <p className="text-sm text-[#1E1B16] leading-relaxed m-0">
                {lang === "bn"
                  ? "আপনার আগের লেনদেনের ধরন অনুযায়ী।"
                  : "Based on your previous transaction patterns."}
              </p>
            </div>

            {/* Layer 3: Reasoning */}
            <div className="py-3 last:pb-0 space-y-1">
              <div className="text-xs font-mono uppercase tracking-wider text-[#6A6355] font-bold">
                {lang === "bn" ? "ব্যাখ্যা" : "Reasoning"}
              </div>
              <p className="text-sm text-[#6A6355] leading-relaxed m-0">
                {lang === "bn"
                  ? "আপনার সাম্প্রতিক খরচ মাসের শেষ দিকে বেশি জমা হয়।"
                  : "Your recent expenditures tend to concentrate towards month-end."}
              </p>
            </div>
          </div>
        </section>

        {/* Component 5: “Do nothing” neutral option */}
        <DoNothingToggle
          costBdt={homeFeeSaving ?? 320}
          outcome={
            lang === "bn"
              ? "৬ মাস পরে সঞ্চয় ৳০ থাকবে। এটাও আপনার সিদ্ধান্ত।"
              : "After 6 months, savings will be ৳0. This is also your decision."
          }
        />

        {/* Component 6: Primary CTA */}
        <section className="space-y-3">
          <Link href="/plan" className="block no-underline">
            <button
              type="button"
              className="w-full h-14 min-h-[56px] bg-[#0054A6] hover:bg-[#003E7E] text-white text-base md:text-lg font-medium rounded-[6px] transition-colors flex items-center justify-center cursor-pointer border-0"
            >
              {lang === "bn" ? "সঞ্চয় পরিকল্পনা শুরু করুন" : "Start your savings plan"}
            </button>
          </Link>
          <div className="text-center pt-1">
            <Link
              href="/forecast"
              className="text-sm font-semibold text-[#0054A6] hover:text-[#003E7E] underline underline-offset-4 decoration-[#0054A6] transition-colors"
            >
              {lang === "bn" ? "আরও বিস্তারিত হিসাব দেখুন" : "See the full breakdown"}
            </Link>
          </div>
        </section>

        {/* Component 7: Legal note */}
        <NotADecisionBanner route="home" />

        {/* Live System Status card */}
        <StatusCard />

        {/* Component 8: Footer */}
        <footer className="border-t border-[#D8CFBB] pt-6 pb-12 flex flex-col sm:flex-row items-center justify-between text-xs text-[#6A6355] gap-3 font-mono">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#1E1B16]">{tr("footer.ledgerSystem")}</span>
          </div>
          <div className="flex items-center gap-2">
            <Stamp variant="muted">{tr("footer.demoDisclaimer")}</Stamp>
          </div>
        </footer>
      </main>
    </>
  );
}
