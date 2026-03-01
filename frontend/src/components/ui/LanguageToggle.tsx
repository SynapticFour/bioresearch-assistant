import { useCallback, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "preferred_language";
export type AppLanguage = "de" | "en";

export function useLanguage(): {
  language: AppLanguage;
  setLanguage: (lang: AppLanguage) => void;
} {
  const [language, setLanguageState] = useState<AppLanguage>(() => {
    if (typeof window === "undefined") return "de";
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "de" || stored === "en") return stored;
    return "de";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  const setLanguage = useCallback((lang: AppLanguage) => {
    setLanguageState(lang);
  }, []);

  return { language, setLanguage };
}

interface LanguageToggleProps {
  value: AppLanguage;
  onChange: (lang: AppLanguage) => void;
  className?: string;
}

export function LanguageToggle({
  value,
  onChange,
  className,
}: LanguageToggleProps) {
  return (
    <div
      className={cn(
        "flex rounded-lg border border-slate-300 p-0.5",
        className
      )}
      role="group"
      aria-label="Sprache"
    >
      <button
        type="button"
        onClick={() => onChange("de")}
        className={cn(
          "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
          value === "de"
            ? "bg-primary text-primary-foreground"
            : "text-slate-600 hover:bg-slate-100"
        )}
      >
        DE
      </button>
      <button
        type="button"
        onClick={() => onChange("en")}
        className={cn(
          "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
          value === "en"
            ? "bg-primary text-primary-foreground"
            : "text-slate-600 hover:bg-slate-100"
        )}
      >
        EN
      </button>
    </div>
  );
}
