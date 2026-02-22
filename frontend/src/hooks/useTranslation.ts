import { useState, useCallback } from "react"
import { translations } from "../i18n"

export type Language = "de" | "en"

const STORAGE_KEY = "bioresearch_language"

export function useTranslation() {
  const [language, setLanguage] = useState<Language>(
    (localStorage.getItem(STORAGE_KEY) as Language) || "de"
  )

  const t = useCallback(
    (section: string, key: string): string => {
      const lang = translations[language] as Record<string, Record<string, string>>
      return lang?.[section]?.[key] ?? key
    },
    [language]
  )

  const changeLanguage = useCallback((lang: Language) => {
    setLanguage(lang)
    localStorage.setItem(STORAGE_KEY, lang)
  }, [])

  return { t, language, changeLanguage }
}
