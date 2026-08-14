import { useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { authService, type AuthStatusResponse } from "@/services/auth";
import { Button } from "@/components/ui/button";

function MicrosoftIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 23 23" aria-hidden>
      <path fill="#f35325" d="M1 1h10v10H1z" />
      <path fill="#81bc06" d="M12 1h10v10H12z" />
      <path fill="#05a6f0" d="M1 12h10v10H1z" />
      <path fill="#ffba08" d="M12 12h10v10H12z" />
    </svg>
  );
}

export function LoginPage() {
  const [authStatus, setAuthStatus] = useState<AuthStatusResponse | null>(null);

  useEffect(() => {
    authService.getStatus().then(setAuthStatus).catch(() => setAuthStatus(null));
  }, []);

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
          Synaptic Four — Sicher. Standards-orientiert. Open.
        </p>

        {authStatus?.mode === "development" && (
          <div className="dev-banner mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">⚠️ Dev-Modus — Authentifizierung deaktiviert</p>
            <Button
              className="mt-3 w-full"
              variant="outline"
              onClick={() => (window.location.href = "/")}
            >
              Ohne Login fortfahren
            </Button>
          </div>
        )}

        {authStatus?.mode === "production" && (
          <div className="login-buttons space-y-3">
            <Button
              className="w-full"
              size="lg"
              onClick={() => authService.loginWithProvider("oidc")}
            >
              🔐 Login mit Institution (OIDC / DFN-AAI / Keycloak)
            </Button>
            <Button
              variant="outline"
              className="w-full border-slate-300 bg-white hover:bg-slate-50"
              size="lg"
              onClick={() => authService.loginWithProvider("microsoft")}
            >
              <MicrosoftIcon />
              <span className="ml-2">Login mit Microsoft Entra ID</span>
            </Button>
            <p className="hint mt-4 text-center text-xs text-slate-500">
              Uniklinik-Standard: institutioneller IdP (Keycloak, DFN-AAI, Entra ID).
              US-IdPs (Google) sind absichtlich nicht als Primärlogin angeboten.
            </p>
          </div>
        )}

        {!authStatus && (
          <p className="text-center text-sm text-slate-500">Lade …</p>
        )}

        <footer className="mt-8 space-y-1 border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
          <p>
            Proudly developed by individuals on the autism spectrum in Germany.
          </p>
          <p className="max-w-xl mx-auto text-[11px] text-slate-500">
            BioResearch Assistant unterstützt Forschung und Dokumentation und ersetzt weder
            medizinische Entscheidungen noch rechtliche Beratung.
          </p>
        </footer>
      </div>
    </div>
  );
}
