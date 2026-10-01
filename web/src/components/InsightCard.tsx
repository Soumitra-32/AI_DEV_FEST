"use client";

import type { ReactNode } from "react";
import { useLanguage } from "@/components/LangToggle";
import type { Provenance } from "@/lib/api";

interface InsightCardProps {
  title: string;
  children: ReactNode;
  provenance?: Provenance | null;
}

/**
 * Every card separates Prediction / Assumption / Explanation: what we think,
 * what we assumed, and why — plus which layer produced the number.
 */
export default function InsightCard({ title, children, provenance }: InsightCardProps) {
  const { tr } = useLanguage();
  return (
    <section className="card">
      <h2>{title}</h2>
      <div>{children}</div>
      {provenance ? (
        <dl className="provenance">
          <div>
            <dt>{tr("common.prediction")}</dt>
            <dd>{provenance.prediction}</dd>
          </div>
          <div>
            <dt>{tr("common.assumption")}</dt>
            <dd>{provenance.assumption}</dd>
          </div>
          <div>
            <dt>{tr("common.explanation")}</dt>
            <dd>{provenance.explanation}</dd>
          </div>
          <div>
            <dt>{tr("common.source")}</dt>
            <dd>
              <span className="badge">{provenance.source}</span>
            </dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
