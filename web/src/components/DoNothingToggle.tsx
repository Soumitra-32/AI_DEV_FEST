"use client";

import { useState } from "react";
import { useLanguage } from "@/components/LangToggle";
import { formatBDT } from "@/lib/i18n";

interface DoNothingToggleProps {
  costBdt?: number | null;
}

/**
 * The consent pattern: every suggestion ships with an explicit
 * "do nothing" option whose cost is stated up front.
 */
export default function DoNothingToggle({ costBdt }: DoNothingToggleProps) {
  const { lang, tr } = useLanguage();
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState(false);
  return (
    <div className="card">
      <h3>{tr("common.doNothing")}</h3>
      <p className="muted">{tr("common.doNothingHint")}</p>
      {typeof costBdt === "number" ? (
        <p>
          {tr("common.doNothingCost")}: <strong>{formatBDT(costBdt, lang)}</strong>
        </p>
      ) : null}
      {!open ? (
        <button type="button" onClick={() => setOpen(true)}>
          {tr("common.doNothing")}
        </button>
      ) : !chosen ? (
        <div>
          <button type="button" className="primary" onClick={() => setChosen(true)}>
            {tr("common.doNothingConfirm")}
          </button>{" "}
          <button type="button" onClick={() => setOpen(false)}>
            {tr("common.doNothingDismiss")}
          </button>
        </div>
      ) : (
        <p role="status">{tr("common.doNothingChosen")}</p>
      )}
    </div>
  );
}
