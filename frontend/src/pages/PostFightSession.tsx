import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, MessageCircle, Sparkles, Brain, Heart, Shield, Zap, ChevronRight, Play, Pause, RotateCcw, Volume2, VolumeX, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { RelatedConflicts } from '@/components/RelatedConflicts';
import { Button } from "@/components/ui/button";
import TranscriptBubble from '../components/TranscriptBubble';
import MediatorModal from '../components/MediatorModal';
import {
  BarChart4Icon, RefreshCwIcon, FileTextIcon, SparklesIcon, HeartIcon,
  LoaderIcon, ChevronDownIcon, ChevronUpIcon, CopyIcon, CheckIcon,
  AlertCircleIcon, LightbulbIcon, ClockIcon, ShieldIcon, XIcon, SendIcon, MicIcon, MicOffIcon, MessageCircleIcon
} from 'lucide-react';

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
  unmet_needs_boyfriend: string[];
  unmet_needs_girlfriend: string[];
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
          const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
          const response = await fetch(`${apiUrl}/api/conflicts/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
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
  const [repairPlanGirlfriend, setRepairPlanGirlfriend] = useState<RepairPlan | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingRepairPlan, setLoadingRepairPlan] = useState(false);
  const [activeView, setActiveView] = useState<'analysis' | 'repair' | null>(null);
  const [povView, setPovView] = useState<'boyfriend' | 'girlfriend'>('boyfriend'); // POV switcher for both analysis and repair plans
  const [isMediatorModalOpen, setIsMediatorModalOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary', 'root_causes', 'escalation']));
  const [copiedText, setCopiedText] = useState<string | null>(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Initialize messages with transcript (merge consecutive messages from same speaker)
  const [messages, setMessages] = useState<Message[]>(() => {
    const initialMessages: Message[] = [];

    if (state?.transcript && state.transcript.length > 0) {
      state.transcript.forEach((line: string) => {
        const boyfriendMatch = line.match(/^(?:Adrian Malhotra|Boyfriend|Speaker\s+1):\s*(.+)$/i);
        const girlfriendMatch = line.match(/^(?:Elara Voss|Girlfriend|Speaker\s+2):\s*(.+)$/i);

        let currentSpeaker: 'speaker1' | 'speaker2' | null = null;
        let messageText = '';

        if (boyfriendMatch) {
          currentSpeaker = 'speaker1';
          messageText = boyfriendMatch[1].trim();
        } else if (girlfriendMatch) {
          currentSpeaker = 'speaker2';
          messageText = girlfriendMatch[1].trim();
        } else {
          const cleanedText = line.replace(/^(?:You|Adrian Malhotra|Elara Voss|Boyfriend|Girlfriend|Speaker\s+\d+):\s*/i, '').trim();
          if (cleanedText) {
            currentSpeaker = 'speaker1';
            messageText = cleanedText;
          }
        }

        if (currentSpeaker && messageText) {
          // Check if last message is from same speaker - merge them
          const lastMessage = initialMessages[initialMessages.length - 1];
          if (lastMessage && lastMessage.speaker === currentSpeaker) {
            // Merge with previous message from same speaker
            lastMessage.message += ' ' + messageText;
          } else {
            // New speaker or first message - add as new message
            initialMessages.push({
              speaker: currentSpeaker,
              message: messageText
            });
          }
        }
      });
    }

    return initialMessages;
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load transcript from API if conflictId is present but transcript is not in state
  useEffect(() => {
    const loadTranscript = async () => {
      // Only load if we have conflictId but no transcript in state
      if (conflictId && (!state?.transcript || state.transcript.length === 0)) {
        try {
          console.log(`📖 Loading transcript for conflict ${conflictId}...`);
          const response = await fetch(`${apiUrl}/api/conflicts/${conflictId}`);

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
              // Parse and add to messages
              const newMessages: Message[] = [];
              transcriptLines.forEach((line: string) => {
                const boyfriendMatch = line.match(/^(?:Adrian Malhotra|Boyfriend|Speaker\s+1|partner_a|Speaker\s+0):\s*(.+)$/i);
                const girlfriendMatch = line.match(/^(?:Elara Voss|Girlfriend|Speaker\s+2|partner_b|Speaker\s+1):\s*(.+)$/i);

                let currentSpeaker: 'speaker1' | 'speaker2' | null = null;
                let messageText = '';

                if (boyfriendMatch) {
                  currentSpeaker = 'speaker1';
                  messageText = boyfriendMatch[1].trim();
                } else if (girlfriendMatch) {
                  currentSpeaker = 'speaker2';
                  messageText = girlfriendMatch[1].trim();
                } else {
                  // Try to extract any text after colon
                  const colonIndex = line.indexOf(':');
                  if (colonIndex > 0) {
                    const cleanedText = line.substring(colonIndex + 1).trim();
                    if (cleanedText) {
                      currentSpeaker = 'speaker1'; // Default to speaker1
                      messageText = cleanedText;
                    }
                  }
                }

                if (currentSpeaker && messageText) {
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage && lastMessage.speaker === currentSpeaker) {
                    // Merge with previous message from same speaker
                    lastMessage.message += ' ' + messageText;
                  } else {
                    // New speaker or first message - add as new message
                    newMessages.push({
                      speaker: currentSpeaker,
                      message: messageText
                    });
                  }
                }
              });

              if (newMessages.length > 0) {
                setMessages(newMessages);
                console.log(`✅ Loaded ${newMessages.length} messages from transcript`);
              } else {
                console.warn('⚠️ No valid messages parsed from transcript lines');
              }
            } else {
              console.log('⚠️ No transcript lines found in API response');
            }
          } else {
            const errorText = await response.text();
            console.error('Failed to load transcript:', response.status, errorText);
          }
        } catch (error) {
          console.error('Error loading transcript:', error);
        }
      }
    };

    loadTranscript();
  }, [conflictId, state?.transcript, apiUrl]);

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
    if (!conflictId) {
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    // If already generated, just show it
    if (analysisBoyfriend) {
      setActiveView('analysis');
      return;
    }

    // Prevent duplicate requests
    if (loadingAnalysis) {
      return;
    }

    setLoadingAnalysis(true);

    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/generate-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      console.log('📦 Analysis API Response:', data);

      if (data.success) {
        if (data.analysis_boyfriend) {
          console.log('✅ Setting analysisBoyfriend');
          setAnalysisBoyfriend(data.analysis_boyfriend);
        }
        addMessage('heartsync', `I've analyzed your conflict from your perspective.`);
        setActiveView('analysis');
      } else {
        throw new Error(data.detail || 'Generation failed');
      }
    } catch (error: any) {
      console.error('Error generating analysis:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      addMessage('heartsync', `Sorry, I encountered an error: ${errorMessage}. Please check the backend logs.`);
    } finally {
      setLoadingAnalysis(false);
    }
  }, [conflictId, apiUrl, addMessage, analysisBoyfriend, loadingAnalysis]);

  const handleGenerateRepairPlans = useCallback(async () => {
    if (!conflictId) {
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    // If already generated, just show it
    if (repairPlanBoyfriend && repairPlanGirlfriend) {
      setActiveView('repair');
      return;
    }

    // Prevent duplicate requests
    if (loadingRepairPlan) {
      return;
    }

    setLoadingRepairPlan(true);

    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/generate-repair-plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        if (data.repair_plan_girlfriend) {
          console.log('✅ Setting repairPlanGirlfriend');
          setRepairPlanGirlfriend(data.repair_plan_girlfriend);
        }
        addMessage('heartsync', `I've prepared personalized repair plans for both partners. Use the POV switcher to see each partner's view.`);
        setActiveView('repair');
      } else {
        throw new Error(data.detail || 'Generation failed');
      }
    } catch (error: any) {
      console.error('Error generating repair plans:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      addMessage('heartsync', `Sorry, I encountered an error: ${errorMessage}. Please check the backend logs.`);
    } finally {
      setLoadingRepairPlan(false);
    }
  }, [conflictId, apiUrl, addMessage, repairPlanBoyfriend, repairPlanGirlfriend, loadingRepairPlan]);

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
        headers: { 'Content-Type': 'application/json' },
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
      console.log('📦 Has analysis_girlfriend:', !!data.analysis_girlfriend);

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
        if (data.repair_plan_girlfriend) {
          console.log('✅ Setting repairPlanGirlfriend');
          setRepairPlanGirlfriend(data.repair_plan_girlfriend);
        }
        addMessage('heartsync', `I've analyzed your conflict from both perspectives and prepared personalized repair plans for both partners. Use the POV switcher to see each partner's view.`);
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

  // Removed handleGetRepairPlan - now handled by handleGenerateAll

  // Debug logging for render state
  useEffect(() => {
    console.log('🔍 PostFightSession State:', {
      conflictId,
      hasState: !!state,
      stateConflictId: state?.conflict_id,
      messagesCount: messages.length,
      analysisBoyfriend: !!analysisBoyfriend,
      repairPlanBoyfriend: !!repairPlanBoyfriend,
      repairPlanGirlfriend: !!repairPlanGirlfriend,
      povView,
      activeView,
      locationPath: location.pathname,
      locationState: location.state,
      locationKey: location.key
    });
  }, [conflictId, state, messages.length, analysisBoyfriend, repairPlanBoyfriend, repairPlanGirlfriend, povView, activeView, location.pathname, location.state, location.key]);

  // Always render something - add error boundary
  if (!conflictId && !state?.conflict_id) {
    console.warn('⚠️ No conflictId found - showing fallback UI');
  }

  return (
    <div className="flex flex-col min-h-[85vh] w-full max-w-full bg-white/50 backdrop-blur-sm rounded-xl p-6 shadow-lg relative z-10">
      {/* Header */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-semibold text-gray-800 mb-1">
          Post-Fight Session
        </h2>
        <p className="text-sm text-gray-600">
          Talk freely — HeartSync is here to help you understand and repair.
        </p>
        {conflictId && (
          <p className="text-xs text-gray-500 mt-2 font-mono">
            Conflict ID: {conflictId.substring(0, 8)}...
          </p>
        )}
      </div>

      {/* Main Content - Split Screen */}
      <div className="flex flex-1 gap-6 pb-4 w-full min-h-0">
        {/* Left Side - Conversation */}
        <div className="flex flex-col flex-1 min-w-0 border-r border-gray-200 pr-6">
          {/* Action Buttons - Top Left */}
          <div className="flex flex-col gap-3 mb-4 pb-4 border-b border-gray-200">
            {!conflictId && (
              <div className="w-full bg-blue-50 border border-blue-200 rounded-lg p-3 mb-2">
                <p className="text-sm text-blue-800 font-medium">
                  🆔 Generating conflict ID...
                </p>
                <p className="text-xs text-blue-600 mt-1">
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
                className={`flex items-center py-2 px-4 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${activeView === 'analysis'
                  ? 'bg-purple-200 text-purple-800 border-2 border-purple-400'
                  : 'bg-purple-100 hover:bg-purple-200 text-purple-700'
                  }`}
                title="View conflict analysis (generates both perspectives)"
              >
                {loadingAnalysis && <LoaderIcon size={16} className="mr-2 animate-spin" />}
                {!loadingAnalysis && <SparklesIcon size={16} className="mr-2" />}
                {loadingAnalysis ? 'Generating Analysis...' : 'View Analysis'}
              </button>

              <button
                onClick={async () => {
                  if (!repairPlanBoyfriend && !repairPlanGirlfriend) {
                    // Generate both repair plans
                    await handleGenerateRepairPlans();
                  }
                  setActiveView('repair');
                }}
                disabled={!conflictId || loadingRepairPlan}
                className={`flex items-center py-2 px-4 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${activeView === 'repair'
                  ? 'bg-rose-200 text-rose-800 border-2 border-rose-400'
                  : 'bg-rose-100 hover:bg-rose-200 text-rose-700'
                  }`}
                title="View repair plans (generates both perspectives)"
              >
                {loadingRepairPlan && <LoaderIcon size={16} className="mr-2 animate-spin" />}
                {!loadingRepairPlan && <HeartIcon size={16} className="mr-2" />}
                {loadingRepairPlan ? 'Generating Repair Plans...' : 'View Repair Plan'}
              </button>

              <button
                onClick={() => {
                  console.log('🔘 Talk to Mediator button clicked', { conflictId, activeView, povView });
                  setIsMediatorModalOpen(true);
                }}
                disabled={!conflictId}
                className="flex items-center py-2 px-4 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed bg-blue-100 hover:bg-blue-200 text-blue-700"
              >
                <MessageCircleIcon size={16} className="mr-2" />
                Talk to Mediator
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
                        <div className={`rounded-2xl py-2.5 px-4 max-w-[85%] shadow-sm ${isBoyfriend
                          ? 'bg-blue-100 text-gray-800'
                          : 'bg-pink-100 text-gray-800'
                          } ${msg.isPrivate ? 'opacity-70 border-2 border-rose-300' : ''}`}>
                          <div className="text-xs font-semibold mb-1 text-gray-600">
                            {isBoyfriend ? 'Adrian Malhotra' : 'Elara Voss'}
                            {msg.isPrivate && <span className="ml-2 text-rose-500 text-[10px]">🔒 Private</span>}
                          </div>
                          <div className="text-sm leading-relaxed">{msg.message}</div>
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
          {activeView === 'analysis' && (
            <div className="bg-gradient-to-br from-purple-50 to-white rounded-2xl p-5 shadow-lg border border-purple-100">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="bg-purple-100 p-2 rounded-lg mr-3">
                    <SparklesIcon size={20} className="text-purple-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-800">Conflict Analysis</h3>
                </div>
                <button
                  onClick={() => setActiveView(null)}
                  className="text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-100 rounded"
                >
                  <XIcon size={18} />
                </button>
              </div>

              {loadingAnalysis ? (
                <div className="flex items-center justify-center py-12">
                  <LoaderIcon size={24} className="animate-spin text-purple-500 mr-3" />
                  <span className="text-gray-600">Analyzing conflict from your perspective...</span>
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
                      {analysisBoyfriend.root_causes.length > 0 && (
                        <div className="bg-white rounded-xl p-4 border border-purple-100">
                          <button
                            onClick={() => toggleSection('root_causes')}
                            className="w-full flex items-center justify-between mb-2"
                          >
                            <div className="flex items-center">
                              <AlertCircleIcon size={18} className="text-orange-500 mr-2" />
                              <h4 className="font-semibold text-gray-800">Root Causes</h4>
                              <span className="ml-2 text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">
                                {analysisBoyfriend.root_causes.length}
                              </span>
                            </div>
                            {expandedSections.has('root_causes') ?
                              <ChevronUpIcon size={18} className="text-gray-400" /> :
                              <ChevronDownIcon size={18} className="text-gray-400" />
                            }
                          </button>
                          {expandedSections.has('root_causes') && (
                            <ul className="space-y-2">
                              {analysisBoyfriend.root_causes.map((cause, idx) => (
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
                      {(analysisBoyfriend.unmet_needs_boyfriend.length > 0 || analysisBoyfriend.unmet_needs_girlfriend.length > 0) && (
                        <div className="grid grid-cols-1 gap-4">
                          {analysisBoyfriend.unmet_needs_boyfriend.length > 0 && (
                            <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                              <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                                <span className="bg-blue-200 px-2 py-0.5 rounded text-xs mr-2">Your Needs</span>
                                Unmet Needs
                              </h4>
                              <ul className="space-y-1.5">
                                {analysisBoyfriend.unmet_needs_boyfriend.map((need, idx) => (
                                  <li key={idx} className="text-sm text-gray-700 flex items-start">
                                    <span className="text-blue-500 mr-2 mt-1">•</span>
                                    <span>{need}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {analysisBoyfriend.unmet_needs_girlfriend.length > 0 && (
                            <div className="bg-pink-50 rounded-xl p-4 border border-pink-100">
                              <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                                <span className="bg-pink-200 px-2 py-0.5 rounded text-xs mr-2">Partner's Needs</span>
                                Unmet Needs
                              </h4>
                              <ul className="space-y-1.5">
                                {analysisBoyfriend.unmet_needs_girlfriend.map((need, idx) => (
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
                  <h3 className="text-lg font-semibold text-gray-800">Repair Plan</h3>
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
                  <span className="text-gray-600">Generating personalized repair plans...</span>
                </div>
              ) : (repairPlanBoyfriend || repairPlanGirlfriend) ? (
                <>
                  {povView === 'boyfriend' && repairPlanBoyfriend && (
                    <div className="space-y-4">
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

                  {povView === 'girlfriend' && repairPlanGirlfriend && (
                    <div className="space-y-4">
                      <div className="bg-pink-50 border border-pink-200 rounded-lg p-3 mb-4">
                        <p className="text-sm text-pink-800 font-medium">👤 Girlfriend's Personalized Repair Plan</p>
                        <p className="text-xs text-pink-600 mt-1">Tailored based on your profile and this conflict</p>
                      </div>

                      {/* Steps */}
                      <div className="bg-white rounded-xl p-4 border border-rose-100">
                        <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                          <LightbulbIcon size={18} className="text-rose-500 mr-2" />
                          Action Steps
                        </h4>
                        <ol className="space-y-3">
                          {repairPlanGirlfriend.steps.map((step, idx) => (
                            <li key={idx} className="flex items-start text-gray-700">
                              <span className="bg-pink-100 text-pink-700 font-semibold rounded-full w-6 h-6 flex items-center justify-center text-xs mr-3 mt-0.5 flex-shrink-0">
                                {idx + 1}
                              </span>
                              <span className="flex-1">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>

                      {/* Apology Script */}
                      <div className="bg-gradient-to-r from-pink-50 to-rose-50 rounded-xl p-5 border-2 border-pink-200">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold text-gray-800 flex items-center">
                            <HeartIcon size={18} className="text-pink-500 mr-2" />
                            Apology Script
                          </h4>
                          <button
                            onClick={() => copyToClipboard(repairPlanGirlfriend.apology_script, 'apology-gf')}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title="Copy to clipboard"
                          >
                            {copiedText === 'apology-gf' ? (
                              <CheckIcon size={18} className="text-green-500" />
                            ) : (
                              <CopyIcon size={18} />
                            )}
                          </button>
                        </div>
                        <p className="text-gray-700 leading-relaxed italic whitespace-pre-wrap">
                          {repairPlanGirlfriend.apology_script}
                        </p>
                      </div>

                      {/* Timing */}
                      <div className="bg-white rounded-xl p-4 border border-rose-100">
                        <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                          <ClockIcon size={18} className="text-pink-500 mr-2" />
                          Timing Suggestion
                        </h4>
                        <p className="text-gray-700 text-sm">{repairPlanGirlfriend.timing_suggestion}</p>
                      </div>

                      {/* Risk Factors */}
                      {repairPlanGirlfriend.risk_factors && repairPlanGirlfriend.risk_factors.length > 0 && (
                        <div className="bg-yellow-50 rounded-xl p-4 border border-yellow-200">
                          <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                            <ShieldIcon size={18} className="text-yellow-600 mr-2" />
                            Things to Avoid
                          </h4>
                          <ul className="space-y-2">
                            {repairPlanGirlfriend.risk_factors.map((risk, idx) => (
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
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <HeartIcon size={48} className="mx-auto mb-3 text-gray-300" />
                  <p>Click "View Repair Plan" to generate and see personalized steps</p>
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

      {/* Mediator Modal */}
      {conflictId && (
        <MediatorModal
          isOpen={isMediatorModalOpen}
          onClose={() => setIsMediatorModalOpen(false)}
          conflictId={conflictId || ''}
          context={{
            activeView,
            povView,
            hasAnalysis: !!analysisBoyfriend,
            hasRepairPlans: !!(repairPlanBoyfriend || repairPlanGirlfriend)
          }}
        />
      )}
    </div>
  );
};

export default PostFightSession;
