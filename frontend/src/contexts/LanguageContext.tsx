import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { translations } from "../i18n";

export type Language = "de" | "en";
const STORAGE_KEY = "bioresearch_language";

interface LanguageContextType {
  language: Language;
  changeLanguage: (lang: Language) => void;
  t: (section: string, key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(
    (localStorage.getItem(STORAGE_KEY) as Language) || "de"
  );

  const changeLanguage = useCallback((lang: Language) => {
    setLanguage(lang);
    localStorage.setItem(STORAGE_KEY, lang);
  }, []);

  const t = useCallback(
    (section: string, key: string): string => {
      const lang = translations[language] as Record<
        string,
        Record<string, string>
      >;
      return lang?.[section]?.[key] ?? key;
    },
    [language]
  );

  return (
    <LanguageContext.Provider value={{ language, changeLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx)
    throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
