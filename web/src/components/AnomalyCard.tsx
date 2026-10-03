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
function formatAnomalyReason(reason: string, lang: "bn" | "en"): string {
  if (!reason) return "";
  if (lang === "en") return reason;

  const m1 = reason.match(/Rapid repeat near ৳([\d,]+)\s*\(([\d,]+)\s*BDT\)\s*—\s*potential transaction splitting under Payment & Settlement Systems Act,\s*2024 monitoring/i);
  if (m1) {
    return `২,০০০ টাকা প্রণোদনা সীমার কাছাকাছি ঘন ঘন লেনদেন (${formatBDT(Number(m1[2].replace(/,/g, "")), "bn")}) — পেমেন্ট অ্যান্ড সেটেলমেন্ট সিস্টেমস আইন, ২০২৪ অনুযায়ী অপব্যবহার প্রতিরোধে নিরীক্ষাধীন।`;
  }

  const m2 = reason.match(/High-value merchant payment\s*\(([\d,]+)\s*BDT\)\s*flagged for unauthorised cash-out review/i);
  if (m2) {
    return `মার্চেন্ট পেমেন্টে বড় অংকের লেনদেন (${formatBDT(Number(m2[1].replace(/,/g, "")), "bn")}) — কিউআর অপব্যবহার বা অননুমোদিত ক্যাশ-আউট প্রতিরোধে সতর্কবার্তা।`;
  }

  const m3 = reason.match(/Another very similar payment within\s*(\d+)\s*minutes/i);
  if (m3) {
    return `${formatDigits(m3[1], "bn")} মিনিটের মধ্যে একই ধরনের আরেকটি লেনদেন।`;
  }

  const m4 = reason.match(/Happened at\s*(\d{2}:\d{2}),\s*outside your usual hours/i);
  if (m4) {
    return `আপনার নিয়মিত সময়ের বাইরে ${formatDigits(m4[1], "bn")} ঘটিকায় এই লেনদেনটি হয়েছে।`;
  }

  const m5 = reason.match(/About\s*([\d.]+)x\s*your own average payment/i);
  if (m5) {
    return `আপনার নিজস্ব গড় লেনদেনের পরিমাণের চেয়ে প্রায় ${formatDigits(m5[1], "bn")} গুণ বেশি।`;
  }

  const m6 = reason.match(/Timing is unusual for you\s*\(([^)]+)\s*is not one of your usual hours\)/i);
  if (m6) {
    return `সময়টি আপনার জন্য অস্বাভাবিক (${formatDigits(m6[1], "bn")} আপনার স্বাভাবিক লেনদেনের সময় নয়)।`;
  }

  return formatDigits(reason, "bn");
}

function formatSuggestedAction(action: string | null | undefined, lang: "bn" | "en"): string {
  if (!action) return "";
  if (lang === "en") return action;
  const lower = action.toLowerCase();
  if (lower.includes("review")) return "পর্যালোচনা করুন";
  if (lower.includes("bangla_qr") || lower.includes("bangla qr")) return "দোকানে বাংলা কিউআরে দিন";
  if (lower.includes("app transfer") || lower.includes("p2p")) return "অ্যাপ ট্রান্সফার করুন";
  if (lower.includes("none")) return "কোনো পদক্ষেপের প্রয়োজন নেই";
  return action;
}

function formatSuggestedChannel(ch: string | null | undefined, lang: "bn" | "en"): string {
  if (!ch) return "";
  if (lang === "en") return ch;
  const lower = ch.toLowerCase();
  if (lower.includes("bangla_qr") || lower.includes("bangla qr")) return "বাংলা কিউআর";
  if (lower.includes("p2p") || lower.includes("app transfer")) return "অ্যাপ ট্রান্সফার";
  if (lower.includes("cash_out") || lower.includes("cash out")) return "ক্যাশ-আউট";
  return ch;
}

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
          {formatAnomalyReason(item.reason, lang)}
        </p>
        <div className="text-xs font-mono text-ink-muted flex items-center gap-2 pt-1">
          <span>{tr("spending.action")}:</span>
          <strong className="text-primaryGreen uppercase tracking-wide">
            {formatSuggestedAction(item.suggested_action, lang)}
          </strong>
          {item.suggested_channel && (
            <span className="text-ink">
              ({formatSuggestedChannel(item.suggested_channel, lang)})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
