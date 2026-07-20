import axios from "axios";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL
  || "http://127.0.0.1:8000/api";


function looksLikeJwt(value) {
  if (
    typeof value !== "string"
    || value.trim() === ""
  ) {
    return false;
  }

  const parts = value.trim().split(".");

  return parts.length === 3;
}


function cleanToken(value) {
  if (
    value === null
    || value === undefined
  ) {
    return null;
  }

  let token = String(value).trim();

  if (
    token === ""
    || token === "null"
    || token === "undefined"
  ) {
    return null;
  }

  if (
    token.toLowerCase().startsWith("bearer ")
  ) {
    token = token.slice(7).trim();
  }

  return token || null;
}


function findTokenInsideObject(
  value,
  visited = new Set(),
) {
  if (
    value === null
    || value === undefined
  ) {
    return null;
  }

  if (typeof value === "string") {
    const cleaned = cleanToken(value);

    if (looksLikeJwt(cleaned)) {
      return cleaned;
    }

    try {
      const parsed = JSON.parse(value);

      return findTokenInsideObject(
        parsed,
        visited,
      );
    } catch {
      return null;
    }
  }

  if (typeof value !== "object") {
    return null;
  }

  if (visited.has(value)) {
    return null;
  }

  visited.add(value);

  const preferredKeys = [
    "access_token",
    "accessToken",
    "token",
    "authToken",
    "jwt",
  ];

  for (const key of preferredKeys) {
    if (
      Object.prototype.hasOwnProperty.call(
        value,
        key,
      )
    ) {
      const candidate = cleanToken(
        value[key],
      );

      if (candidate) {
        return candidate;
      }
    }
  }

  for (const nestedValue of Object.values(value)) {
    const nestedToken =
      findTokenInsideObject(
        nestedValue,
        visited,
      );

    if (nestedToken) {
      return nestedToken;
    }
  }

  return null;
}


function getTokenFromStorage(
  storage,
) {
  if (!storage) {
    return null;
  }

  const preferredKeys = [
    "access_token",
    "accessToken",
    "token",
    "authToken",
    "jwt",
    "auth",
    "user",
    "currentUser",
    "cdr_auth",
  ];

  for (const key of preferredKeys) {
    const value = storage.getItem(key);

    if (!value) {
      continue;
    }

    const directToken = cleanToken(value);

    if (
      directToken
      && looksLikeJwt(directToken)
    ) {
      return directToken;
    }

    const nestedToken =
      findTokenInsideObject(value);

    if (nestedToken) {
      return nestedToken;
    }
  }

  /*
   * Search remaining storage values.
   * This helps when the existing AuthContext uses
   * a project-specific storage key.
   */

  for (
    let index = 0;
    index < storage.length;
    index += 1
  ) {
    const key = storage.key(index);

    if (!key) {
      continue;
    }

    const value = storage.getItem(key);

    if (!value) {
      continue;
    }

    const directToken = cleanToken(value);

    if (
      directToken
      && looksLikeJwt(directToken)
    ) {
      return directToken;
    }

    const nestedToken =
      findTokenInsideObject(value);

    if (nestedToken) {
      return nestedToken;
    }
  }

  return null;
}


export function getAuthenticationToken() {
  const localToken =
    getTokenFromStorage(
      window.localStorage,
    );

  if (localToken) {
    return localToken;
  }

  return getTokenFromStorage(
    window.sessionStorage,
  );
}


const apiClient = axios.create({
  baseURL: API_BASE_URL,

  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },

  timeout: 120000,

  /*
   * Also supports cookie-based authentication
   * when the backend uses cookies.
   */
  withCredentials: true,
});


apiClient.interceptors.request.use(
  (config) => {
    const token =
      getAuthenticationToken();

    config.headers =
      config.headers || {};

    /*
     * Never send values such as:
     *
     * Bearer null
     * Bearer undefined
     */
    if (token) {
      config.headers.Authorization =
        `Bearer ${token}`;
    } else {
      delete config.headers.Authorization;
    }

    return config;
  },

  (error) =>
    Promise.reject(error),
);


apiClient.interceptors.response.use(
  (response) => response,

  (error) => {
    if (
      error.response?.status === 401
    ) {
      console.error(
        "API authentication failed.",
        {
          url: error.config?.url,
          detail:
            error.response?.data?.detail,
        },
      );
    }

    return Promise.reject(error);
  },
);


export default apiClient;