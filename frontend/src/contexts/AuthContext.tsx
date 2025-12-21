import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

interface UserContextData {
  userId: string;
  email: string;
  name: string;
  relationshipId: string | null;
  displayName: string | null;
  partnerDisplayName: string | null;
  needsOnboarding: boolean;
}

interface AuthContextType {
  user: UserContextData | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  getAccessToken: () => Promise<string>;
  refreshUserContext: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const {
    isAuthenticated,
    isLoading: auth0Loading,
    user: auth0User,
    loginWithRedirect,
    logout: auth0Logout,
    getAccessTokenSilently,
  } = useAuth0();

  const [userContext, setUserContext] = useState<UserContextData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserContext = useCallback(async () => {
    if (!isAuthenticated || !auth0User) {
      setUserContext(null);
      setIsLoading(false);
      return;
    }

    try {
      const token = await getAccessTokenSilently();
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      const response = await fetch(`${apiUrl}/api/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setUserContext({
          userId: data.user_id || '',
          email: data.email || auth0User.email || '',
          name: data.name || auth0User.name || '',
          relationshipId: data.relationship_id || null,
          displayName: data.display_name || null,
          partnerDisplayName: data.partner_display_name || null,
          needsOnboarding: data.needs_onboarding || false,
        });
      } else if (response.status === 401) {
        // Token might be invalid, user needs to re-authenticate
        console.warn('Auth token invalid, user not in database yet');
        setUserContext({
          userId: '',
          email: auth0User.email || '',
          name: auth0User.name || '',
          relationshipId: null,
          displayName: null,
          partnerDisplayName: null,
          needsOnboarding: true,
        });
      } else {
        // Other error - user might not be in database yet
        setUserContext({
          userId: '',
          email: auth0User.email || '',
          name: auth0User.name || '',
          relationshipId: null,
          displayName: null,
          partnerDisplayName: null,
          needsOnboarding: true,
        });
      }
    } catch (error) {
      console.error('Failed to fetch user context:', error);
      // Fallback to Auth0 user data
      setUserContext({
        userId: '',
        email: auth0User?.email || '',
        name: auth0User?.name || '',
        relationshipId: null,
        displayName: null,
        partnerDisplayName: null,
        needsOnboarding: true,
      });
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, auth0User, getAccessTokenSilently]);

  useEffect(() => {
    if (!auth0Loading) {
      fetchUserContext();
    }
  }, [auth0Loading, fetchUserContext]);

  const login = () => loginWithRedirect();

  const logout = () =>
    auth0Logout({
      logoutParams: { returnTo: window.location.origin },
    });

  const getAccessToken = async () => {
    return await getAccessTokenSilently();
  };

  const refreshUserContext = async () => {
    await fetchUserContext();
  };

  return (
    <AuthContext.Provider
      value={{
        user: userContext,
        isLoading: isLoading || auth0Loading,
        isAuthenticated,
        login,
        logout,
        getAccessToken,
        refreshUserContext,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Hook for getting display name with fallbacks
export function useDisplayName(): string {
  const { user } = useAuth();
  if (!user) return 'Guest';
  return user.displayName || user.name?.split(' ')[0] || user.email?.split('@')[0] || 'User';
}

// Hook for getting partner name with fallback
export function usePartnerName(): string {
  const { user } = useAuth();
  return user?.partnerDisplayName || 'Partner';
}
