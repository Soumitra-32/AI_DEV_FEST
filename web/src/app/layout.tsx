import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { LanguageProvider } from "@/components/LangToggle";
import BottomNav from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "সঞ্চয় Copilot — Institutional Khata (upay)",
  description:
    "A flat, zero-elevation, high-readability Bangladeshi fintech ledger UI inspired by upay. Calm, trustworthy, Bangla-first institutional digital khata.",
  openGraph: {
    title: "সঞ্চয় Copilot — Institutional Khata (upay)",
    description:
      "Bangla-first institutional financial coach and digital ledger system inspired by upay.",
    locale: "bn_BD",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="bn">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700&family=Noto+Serif+Bengali:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
        />
      </head>
      <body className="min-h-screen bg-surface-white text-ink font-hind antialiased">
        <LanguageProvider>
          <div className="shell">{children}</div>
          <BottomNav />
        </LanguageProvider>
      </body>
    </html>
  );
}
