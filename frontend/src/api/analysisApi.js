import api from "./axios";


export async function getCaseSummary(
  caseId,
  evidenceId,
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/summary`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}


export async function getNumbers(
  caseId,
  evidenceId,
  params = {},
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/numbers`,
    {
      params: {
        evidence_id: evidenceId,
        ...params,
      },
    },
  );

  return response.data;
}


export async function getNumberAnalysis(
  caseId,
  evidenceId,
  phoneNumber,
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/numbers/${encodeURIComponent(
      phoneNumber,
    )}`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}


export async function getTopContacts(
  caseId,
  evidenceId,
  phoneNumber,
  limit = 10,
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/numbers/${encodeURIComponent(
      phoneNumber,
    )}/top-contacts`,
    {
      params: {
        evidence_id: evidenceId,
        limit,
      },
    },
  );

  return response.data;
}


export async function getContactTimeline(
  caseId,
  evidenceId,
  phoneNumber,
  contactNumber,
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/numbers/${encodeURIComponent(
      phoneNumber,
    )}/contacts/${encodeURIComponent(
      contactNumber,
    )}/timeline`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}


export async function getCallsByHour(
  caseId,
  evidenceId,
  phoneNumber = "",
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/calls-by-hour`,
    {
      params: {
        evidence_id: evidenceId,
        phone_number: phoneNumber || undefined,
      },
    },
  );

  return response.data;
}


export async function getCallsByDate(
  caseId,
  evidenceId,
  phoneNumber = "",
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/calls-by-date`,
    {
      params: {
        evidence_id: evidenceId,
        phone_number: phoneNumber || undefined,
      },
    },
  );

  return response.data;
}


export async function getContactNetwork(
  caseId,
  evidenceId,
  phoneNumber,
) {
  const response = await api.get(
    `/cases/${caseId}/analysis/numbers/${encodeURIComponent(
      phoneNumber,
    )}/network`,
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}