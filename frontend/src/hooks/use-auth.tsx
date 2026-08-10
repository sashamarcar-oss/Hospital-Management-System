import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, apiPost, clearTokens, getTokens, setTokens, USER_STORAGE_KEY } from "@/lib/api";
import type { User } from "@/lib/types";

interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User>;
  can: (permissionCode: string) => boolean;
  canAny: (permissionCodes: string[]) => boolean;
  hasRole: (...roleCodes: string[]) => boolean;
  isPatient: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(readStoredUser);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const init = async () => {
      const tokens = getTokens();
      if (!tokens?.access) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await api.get<User>("/auth/me/").then((r) => r.data);
        if (active) {
          setUser(me);
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(me));
        }
      } catch {
        if (active) {
          clearTokens();
          localStorage.removeItem(USER_STORAGE_KEY);
          setUser(null);
        }
      } finally {
        if (active) setIsLoading(false);
      }
    };
    init();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      clearTokens();
      localStorage.removeItem(USER_STORAGE_KEY);
      setUser(null);
    };
    window.addEventListener("hms:unauthorized", onUnauthorized);
    return () => window.removeEventListener("hms:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await apiPost<LoginResponse>("/auth/login/", { username, password });
    setTokens({ access: data.access, refresh: data.refresh });
    setUser(data.user);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    const tokens = getTokens();
    if (tokens?.refresh) {
      try {
        await apiPost("/auth/logout/", { refresh: tokens.refresh });
      } catch {
        // ignore network errors on logout
      }
    }
    clearTokens();
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await api.get<User>("/auth/me/").then((r) => r.data);
    setUser(me);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(me));
    return me;
  }, []);

  const can = useCallback(
    (permissionCode: string) => {
      if (!user) return false;
      if (user.role_code === "super_admin") return true;
      return user.permission_codes.includes(permissionCode);
    },
    [user]
  );

  const canAny = useCallback(
    (permissionCodes: string[]) => permissionCodes.some((code) => can(code)),
    [can]
  );

  const hasRole = useCallback(
    (...roleCodes: string[]) => !!user && roleCodes.includes(user.role_code ?? ""),
    [user]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      refreshUser,
      can,
      canAny,
      hasRole,
      isPatient: user?.role_code === "patient",
    }),
    [user, isLoading, login, logout, refreshUser, can, canAny, hasRole]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
