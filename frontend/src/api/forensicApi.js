import api from "./axios";

export async function getCommonContacts(
  caseId,
  evidenceId,
  payload,
) {
  const response = await api.post(
    `/cases/${caseId}/forensics/common-contacts`,
    payload,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getImeiAnalysis(
  caseId,
  evidenceId,
  imei,
) {
  const response = await api.get(
    `/cases/${caseId}/forensics/imei/${imei}`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getImsiAnalysis(
  caseId,
  evidenceId,
  imsi,
) {
  const response = await api.get(
    `/cases/${caseId}/forensics/imsi/${imsi}`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getDeviceHistory(
  caseId,
  evidenceId,
  phoneNumber,
) {
  const response = await api.get(
    `/cases/${caseId}/forensics/numbers/${phoneNumber}/device-history`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getCommonDevices(
  caseId,
  evidenceId,
  params = {},
) {
  const response = await api.get(
    `/cases/${caseId}/forensics/common-devices`,
    {
      params: {
        evidence_id: evidenceId,
        ...params,
      },
    },
  );

  return response.data;
}

export async function getIncidentWindow(
  caseId,
  payload,
) {
  const response = await api.post(
    `/cases/${caseId}/forensics/incident-window`,
    payload,
  );

  return response.data;
}