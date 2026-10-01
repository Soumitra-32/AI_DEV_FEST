"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

export default function SpendingPage() {
  const { tr } = useLanguage();
  return (
    <main>
      <h1>{tr("nav.spending")}</h1>
      <p className="muted">{tr("comingSoon.phase5")}</p>
      <Link href="/">{tr("nav.home")}</Link>
    </main>
  );
}

