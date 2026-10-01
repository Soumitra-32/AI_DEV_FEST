"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

export default function MetricsPage() {
  const { tr } = useLanguage();
  return (
    <main>
      <h1>{tr("nav.metrics")}</h1>
      <p className="muted">{tr("comingSoon.phase8")}</p>
      <Link href="/">{tr("nav.home")}</Link>
    </main>
  );
}

