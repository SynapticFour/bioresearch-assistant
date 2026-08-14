import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { ToastProvider } from "@/contexts/ToastContext";
import { AuditPage } from "@/pages/AuditPage";
import { AuthCallbackPage } from "@/pages/AuthCallbackPage";
import { BlastPage } from "@/pages/BlastPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DRSPage } from "@/pages/DRSPage";
import FAIRExportPage from "@/pages/FAIRExportPage";
import { ConsentPage } from "@/pages/ConsentPage";
import MIIExportPage from "@/pages/MIIExportPage";
import { LibraryPage } from "@/pages/LibraryPage";
import { LiteraturePage } from "@/pages/LiteraturePage";
import NotebookPage from "@/pages/NotebookPage";
import { PhenopacketsPage } from "@/pages/PhenopacketsPage";
import { PhenoFlowPage } from "@/pages/PhenoFlowPage";
import { LoginPage } from "@/components/auth/LoginPage";
import { PipelinesPage } from "@/pages/PipelinesPage";
import { PseudonymizePage } from "@/pages/PseudonymizePage";
import { WorkflowsPage } from "@/pages/WorkflowsPage";

function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/literature" element={<LiteraturePage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/notebooks" element={<NotebookPage />} />
          <Route path="/pseudonymize" element={<PseudonymizePage />} />
          <Route path="/pipelines" element={<PipelinesPage />} />
          <Route path="/blast" element={<BlastPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/drs" element={<DRSPage />} />
          <Route path="/phenopackets" element={<PhenopacketsPage />} />
          <Route path="/phenoflow" element={<PhenoFlowPage />} />
          <Route path="/fair-export" element={<FAIRExportPage />} />
          <Route path="/consent" element={<ConsentPage />} />
          <Route path="/mii-export" element={<MIIExportPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Route>
      </Routes>
    </ToastProvider>
  );
}

export default App;
