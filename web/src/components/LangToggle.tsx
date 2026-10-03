"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
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

  useEffect(() => {
    try {
      const saved = localStorage.getItem("shonchoy_lang") as Lang | null;
      if (saved === "bn" || saved === "en") {
        setLangState(saved);
        document.documentElement.lang = saved;
      } else {
        document.documentElement.lang = DEFAULT_LANG;
      }
    } catch {
      // ignore
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem("shonchoy_lang", next);
      document.documentElement.lang = next;
    } catch {
      // ignore
    }
  }, []);

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
      className="text-xs font-mono flex items-center gap-1.5 select-none"
    >
      <button
        type="button"
        className={`px-2.5 py-1 text-xs font-mono cursor-pointer rounded-none transition-colors ${
          lang === "bn"
            ? "bg-[#1E1B16] text-[#FBF8F1] border border-[#1E1B16] font-bold"
            : "bg-transparent text-ink-muted hover:text-ink border border-rule"
        }`}
        onClick={() => setLang("bn")}
      >
        বাংলা
      </button>
      <button
        type="button"
        className={`px-2.5 py-1 text-xs font-mono cursor-pointer rounded-none transition-colors ${
          lang === "en"
            ? "bg-[#1E1B16] text-[#FBF8F1] border border-[#1E1B16] font-bold"
            : "bg-transparent text-ink-muted hover:text-ink border border-rule"
        }`}
        onClick={() => setLang("en")}
      >
        EN
      </button>
    </div>
  );
}
