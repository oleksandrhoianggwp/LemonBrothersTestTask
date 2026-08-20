import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, authStore } from "./api";

interface AuthContextValue {
  authenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [authenticated, setAuthenticated] = useState(Boolean(authStore.get()));
  const value = useMemo<AuthContextValue>(
    () => ({
      authenticated,
      login: async (username, password) => {
        await api.login(username, password);
        setAuthenticated(true);
      },
      logout: () => {
        authStore.clear();
        setAuthenticated(false);
      },
    }),
    [authenticated],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { authenticated } = useAuth();
  const location = useLocation();
  if (!authenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}
