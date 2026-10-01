"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { DEFAULT_LANG, LANGUAGES, t } from "@/lib/i18n";
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
 * Language switch. Plain buttons (not a select) so the choice is obvious even
 * for users who have never changed a language setting before.
 */
export default function LangToggle() {
  const { lang, setLang, tr } = useLanguage();
  return (
    <div role="group" aria-label={tr("lang.switchTo")}>
      {LANGUAGES.map((option) => (
        <button
          key={option.code}
          type="button"
          aria-pressed={lang === option.code}
          onClick={() => setLang(option.code)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
