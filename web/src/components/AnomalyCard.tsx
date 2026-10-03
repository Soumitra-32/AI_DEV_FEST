"use client";

import { useLanguage } from "@/components/LangToggle";
import { formatBDT, formatDigits } from "@/lib/i18n";
import type { AnomalyItem } from "@/lib/api";
import Stamp from "@/components/Stamp";

const CHANNEL_MAP: Record<string, { bn: string; en: string }> = {
  cash_out: { bn: "ক্যাশ-আউট", en: "Cash-Out" },
  p2p: { bn: "অ্যাপ ট্রান্সফার", en: "App Transfer" },
  merchant: { bn: "মার্চেন্ট পেমেন্ট", en: "Merchant" },
  bill_pay: { bn: "বিল পে", en: "Bill Pay" },
};

const ANOMALY_TYPE_MAP: Record<string, { bn: string; en: string }> = {
  amount_anomaly: { bn: "ব্যতিক্রমী পরিমাণ", en: "Amount Outlier" },
  time_anomaly: { bn: "অস্বাভাবিক সময়", en: "Time Outlier" },
  frequency_anomaly: { bn: "ঘন ঘন লেনদেন", en: "Frequency Outlier" },
  channel_anomaly: { bn: "অস্বাভাবিক চ্যানেল", en: "Channel Outlier" },
};

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
            {CHANNEL_MAP[item.channel]?.[lang] ?? item.channel}
          </span>
          <span className="text-xs font-mono text-ink-muted">
            {item.timestamp ? formatDigits(item.timestamp.slice(0, 10), lang) : ""}
          </span>
          <Stamp variant="muted">
            {(item.anomaly_type && ANOMALY_TYPE_MAP[item.anomaly_type]?.[lang]) ||
              (item.anomaly_type ? item.anomaly_type.replace(/_/g, " ") : tr("spending.anomalies"))}
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
