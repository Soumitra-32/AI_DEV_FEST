"use client";

import type { ReactNode } from "react";
import { useLanguage } from "@/components/LangToggle";
import type { Provenance } from "@/lib/api";

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
    <section className="bg-surface border border-rule rounded-ledger mb-6 overflow-hidden">
      {/* Title & Main Content */}
      {(title || children) && (
        <div className="p-4 md:p-6 space-y-3">
          {title && (
            <div className="flex items-baseline justify-between border-b border-rule pb-2">
              <h2 className="font-serif-bn font-bold text-xl text-ink m-0">{title}</h2>
              <span className="text-xs font-mono text-ink-muted uppercase">
                {tr("stamp.verified")}
              </span>
            </div>
          )}
          {children}
        </div>
      )}

      {/* 3-Layer Explanation Block */}
      {provenance && (
        <div className="border-t border-rule divide-y divide-rule bg-surface">
          {/* Layer 1: Prediction */}
          <div className="p-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-semibold">
                {tr("common.prediction")}
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 border border-ink-muted rounded-stamp text-[11px] font-mono text-ink">
                <span className="w-1.5 h-1.5 bg-ink-muted inline-block" />
                <span>{tr("stamp.computed")}</span>
              </span>
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
