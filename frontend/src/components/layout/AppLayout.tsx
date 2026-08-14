import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { authService } from "@/services/auth";

export function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [authGate, setAuthGate] = useState<"loading" | "ok" | "login">("loading");
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await authService.getStatus();
        if (!status.auth_enabled) {
          if (!cancelled) setAuthGate("ok");
          return;
        }
        const me = await authService.getMe();
        if (!cancelled) setAuthGate(me?.sub ? "ok" : "login");
      } catch {
        if (!cancelled) setAuthGate("login");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => !prev);
  };

  if (authGate === "loading") {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-slate-500">
        Sitzung wird geprüft …
      </div>
    );
  }
  if (authGate === "login") {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar collapsed={sidebarCollapsed} />
      <div className="flex flex-1 flex-col min-w-0">
        <Header
          onMenuClick={toggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
        />
        <main className="flex-1 overflow-auto bg-background p-6 scrollbar-thin">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
