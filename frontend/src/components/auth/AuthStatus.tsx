import { useQuery } from "@tanstack/react-query";
import { LogIn, LogOut, User } from "lucide-react";
import { authService, type AuthUser } from "@/services/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function AuthStatus() {
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => authService.getStatus(),
  });

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => authService.getMe(),
    enabled: !!status?.auth_enabled,
  });

  if (statusLoading || !status) {
    return null;
  }

  const isDevMode = !status.auth_enabled;
  const isLoggedIn = !!user && (user as AuthUser).sub;

  if (isDevMode) {
    return (
      <Badge
        variant="secondary"
        className="bg-amber-100 text-amber-800 border-amber-200 text-xs"
        title="Auth deaktiviert — Dev-Modus"
      >
        Dev Mode — Auth deaktiviert
      </Badge>
    );
  }

  if (isLoggedIn && user) {
    const u = user as AuthUser;
    const name = u.name ?? u.email ?? u.sub ?? "User";
    const isolationMode = u.isolation_mode ?? "open";
    const teamId = u.team_id ?? "";
    return (
      <div className="flex items-center gap-2">
        {isolationMode === "user" && (
          <span
            className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
            title="Persönliche Ansicht"
          >
            👤 Nur meine Daten
          </span>
        )}
        {isolationMode === "team" && (
          <span
            className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary"
            title={`Team: ${teamId}`}
          >
            👥 Team: {teamId}
          </span>
        )}
        {isolationMode === "open" && (
          <span
            className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800"
            title="Geteilte Ansicht (Demo)"
          >
            ⚠️ Geteilte Ansicht (Demo)
          </span>
        )}
        <span className="flex items-center gap-1.5 text-sm text-slate-700">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
            <User className="h-4 w-4" />
          </span>
          <span className="max-w-[120px] truncate" title={String(name)}>
            {String(name)}
          </span>
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => authService.logout()}
          className="text-slate-600"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    );
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => authService.login()}
      disabled={userLoading}
    >
      <LogIn className="h-4 w-4" />
      Login
    </Button>
  );
}
