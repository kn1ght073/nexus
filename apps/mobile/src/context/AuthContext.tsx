import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  initApiClient,
  getAccessToken,
  saveAuthTokens,
  clearAuthTokens,
  setServerUrl,
  getServerUrl,
  setHostUrl,
  getHostUrl,
  autoDiscoverHost,
  apiClient,
} from '../api/client';
import { AccountOverviewResponse } from '../api/types';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  serverUrl: string;
  hostUrl: string | null;
  hostConnectionMode: 'lan' | 'relay' | 'none';
  account: AccountOverviewResponse | null;
  loginWithToken: (accessToken: string, refreshToken?: string) => Promise<void>;
  updateServerUrl: (url: string) => Promise<void>;
  updateHostUrl: (url: string | null) => Promise<void>;
  discoverHost: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAccount: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverUrl, setLocalServerUrl] = useState<string>(getServerUrl());
  const [hostUrl, setLocalHostUrl] = useState<string | null>(getHostUrl());
  const [hostConnectionMode, setHostConnectionMode] = useState<'lan' | 'relay' | 'none'>('none');
  const [account, setAccount] = useState<AccountOverviewResponse | null>(null);

  const discoverHost = async () => {
    try {
      const res = await autoDiscoverHost();
      if (res.discovered && res.activeHostUrl) {
        setLocalHostUrl(res.activeHostUrl);
        setHostConnectionMode(res.mode);
      } else {
        setHostConnectionMode('none');
      }
    } catch {
      setHostConnectionMode('none');
    }
  };

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
        const { serverUrl: url, hostUrl: hUrl, hasToken } = await initApiClient();
        setLocalServerUrl(url);
        setLocalHostUrl(hUrl);
        if (hasToken) {
          await fetchOverview();
          await discoverHost();
        }
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const loginWithToken = async (accessToken: string, refreshToken?: string) => {
    await saveAuthTokens(accessToken, refreshToken || accessToken);
    await fetchOverview();
    await discoverHost();
  };

  const updateServerUrl = async (url: string) => {
    await setServerUrl(url);
    setLocalServerUrl(getServerUrl());
  };

  const updateHostUrl = async (url: string | null) => {
    await setHostUrl(url);
    setLocalHostUrl(getHostUrl());
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
        hostUrl,
        hostConnectionMode,
        account,
        loginWithToken,
        updateServerUrl,
        updateHostUrl,
        discoverHost,
        logout,
        refreshAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
