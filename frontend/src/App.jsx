import { Navigate, Route, Routes } from "react-router";

import AppLayout from "./components/layout/AppLayout";
import PublicLayout from "./components/layout/PublicLayout";

import DeviceAnalysisPage from "./pages/analysis/DeviceAnalysisPage";
import FraudAnalysisPage from "./pages/analysis/FraudAnalysisPage";
import IncidentAnalysisPage from "./pages/analysis/IncidentAnalysisPage";
import LocationAnalysisPage from "./pages/analysis/LocationAnalysisPage";
import NumberAnalysisPage from "./pages/analysis/NumberAnalysisPage";

import CasesPage from "./pages/cases/CasesPage";
import UploadEvidencePage from "./pages/cases/UploadEvidencePage";

import CaseDashboardPage from "./pages/dashboard/CaseDashboardPage";

import LandingPage from "./pages/public/LandingPage";
import LoginPage from "./pages/public/LoginPage";
import SignupPage from "./pages/public/SignupPage";

import AnalysisContextGuard from "./routes/AnalysisContextGuard";
import ProtectedRoute from "./routes/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      {/* ==================================================
          Public routes
      ================================================== */}

      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />

        <Route path="/login" element={<LoginPage />} />

        <Route path="/signup" element={<SignupPage />} />
      </Route>

      {/* ==================================================
          Protected application routes
      ================================================== */}

      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        {/* Default protected route */}

        <Route index element={<Navigate to="cases" replace />} />

        {/* ==================================================
            Case routes
        ================================================== */}

        <Route path="cases" element={<CasesPage />} />

        <Route path="cases/:caseId/evidence" element={<UploadEvidencePage />} />

        <Route path="cases/:caseId/dashboard" element={<CaseDashboardPage />} />

        {/* ==================================================
            Old routes redirected safely
        ================================================== */}

        <Route
          path="dashboard"
          element={<Navigate to="/app/cases" replace />}
        />

        <Route path="evidence" element={<Navigate to="/app/cases" replace />} />

        {/* ==================================================
            Analysis routes

            AnalysisContextGuard verifies that:
            1. A case has been opened
            2. Imported evidence has been selected
        ================================================== */}

        <Route
          path="analysis/numbers"
          element={
            <AnalysisContextGuard>
              <NumberAnalysisPage />
            </AnalysisContextGuard>
          }
        />

        <Route
          path="analysis/devices"
          element={
            <AnalysisContextGuard>
              <DeviceAnalysisPage />
            </AnalysisContextGuard>
          }
        />

        <Route
          path="analysis/locations"
          element={
            <AnalysisContextGuard>
              <LocationAnalysisPage />
            </AnalysisContextGuard>
          }
        />

        <Route
          path="analysis/incidents"
          element={
            <AnalysisContextGuard>
              <IncidentAnalysisPage />
            </AnalysisContextGuard>
          }
        />

        <Route
          path="analysis/fraud"
          element={
            <AnalysisContextGuard>
              <FraudAnalysisPage />
            </AnalysisContextGuard>
          }
        />
      </Route>

      {/* ==================================================
          Unknown routes
      ================================================== */}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
