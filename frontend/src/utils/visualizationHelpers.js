export function formatVisualizationDateTime(
  value,
) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString(
    "en-IN",
    {
      dateStyle: "medium",
      timeStyle: "medium",
    },
  );
}


export function formatVisualizationDuration(
  value,
) {
  const totalSeconds =
    Number(value) || 0;

  const hours = Math.floor(
    totalSeconds / 3600,
  );

  const minutes = Math.floor(
    (totalSeconds % 3600) / 60,
  );

  const seconds =
    totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }

  return `${seconds}s`;
}


export function normalizeArray(
  value,
) {
  return Array.isArray(value)
    ? value
    : [];
}


export function getContactArray(
  result,
) {
  if (!result) {
    return [];
  }

  if (Array.isArray(result)) {
    return result;
  }

  return (
    result.contacts ||
    result.top_contacts ||
    result.items ||
    []
  );
}


export function getDeviceChangeArray(
  result,
) {
  if (!result) {
    return [];
  }

  return (
    result.change_events ||
    result.device_changes ||
    result.events ||
    []
  );
}


export function getCommonDeviceArray(
  result,
) {
  if (!result) {
    return [];
  }

  return (
    result.devices ||
    result.common_devices ||
    result.items ||
    []
  );
}


export function getLocationArray(
  result,
) {
  if (!result) {
    return [];
  }

  return (
    result.locations ||
    result.history ||
    result.events ||
    result.towers ||
    result.items ||
    []
  );
}


export function getIncidentEventArray(
  result,
) {
  if (!result) {
    return [];
  }

  return (
    result.events ||
    result.records ||
    result.activity ||
    []
  );
}


export function isValidCoordinate(
  latitude,
  longitude,
) {
  const lat = Number(latitude);
  const lng = Number(longitude);

  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}