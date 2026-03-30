import { NavLink } from "react-router-dom";
import {
  Bookmark,
  BookOpen,
  ClipboardList,
  Dna,
  FileSearch,
  FileText,
  FolderOpen,
  Home,
  Settings,
  Shield,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealth } from "@/hooks/useHealth";
import { useTranslation } from "@/hooks/useTranslation";
import { Badge } from "@/components/ui/badge";

const APP_VERSION =
  import.meta.env.VITE_APP_VERSION ?? "dev";

const navItems: { to: string; labelKey: string; icon: typeof Home }[] = [
  { to: "/", labelKey: "dashboard", icon: Home },
  { to: "/literature", labelKey: "literature", icon: BookOpen },
  { to: "/library", labelKey: "library", icon: Bookmark },
  { to: "/notebooks", labelKey: "notebooks", icon: FileText },
  { to: "/pseudonymize", labelKey: "pseudonymize", icon: Shield },
  { to: "/pipelines", labelKey: "pipelines", icon: Settings },
  { to: "/blast", labelKey: "blast", icon: FileSearch },
  { to: "/drs", labelKey: "drs", icon: FolderOpen },
  { to: "/phenopackets", labelKey: "phenopackets", icon: Dna },
  { to: "/phenoflow", labelKey: "phenoflow", icon: Dna },
  { to: "/fair-export", labelKey: "fairExport", icon: Upload },
  { to: "/audit", labelKey: "audit", icon: ClipboardList },
];

interface SidebarProps {
  collapsed: boolean;
}

function SynapticFourLogo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2" />
      <path
        d="M16 8v16M8 16h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="4" fill="currentColor" />
    </svg>
  );
}

export function Sidebar({ collapsed }: SidebarProps) {
  const { data: healthData, isSuccess } = useHealth();
  const { t } = useTranslation();
  const isHealthy = isSuccess && healthData != null;

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-slate-200 bg-surface transition-smooth",
        collapsed ? "w-[72px]" : "w-[260px]"
      )}
      style={{ minWidth: collapsed ? 72 : 260 }}
    >
      {/* Logo + App name */}
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-slate-200 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <SynapticFourLogo className="h-5 w-5" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-muted">Synaptic Four</p>
            <p className="truncate text-sm font-semibold text-text">
              BioResearch Assistant
            </p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto scrollbar-thin p-2">
        {navItems.map(({ to, labelKey, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-smooth",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-text hover:bg-slate-100"
              )
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            {!collapsed && (
              <span className="truncate">{t("nav", labelKey)}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Version + Health */}
      <div className="shrink-0 border-t border-slate-200 p-3">
        {!collapsed && (
          <div className="flex items-center justify-between gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              v{healthData?.version ?? APP_VERSION}
            </Badge>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  isHealthy ? "bg-secondary" : "bg-red-500"
                )}
                aria-label={isHealthy ? "API erreichbar" : "API nicht erreichbar"}
              />
              <span className="text-xs text-muted">
                {isHealthy ? t("status", "online") : t("status", "offline")}
              </span>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="flex flex-col items-center gap-2">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isHealthy ? "bg-secondary" : "bg-red-500"
              )}
              aria-label={isHealthy ? "API erreichbar" : "API nicht erreichbar"}
            />
          </div>
        )}
      </div>

      {/* Attribution */}
      {!collapsed && (
        <div className="px-4 py-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 leading-relaxed">
            Proudly developed by individuals on the autism spectrum in Germany.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            © 2026 Synaptic Four, Stuttgart
          </p>
        </div>
      )}
    </aside>
  );
}
