import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import api from '@/services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [bootstrapData, setBootstrapData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const response = await api.get('/auth/bootstrap', { cache: false });
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
    const credentials = { email, password };
    await api.post('/auth/login', credentials);

    // Immediately fetch the authenticated bootstrap payload after login.
    const bootRes = await api.get('/auth/bootstrap', { cache: false });

    setUser(bootRes.data.user);
    setBootstrapData({
      dashboard: bootRes.data.dashboard || null,
      notifications: bootRes.data.notifications || null,
      chat_unread: bootRes.data.chat_unread || null,
    });

    return bootRes.data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      api.invalidateCache();
      setUser(null);
      setBootstrapData(null);
      window.location.replace('/login');
    }
  }, []);

  const consumeBootstrapDashboard = useCallback(() => {
    if (!bootstrapData?.dashboard) return null;
    const dash = bootstrapData.dashboard;
    setBootstrapData((prev) => (prev ? { ...prev, dashboard: null } : null));
    return dash;
  }, [bootstrapData]);

  const value = useMemo(
    () => ({
      user,
      bootstrapData,
      consumeBootstrapDashboard,
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
    [user, bootstrapData, consumeBootstrapDashboard, isLoading, login, logout, checkAuth]
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
