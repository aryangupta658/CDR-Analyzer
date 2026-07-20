import api from "./axios";

export async function uploadEvidence(
  caseId,
  file,
) {
  const formData = new FormData();

  formData.append("file", file);

  const response = await api.post(
    `/cases/${caseId}/evidence/upload`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );

  return response.data;
}

export async function getEvidence(caseId) {
  const response = await api.get(
    `/cases/${caseId}/evidence`,
  );

  return response.data;
}

export async function importEvidence(
  evidenceId,
  payload,
) {
  const response = await api.post(
    `/evidence/${evidenceId}/import`,
    payload,
  );

  return response.data;
}