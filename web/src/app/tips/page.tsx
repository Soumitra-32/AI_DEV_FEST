"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LangToggle";

export default function TipsPage() {
  const { tr } = useLanguage();
  return (
    <main>
      <h1>{tr("nav.tips")}</h1>
      <p className="muted">{tr("comingSoon.phase7")}</p>
      <Link href="/">{tr("nav.home")}</Link>
    </main>
  );
}

