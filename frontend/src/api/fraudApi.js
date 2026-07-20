import apiClient from "./apiClient.js";

function parseIncidentCellIds(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function runPatternAnalysis({
  caseId,
  evidenceId,
  phoneNumber = "",
  incidentDateTime = "",
  incidentCellIds = "",
  includeCallPatterns = true,
  includeSmsPatterns = true,
  includeDevicePatterns = true,
  includeLocationPatterns = true,
  includeRoamingPatterns = true,
  includeForwardingPatterns = true,
}) {
  if (!caseId) {
    throw new Error("Case ID is required for pattern analysis.");
  }

  if (!evidenceId) {
    throw new Error("Evidence ID is required for pattern analysis.");
  }

  const response = await apiClient.post(
    `/cases/${caseId}/pattern-analysis`,
    {
      phone_number: String(phoneNumber || "").trim() || null,
      incident_datetime: incidentDateTime || null,
      incident_cell_ids: parseIncidentCellIds(incidentCellIds),
      include_call_patterns: Boolean(includeCallPatterns),
      include_sms_patterns: Boolean(includeSmsPatterns),
      include_device_patterns: Boolean(includeDevicePatterns),
      include_location_patterns: Boolean(includeLocationPatterns),
      include_roaming_patterns: Boolean(includeRoamingPatterns),
      include_forwarding_patterns: Boolean(includeForwardingPatterns),
    },
    {
      params: {
        evidence_id: evidenceId,
      },
    },
  );

  return response.data;
}

export async function getNumberPatterns(
  caseId,
  evidenceId,
  phoneNumber,
  incidentDateTime = "",
  incidentCellIds = "",
) {
  const parsedCellIds = parseIncidentCellIds(incidentCellIds);

  const response = await apiClient.get(
    `/cases/${caseId}/analysis/numbers/${encodeURIComponent(
      phoneNumber,
    )}/patterns`,
    {
      params: {
        evidence_id: evidenceId,
        incident_datetime: incidentDateTime || undefined,
        incident_cell_ids:
          parsedCellIds.length > 0 ? parsedCellIds.join(",") : undefined,
      },
    },
  );

  return response.data;
}