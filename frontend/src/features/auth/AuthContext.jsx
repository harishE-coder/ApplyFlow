import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '@/services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data);
      return response.data;
    } catch (err) {
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    setUser(response.data.user);
    return response.data.user;
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      window.location.href = '/login';
    }
  };

  const value = {
    user,
    isLoading,
    login,
    logout,
    checkAuth,
    isAdmin: user?.role === 'admin',
    isSubAdmin: user?.role === 'sub_admin',
    isAnyAdmin: user?.role === 'admin' || user?.role === 'sub_admin',
    isEmployee: user?.role === 'employee',
    isClient: user?.role === 'client',
  };

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
