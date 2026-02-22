import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlaskConical } from "lucide-react";

export function LoginPage() {
  const navigate = useNavigate();
  const [token, setToken] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (token.trim()) {
      localStorage.setItem("bioresearch_token", token.trim());
    }
    navigate("/", { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-surface p-6 shadow-md">
        <div className="mb-6 flex justify-center">
          <FlaskConical className="h-12 w-12 text-primary" />
        </div>
        <h1 className="mb-2 text-center text-xl font-semibold text-text">
          BioResearch Assistant
        </h1>
        <p className="mb-6 text-center text-sm text-muted">
          On-Premise KI für Forschung
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="token"
              className="mb-1 block text-sm font-medium text-text"
            >
              JWT Token (optional)
            </label>
            <input
              id="token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-text focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Leer lassen wenn kein Auth"
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            Weiter
          </button>
        </form>
      </div>
    </div>
  );
}
