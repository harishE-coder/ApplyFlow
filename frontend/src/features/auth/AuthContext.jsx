import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import api from '@/services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [bootstrapData, setBootstrapData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const response = await api.get('/auth/bootstrap');
      if (response.data) {
        setUser(response.data.user || null);
        setBootstrapData({
          dashboard: response.data.dashboard || null,
          notifications: response.data.notifications || null,
          chat_unread: response.data.chat_unread || null,
        });
        return response.data.user;
      }
      setUser(null);
      setBootstrapData(null);
      return null;
    } catch (err) {
      setUser(null);
      setBootstrapData(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email, password) => {
    const loginRes = await api.post('/auth/login', { email, password });
    const authUser = loginRes.data.user;
    setUser(authUser);

    // Immediately fetch pre-warmed bootstrap data in 1 fast roundtrip
    try {
      const bootRes = await api.get('/auth/bootstrap');
      if (bootRes.data) {
        setBootstrapData({
          dashboard: bootRes.data.dashboard || null,
          notifications: bootRes.data.notifications || null,
          chat_unread: bootRes.data.chat_unread || null,
        });
      }
    } catch (err) {
      // Fallback
    }

    return authUser;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      setBootstrapData(null);
      window.location.href = '/login';
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      bootstrapData,
      isLoading,
      login,
      logout,
      checkAuth,
      isAdmin: user?.role === 'admin',
      isSubAdmin: user?.role === 'sub_admin',
      isAnyAdmin: user?.role === 'admin' || user?.role === 'sub_admin',
      isEmployee: user?.role === 'employee',
      isClient: user?.role === 'client',
    }),
    [user, bootstrapData, isLoading, login, logout, checkAuth]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
