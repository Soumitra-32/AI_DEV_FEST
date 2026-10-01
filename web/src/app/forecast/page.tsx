"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

export default function ForecastPage() {
  const { tr } = useLanguage();
  return (
    <main>
      <h1>{tr("nav.forecast")}</h1>
      <p className="muted">{tr("comingSoon.phase3")}</p>
      <Link href="/">{tr("nav.home")}</Link>
    </main>
  );
}

