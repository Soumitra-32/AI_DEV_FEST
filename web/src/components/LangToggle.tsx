"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { DEFAULT_LANG, t } from "@/lib/i18n";
import type { Lang, TranslationKey } from "@/lib/i18n";

interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  tr: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: DEFAULT_LANG,
  setLang: () => undefined,
  tr: (key: TranslationKey) => t(DEFAULT_LANG, key),
});

export function useLanguage(): LanguageContextValue {
  return useContext(LanguageContext);
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(DEFAULT_LANG);
  const setLang = useCallback((next: Lang) => setLangState(next), []);
  const value = useMemo<LanguageContextValue>(
    () => ({ lang, setLang, tr: (key: TranslationKey) => t(lang, key) }),
    [lang, setLang],
  );
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

/**
 * Language switch.
 * Elegant ledger typographic switch with 2px solid primaryGreen underline under active language.
 */
export default function LangToggle() {
  const { lang, setLang, tr } = useLanguage();

  return (
    <div
      role="group"
      aria-label={tr("lang.switchTo")}
      className="text-xs font-mono text-ink flex items-center gap-2 select-none"
    >
      <button
        type="button"
        className={`bg-transparent border-0 p-0 cursor-pointer text-xs font-mono ${
          lang === "bn"
            ? "font-bold text-primaryGreen pb-0.5 border-b-2 border-primaryGreen"
            : "text-ink-muted hover:text-ink"
        }`}
        onClick={() => setLang("bn")}
      >
        বাংলা
      </button>
      <span className="text-rule">·</span>
      <button
        type="button"
        className={`bg-transparent border-0 p-0 cursor-pointer text-xs font-mono ${
          lang === "en"
            ? "font-bold text-primaryGreen pb-0.5 border-b-2 border-primaryGreen"
            : "text-ink-muted hover:text-ink"
        }`}
        onClick={() => setLang("en")}
      >
        EN
      </button>
    </div>
  );
}
