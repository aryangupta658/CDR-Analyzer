import { createContext, useContext, useMemo, useState } from "react";

import {
  getStoredCase,
  getStoredEvidence,
  removeStoredCase,
  removeStoredEvidence,
  setStoredCase,
  setStoredEvidence,
} from "../utils/storage";

const CaseContext = createContext(null);

export function CaseProvider({ children }) {
  const [selectedCase, setSelectedCaseState] = useState(getStoredCase);

  const [selectedEvidence, setSelectedEvidenceState] =
    useState(getStoredEvidence);

  function selectCase(caseData) {
    setSelectedCaseState(caseData);
    setStoredCase(caseData);

    setSelectedEvidenceState(null);
    removeStoredEvidence();
  }

  function selectEvidence(evidence) {
    setSelectedEvidenceState(evidence);
    setStoredEvidence(evidence);
  }

  function clearCase() {
    setSelectedCaseState(null);
    setSelectedEvidenceState(null);

    removeStoredCase();
    removeStoredEvidence();
  }

  const value = useMemo(
    () => ({
      selectedCase,
      selectedEvidence,
      selectCase,
      selectEvidence,
      clearCase,
    }),
    [selectedCase, selectedEvidence],
  );

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
}

export function useCase() {
  const context = useContext(CaseContext);

  if (!context) {
    throw new Error("useCase must be used inside CaseProvider.");
  }

  return context;
}
