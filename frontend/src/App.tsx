import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { Toaster } from "@/components/ui/toaster";
import { AuditPage } from "@/pages/AuditPage";
import { BlastPage } from "@/pages/BlastPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DRSPage } from "@/pages/DRSPage";
import { LiteraturePage } from "@/pages/LiteraturePage";
import { LoginPage } from "@/pages/LoginPage";
import { PipelinesPage } from "@/pages/PipelinesPage";
import { PseudonymizePage } from "@/pages/PseudonymizePage";
import { WorkflowsPage } from "@/pages/WorkflowsPage";

function App() {
  return (
    <Toaster>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/literature" element={<LiteraturePage />} />
          <Route path="/pseudonymize" element={<PseudonymizePage />} />
          <Route path="/pipelines" element={<PipelinesPage />} />
          <Route path="/blast" element={<BlastPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/drs" element={<DRSPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Route>
      </Routes>
    </Toaster>
  );
}

export default App;
