import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  MessageCircleIcon, SparklesIcon, HeartIcon, LoaderIcon, XIcon,
  BarChart4Icon, RefreshCwIcon, FileTextIcon, ChevronDownIcon, ChevronUpIcon, CopyIcon, CheckIcon,
  AlertCircleIcon, LightbulbIcon, ClockIcon, ShieldIcon, SendIcon, MicIcon, MicOffIcon, PencilIcon,
  LayersIcon, ActivityIcon, PlayIcon, UserIcon
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button } from "@/components/ui/button";
import VoiceButton from '../components/VoiceButton';
import VoiceCallModal from '../components/voice/VoiceCallModal';
import TranscriptBubble from '../components/TranscriptBubble';
import { RelatedConflicts } from '@/components/RelatedConflicts';
import LunaChatPanel from '../components/LunaChatPanel';
import {
  SurfaceUnderlyingCard,
  EmotionalTimelineChart,
  ConflictReplayViewer,
} from '../components/premium';

interface LocationState {
  transcript?: string[];
  interimTranscript?: string;
  conflict_id?: string;
}

interface Message {
  speaker: 'speaker1' | 'speaker2' | 'heartsync';
  message: string;
  isPrivate?: boolean;
}

interface ConflictAnalysis {
  conflict_id: string;
  fight_summary: string;
  root_causes: string[];
  escalation_points: Array<{ timestamp?: number; reason: string; description?: string }>;
  unmet_needs_partner_a?: string[];
  unmet_needs_partner_b?: string[];
  // Backward compatibility
  unmet_needs_boyfriend?: string[];
  unmet_needs_girlfriend?: string[];
  communication_breakdowns: string[];
}

interface RepairPlan {
  conflict_id: string;
  partner_requesting: string;
  steps: string[];
  apology_script: string;
  timing_suggestion: string;
  risk_factors: string[];
}

const PostFightSession = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState | null;

  console.log('🚀 PostFightSession Component Mounted/Rendered');
  console.log('📍 Location:', {
    pathname: location.pathname,
    search: location.search,
    state: location.state,
    key: location.key
  });

  const [isPrivateMode, setIsPrivateMode] = useState(false);

  // Refs must be declared before useEffects that use them
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasAutoAnalyzedRef = useRef<boolean>(false);

  // Initialize conflictId from state - use a function to access location.state safely
  const [conflictId, setConflictId] = useState<string | null>(() => {
    const initialState = (location.state as LocationState | null)?.conflict_id;
    if (initialState) {
      console.log('✅ Initial conflictId from state:', initialState);
      return initialState;
    }
    // Try to get from URL params if state is lost (e.g., page refresh)
    const urlParams = new URLSearchParams(window.location.search);
    const urlConflictId = urlParams.get('conflict_id');
    if (urlConflictId) {
      console.log('✅ Initial conflictId from URL:', urlConflictId);
      return urlConflictId;
    }
    console.log('⚠️ No conflictId found in initial state - will generate one');
    return null;
  });

  // Auto-generate conflict ID if none exists (runs once on mount)
  useEffect(() => {
    const generateConflictId = async () => {
      if (!conflictId) {
        console.log('🆔 No conflict ID found, generating new one...');
        try {
          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/conflicts/create`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'ngrok-skip-browser-warning': 'true'
            },
          });

          if (response.ok) {
            const data = await response.json();
            if (data.conflict_id) {
              console.log('✅ Generated new conflict ID:', data.conflict_id);
              setConflictId(data.conflict_id);
              // Update URL to include conflict_id for bookmarking
              const newUrl = `/post-fight?conflict_id=${data.conflict_id}`;
              window.history.replaceState({ ...location.state, conflict_id: data.conflict_id }, '', newUrl);
            }
          } else {
            // Fallback: Generate UUID on frontend if API fails
            const fallbackId = crypto.randomUUID();
            console.log('⚠️ API failed, using fallback UUID:', fallbackId);
            setConflictId(fallbackId);
            const newUrl = `/post-fight?conflict_id=${fallbackId}`;
            window.history.replaceState({ ...location.state, conflict_id: fallbackId }, '', newUrl);
          }
        } catch (error) {
          // Fallback: Generate UUID on frontend if API fails
          const fallbackId = crypto.randomUUID();
          console.log('⚠️ Error generating conflict ID, using fallback UUID:', fallbackId);
          setConflictId(fallbackId);
          const newUrl = `/post-fight?conflict_id=${fallbackId}`;
          window.history.replaceState({ ...location.state, conflict_id: fallbackId }, '', newUrl);
        }
      }
    };

    generateConflictId();
  }, []); // Only run once on mount

  // Update conflictId when location state changes (e.g., navigating from History)
  useEffect(() => {
    console.log('🔄 useEffect: Checking for conflictId updates', {
      stateConflictId: state?.conflict_id,
      currentConflictId: conflictId,
      locationState: location.state,
      locationSearch: location.search
    });

    // Check navigation state
    if (state?.conflict_id) {
      if (state.conflict_id !== conflictId) {
        console.log('✅ Updating conflictId from navigation state:', state.conflict_id);
        setConflictId(state.conflict_id);
        hasAutoAnalyzedRef.current = false;
      } else {
        console.log('ℹ️ conflictId already set to:', conflictId);
      }
    } else {
      console.log('⚠️ No conflict_id in navigation state');
    }

    // Also check URL params as fallback
    const urlParams = new URLSearchParams(location.search);
    const urlConflictId = urlParams.get('conflict_id');
    if (urlConflictId && urlConflictId !== conflictId) {
      console.log('✅ Updating conflictId from URL params:', urlConflictId);
      setConflictId(urlConflictId);
      hasAutoAnalyzedRef.current = false;
    }
  }, [state?.conflict_id, location.search, location.state, conflictId]);

  const [analysisBoyfriend, setAnalysisBoyfriend] = useState<ConflictAnalysis | null>(null);
  const [repairPlanBoyfriend, setRepairPlanBoyfriend] = useState<RepairPlan | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingRepairPlan, setLoadingRepairPlan] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [repairPlanError, setRepairPlanError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'analysis' | 'repair' | 'chat' | null>(null);
  const [deepInsightsData, setDeepInsightsData] = useState<{
    replayData: any;
    surfaceData: any;
    timelineData: any;
  } | null>(null);
  const [loadingDeepInsights, setLoadingDeepInsights] = useState(false);
  const [deepInsightsSubTab, setDeepInsightsSubTab] = useState<'replay' | 'meanings' | 'timeline'>('replay');
  const [isVoiceCallOpen, setIsVoiceCallOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary', 'root_causes', 'escalation']));
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [title, setTitle] = useState<string>('Post-Fight Session');
  const [activeRepairTab, setActiveRepairTab] = useState<'partner_a' | 'partner_b'>('partner_a');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Helper function to parse transcript lines
  const parseTranscriptLines = (lines: string[]): Message[] => {
    const parsedMessages: Message[] = [];

    // First, join all lines and split by speaker labels to handle concatenated transcripts
    const fullText = lines.join(' ');

    // Regex to split by speaker labels - captures the speaker name
    // Matches: "Adrian:", "Elara:", "Adrian Malhotra:", "Elara Voss:", "Speaker 1:", etc.
    const speakerSplitRegex = /\b(Adrian(?:\s+Malhotra)?|Elara(?:\s+Voss)?|Boyfriend|Girlfriend|Speaker\s+\d+|partner_[ab]):\s*/gi;

    // Split and get all parts
    const parts = fullText.split(speakerSplitRegex).filter(p => p.trim());

    if (parts.length === 0) return parsedMessages;

    // If the first part isn't a speaker label, it's orphan text - assign to speaker1
    let i = 0;
    const isSpeakerLabel = (text: string) => /^(Adrian(?:\s+Malhotra)?|Elara(?:\s+Voss)?|Boyfriend|Girlfriend|Speaker\s+\d+|partner_[ab])$/i.test(text.trim());

    if (!isSpeakerLabel(parts[0])) {
      parsedMessages.push({ speaker: 'speaker1', message: parts[0].trim() });
      i = 1;
    }

    // Process speaker-message pairs
    while (i < parts.length) {
      const speakerLabel = parts[i]?.trim() || '';
      const messageContent = parts[i + 1]?.trim() || '';

      // Determine speaker from label
      let currentSpeaker: 'speaker1' | 'speaker2' = 'speaker1';
      if (/Adrian|Boyfriend|partner_a/i.test(speakerLabel)) {
        currentSpeaker = 'speaker1';
      } else if (/Elara|Girlfriend|partner_b/i.test(speakerLabel)) {
        currentSpeaker = 'speaker2';
      } else if (/Speaker\s+1|Speaker\s+0/i.test(speakerLabel)) {
        currentSpeaker = 'speaker1';
      } else if (/Speaker\s+2/i.test(speakerLabel)) {
        currentSpeaker = 'speaker2';
      }

      if (messageContent) {
        // Always create a new message for each speaker label (don't merge)
        // This preserves the conversation flow
        parsedMessages.push({
          speaker: currentSpeaker,
          message: messageContent
        });
      }

      i += 2;
    }

    return parsedMessages;
  };

  // Initialize messages with transcript
  const [messages, setMessages] = useState<Message[]>(() => {
    if (state?.transcript && state.transcript.length > 0) {
      return parseTranscriptLines(state.transcript);
    }
    return [];
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Track if transcript has been loaded to prevent duplicate fetches
  const transcriptLoadedRef = useRef<string | null>(null);
  const isLoadingTranscriptRef = useRef(false);

  // Load transcript from API if conflictId is present but transcript is not in state
  useEffect(() => {
    const loadTranscript = async () => {
      // Skip if already loading or already loaded for this conflict
      if (isLoadingTranscriptRef.current) {
        console.log('⏳ Already loading transcript, skipping...');
        return;
      }
      if (transcriptLoadedRef.current === conflictId) {
        console.log('✅ Transcript already loaded for this conflict, skipping...');
        return;
      }

      // Only load if we have conflictId but no transcript in state
      if (conflictId && (!state?.transcript || state.transcript.length === 0)) {
        isLoadingTranscriptRef.current = true;
        try {
          console.log(`📖 Loading transcript for conflict ${conflictId}...`);
          const response = await fetch(`${apiUrl}/api/conflicts/${conflictId}`, {
            headers: {
              'ngrok-skip-browser-warning': 'true'
            }
          });

          if (response.ok) {
            const data = await response.json();
            console.log('📄 API response:', data);

            // Check if transcript is in the response (API returns { conflict: {...}, transcript: [...], message: "..." })
            let transcriptLines: string[] = [];

            if (data.transcript) {
              if (Array.isArray(data.transcript)) {
                transcriptLines = data.transcript;
              } else if (data.transcript.segments && Array.isArray(data.transcript.segments)) {
                // Convert segments to lines
                transcriptLines = data.transcript.segments.map((seg: any) => {
                  const speaker = seg.speaker || seg.speaker_name || 'Speaker';
                  return `${speaker}: ${seg.text || seg.transcript || ''}`;
                });
              } else if (typeof data.transcript === 'string') {
                // Single transcript text - split by lines
                transcriptLines = data.transcript.split('\n').filter((line: string) => line.trim());
              } else if (data.transcript.transcript_text) {
                // Nested transcript_text
                const text = data.transcript.transcript_text;
                transcriptLines = text.split('\n').filter((line: string) => line.trim());
              }
            }

            if (transcriptLines.length > 0) {
              console.log(`📝 Parsing ${transcriptLines.length} transcript lines...`);
              // Parse and add to messages using the helper function
              const newMessages = parseTranscriptLines(transcriptLines);
              setMessages(newMessages);
              console.log(`✅ Loaded ${newMessages.length} messages from transcript`);
            } else {
              console.log('⚠️ No transcript lines found in API response');
            }

            // Mark as loaded for this conflict
            transcriptLoadedRef.current = conflictId;
          } else {
            const errorText = await response.text();
            console.error('Failed to load transcript:', response.status, errorText);
          }
        } catch (error) {
          console.error('Error loading transcript:', error);
        } finally {
          isLoadingTranscriptRef.current = false;
        }
      }
    };

    loadTranscript();
  }, [conflictId, apiUrl]); // Removed state?.transcript from dependencies to prevent re-fetching

  // Define functions before useEffects that use them
  const addMessage = useCallback((speaker: 'speaker1' | 'speaker2' | 'heartsync', message: string, isPrivate: boolean = false) => {
    setMessages(prev => [...prev, { speaker, message, isPrivate }]);
  }, []);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedText(id);
      setTimeout(() => setCopiedText(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleGenerateAnalysis = useCallback(async () => {
    console.log('🔄 handleGenerateAnalysis called', { conflictId, analysisBoyfriend: !!analysisBoyfriend, loadingAnalysis });

    if (!conflictId) {
      console.error('❌ No conflictId');
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    // If already generated, just show it
    if (analysisBoyfriend) {
      console.log('✅ Analysis already exists, showing it');
      setActiveView('analysis');
      return;
    }

    // Prevent duplicate requests
    if (loadingAnalysis) {
      console.log('⏳ Already loading, skipping');
      return;
    }

    setLoadingAnalysis(true);
    setAnalysisError(null); // Clear previous error
    console.log('🚀 Starting analysis generation...');

    try {
      const url = `${apiUrl}/api/post-fight/conflicts/${conflictId}/generate-analysis`;
      console.log('📡 Fetching:', url);

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          relationship_id: "00000000-0000-0000-0000-000000000000",
          partner_a_id: "partner_a",
          partner_b_id: "partner_b"
        })
      });

      console.log('📥 Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Response not OK:', errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { detail: response.statusText };
        }
        throw new Error(errorData.detail || `Generation failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('📦 Analysis API Response:', data);

      if (data.success) {
        if (data.analysis_boyfriend) {
          console.log('✅ Setting analysisBoyfriend:', data.analysis_boyfriend);
          setAnalysisBoyfriend(data.analysis_boyfriend);
        } else {
          console.warn('⚠️ No analysis_boyfriend in response');
        }
        setActiveView('analysis');

        // Also fetch deep insights data for the analysis view
        const relationshipId = "00000000-0000-0000-0000-000000000000";
        try {
          const [replayRes, surfaceRes, timelineRes] = await Promise.all([
            fetch(`${apiUrl}/api/analytics/advanced/conflict-replay/${conflictId}?relationship_id=${relationshipId}`, {
              headers: { 'ngrok-skip-browser-warning': 'true' }
            }),
            fetch(`${apiUrl}/api/analytics/advanced/surface-underlying/${conflictId}?relationship_id=${relationshipId}`, {
              headers: { 'ngrok-skip-browser-warning': 'true' }
            }),
            fetch(`${apiUrl}/api/analytics/advanced/emotional-timeline/${conflictId}?relationship_id=${relationshipId}`, {
              headers: { 'ngrok-skip-browser-warning': 'true' }
            })
          ]);

          const replayData = replayRes.ok ? await replayRes.json() : null;
          const surfaceData = surfaceRes.ok ? await surfaceRes.json() : null;
          const timelineData = timelineRes.ok ? await timelineRes.json() : null;

          setDeepInsightsData({ replayData, surfaceData, timelineData });
        } catch (insightsError) {
          console.warn('⚠️ Could not fetch deep insights:', insightsError);
        }
      } else {
        console.error('❌ Response success=false:', data);
        throw new Error(data.detail || 'Generation failed');
      }
    } catch (error: any) {
      console.error('❌ Error generating analysis:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      console.log('Setting analysisError to:', errorMessage);
      setAnalysisError(errorMessage);
      setActiveView('analysis'); // Show the analysis panel with error
    } finally {
      console.log('🏁 Analysis generation complete');
      setLoadingAnalysis(false);
    }
  }, [conflictId, apiUrl, analysisBoyfriend, loadingAnalysis]);

  const handleGenerateRepairPlans = useCallback(async () => {
    if (!conflictId) {
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    // If already generated, just show it
    if (repairPlanBoyfriend) {
      setActiveView('repair');
      return;
    }

    // Prevent duplicate requests
    if (loadingRepairPlan) {
      return;
    }

    setLoadingRepairPlan(true);
    setRepairPlanError(null); // Clear previous error

    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/generate-repair-plans`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          relationship_id: "00000000-0000-0000-0000-000000000000",
          partner_a_id: "partner_a",
          partner_b_id: "partner_b"
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Generation failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('📦 Repair Plans API Response:', data);

      if (data.success) {
        if (data.repair_plan_boyfriend) {
          console.log('✅ Setting repairPlanBoyfriend');
          setRepairPlanBoyfriend(data.repair_plan_boyfriend);
        }
        setActiveView('repair');
      } else {
        throw new Error(data.detail || 'Generation failed');
      }
    } catch (error: any) {
      console.error('Error generating repair plans:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      setRepairPlanError(errorMessage);
      setActiveView('repair'); // Show the repair panel with error
    } finally {
      setLoadingRepairPlan(false);
    }
  }, [conflictId, apiUrl, repairPlanBoyfriend, loadingRepairPlan]);

  const handleGenerateAll = useCallback(async () => {
    if (!conflictId) {
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    // Prevent duplicate requests while loading
    if (loadingAnalysis || loadingRepairPlan) {
      console.log('⏳ Already generating, please wait...');
      return;
    }

    setLoadingAnalysis(true);
    setLoadingRepairPlan(true);

    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/generate-all`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({})
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Generation failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('📦 API Response:', data);
      console.log('📦 Response keys:', Object.keys(data));
      console.log('📦 Has analysis_boyfriend:', !!data.analysis_boyfriend);

      if (data.success) {
        if (data.analysis_boyfriend) {
          console.log('✅ Setting analysisBoyfriend:', data.analysis_boyfriend);
          setAnalysisBoyfriend(data.analysis_boyfriend);
        } else {
          console.warn('⚠️ No analysis_boyfriend in response');
        }
        if (data.repair_plan_boyfriend) {
          console.log('✅ Setting repairPlanBoyfriend');
          setRepairPlanBoyfriend(data.repair_plan_boyfriend);
        }
        // Auto-show analysis tab
        setActiveView('analysis');
      } else {
        throw new Error(data.detail || 'Generation failed');
      }
    } catch (error: any) {
      console.error('Error generating analysis and repair plans:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      addMessage('heartsync', `Sorry, I encountered an error: ${errorMessage}. Please check the backend logs.`);
    } finally {
      setLoadingAnalysis(false);
      setLoadingRepairPlan(false);
    }
  }, [conflictId, apiUrl, addMessage, loadingAnalysis, loadingRepairPlan]);

  // Debug logging for render state
  useEffect(() => {
    console.log('🔍 PostFightSession State:', {
      conflictId,
      hasState: !!state,
      stateConflictId: state?.conflict_id,
      messagesCount: messages.length,
      analysisBoyfriend: !!analysisBoyfriend,
      repairPlanBoyfriend: !!repairPlanBoyfriend,
      activeView,
      locationPath: location.pathname,
      locationState: location.state,
      locationKey: location.key
    });
  }, [conflictId, state, messages.length, analysisBoyfriend, repairPlanBoyfriend, activeView, location.pathname, location.state, location.key]);

  // Always render something - add error boundary
  if (!conflictId && !state?.conflict_id) {
    console.warn('⚠️ No conflictId found - showing fallback UI');
  }

  // Fetch title and poll if needed
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    const fetchTitle = async () => {
      if (!conflictId) return;
      try {
        const response = await fetch(`${apiUrl}/api/conflicts/${conflictId}`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        if (response.ok) {
          const data = await response.json();
          if (data.conflict && data.conflict.title) {
            setTitle(data.conflict.title);
            // Stop polling if we have a real title (not default)
            if (data.conflict.title !== 'Post-Fight Session' && data.conflict.title !== 'Untitled Conflict') {
              clearInterval(pollInterval);
            }
          }
        }
      } catch (error) {
        console.error('Error fetching title:', error);
      }
    };

    if (conflictId) {
      fetchTitle();
      // Poll every 5 seconds if title is default
      pollInterval = setInterval(fetchTitle, 5000);
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [conflictId, apiUrl]);

  const handleUpdateTitle = async () => {
    if (!conflictId || !editedTitle.trim()) return;
    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/title`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ title: editedTitle })
      });

      if (response.ok) {
        setTitle(editedTitle);
        setIsEditingTitle(false);
      } else {
        console.error('Failed to update title');
      }
    } catch (error) {
      console.error('Error updating title:', error);
    }
  };

  return (
    <div className="flex flex-col min-h-[85vh] w-full max-w-full bg-surface-elevated rounded-2xl p-6 shadow-lifted relative z-10 border border-border-subtle">
      {/* Header */}
      <div className="text-center mb-6">
        {isEditingTitle ? (
          <div className="flex items-center justify-center gap-2 mb-2">
            <input
              type="text"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              className="text-h2 text-text-primary text-center bg-white border border-accent rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent/20 min-w-[200px]"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleUpdateTitle();
                if (e.key === 'Escape') setIsEditingTitle(false);
              }}
            />
            <button
              onClick={handleUpdateTitle}
              className="p-1.5 bg-accent text-white rounded-full hover:bg-accent-hover transition-colors"
            >
              <CheckIcon size={18} />
            </button>
            <button
              onClick={() => setIsEditingTitle(false)}
              className="p-1.5 bg-gray-200 text-gray-600 rounded-full hover:bg-gray-300 transition-colors"
            >
              <XIcon size={18} />
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 mb-2 group">
            <h2 className="text-h2 text-text-primary">
              {title}
            </h2>
            <button
              onClick={() => {
                setEditedTitle(title);
                setIsEditingTitle(true);
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-text-tertiary hover:text-accent hover:bg-surface-hover rounded-full"
              title="Edit title"
            >
              <PencilIcon size={16} />
            </button>
          </div>
        )}
        <p className="text-body text-text-secondary">
          Talk freely — Luna is here to help you understand and repair.
        </p>
        {conflictId && (
          <p className="text-tiny text-text-tertiary mt-2 font-mono">
            Conflict ID: {conflictId.substring(0, 8)}...
          </p>
        )}
      </div>

      {/* Main Content - Split Screen */}
      <div className="flex flex-1 gap-6 pb-4 w-full min-h-0">
        {/* Left Side - Conversation */}
        <div className="flex flex-col flex-1 min-w-0 border-r border-gray-200 pr-6">
          {/* Action Buttons - Top Left */}
          {/* Action Buttons - Top Left */}
          <div className="flex flex-col gap-3 mb-4 pb-4 border-b border-border-subtle">
            {!conflictId && (
              <div className="w-full bg-blue-50 border border-blue-100 rounded-xl p-3 mb-2">
                <p className="text-small text-blue-800 font-medium">
                  Generating conflict ID...
                </p>
                <p className="text-tiny text-blue-600 mt-1">
                  Creating a new session for you...
                </p>
              </div>
            )}

            {/* View Buttons - Always visible */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={async () => {
                  if (!analysisBoyfriend) {
                    // Generate both analyses
                    await handleGenerateAnalysis();
                  }
                  setActiveView('analysis');
                }}
                disabled={!conflictId || loadingAnalysis}
                className={`flex items-center py-2.5 px-4 rounded-xl text-small font-medium transition-all shadow-soft hover:shadow-subtle disabled:opacity-50 disabled:cursor-not-allowed ${activeView === 'analysis'
                  ? 'bg-surface-elevated text-text-primary border border-accent'
                  : 'bg-surface-hover text-text-secondary border border-transparent hover:bg-white hover:text-text-primary hover:border-border-subtle'
                  }`}
                title="View conflict analysis (generates both perspectives)"
              >
                {loadingAnalysis && <LoaderIcon size={16} className="mr-2 animate-spin" strokeWidth={1.5} />}
                {!loadingAnalysis && <SparklesIcon size={16} className="mr-2" strokeWidth={1.5} />}
                {loadingAnalysis ? 'Generating Analysis...' : 'View Analysis'}
              </button>

              <button
                onClick={async () => {
                  if (!repairPlanBoyfriend) {
                    // Generate repair plan
                    await handleGenerateRepairPlans();
                  }
                  setActiveView('repair');
                }}
                disabled={!conflictId || loadingRepairPlan}
                className={`flex items-center py-2.5 px-4 rounded-xl text-small font-medium transition-all shadow-soft hover:shadow-subtle disabled:opacity-50 disabled:cursor-not-allowed ${activeView === 'repair'
                  ? 'bg-surface-elevated text-text-primary border border-accent'
                  : 'bg-surface-hover text-text-secondary border border-transparent hover:bg-white hover:text-text-primary hover:border-border-subtle'
                  }`}
                title="View repair plan"
              >
                {loadingRepairPlan && <LoaderIcon size={16} className="mr-2 animate-spin" strokeWidth={1.5} />}
                {!loadingRepairPlan && <HeartIcon size={16} className="mr-2" strokeWidth={1.5} />}
                {loadingRepairPlan ? 'Generating Repair Plan...' : 'View Repair Plan'}
              </button>

              <button
                onClick={() => setActiveView('chat')}
                disabled={!conflictId}
                className={`flex items-center py-2.5 px-4 rounded-xl text-small font-medium transition-all shadow-soft hover:shadow-subtle disabled:opacity-50 disabled:cursor-not-allowed ${activeView === 'chat'
                  ? 'bg-surface-elevated text-text-primary border border-accent'
                  : 'bg-surface-hover text-text-secondary border border-transparent hover:bg-white hover:text-text-primary hover:border-border-subtle'
                  }`}
                title="Chat with Luna about this conflict"
              >
                <MessageCircleIcon size={16} className="mr-2" strokeWidth={1.5} />
                Chat with Luna
              </button>

              <button
                onClick={() => {
                  console.log('🔘 Talk to Luna (Voice) button clicked', { conflictId, activeView });
                  setIsVoiceCallOpen(true);
                }}
                disabled={!conflictId}
                className="flex items-center py-2.5 px-4 rounded-xl text-small font-medium transition-all shadow-soft hover:shadow-subtle disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-rose-500 to-purple-500 text-white hover:from-rose-600 hover:to-purple-600"
              >
                <MicIcon size={16} className="mr-2" strokeWidth={1.5} />
                Talk to Luna
              </button>
            </div>
          </div>

          {/* Messages/Transcript */}
          <div className="flex-1 overflow-y-auto pr-2">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <FileTextIcon size={48} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm">
                    {conflictId
                      ? 'Loading transcript...'
                      : 'No transcript available. Start a fight capture session to record a conflict.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((msg, idx) => {
                  if (msg.speaker === 'heartsync') {
                    return <TranscriptBubble key={idx} speaker="heartsync" message={msg.message} isPrivate={msg.isPrivate} />;
                  } else {
                    const isBoyfriend = msg.speaker === 'speaker1';
                    return (
                      <div key={idx} className={`flex w-full ${isBoyfriend ? 'justify-start' : 'justify-end'}`}>
                        <div className={`rounded-2xl py-3 px-5 max-w-[85%] shadow-sm border ${isBoyfriend
                          ? 'bg-surface-hover text-text-primary border-border-subtle rounded-tl-sm'
                          : 'bg-white text-text-primary border-accent/20 rounded-tr-sm'
                          } ${msg.isPrivate ? 'opacity-70 border-dashed border-accent' : ''}`}>
                          <div className="text-tiny font-medium mb-1 text-text-tertiary">
                            {isBoyfriend ? 'Adrian Malhotra' : 'Elara Voss'}
                            {msg.isPrivate && <span className="ml-2 text-accent text-tiny">🔒 Private</span>}
                          </div>
                          <div className="text-body leading-relaxed">{msg.message}</div>
                        </div>
                      </div>
                    );
                  }
                })}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Right Side - Results Panel */}
        <div className="flex-1 min-w-0 overflow-y-auto pl-6">
          {activeView === 'chat' && conflictId && (
            <div className="h-full animate-slide-up">
              <LunaChatPanel conflictId={conflictId} />
            </div>
          )}
          {activeView === 'analysis' && (
            <div className="bg-surface-elevated rounded-2xl p-6 shadow-lifted border border-border-subtle animate-slide-up">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <div className="bg-surface-hover p-2.5 rounded-xl mr-3 border border-border-subtle">
                    <SparklesIcon size={20} className="text-accent" strokeWidth={1.5} />
                  </div>
                  <h3 className="text-h3 text-text-primary">Conflict Analysis</h3>
                </div>
                <button
                  onClick={() => setActiveView(null)}
                  className="text-text-tertiary hover:text-text-primary transition-colors p-2 hover:bg-surface-hover rounded-full"
                >
                  <XIcon size={20} strokeWidth={1.5} />
                </button>
              </div>

              {loadingAnalysis ? (
                <div className="flex items-center justify-center py-12">
                  <LoaderIcon size={24} className="animate-spin text-purple-500 mr-3" />
                  <span className="text-gray-600">Analyzing conflict from your perspective...</span>
                </div>
              ) : analysisError ? (
                <div className="bg-red-50 rounded-xl p-6 border border-red-200">
                  <div className="flex items-start">
                    <AlertCircleIcon size={24} className="text-red-500 mr-3 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-red-800 mb-2">Error Generating Analysis</h4>
                      <p className="text-red-700 text-sm mb-4">{analysisError}</p>
                      <button
                        onClick={() => {
                          setAnalysisError(null);
                          setAnalysisBoyfriend(null);
                          handleGenerateAnalysis();
                        }}
                        className="bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
                      >
                        <RefreshCwIcon size={16} className="mr-2" />
                        Retry
                      </button>
                    </div>
                  </div>
                </div>
              ) : analysisBoyfriend ? (
                <>
                  {analysisBoyfriend && (
                    <div className="space-y-4">
                      {/* Summary */}
                      <div className="bg-white rounded-xl p-4 border border-purple-100">
                        <button
                          onClick={() => toggleSection('summary')}
                          className="w-full flex items-center justify-between mb-2"
                        >
                          <div className="flex items-center">
                            <LightbulbIcon size={18} className="text-purple-500 mr-2" />
                            <h4 className="font-semibold text-gray-800">Summary</h4>
                          </div>
                          {expandedSections.has('summary') ?
                            <ChevronUpIcon size={18} className="text-gray-400" /> :
                            <ChevronDownIcon size={18} className="text-gray-400" />
                          }
                        </button>
                        {expandedSections.has('summary') && (
                          <p className="text-gray-700 leading-relaxed">{analysisBoyfriend.fight_summary}</p>
                        )}
                      </div>

                      {/* Root Causes */}
                      {(analysisBoyfriend.root_causes || []).length > 0 && (
                        <div className="bg-white rounded-xl p-4 border border-purple-100">
                          <button
                            onClick={() => toggleSection('root_causes')}
                            className="w-full flex items-center justify-between mb-2"
                          >
                            <div className="flex items-center">
                              <AlertCircleIcon size={18} className="text-orange-500 mr-2" />
                              <h4 className="font-semibold text-gray-800">Root Causes</h4>
                              <span className="ml-2 text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">
                                {(analysisBoyfriend.root_causes || []).length}
                              </span>
                            </div>
                            {expandedSections.has('root_causes') ?
                              <ChevronUpIcon size={18} className="text-gray-400" /> :
                              <ChevronDownIcon size={18} className="text-gray-400" />
                            }
                          </button>
                          {expandedSections.has('root_causes') && (
                            <ul className="space-y-2">
                              {(analysisBoyfriend.root_causes || []).map((cause, idx) => (
                                <li key={idx} className="flex items-start text-gray-700">
                                  <span className="text-orange-500 mr-2 mt-1">•</span>
                                  <span>{cause}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}

                      {/* Unmet Needs */}
                      {((analysisBoyfriend.unmet_needs_partner_a || analysisBoyfriend.unmet_needs_boyfriend || []).length > 0 ||
                        (analysisBoyfriend.unmet_needs_partner_b || analysisBoyfriend.unmet_needs_girlfriend || []).length > 0) && (
                        <div className="grid grid-cols-1 gap-4">
                          {(analysisBoyfriend.unmet_needs_partner_a || analysisBoyfriend.unmet_needs_boyfriend || []).length > 0 && (
                            <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                              <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                                <span className="bg-blue-200 px-2 py-0.5 rounded text-xs mr-2">Your Needs</span>
                                Unmet Needs
                              </h4>
                              <ul className="space-y-1.5">
                                {(analysisBoyfriend.unmet_needs_partner_a || analysisBoyfriend.unmet_needs_boyfriend || []).map((need, idx) => (
                                  <li key={idx} className="text-sm text-gray-700 flex items-start">
                                    <span className="text-blue-500 mr-2 mt-1">•</span>
                                    <span>{need}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {(analysisBoyfriend.unmet_needs_partner_b || analysisBoyfriend.unmet_needs_girlfriend || []).length > 0 && (
                            <div className="bg-pink-50 rounded-xl p-4 border border-pink-100">
                              <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                                <span className="bg-pink-200 px-2 py-0.5 rounded text-xs mr-2">Partner's Needs</span>
                                Unmet Needs
                              </h4>
                              <ul className="space-y-1.5">
                                {(analysisBoyfriend.unmet_needs_partner_b || analysisBoyfriend.unmet_needs_girlfriend || []).map((need, idx) => (
                                  <li key={idx} className="text-sm text-gray-700 flex items-start">
                                    <span className="text-pink-500 mr-2 mt-1">•</span>
                                    <span>{need}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Escalation Points */}
                      {analysisBoyfriend.escalation_points && analysisBoyfriend.escalation_points.length > 0 && (
                        <div className="bg-white rounded-xl p-4 border border-red-100">
                          <button
                            onClick={() => toggleSection('escalation')}
                            className="w-full flex items-center justify-between mb-2"
                          >
                            <div className="flex items-center">
                              <AlertCircleIcon size={18} className="text-red-500 mr-2" />
                              <h4 className="font-semibold text-gray-800">Escalation Points</h4>
                              <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                                {analysisBoyfriend.escalation_points.length}
                              </span>
                            </div>
                            {expandedSections.has('escalation') ?
                              <ChevronUpIcon size={18} className="text-gray-400" /> :
                              <ChevronDownIcon size={18} className="text-gray-400" />
                            }
                          </button>
                          {expandedSections.has('escalation') && (
                            <div className="space-y-3">
                              {analysisBoyfriend.escalation_points.map((point, idx) => (
                                <div key={idx} className="bg-red-50 rounded-lg p-3">
                                  <p className="font-medium text-gray-800 text-sm">{point.reason}</p>
                                  {point.description && (
                                    <p className="text-xs text-gray-600 mt-1">{point.description}</p>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  {/* Related Conflicts Graph */}
                  <RelatedConflicts
                    conflictId={conflictId || ''}
                    apiBase={import.meta.env.VITE_API_URL || 'http://localhost:8000'}
                  />

                  {/* Deep Insights Section */}
                  {deepInsightsData && (
                    <div className="mt-6 space-y-4">
                      {/* Deep Insights Sub-tabs */}
                      <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
                        <button
                          onClick={() => setDeepInsightsSubTab('replay')}
                          className={`flex-1 py-2 px-3 rounded-lg text-tiny font-medium transition-all flex items-center justify-center gap-1.5 ${
                            deepInsightsSubTab === 'replay'
                              ? 'bg-white text-text-primary shadow-sm'
                              : 'text-text-secondary hover:text-text-primary'
                          }`}
                        >
                          <PlayIcon size={14} />
                          Replay
                        </button>
                        <button
                          onClick={() => setDeepInsightsSubTab('meanings')}
                          className={`flex-1 py-2 px-3 rounded-lg text-tiny font-medium transition-all flex items-center justify-center gap-1.5 ${
                            deepInsightsSubTab === 'meanings'
                              ? 'bg-white text-text-primary shadow-sm'
                              : 'text-text-secondary hover:text-text-primary'
                          }`}
                        >
                          <LayersIcon size={14} />
                          What They Meant
                        </button>
                        <button
                          onClick={() => setDeepInsightsSubTab('timeline')}
                          className={`flex-1 py-2 px-3 rounded-lg text-tiny font-medium transition-all flex items-center justify-center gap-1.5 ${
                            deepInsightsSubTab === 'timeline'
                              ? 'bg-white text-text-primary shadow-sm'
                              : 'text-text-secondary hover:text-text-primary'
                          }`}
                        >
                          <ActivityIcon size={14} />
                          Emotional Arc
                        </button>
                      </div>

                      {/* Deep Insights Content */}
                      <div className="bg-white rounded-xl p-4 border border-purple-100">
                        {deepInsightsSubTab === 'replay' && (
                          <ConflictReplayViewer
                            messages={deepInsightsData.replayData?.messages || []}
                            surfaceUnderlying={deepInsightsData.replayData?.surface_underlying}
                            partnerAName="Adrian"
                            partnerBName="Elara"
                          />
                        )}
                        {deepInsightsSubTab === 'meanings' && (
                          <SurfaceUnderlyingCard
                            mappings={deepInsightsData.surfaceData?.mappings || []}
                            overallPattern={deepInsightsData.surfaceData?.overall_pattern}
                            keyInsight={deepInsightsData.surfaceData?.key_insight}
                          />
                        )}
                        {deepInsightsSubTab === 'timeline' && (
                          <EmotionalTimelineChart
                            moments={deepInsightsData.timelineData?.moments || []}
                            summary={deepInsightsData.timelineData?.summary}
                          />
                        )}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <SparklesIcon size={48} className="mx-auto mb-3 text-gray-300" />
                  <p>Click "View Analysis" to generate and see insights</p>
                </div>
              )}
            </div>
          )}

          {activeView === 'repair' && (
            <div className="bg-gradient-to-br from-rose-50 to-white rounded-2xl p-5 shadow-lg border border-rose-100">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="bg-rose-100 p-2 rounded-lg mr-3">
                    <HeartIcon size={20} className="text-rose-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-800">Repair Plans</h3>
                </div>
                <button
                  onClick={() => setActiveView(null)}
                  className="text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-100 rounded"
                >
                  <XIcon size={18} />
                </button>
              </div>


              {loadingRepairPlan ? (
                <div className="flex items-center justify-center py-12">
                  <LoaderIcon size={24} className="animate-spin text-rose-500 mr-3" />
                  <span className="text-gray-600">Generating personalized repair plan...</span>
                </div>
              ) : repairPlanError ? (
                <div className="bg-red-50 rounded-xl p-6 border border-red-200">
                  <div className="flex items-start">
                    <AlertCircleIcon size={24} className="text-red-500 mr-3 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-red-800 mb-2">Error Generating Repair Plans</h4>
                      <p className="text-red-700 text-sm mb-4">{repairPlanError}</p>
                      <button
                        onClick={() => {
                          setRepairPlanError(null);
                          setRepairPlanBoyfriend(null);
                          setRepairPlanGirlfriend(null);
                          handleGenerateRepairPlans();
                        }}
                        className="bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
                      >
                        <RefreshCwIcon size={16} className="mr-2" />
                        Retry
                      </button>
                    </div>
                  </div>
                </div>
              ) : repairPlanBoyfriend ? (
                <>
                  {/* Repair Plan */}
                  {repairPlanBoyfriend && (
                    <div className="space-y-4 animate-fade-in">

                      {/* Steps */}
                      <div className="bg-white rounded-xl p-4 border border-rose-100">
                        <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                          <LightbulbIcon size={18} className="text-rose-500 mr-2" />
                          Action Steps
                        </h4>
                        <ol className="space-y-3">
                          {repairPlanBoyfriend.steps.map((step, idx) => (
                            <li key={idx} className="flex items-start text-gray-700">
                              <span className="bg-blue-100 text-blue-700 font-semibold rounded-full w-6 h-6 flex items-center justify-center text-xs mr-3 mt-0.5 flex-shrink-0">
                                {idx + 1}
                              </span>
                              <span className="flex-1">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>

                      {/* Apology Script */}
                      <div className="bg-gradient-to-r from-blue-50 to-rose-50 rounded-xl p-5 border-2 border-blue-200">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold text-gray-800 flex items-center">
                            <HeartIcon size={18} className="text-blue-500 mr-2" />
                            Apology Script
                          </h4>
                          <button
                            onClick={() => copyToClipboard(repairPlanBoyfriend.apology_script, 'apology-bf')}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title="Copy to clipboard"
                          >
                            {copiedText === 'apology-bf' ? (
                              <CheckIcon size={18} className="text-green-500" />
                            ) : (
                              <CopyIcon size={18} />
                            )}
                          </button>
                        </div>
                        <p className="text-gray-700 leading-relaxed italic whitespace-pre-wrap">
                          {repairPlanBoyfriend.apology_script}
                        </p>
                      </div>

                      {/* Timing */}
                      <div className="bg-white rounded-xl p-4 border border-rose-100">
                        <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                          <ClockIcon size={18} className="text-blue-500 mr-2" />
                          Timing Suggestion
                        </h4>
                        <p className="text-gray-700 text-sm">{repairPlanBoyfriend.timing_suggestion}</p>
                      </div>

                      {/* Risk Factors */}
                      {repairPlanBoyfriend.risk_factors && repairPlanBoyfriend.risk_factors.length > 0 && (
                        <div className="bg-yellow-50 rounded-xl p-4 border border-yellow-200">
                          <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                            <ShieldIcon size={18} className="text-yellow-600 mr-2" />
                            Things to Avoid
                          </h4>
                          <ul className="space-y-2">
                            {repairPlanBoyfriend.risk_factors.map((risk, idx) => (
                              <li key={idx} className="flex items-start text-sm text-gray-700">
                                <span className="text-yellow-600 mr-2 mt-1">⚠</span>
                                <span>{risk}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* No plan available */}
                  {!repairPlanBoyfriend && (
                    <div className="text-center py-8 text-gray-500">
                      <AlertCircleIcon size={32} className="mx-auto mb-3 text-gray-300" />
                      <p>Repair plan is not available yet.</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <HeartIcon size={48} className="mx-auto mb-3 text-gray-300" />
                  <p>Click "View Repair Plan" to generate personalized repair steps</p>
                </div>
              )}
            </div>
          )}

          {!activeView && (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <SparklesIcon size={48} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">Select an action to see results here</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Voice Call Modal */}
      {conflictId && (
        <VoiceCallModal
          isOpen={isVoiceCallOpen}
          onClose={() => setIsVoiceCallOpen(false)}
          conflictId={conflictId || ''}
          relationshipId={conflictId || ''} // Use conflict_id as relationship context
          partnerAName="Adrian"
          partnerBName="Elara"
        />
      )}
    </div>
  );
};

export default PostFightSession;
