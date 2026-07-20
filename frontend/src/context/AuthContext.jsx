import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getCurrentUser, loginUser, registerUser } from "../api/authApi";

import {
  getToken,
  removeStoredCase,
  removeStoredEvidence,
  removeToken,
  setToken,
} from "../utils/storage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      const token = getToken();

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();

        setUser(currentUser);
      } catch {
        removeToken();
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  async function login(credentials) {
    const result = await loginUser(credentials);

    const token = result.access_token || result.token;

    if (!token) {
      throw new Error("Login response did not include an access token.");
    }

    setToken(token);

    const currentUser = await getCurrentUser();

    setUser(currentUser);

    return currentUser;
  }

  async function signup(payload) {
    return registerUser(payload);
  }

  function logout() {
    removeToken();
    removeStoredCase();
    removeStoredEvidence();
    setUser(null);
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      signup,
      logout,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}
