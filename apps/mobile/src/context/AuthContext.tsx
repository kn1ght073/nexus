import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  initApiClient,
  getAccessToken,
  saveAuthTokens,
  clearAuthTokens,
  setServerUrl,
  getServerUrl,
  apiClient,
} from '../api/client';
import { AccountOverviewResponse } from '../api/types';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  serverUrl: string;
  account: AccountOverviewResponse | null;
  loginWithToken: (accessToken: string, refreshToken?: string) => Promise<void>;
  updateServerUrl: (url: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccount: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverUrl, setLocalServerUrl] = useState<string>(getServerUrl());
  const [account, setAccount] = useState<AccountOverviewResponse | null>(null);

  const fetchOverview = async () => {
    try {
      const data = await apiClient<AccountOverviewResponse>('/api/account/overview');
      setAccount(data);
      setIsAuthenticated(true);
    } catch (err) {
      console.warn('[AuthContext] Failed to load account overview:', err);
      setIsAuthenticated(false);
      setAccount(null);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const { serverUrl: url, hasToken } = await initApiClient();
        setLocalServerUrl(url);
        if (hasToken) {
          await fetchOverview();
        }
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const loginWithToken = async (accessToken: string, refreshToken?: string) => {
    await saveAuthTokens(accessToken, refreshToken || accessToken);
    await fetchOverview();
  };

  const updateServerUrl = async (url: string) => {
    await setServerUrl(url);
    setLocalServerUrl(getServerUrl());
  };

  const logout = async () => {
    try {
      await apiClient('/api/auth/logout', { method: 'POST' });
    } catch {
      // Ignored during client purge
    }
    await clearAuthTokens();
    setIsAuthenticated(false);
    setAccount(null);
  };

  const refreshAccount = async () => {
    if (getAccessToken()) {
      await fetchOverview();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        serverUrl,
        account,
        loginWithToken,
        updateServerUrl,
        logout,
        refreshAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
