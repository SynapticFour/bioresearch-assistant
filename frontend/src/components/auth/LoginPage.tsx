import { useQuery } from "@tanstack/react-query";
import { LogIn, Shield } from "lucide-react";
import { authService } from "@/services/auth";
import { Button } from "@/components/ui/button";

export function LoginPage() {
  const { data: status, isLoading, error } = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => authService.getStatus(),
  });

  const isDevMode = status && !status.auth_enabled;
  const providers = status?.supported_providers ?? [];

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex justify-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Shield className="h-8 w-8" />
          </div>
        </div>
        <h1 className="mb-2 text-center text-xl font-semibold text-slate-800">
          BioResearch Assistant
        </h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          Anmelden mit OIDC Provider
        </p>

        {isLoading && (
          <p className="text-center text-sm text-slate-500">Lade …</p>
        )}
        {error && (
          <p className="mb-4 text-center text-sm text-red-600">
            Konfiguration konnte nicht geladen werden.
          </p>
        )}

        {isDevMode && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">Dev-Modus — Auth deaktiviert</p>
            <p className="mt-1 text-amber-800">
              OIDC ist nicht konfiguriert. Alle Endpunkte sind ohne Login
              nutzbar. Für Produktion OIDC_ISSUER und OIDC_CLIENT_ID in .env
              setzen.
            </p>
          </div>
        )}

        {status?.auth_enabled && (
          <>
            <p className="mb-2 text-xs text-slate-500">
              Unterstützte Provider: {providers.join(", ")}
            </p>
            <Button
              className="w-full"
              size="lg"
              onClick={() => authService.login()}
            >
              <LogIn className="mr-2 h-5 w-5" />
              Login with OIDC Provider
            </Button>
          </>
        )}

        {!isLoading && !status?.auth_enabled && (
          <p className="text-center text-sm text-slate-500">
            Kein Login nötig. Weiter zur App.
          </p>
        )}
      </div>
    </div>
  );
}
