"use client";

import { useLanguage } from "@/components/LangToggle";
import { formatBDT } from "@/lib/i18n";
import type { AnomalyItem } from "@/lib/api";

interface AnomalyCardProps {
  item: AnomalyItem;
}

/**
 * Section 8: Warning & Anomaly Marker
 * 3px Brick Red Left Border, pure flat, no solid red background fill.
 */
export default function AnomalyCard({ item }: AnomalyCardProps) {
  const { lang, tr } = useLanguage();

  return (
    <div className="bg-surface border-l-4 border-brickRed border-t border-r border-b border-rule rounded-ledger p-4 md:p-5 mb-4 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-2">
        <div className="flex items-center gap-2">
          <span className="font-serif-bn font-bold text-xl text-brickRed">
            {formatBDT(item.amount_bdt, lang)}
          </span>
          <span className="text-xs font-mono text-ink-muted uppercase">
            {item.channel}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-ink-muted">
            {item.timestamp ? item.timestamp.slice(0, 10) : ""}
          </span>
          <span className="border border-brickRed rounded-stamp px-2 py-0.5 text-[10px] font-mono text-brickRed uppercase">
            {item.anomaly_type ? item.anomaly_type.replace(/_/g, " ") : tr("spending.anomalies")}
          </span>
        </div>
      </div>

      <div className="space-y-1 text-sm font-hind">
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
