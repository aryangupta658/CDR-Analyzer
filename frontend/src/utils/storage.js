const TOKEN_KEY = "cdr_access_token";
const CASE_KEY = "cdr_selected_case";
const EVIDENCE_KEY = "cdr_selected_evidence";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getStoredCase() {
  const value = localStorage.getItem(CASE_KEY);

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch {
    localStorage.removeItem(CASE_KEY);
    return null;
  }
}

export function setStoredCase(caseData) {
  localStorage.setItem(
    CASE_KEY,
    JSON.stringify(caseData),
  );
}

export function removeStoredCase() {
  localStorage.removeItem(CASE_KEY);
}

export function getStoredEvidence() {
  const value = localStorage.getItem(EVIDENCE_KEY);

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch {
    localStorage.removeItem(EVIDENCE_KEY);
    return null;
  }
}

export function setStoredEvidence(evidence) {
  localStorage.setItem(
    EVIDENCE_KEY,
    JSON.stringify(evidence),
  );
}

export function removeStoredEvidence() {
  localStorage.removeItem(EVIDENCE_KEY);
}