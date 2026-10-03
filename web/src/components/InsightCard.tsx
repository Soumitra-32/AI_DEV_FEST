"use client";

import type { ReactNode } from "react";
import { useLanguage } from "@/components/LangToggle";
import type { Provenance } from "@/lib/api";
import Stamp from "@/components/Stamp";

interface InsightCardProps {
  title?: string;
  children?: ReactNode;
  provenance?: Provenance | null;
}

/**
 * Section 6: Three-layer Explanation Block & Ledger Insight Card
 * Separates Prediction / Assumption / Explanation with rubber stamps.
 * Pure flat design on #FBF8F1 surface with #D8CFBB rule borders.
 */
export default function InsightCard({ title, children, provenance }: InsightCardProps) {
  const { tr } = useLanguage();

  return (
    <section className="border-t border-b border-rule bg-surface/50 mb-6">
      {/* Title & Main Content */}
      {(title || children) && (
        <div className="p-4 md:p-6 space-y-3">
          {title && (
            <div className="flex items-baseline justify-between border-b border-rule pb-2">
              <h2 className="font-serif-bn font-bold text-xl text-ink m-0">{title}</h2>
              <Stamp variant="muted">{tr("stamp.verified")}</Stamp>
            </div>
          )}
          {children}
        </div>
      )}

      {/* 3-Layer Explanation Block */}
      {provenance && (
        <div className="border-t border-rule divide-y divide-rule/60 bg-surface/30">
          {/* Layer 1: Prediction */}
          <div className="p-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-semibold">
                {tr("common.prediction")}
              </span>
              <Stamp variant="ink">{tr("stamp.computed")}</Stamp>
            </div>
            <p className="font-serif-bn text-base md:text-lg font-bold text-ink leading-snug">
              {provenance.prediction}
            </p>
          </div>

          {/* Layer 2: Assumption */}
          <div className="p-4 space-y-1">
            <div className="text-xs font-mono uppercase tracking-wider text-ink-muted font-semibold">
              {tr("common.assumption")}
            </div>
            <p className="text-[15px] text-ink leading-relaxed font-hind">
              {provenance.assumption}
            </p>
          </div>

          {/* Layer 3: Explanation */}
          <div className="p-4 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-semibold">
                {tr("common.explanation")}
              </span>
              <span className="text-xs font-mono text-ink-muted">
                [{tr("stamp.easyExplain")}]
              </span>
            </div>
            <p className="text-[15px] text-ink-muted leading-relaxed font-hind">
              {provenance.explanation}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
