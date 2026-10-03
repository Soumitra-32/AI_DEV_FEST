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
 * Language switch: plain text “বাংলা · EN” with 2px upay-blue underline on active. No pill toggle.
 */
export default function LangToggle() {
  const { lang, setLang, tr } = useLanguage();

  return (
    <div
      role="group"
      aria-label={tr("lang.switchTo")}
      className="text-sm font-hind font-medium flex items-center gap-1.5 select-none"
    >
      <button
        type="button"
        className={`bg-transparent border-0 min-h-[48px] px-1.5 py-1 text-sm font-medium cursor-pointer transition-colors ${
          lang === "bn"
            ? "text-[#0054A6] font-bold border-b-2 border-[#0054A6]"
            : "text-[#6A6355] hover:text-[#1E1B16] border-b-2 border-transparent"
        }`}
        onClick={() => setLang("bn")}
      >
        বাংলা
      </button>
      <span className="text-[#6A6355] select-none text-xs">·</span>
      <button
        type="button"
        className={`bg-transparent border-0 min-h-[48px] px-1.5 py-1 text-sm font-medium cursor-pointer transition-colors ${
          lang === "en"
            ? "text-[#0054A6] font-bold border-b-2 border-[#0054A6]"
            : "text-[#6A6355] hover:text-[#1E1B16] border-b-2 border-transparent"
        }`}
        onClick={() => setLang("en")}
      >
        EN
      </button>
    </div>
  );
}
