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
    queryKey: ["auth-me", authService.getToken()],
    queryFn: () => authService.getMe(),
    enabled: !!authService.getToken(),
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
    const name = (user as AuthUser).name ?? (user as AuthUser).email ?? (user as AuthUser).sub ?? "User";
    return (
      <div className="flex items-center gap-2">
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
