# Frontend Integration - Phase 3: Luna Context Awareness

**Phase**: 3 - Luna Context-Aware Mediation
**Timeline**: 2-3 weeks
**Priority**: High (improves Luna effectiveness)
**User Impact**: Luna references past conflicts and understands patterns

---

## Overview

Phase 3 integrates conflict intelligence into Luna's mediation. The frontend passes enrichment context to the agent and handles enhanced responses.

---

## API Integration

### New Endpoint: Mediation with Context

The existing Luna endpoint now includes enrichment context:

**File**: `src/hooks/useLunaMediator.ts`

```typescript
import { useCallback, useState } from 'react';

interface MediationContext {
  current_conflict: {
    topic: string;
    resentment_level: number;
    unmet_needs: string[];
  };
  unresolved_issues: Array<{
    topic: string;
    days_unresolved: number;
  }>;
  chronic_needs: string[];
  high_impact_triggers: string[];
  escalation_risk: {
    score: number;
    interpretation: string;
  };
}

export const useLunaMediator = (conflictId: string) => {
  const [context, setContext] = useState<MediationContext | null>(null);
  const [messages, setMessages] = useState<Array<{role: string; content: string}>>([]);

  // Load context when session starts
  useCallback(async () => {
    const response = await fetch(`/api/mediator/context/${conflictId}`);
    const contextData = await response.json();
    setContext(contextData);
  }, [conflictId]);

  // Send message to Luna (context is sent automatically)
  const sendMessage = useCallback(async (message: string) => {
    const response = await fetch(`/api/mediator/token/${conflictId}`, {
      method: 'POST',
      body: JSON.stringify({
        message,
        context // Include enrichment context
      })
    });

    const { response: lunaResponse } = await response.json();
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    setMessages(prev => [...prev, { role: 'assistant', content: lunaResponse }]);

    return lunaResponse;
  }, [conflictId, context]);

  return { context, messages, sendMessage };
};
```

### New Endpoints

```typescript
// Get mediation context for a conflict
GET /api/mediator/context/{conflict_id}
→ {
  current_conflict: { ... },
  unresolved_issues: [ ... ],
  chronic_needs: [ ... ],
  escalation_risk: { ... }
}

// Send message with context
POST /api/mediator/message/{conflict_id}
Body: {
  message: "How do we resolve this?",
  context: { ... }
}
→ {
  response: "I notice this connects to..."
}
```

---

## Enhanced MediatorModal

**File**: `src/components/MediatorModal.tsx` (UPDATED)

```tsx
import { useEffect, useState } from 'react';
import { useLunaMediator } from '../hooks/useLunaMediator';

interface Props {
  conflictId: string;
  onClose: () => void;
}

export const MediatorModal: React.FC<Props> = ({ conflictId, onClose }) => {
  const { context, messages, sendMessage } = useLunaMediator(conflictId);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl h-[600px] flex flex-col">

        {/* Header with Context Info */}
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-lg">
          <h2 className="text-2xl font-bold mb-2">Luna - Relationship Mediator</h2>

          {/* Show context awareness */}
          {context && (
            <div className="mt-4 space-y-2 text-sm bg-white/10 p-3 rounded">
              {context.escalation_risk.score > 0.5 && (
                <p className="flex items-center">
                  <span className="mr-2">⚠️</span>
                  High escalation risk detected
                </p>
              )}

              {context.unresolved_issues.length > 0 && (
                <p className="flex items-center">
                  <span className="mr-2">📋</span>
                  {context.unresolved_issues.length} unresolved issues
                </p>
              )}

              {context.chronic_needs.length > 0 && (
                <p className="flex items-center">
                  <span className="mr-2">💔</span>
                  Core need: {context.chronic_needs[0]}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Message Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs px-4 py-2 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-800'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-200 p-3 rounded-lg">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t p-4 flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Tell Luna about your conflict..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />

          <button
            onClick={async () => {
              setIsLoading(true);
              await sendMessage(inputValue);
              setInputValue('');
              setIsLoading(false);
            }}
            disabled={isLoading || !inputValue.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-white hover:text-gray-200"
        >
          ✕
        </button>
      </div>
    </div>
  );
};
```

---

## New Components

### Context Display Component

**File**: `src/components/MediatorContextPanel.tsx`

```tsx
interface Props {
  context: MediationContext;
}

export const MediatorContextPanel: React.FC<Props> = ({ context }) => {
  return (
    <div className="space-y-4">
      {/* Escalation Risk */}
      <div className={`p-4 rounded-lg ${
        context.escalation_risk.score > 0.7
          ? 'bg-red-50 border border-red-200'
          : 'bg-yellow-50 border border-yellow-200'
      }`}>
        <p className="font-semibold text-sm">
          Escalation Risk: {(context.escalation_risk.score * 100).toFixed(0)}%
        </p>
        <p className="text-xs text-gray-600 mt-1">
          {context.escalation_risk.interpretation}
        </p>
      </div>

      {/* Unresolved Issues */}
      {context.unresolved_issues.length > 0 && (
        <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
          <p className="font-semibold text-sm mb-2">Unresolved Issues:</p>
          <ul className="text-xs space-y-1">
            {context.unresolved_issues.map((issue) => (
              <li key={issue.topic} className="text-gray-700">
                • {issue.topic} ({issue.days_unresolved} days)
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Chronic Needs */}
      {context.chronic_needs.length > 0 && (
        <div className="p-4 rounded-lg bg-purple-50 border border-purple-200">
          <p className="font-semibold text-sm mb-2">Core Needs:</p>
          <div className="flex flex-wrap gap-2">
            {context.chronic_needs.map((need) => (
              <span
                key={need}
                className="inline-block px-2 py-1 bg-purple-200 text-purple-800 text-xs rounded"
              >
                {need.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

---

## Integration with PostFightSession

**File**: `src/pages/PostFightSession.tsx` (UPDATED)

```tsx
import { MediatorModal } from '../components/MediatorModal';
import { MediatorContextPanel } from '../components/MediatorContextPanel';
import { useState } from 'react';

export const PostFightSession: React.FC = () => {
  const [showMediator, setShowMediator] = useState(false);
  const [context, setContext] = useState(null);

  useEffect(() => {
    // Load context when page loads
    const loadContext = async () => {
      const response = await fetch(`/api/mediator/context/${conflictId}`);
      const data = await response.json();
      setContext(data);
    };

    loadContext();
  }, [conflictId]);

  return (
    <div className="space-y-6">
      <h1>Post-Fight Session</h1>

      {/* Context Panel */}
      {context && <MediatorContextPanel context={context} />}

      {/* Existing Analysis Display */}
      <div>{/* ... existing analysis ... */}</div>

      {/* Start Mediation Button */}
      <button
        onClick={() => setShowMediator(true)}
        className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
      >
        💬 Talk to Luna
      </button>

      {/* Mediator Modal */}
      {showMediator && (
        <MediatorModal
          conflictId={conflictId}
          onClose={() => setShowMediator(false)}
        />
      )}
    </div>
  );
};
```

---

## Real-Time Context Updates

**File**: `src/hooks/useConflictContext.ts`

```typescript
import { useEffect, useState } from 'react';

export const useConflictContext = (conflictId: string) => {
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/mediator/context/${conflictId}`)
      .then(r => r.json())
      .then(setContext)
      .finally(() => setLoading(false));
  }, [conflictId]);

  // Refresh context every 5 seconds while mediating
  useEffect(() => {
    const interval = setInterval(() => {
      fetch(`/api/mediator/context/${conflictId}`)
        .then(r => r.json())
        .then(setContext);
    }, 5000);

    return () => clearInterval(interval);
  }, [conflictId]);

  return { context, loading };
};
```

---

## TypeScript Types

**File**: `src/types/mediation.ts` (NEW/UPDATED)

```typescript
export interface MediationContext {
  current_conflict: {
    topic: string;
    resentment_level: number;
    unmet_needs: string[];
  };
  unresolved_issues: Array<{
    conflict_id: string;
    topic: string;
    days_unresolved: number;
    resentment_level: number;
  }>;
  chronic_needs: Array<{
    need: string;
    conflict_count: number;
    percentage: number;
  }>;
  high_impact_triggers: Array<{
    phrase: string;
    category: string;
    escalation_rate: number;
  }>;
  escalation_risk: {
    score: number;
    interpretation: 'low' | 'medium' | 'high' | 'critical';
  };
  active_chains: Array<{
    root_cause: string;
    conflicts: number;
  }>;
}

export interface MediationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  detectedPatterns?: string[];
}
```

---

## Styling Updates

Add to `src/index.css`:

```css
/* Mediation modal animations */
@keyframes slideIn {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.mediator-modal {
  animation: slideIn 0.3s ease-out;
}

/* Context panel */
.context-panel {
  @apply bg-gradient-to-b from-gray-50 to-gray-100 rounded-lg p-4 space-y-3;
}

.context-alert {
  @apply flex items-start gap-2 p-3 rounded border-l-4;
}

.context-alert.high {
  @apply bg-red-50 border-red-400 text-red-800;
}

.context-alert.medium {
  @apply bg-yellow-50 border-yellow-400 text-yellow-800;
}
```

---

## Testing Checklist

- [ ] Context loads when mediation starts
- [ ] Unresolved issues display correctly
- [ ] Chronic needs show up
- [ ] Luna references past conflicts
- [ ] Messages send and receive
- [ ] Context updates in real-time
- [ ] Error handling works
- [ ] Mobile responsive

---

## Summary: Phase 3 Frontend

| Item | Status |
|------|--------|
| Context loading | ✅ |
| Enhanced MediatorModal | ✅ |
| Context display component | ✅ |
| Real-time updates | ✅ |
| TypeScript types | ✅ |
| Styling | ✅ |

---

## Next Phase

See `FRONTEND-PHASE-4.md` for dashboard visualizations.
