"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import DoNothingToggle from "@/components/DoNothingToggle";
import InsightCard from "@/components/InsightCard";
import TopBar from "@/components/TopBar";
import { useLanguage } from "@/components/LangToggle";
import { fetchHealth, fetchIdentity } from "@/lib/api";
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
    <InsightCard title={tr("status.title")}>
      {status === "checking" && <p>{tr("status.checking")}</p>}
      {status === "unreachable" && (
        <>
          <p>
            <span className="badge danger">{tr("status.apiUnreachable")}</span>
          </p>
          <p className="muted">{tr("status.apiHint")}</p>
        </>
      )}
      {status === "ok" && health && (
        <>
          <p>
            <span className="badge">{tr("status.apiReachable")}</span>{" "}
            <span className="muted">
              {tr("status.serviceVersion")}: {health.version}
            </span>
            {health.status === "degraded" && (
              <span className="badge warn"> {tr("status.degraded")}</span>
            )}
          </p>
          <p>
            {tr("status.database")}:{" "}
            {health.database.available
              ? tr("status.databaseReady")
              : tr("status.databaseMissing")}
            {" · "}
            {tr("status.users")}: {formatInteger(health.database.users, lang)}{" "}
            {" · "}
            {tr("status.transactions")}:{" "}
            {formatInteger(health.database.transactions, lang)}
          </p>
          <p className="muted">
            {tr("status.features")}:{" "}
            {Object.entries(health.features)
              .filter(([, on]) => on)
              .map(([name]) => name)
              .join(", ")}
          </p>
        </>
      )}
      {identity && (
        <p>
          {tr("identity.title")}:{" "}
          <strong>{lang === "bn" ? identity.name_bn : identity.name_en}</strong>{" "}
          <span className="muted">
            ({tr("identity.persona")}: {identity.persona} ·{" "}
            {tr("identity.district")}: {identity.district} ·{" "}
            {tr("identity.incomeBand")}: {identity.income_band})
          </span>
        </p>
      )}
    </InsightCard>
  );
}

function ComingSoon({ phaseKey, href }: { phaseKey: "comingSoon.phase3" | "comingSoon.phase5" | "comingSoon.phase7" | "comingSoon.phase8"; href: string }) {
  const { tr } = useLanguage();
  return (
    <div className="card">
      <h3>{tr(phaseKey)}</h3>
      <p className="muted">{tr("comingSoon.title")}</p>
      <Link href={href}>{href}</Link>
    </div>
  );
}

export default function HomePage() {
  const { tr } = useLanguage();
  return (
    <>
      <TopBar />
      <main>
        <h1>{tr("appName")}</h1>
        <p>{tr("tagline")}</p>
        <StatusCard />
        <InsightCard title={tr("home.next.title")}>
          <p>{tr("home.next.body")}</p>
        </InsightCard>
        <InsightCard title={tr("plan.title")}>
          <p>{tr("plan.subtitle")}</p>
          <p>
            <Link href="/plan">{tr("nav.plan")}</Link> ·{" "}
            <Link href="/forecast">{tr("nav.forecast")}</Link>
          </p>
        </InsightCard>
        <ComingSoon phaseKey="comingSoon.phase5" href="/spending" />
        <ComingSoon phaseKey="comingSoon.phase7" href="/tips" />
        <ComingSoon phaseKey="comingSoon.phase8" href="/metrics" />
        <DoNothingToggle />
      </main>
    </>
  );
}

