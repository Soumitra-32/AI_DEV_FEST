import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { LanguageProvider } from "@/components/LangToggle";
import BottomNav from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "সঞ্চয় Copilot — খতিয়ান ও হিসাবের খাতা",
  description:
    "দোকানের খাঁটি লাল-বাঁধানো জাবেদা ও খতিয়ান খাতার নান্দনিকতা। সম্পূর্ণ ফ্ল্যাট, শান্ত, উচ্চ পঠনযোগ্যতা এবং শূন্য অলঙ্করণ সহ সাধারণ মানুষের জন্য নির্মিত ডিজিটাল লেজার।",
  openGraph: {
    title: "সঞ্চয় Copilot — খতিয়ান ও হিসাবের খাতা",
    description:
      "Bangla-first financial coach and digital ledger system built for Bangladeshi shopkeepers and households.",
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
          href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Noto+Serif+Bengali:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-paper text-ink font-hind antialiased">
        <LanguageProvider>
          <div className="shell">{children}</div>
          <BottomNav />
        </LanguageProvider>
      </body>
    </html>
  );
}
