import { Navigate, useLocation } from "react-router";

import { toast } from "react-toastify";

import { useEffect, useRef } from "react";

import { useCase } from "../context/CaseContext";

export default function AnalysisContextGuard({ children }) {
  const { selectedCase, selectedEvidence } = useCase();

  const location = useLocation();

  const notificationShown = useRef(false);

  useEffect(() => {
    if ((!selectedCase || !selectedEvidence) && !notificationShown.current) {
      toast.error(
        "Open a case and select imported evidence before running analysis.",
      );

      notificationShown.current = true;
    }
  }, [selectedCase, selectedEvidence]);

  if (!selectedCase) {
    return (
      <Navigate
        to="/app/cases"
        replace
        state={{
          from: location.pathname,
        }}
      />
    );
  }

  if (!selectedEvidence) {
    return (
      <Navigate
        to={`/app/cases/${selectedCase.id}/dashboard`}
        replace
        state={{
          from: location.pathname,
        }}
      />
    );
  }

  return children;
}
