import { useLocation } from "react-router-dom";
import { Bell, Menu, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/hooks/useTranslation";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { Badge } from "@/components/ui/badge";

function getRouteLabelKey(pathname: string): string {
  if (pathname === "/") return "dashboard";
  const segment = pathname.slice(1).split("/")[0];
  const keyMap: Record<string, string> = {
    literature: "literature",
    library: "library",
    pseudonymize: "pseudonymize",
    pipelines: "pipelines",
    blast: "blast",
    workflows: "workflows",
    drs: "drs",
    audit: "audit",
  };
  return keyMap[segment] ?? "dashboard";
}

interface HeaderProps {
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
}

function Breadcrumb() {
  const location = useLocation();
  const { t } = useTranslation();
  const pathname = location.pathname;
  const labelKey = getRouteLabelKey(pathname);
  const label = t("nav", labelKey);

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm">
      <span className="text-muted">BioResearch</span>
      <span className="text-muted">/</span>
      <span className="font-medium text-text">{label}</span>
    </nav>
  );
}

export function Header({ onMenuClick, sidebarCollapsed }: HeaderProps) {
  const { language, changeLanguage } = useTranslation();
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-surface px-4 shadow-sm transition-smooth">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onMenuClick}
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg text-text transition-smooth hover:bg-slate-100",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          )}
          aria-label={sidebarCollapsed ? "Sidebar öffnen" : "Sidebar schließen"}
        >
          <Menu className="h-5 w-5" />
        </button>
        <Breadcrumb />
      </div>

      <div className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className="font-mono text-xs"
          aria-label={`Sprache: ${language === "de" ? "Deutsch" : "English"}`}
        >
          {language === "de" ? "DE" : "EN"}
        </Badge>
        <LanguageToggle
          value={language}
          onChange={changeLanguage}
          className="w-24"
        />
        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-text transition-smooth hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Benachrichtigungen"
        >
          <Bell className="h-5 w-5" />
        </button>
        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground transition-smooth hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Benutzer-Menü"
        >
          <User className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
