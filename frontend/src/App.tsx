import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { ToastProvider } from "@/contexts/ToastContext";
import { AuditPage } from "@/pages/AuditPage";
import { BlastPage } from "@/pages/BlastPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DRSPage } from "@/pages/DRSPage";
import { LibraryPage } from "@/pages/LibraryPage";
import { LiteraturePage } from "@/pages/LiteraturePage";
import { PhenopacketsPage } from "@/pages/PhenopacketsPage";
import { LoginPage } from "@/components/auth/LoginPage";
import { PipelinesPage } from "@/pages/PipelinesPage";
import { PseudonymizePage } from "@/pages/PseudonymizePage";
import { WorkflowsPage } from "@/pages/WorkflowsPage";

function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/literature" element={<LiteraturePage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/pseudonymize" element={<PseudonymizePage />} />
          <Route path="/pipelines" element={<PipelinesPage />} />
          <Route path="/blast" element={<BlastPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/drs" element={<DRSPage />} />
          <Route path="/phenopackets" element={<PhenopacketsPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Route>
      </Routes>
    </ToastProvider>
  );
}

export default App;
