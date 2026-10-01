import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { LanguageProvider } from "@/components/LangToggle";

export const metadata: Metadata = {
  title: "Shonchoy Copilot",
  description:
    "Bangla-first coach that explains transactions, plans saving goals, and warns before the month-end squeeze.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="bn">
      <body>
        <LanguageProvider>
          <div className="shell">{children}</div>
        </LanguageProvider>
      </body>
    </html>
  );
}
