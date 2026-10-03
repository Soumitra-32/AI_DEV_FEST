"use client";

import { useLanguage } from "@/components/LangToggle";
import { formatBDT, formatDigits, formatWrittenDate } from "@/lib/i18n";
import type { AnomalyItem } from "@/lib/api";
import Stamp from "@/components/Stamp";

const CHANNEL_MAP: Record<string, { bn: string; en: string }> = {
  cash_out: { bn: "ক্যাশ-আউট", en: "Cash out" },
  p2p: { bn: "অ্যাপে পাঠানো", en: "App transfer" },
  merchant: { bn: "দোকানে পেমেন্ট", en: "Shop payment" },
  bill_pay: { bn: "বিল দেওয়া", en: "Bill payment" },
};

const ANOMALY_TYPE_MAP: Record<string, { bn: string; en: string }> = {
  amount_anomaly: { bn: "অস্বাভাবিক পরিমাণ", en: "Unusual amount" },
  time_anomaly: { bn: "অস্বাভাবিক সময়", en: "Unusual time" },
  frequency_anomaly: { bn: "ঘন ঘন লেনদেন", en: "Too often" },
  channel_anomaly: { bn: "অস্বাভাবিক উপায়", en: "Unusual way" },
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

  const m1 = reason.match(/Rapid repeat near ৳([\d,]+)\s*\(([\d,]+)\s*BDT\)\s*—\s*potential transaction splitting under Payment & Settlement Systems Act,\s*2024 monitoring/i);
  if (m1) {
    const amt = formatBDT(Number(m1[2].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `২,০০০ টাকার সীমার কাছে বারবার লেনদেন (${amt}) — নিয়ম ভাঙা ঠেকাতে নজরে রাখা হচ্ছে।`
      : `Several payments near ${amt} — watched to stop rule-breaking (payment law, 2024).`;
  }

  const m2 = reason.match(/High-value merchant payment\s*\(([\d,]+)\s*BDT\)\s*flagged for unauthorised cash-out review/i);
  if (m2) {
    const amt = formatBDT(Number(m2[1].replace(/,/g, "")), lang);
    return lang === "bn"
      ? `দোকানে বড় অংকের পেমেন্ট (${amt}) — কিউআরের ভুল ব্যবহার বা অনুমতি ছাড়া ক্যাশ-আউট ঠেকাতে দেখা হচ্ছে।`
      : `A big shop payment (${amt}) — checked to stop QR misuse or cash-outs without permission.`;
  }

  const m3 = reason.match(/Another very similar payment within\s*(\d+)\s*minutes/i);
  if (m3) {
    return lang === "bn"
      ? `${formatDigits(m3[1], "bn")} মিনিটের মধ্যে একই ধরনের আরেকটি লেনদেন।`
      : `Another payment just like this one within ${m3[1]} minutes.`;
  }

  const m4 = reason.match(/Happened at\s*(\d{2}:\d{2}),\s*outside your usual hours/i);
  if (m4) {
    return lang === "bn"
      ? `আপনি সাধারণত এই সময়ে লেনদেন করেন না — এবার ${formatDigits(m4[1], "bn")} টায় হয়েছে।`
      : `You don't usually pay at this hour — this one was at ${m4[1]}.`;
  }

  const m5 = reason.match(/About\s*([\d.]+)x\s*your own average payment/i);
  if (m5) {
    return lang === "bn"
      ? `আপনার সাধারণ লেনদেনের চেয়ে প্রায় ${formatDigits(m5[1], "bn")} গুণ বড়।`
      : `About ${m5[1]} times bigger than what you usually pay.`;
  }

  const m6 = reason.match(/Timing is unusual for you\s*\(([^)]+)\s*is not one of your usual hours\)/i);
  if (m6) {
    return lang === "bn"
      ? `এই সময়ে আপনি সাধারণত লেনদেন করেন না।`
      : `You don't usually pay at this time.`;
  }

  return lang === "bn" ? formatDigits(reason, lang) : reason;
}

function formatSuggestedAction(action: string | null | undefined, lang: "bn" | "en"): string {
  if (!action) return "";
  const lower = action.toLowerCase();
  if (lower.includes("review")) return lang === "bn" ? "যাচাই করুন" : "Check it";
  if (lower.includes("bangla_qr") || lower.includes("bangla qr")) return lang === "bn" ? "দোকানে বাংলা কিউআরে দিন" : "Pay by QR";
  if (lower.includes("app transfer") || lower.includes("p2p")) return lang === "bn" ? "অ্যাপে পাঠান" : "Send in the app";
  if (lower.includes("none")) return lang === "bn" ? "কিছু করতে হবে না" : "Nothing to do";
  return action;
}

function formatSuggestedChannel(ch: string | null | undefined, lang: "bn" | "en"): string {
  if (!ch) return "";
  const lower = ch.toLowerCase();
  if (lower.includes("bangla_qr") || lower.includes("bangla qr")) return "বাংলা কিউআর";
  if (lower.includes("p2p") || lower.includes("app transfer")) return lang === "bn" ? "অ্যাপে পাঠানো" : "App transfer";
  if (lower.includes("cash_out") || lower.includes("cash out")) return lang === "bn" ? "ক্যাশ-আউট" : "Cash out";
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
            {item.timestamp ? formatWrittenDate(item.timestamp.slice(0, 10), lang) : ""}
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
