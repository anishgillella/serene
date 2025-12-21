import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// Local storage key for relationship_id
const RELATIONSHIP_ID_KEY = 'serene_relationship_id';

interface RelationshipProfile {
  relationship_id: string;
  partner_a_name: string;
  partner_b_name: string;
}

interface RelationshipContextType {
  relationshipId: string | null;
  partnerAName: string;
  partnerBName: string;
  isLoading: boolean;
  error: string | null;
  setRelationshipId: (id: string) => void;
  createRelationship: (partnerAName: string, partnerBName: string) => Promise<string>;
  loadRelationshipProfile: () => Promise<void>;
  clearRelationship: () => void;
}

const RelationshipContext = createContext<RelationshipContextType | null>(null);

// Default relationship ID for backward compatibility (Adrian & Elara)
const DEFAULT_RELATIONSHIP_ID = '00000000-0000-0000-0000-000000000000';

export function RelationshipProvider({ children }: { children: ReactNode }) {
  const [relationshipId, setRelationshipIdState] = useState<string | null>(null);
  const [partnerAName, setPartnerAName] = useState<string>('Partner A');
  const [partnerBName, setPartnerBName] = useState<string>('Partner B');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Load relationship ID from localStorage on mount
  useEffect(() => {
    const storedId = localStorage.getItem(RELATIONSHIP_ID_KEY);

    // Check URL params for relationship_id (for shareable links)
    const urlParams = new URLSearchParams(window.location.search);
    const urlRelationshipId = urlParams.get('r') || urlParams.get('relationship_id');

    if (urlRelationshipId) {
      // URL param takes precedence
      setRelationshipIdState(urlRelationshipId);
      localStorage.setItem(RELATIONSHIP_ID_KEY, urlRelationshipId);
      // Clean up URL
      urlParams.delete('r');
      urlParams.delete('relationship_id');
      const newUrl = urlParams.toString()
        ? `${window.location.pathname}?${urlParams.toString()}`
        : window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    } else if (storedId) {
      setRelationshipIdState(storedId);
    } else {
      // Fall back to default relationship for backward compatibility
      setRelationshipIdState(DEFAULT_RELATIONSHIP_ID);
      localStorage.setItem(RELATIONSHIP_ID_KEY, DEFAULT_RELATIONSHIP_ID);
    }
  }, []);

  // Load relationship profile when ID changes
  const loadRelationshipProfile = useCallback(async () => {
    if (!relationshipId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/relationships/${relationshipId}/profile`);

      if (response.ok) {
        const data = await response.json();
        if (data.profile) {
          setPartnerAName(data.profile.partner_a_name || 'Partner A');
          setPartnerBName(data.profile.partner_b_name || 'Partner B');
        }
      } else if (response.status === 404) {
        // Relationship not found - might need onboarding
        console.warn('Relationship not found, may need to create one');
        setError('Relationship not found');
      } else {
        console.error('Failed to load relationship profile');
      }
    } catch (err) {
      console.error('Error loading relationship profile:', err);
      setError('Failed to load relationship');
    } finally {
      setIsLoading(false);
    }
  }, [relationshipId, apiUrl]);

  // Load profile when relationship ID changes
  useEffect(() => {
    if (relationshipId) {
      loadRelationshipProfile();
    }
  }, [relationshipId, loadRelationshipProfile]);

  // Set relationship ID and persist to localStorage
  const setRelationshipId = useCallback((id: string) => {
    setRelationshipIdState(id);
    localStorage.setItem(RELATIONSHIP_ID_KEY, id);
  }, []);

  // Create a new relationship
  const createRelationship = useCallback(async (partnerA: string, partnerB: string): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/relationships/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          partner_a_name: partnerA,
          partner_b_name: partnerB,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create relationship');
      }

      const data = await response.json();
      const newRelationshipId = data.relationship_id;

      // Update state and localStorage
      setRelationshipId(newRelationshipId);
      setPartnerAName(partnerA);
      setPartnerBName(partnerB);

      return newRelationshipId;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create relationship';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, setRelationshipId]);

  // Clear relationship and remove from localStorage
  const clearRelationship = useCallback(() => {
    setRelationshipIdState(null);
    setPartnerAName('Partner A');
    setPartnerBName('Partner B');
    localStorage.removeItem(RELATIONSHIP_ID_KEY);
  }, []);

  return (
    <RelationshipContext.Provider
      value={{
        relationshipId,
        partnerAName,
        partnerBName,
        isLoading,
        error,
        setRelationshipId,
        createRelationship,
        loadRelationshipProfile,
        clearRelationship,
      }}
    >
      {children}
    </RelationshipContext.Provider>
  );
}

// Hook to use relationship context
export function useRelationship() {
  const context = useContext(RelationshipContext);
  if (!context) {
    throw new Error('useRelationship must be used within a RelationshipProvider');
  }
  return context;
}

// Hook to get current relationship ID (returns default if not set)
export function useRelationshipId(): string {
  const { relationshipId } = useRelationship();
  return relationshipId || DEFAULT_RELATIONSHIP_ID;
}

// Hook to get partner names
export function usePartnerNames(): { partnerA: string; partnerB: string } {
  const { partnerAName, partnerBName } = useRelationship();
  return {
    partnerA: partnerAName,
    partnerB: partnerBName,
  };
}

// Helper to generate shareable link
export function getShareableLink(relationshipId: string): string {
  const baseUrl = window.location.origin;
  return `${baseUrl}?r=${relationshipId}`;
}
