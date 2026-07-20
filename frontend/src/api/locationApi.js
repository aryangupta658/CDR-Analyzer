import api from "./axios";

export async function getTowerSummary(
  caseId,
  evidenceId,
  params = {},
) {
  const response = await api.get(
    `/cases/${caseId}/locations/towers`,
    {
      params: {
        evidence_id: evidenceId,
        ...params,
      },
    },
  );

  return response.data;
}

export async function getTowerDetail(
  caseId,
  evidenceId,
  cellId,
) {
  const response = await api.get(
    `/cases/${caseId}/locations/towers/${cellId}`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getNumberLocationHistory(
  caseId,
  evidenceId,
  phoneNumber,
) {
  const response = await api.get(
    `/cases/${caseId}/locations/numbers/${phoneNumber}/history`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getCoLocation(
  caseId,
  evidenceId,
  payload,
) {
  const response = await api.post(
    `/cases/${caseId}/locations/co-location`,
    payload,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getIncidentTower(
  caseId,
  evidenceId,
  payload,
) {
  const response = await api.post(
    `/cases/${caseId}/locations/incident-tower`,
    payload,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}