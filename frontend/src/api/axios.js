import axios from "axios";

import {
  getToken,
  removeStoredCase,
  removeStoredEvidence,
  removeToken,
} from "../utils/storage";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000/api",

  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    const token = getToken();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },

  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,

  (error) => {
    if (error.response?.status === 401) {
      removeToken();
      removeStoredCase();
      removeStoredEvidence();

      const publicPaths = [
        "/",
        "/login",
        "/signup",
      ];

      if (
        !publicPaths.includes(
          window.location.pathname,
        )
      ) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  },
);

export default api;