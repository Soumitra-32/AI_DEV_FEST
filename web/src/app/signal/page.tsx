"use client";

import Link from "next/link";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import { useLanguage } from "@/components/LangToggle";

export default function SignalPage() {
  const { tr } = useLanguage();
  return (
    <main>
      <NotADecisionBanner />
      <h1>{tr("nav.signal")}</h1>
      <p className="muted">{tr("comingSoon.phase7")}</p>
      <Link href="/">{tr("nav.home")}</Link>
    </main>
  );
}

