import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/** OIDC lands here after the API set the httpOnly session cookie. */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate("/", { replace: true });
  }, [navigate]);
  return (
    <p className="p-8 text-center text-sm text-slate-600">Anmeldung wird abgeschlossen …</p>
  );
}
