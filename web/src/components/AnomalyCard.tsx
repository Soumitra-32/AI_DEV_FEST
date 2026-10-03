"use client";

import { useLanguage } from "@/components/LangToggle";
import { formatBDT } from "@/lib/i18n";
import type { AnomalyItem } from "@/lib/api";
import Stamp from "@/components/Stamp";

interface AnomalyCardProps {
  item: AnomalyItem;
}

/**
 * Section 8 / D2: Khata Anomaly Row
 * A ruled row with a 2px left brick-red indicator rule, dotted leader to amount,
 * tabular numerals, and authentic ink-muted stamp. No card boxes.
 */
export default function AnomalyCard({ item }: AnomalyCardProps) {
  const { lang, tr } = useLanguage();

  return (
    <div className="border-l-2 border-brickRed border-b border-rule/60 bg-surface/40 px-3.5 py-3 hover:bg-surface/80 transition-colors space-y-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-ink-muted uppercase">
            {item.channel}
          </span>
          <span className="text-xs font-mono text-ink-muted">
            {item.timestamp ? item.timestamp.slice(0, 10) : ""}
          </span>
          <Stamp variant="muted">
            {item.anomaly_type ? item.anomaly_type.replace(/_/g, " ") : tr("spending.anomalies")}
          </Stamp>
        </div>

        <div className="flex items-baseline gap-2">
          <span className="font-serif-bn font-bold text-lg text-brickRed tabular-nums">
            {formatBDT(item.amount_bdt, lang)}
          </span>
        </div>
      </div>

      <div className="text-sm font-hind">
        <p className="text-ink leading-relaxed font-medium">
          {item.reason}
        </p>
        <div className="text-xs font-mono text-ink-muted flex items-center gap-2 pt-1">
          <span>{tr("spending.action")}:</span>
          <strong className="text-primaryGreen uppercase tracking-wide">
            {item.suggested_action}
          </strong>
          {item.suggested_channel && (
            <span className="text-ink">
              ({item.suggested_channel})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
