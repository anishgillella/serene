import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'serene_token';

interface User {
  id: string;
  email: string;
  name: string;
}

interface PartnerContextType {
  user: User | null;
  token: string | null;
  partnerRole: 'partner_a' | 'partner_b' | null;
  partnerName: string;
  otherPartnerName: string;
  relationshipId: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const DEFAULT_RELATIONSHIP_ID = '00000000-0000-0000-0000-000000000000';

const PartnerContext = createContext<PartnerContextType>({
  user: null,
  token: null,
  partnerRole: null,
  partnerName: '',
  otherPartnerName: '',
  relationshipId: '',
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  signup: async () => {},
  logout: () => {},
});

export const usePartnerContext = () => useContext(PartnerContext);

export const PartnerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [partnerRole, setPartnerRole] = useState<'partner_a' | 'partner_b' | null>(null);
  const [partnerName, setPartnerName] = useState('');
  const [otherPartnerName, setOtherPartnerName] = useState('');
  const [relationshipId, setRelationshipId] = useState(DEFAULT_RELATIONSHIP_ID);
  const [isLoading, setIsLoading] = useState(true);

  const applyAuthData = (data: any) => {
    setUser(data.user);
    setPartnerRole(data.partner_role || null);
    setPartnerName(data.partner_name || data.user?.name || '');
    setOtherPartnerName(data.other_partner_name || '');
    setRelationshipId(data.relationship_id || DEFAULT_RELATIONSHIP_ID);
  };

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setPartnerRole(null);
    setPartnerName('');
    setOtherPartnerName('');
    setRelationshipId(DEFAULT_RELATIONSHIP_ID);
  }, []);

  // On mount, verify stored token
  useEffect(() => {
    const verifyToken = async () => {
      const stored = localStorage.getItem(TOKEN_KEY);
      if (!stored) {
        setIsLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
          headers: {
            Authorization: `Bearer ${stored}`,
            'ngrok-skip-browser-warning': 'true',
          },
        });

        if (!res.ok) {
          clearAuth();
          return;
        }

        const data = await res.json();
        setToken(stored);
        applyAuthData(data);
      } catch {
        clearAuth();
      } finally {
        setIsLoading(false);
      }
    };

    verifyToken();
  }, [clearAuth]);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    localStorage.setItem(TOKEN_KEY, data.token);
    setToken(data.token);
    applyAuthData(data);
  };

  const signup = async (name: string, email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Signup failed');
    }

    localStorage.setItem(TOKEN_KEY, data.token);
    setToken(data.token);
    applyAuthData(data);
  };

  const logout = () => {
    clearAuth();
  };

  return (
    <PartnerContext.Provider
      value={{
        user,
        token,
        partnerRole,
        partnerName,
        otherPartnerName,
        relationshipId,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </PartnerContext.Provider>
  );
};
