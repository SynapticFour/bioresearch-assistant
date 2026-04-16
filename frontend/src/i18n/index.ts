export const translations = {
  de: {
    literature: {
      title: "Literature Mining",
      search: "Suchen",
      save: "Speichern",
      noResults: "Keine Ergebnisse gefunden",
    },
    pseudonymize: {
      title: "Pseudonymisierung",
      analyze: "Analysieren",
      language: "Sprache",
    },
    nav: {
      dashboard: "Dashboard",
      literature: "Literatur",
      library: "Bibliothek",
      notebooks: "Notizbuch",
      pseudonymize: "Pseudonymisierung",
      pipelines: "Pipelines",
      blast: "BLAST",
      workflows: "Workflows",
      drs: "DRS Files",
      phenopackets: "Phenopackets",
      fairExport: "FAIR Export",
      consentTracker: "Consent",
      miiExport: "MII Export",
      audit: "Audit Log",
    },
    status: {
      online: "Online",
      offline: "Offline",
      error: "Fehler",
    },
  },
  en: {
    literature: {
      title: "Literature Mining",
      search: "Search",
      save: "Save",
      noResults: "No results found",
    },
    pseudonymize: {
      title: "Pseudonymization",
      analyze: "Analyze",
      language: "Language",
    },
    nav: {
      dashboard: "Dashboard",
      literature: "Literature",
      library: "Library",
      notebooks: "Notebook",
      pseudonymize: "Pseudonymization",
      pipelines: "Pipelines",
      blast: "BLAST",
      workflows: "Workflows",
      drs: "DRS Files",
      phenopackets: "Phenopackets",
      fairExport: "FAIR Export",
      consentTracker: "Consent",
      miiExport: "MII Export",
      audit: "Audit Log",
    },
    status: {
      online: "Online",
      offline: "Offline",
      error: "Error",
    },
  },
};

export type Language = "de" | "en";
export type TranslationKey = keyof (typeof translations)["de"];
