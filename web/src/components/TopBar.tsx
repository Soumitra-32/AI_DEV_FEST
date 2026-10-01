"use client";

import Link from "next/link";
import LangToggle, { useLanguage } from "@/components/LangToggle";

/**
 * Shared navigation, used by every screen so the language toggle and the route
 * list never drift between pages.
 */
export default function TopBar() {
const { tr } = useLanguage();
  return (
    <header className="topbar">
      <strong>{tr("appName")}</strong>
      <nav>
        <Link href="/">{tr("nav.home")}</Link>
        <Link href="/plan">{tr("nav.plan")}</Link>
        <Link href="/forecast">{tr("nav.forecast")}</Link>
        <Link href="/spending">{tr("nav.spending")}</Link>
        <Link href="/tips">{tr("nav.tips")}</Link>
        <Link href="/signal">{tr("nav.signal")}</Link>
        <Link href="/metrics">{tr("nav.metrics")}</Link>
      </nav>
      <LangToggle />
    </header>
  );
}