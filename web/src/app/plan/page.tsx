"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

export default function PlanPage() {
  const { tr } = useLanguage();
  return (
    <main>
      <h1>{tr("nav.plan")}</h1>
      <p className="muted">{tr("comingSoon.phase3")}</p>
      <Link href="/">{tr("nav.home")}</Link>
    </main>
  );
}

