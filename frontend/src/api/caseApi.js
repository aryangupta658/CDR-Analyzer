import api from "./axios";


export async function createCase(
  payload,
) {
  const response = await api.post(
    "/cases",
    payload,
  );

  return response.data;
}


export async function getCases() {
  const response = await api.get(
    "/cases",
  );

  return response.data;
}


export async function getCase(
  caseId,
) {
  const response = await api.get(
    `/cases/${caseId}`,
  );

  return response.data;
}