import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import TranscriptBubble from '../components/TranscriptBubble';
import { 
  BarChart4Icon, RefreshCwIcon, FileTextIcon, SparklesIcon, HeartIcon, 
  LoaderIcon, ChevronDownIcon, ChevronUpIcon, CopyIcon, CheckIcon, 
  AlertCircleIcon, LightbulbIcon, ClockIcon, ShieldIcon, XIcon, SendIcon
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
  const state = location.state as LocationState | null;
  
  const [isPrivateMode, setIsPrivateMode] = useState(false);
  const [conflictId, setConflictId] = useState<string | null>(state?.conflict_id || null);
  const [rantInput, setRantInput] = useState('');
  const [sendingRant, setSendingRant] = useState(false);
  const [rantHistory, setRantHistory] = useState<Array<{role: 'user' | 'assistant', content: string}>>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const [analysis, setAnalysis] = useState<ConflictAnalysis | null>(null);
  const [repairPlan, setRepairPlan] = useState<RepairPlan | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingRepairPlan, setLoadingRepairPlan] = useState(false);
  const [activeView, setActiveView] = useState<'analysis' | 'repair' | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['summary']));
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  
  // Initialize messages with transcript
  const [messages, setMessages] = useState<Message[]>(() => {
    const initialMessages: Message[] = [];
    
    if (state?.transcript && state.transcript.length > 0) {
      state.transcript.forEach((line: string) => {
        const boyfriendMatch = line.match(/^(?:Boyfriend|Speaker\s+1):\s*(.+)$/i);
        const girlfriendMatch = line.match(/^(?:Girlfriend|Speaker\s+2):\s*(.+)$/i);
        
        if (boyfriendMatch) {
          initialMessages.push({
            speaker: 'speaker1',
            message: boyfriendMatch[1].trim()
          });
        } else if (girlfriendMatch) {
          initialMessages.push({
            speaker: 'speaker2',
            message: girlfriendMatch[1].trim()
          });
        } else {
          const messageText = line.replace(/^(?:You|Boyfriend|Girlfriend|Speaker\s+\d+):\s*/i, '').trim();
          if (messageText) {
            initialMessages.push({
              speaker: 'speaker1',
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

  const handleAnalyzeConflict = async () => {
    if (!conflictId) {
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    setLoadingAnalysis(true);
    setActiveView('analysis');
    
    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ partner_id: 'partner_a' })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Analysis failed: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success && data.analysis) {
        setAnalysis(data.analysis);
        addMessage('heartsync', `I've analyzed your conflict. Check the analysis panel on the right.`);
      } else {
        throw new Error(data.detail || 'Analysis failed');
      }
    } catch (error: any) {
      console.error('Error analyzing conflict:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      addMessage('heartsync', `Sorry, I encountered an error: ${errorMessage}. Please check the backend logs.`);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleGetRepairPlan = async () => {
    if (!conflictId) {
      alert('Conflict ID not available. Please ensure the fight was properly captured.');
      return;
    }

    setLoadingRepairPlan(true);
    setActiveView('repair');
    
    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/repair-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ partner_id: 'partner_a' })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Repair plan failed: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success && data.repair_plan) {
        setRepairPlan(data.repair_plan);
        addMessage('heartsync', `I've prepared a personalized repair plan. Check the repair plan panel on the right.`);
      } else {
        throw new Error(data.detail || 'Repair plan generation failed');
      }
    } catch (error: any) {
      console.error('Error getting repair plan:', error);
      const errorMessage = error.message || error.toString() || 'Unknown error';
      addMessage('heartsync', `Sorry, I encountered an error: ${errorMessage}. Please check the backend logs.`);
    } finally {
      setLoadingRepairPlan(false);
    }
  };

  const handleStoreRant = async () => {
    if (!conflictId) {
      alert('Conflict ID not available.');
      return;
    }

    const rantText = prompt('What would you like to say? (This will be stored privately)');
    if (!rantText) return;

    try {
      const response = await fetch(`${apiUrl}/api/post-fight/conflicts/${conflictId}/rant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: rantText,
          partner_id: 'partner_a',
          is_shared: false
        })
      });

      if (response.ok) {
        addMessage('speaker1', rantText, isPrivateMode);
        addMessage('heartsync', 'Your private rant has been saved.');
      }
    } catch (error) {
      console.error('Error storing rant:', error);
    }
  };

  const toggleListening = () => {
    setIsListening(!isListening);
    if (!isListening) {
      setTimeout(() => {
        addMessage('speaker1', 'I felt ignored when they were on their phone during our conversation.', isPrivateMode);
        setTimeout(() => {
          addMessage('heartsync', 'I understand that felt hurtful. Have you shared how that specific behavior makes you feel?');
          setIsListening(false);
        }, 2000);
      }, 2000);
    }
  };

  const addMessage = (speaker: 'speaker1' | 'speaker2' | 'heartsync', message: string, isPrivate: boolean = false) => {
    setMessages(prev => [...prev, { speaker, message, isPrivate }]);
  };

  return (
    <div className="flex flex-col h-[85vh] w-full max-w-full">
      {/* Header */}
      <div className="text-center mb-4 px-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-1">
          Post-Fight Session
        </h2>
        <p className="text-sm text-gray-600">
          Talk freely — HeartSync is here to help you understand and repair.
        </p>
      </div>

      {/* Main Content - Split Screen */}
      <div className="flex flex-1 gap-6 px-6 pb-4 overflow-hidden w-full">
        {/* Left Side - Conversation */}
        <div className="flex flex-col flex-1 min-w-0 border-r border-gray-200 pr-6">
          {/* Action Buttons - Top Left */}
          <div className="flex flex-wrap gap-2 mb-4 pb-4 border-b border-gray-200">
            <button
              onClick={handleAnalyzeConflict}
              disabled={!conflictId || loadingAnalysis}
              className={`flex items-center py-2 px-4 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${
                activeView === 'analysis' 
                  ? 'bg-purple-200 text-purple-800 border-2 border-purple-400' 
                  : 'bg-purple-100 hover:bg-purple-200 text-purple-700'
              }`}
            >
              <SparklesIcon size={16} className="mr-2" />
              {loadingAnalysis ? 'Analyzing...' : 'Analyze Conflict'}
            </button>
            
            <button
              onClick={handleGetRepairPlan}
              disabled={!conflictId || loadingRepairPlan}
              className={`flex items-center py-2 px-4 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${
                activeView === 'repair' 
                  ? 'bg-rose-200 text-rose-800 border-2 border-rose-400' 
                  : 'bg-rose-100 hover:bg-rose-200 text-rose-700'
              }`}
            >
              <HeartIcon size={16} className="mr-2" />
              {loadingRepairPlan ? 'Generating...' : 'Get Repair Plan'}
            </button>
            
            <button
              onClick={handleStoreRant}
              disabled={!conflictId}
              className={`flex items-center py-2 px-4 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${
                isPrivateMode ? 'bg-rose-200 text-rose-700 border-2 border-rose-400' : 'bg-white/70 text-gray-600 hover:bg-white/90'
              }`}
            >
              <FileTextIcon size={16} className="mr-2" />
              {isPrivateMode ? 'Exit Private Rant' : 'Private Rant'}
            </button>
          </div>

          {/* Private Rant Chat Input */}
          {isPrivateMode && (
            <div className="mb-4 p-3 bg-rose-50 rounded-xl border-2 border-rose-200">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={rantInput}
                  onChange={(e) => setRantInput(e.target.value)}
                  onKeyPress={handleRantKeyPress}
                  placeholder="Share your thoughts privately with HeartSync..."
                  disabled={sendingRant}
                  className="flex-1 px-4 py-2 bg-white rounded-lg border border-rose-200 focus:outline-none focus:ring-2 focus:ring-rose-400 focus:border-transparent text-sm disabled:opacity-50"
                />
                <button
                  onClick={handleSendRant}
                  disabled={!rantInput.trim() || sendingRant}
                  className="px-4 py-2 bg-rose-500 text-white rounded-lg hover:bg-rose-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {sendingRant ? (
                    <LoaderIcon size={18} className="animate-spin" />
                  ) : (
                    <SendIcon size={18} />
                  )}
                </button>
              </div>
              <p className="text-xs text-rose-600 mt-2 flex items-center">
                <span className="mr-1">🔒</span>
                This conversation is private and confidential
              </p>
            </div>
          )}

          {/* Messages/Transcript */}
          <div className="flex-1 overflow-y-auto pr-2">
            <div className="space-y-3">
              {messages.map((msg, idx) => {
                if (msg.speaker === 'heartsync') {
                  return <TranscriptBubble key={idx} speaker="heartsync" message={msg.message} isPrivate={msg.isPrivate} />;
                } else {
                  const isBoyfriend = msg.speaker === 'speaker1';
                  return (
                    <div key={idx} className={`flex w-full ${isBoyfriend ? 'justify-start' : 'justify-end'}`}>
                      <div className={`rounded-2xl py-2.5 px-4 max-w-[85%] shadow-sm ${
                        isBoyfriend 
                          ? 'bg-blue-100 text-gray-800' 
                          : 'bg-pink-100 text-gray-800'
                      } ${msg.isPrivate ? 'opacity-70 border-2 border-rose-300' : ''}`}>
                        <div className="text-xs font-semibold mb-1 text-gray-600">
                          {isBoyfriend ? 'Boyfriend' : 'Girlfriend'}
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
                  <span className="text-gray-600">Analyzing conflict with AI...</span>
                </div>
              ) : analysis ? (
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
                      <p className="text-gray-700 leading-relaxed">{analysis.fight_summary}</p>
                    )}
                  </div>

                  {/* Root Causes */}
                  {analysis.root_causes.length > 0 && (
                    <div className="bg-white rounded-xl p-4 border border-purple-100">
                      <button
                        onClick={() => toggleSection('root_causes')}
                        className="w-full flex items-center justify-between mb-2"
                      >
                        <div className="flex items-center">
                          <AlertCircleIcon size={18} className="text-orange-500 mr-2" />
                          <h4 className="font-semibold text-gray-800">Root Causes</h4>
                          <span className="ml-2 text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">
                            {analysis.root_causes.length}
                          </span>
                        </div>
                        {expandedSections.has('root_causes') ? 
                          <ChevronUpIcon size={18} className="text-gray-400" /> : 
                          <ChevronDownIcon size={18} className="text-gray-400" />
                        }
                      </button>
                      {expandedSections.has('root_causes') && (
                        <ul className="space-y-2">
                          {analysis.root_causes.map((cause, idx) => (
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
                  {(analysis.unmet_needs_boyfriend.length > 0 || analysis.unmet_needs_girlfriend.length > 0) && (
                    <div className="grid grid-cols-1 gap-4">
                      {analysis.unmet_needs_boyfriend.length > 0 && (
                        <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                          <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                            <span className="bg-blue-200 px-2 py-0.5 rounded text-xs mr-2">Boyfriend</span>
                            Unmet Needs
                          </h4>
                          <ul className="space-y-1.5">
                            {analysis.unmet_needs_boyfriend.map((need, idx) => (
                              <li key={idx} className="text-sm text-gray-700 flex items-start">
                                <span className="text-blue-500 mr-2 mt-1">•</span>
                                <span>{need}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {analysis.unmet_needs_girlfriend.length > 0 && (
                        <div className="bg-pink-50 rounded-xl p-4 border border-pink-100">
                          <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                            <span className="bg-pink-200 px-2 py-0.5 rounded text-xs mr-2">Girlfriend</span>
                            Unmet Needs
                          </h4>
                          <ul className="space-y-1.5">
                            {analysis.unmet_needs_girlfriend.map((need, idx) => (
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
                  {analysis.escalation_points && analysis.escalation_points.length > 0 && (
                    <div className="bg-white rounded-xl p-4 border border-red-100">
                      <button
                        onClick={() => toggleSection('escalation')}
                        className="w-full flex items-center justify-between mb-2"
                      >
                        <div className="flex items-center">
                          <AlertCircleIcon size={18} className="text-red-500 mr-2" />
                          <h4 className="font-semibold text-gray-800">Escalation Points</h4>
                          <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                            {analysis.escalation_points.length}
                          </span>
                        </div>
                        {expandedSections.has('escalation') ? 
                          <ChevronUpIcon size={18} className="text-gray-400" /> : 
                          <ChevronDownIcon size={18} className="text-gray-400" />
                        }
                      </button>
                      {expandedSections.has('escalation') && (
                        <div className="space-y-3">
                          {analysis.escalation_points.map((point, idx) => (
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
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <SparklesIcon size={48} className="mx-auto mb-3 text-gray-300" />
                  <p>Click "Analyze Conflict" to see insights</p>
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
                  <span className="text-gray-600">Generating personalized repair plan...</span>
                </div>
              ) : repairPlan ? (
                <div className="space-y-4">
                  {/* Steps */}
                  <div className="bg-white rounded-xl p-4 border border-rose-100">
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                      <LightbulbIcon size={18} className="text-rose-500 mr-2" />
                      Action Steps
                    </h4>
                    <ol className="space-y-3">
                      {repairPlan.steps.map((step, idx) => (
                        <li key={idx} className="flex items-start text-gray-700">
                          <span className="bg-rose-100 text-rose-700 font-semibold rounded-full w-6 h-6 flex items-center justify-center text-xs mr-3 mt-0.5 flex-shrink-0">
                            {idx + 1}
                          </span>
                          <span className="flex-1">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>

                  {/* Apology Script */}
                  <div className="bg-gradient-to-r from-rose-50 to-pink-50 rounded-xl p-5 border-2 border-rose-200">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-gray-800 flex items-center">
                        <HeartIcon size={18} className="text-rose-500 mr-2" />
                        Apology Script
                      </h4>
                      <button
                        onClick={() => copyToClipboard(repairPlan.apology_script, 'apology')}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                        title="Copy to clipboard"
                      >
                        {copiedText === 'apology' ? (
                          <CheckIcon size={18} className="text-green-500" />
                        ) : (
                          <CopyIcon size={18} />
                        )}
                      </button>
                    </div>
                    <p className="text-gray-700 leading-relaxed italic whitespace-pre-wrap">
                      {repairPlan.apology_script}
                    </p>
                  </div>

                  {/* Timing */}
                  <div className="bg-white rounded-xl p-4 border border-rose-100">
                    <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                      <ClockIcon size={18} className="text-blue-500 mr-2" />
                      Timing Suggestion
                    </h4>
                    <p className="text-gray-700 text-sm">{repairPlan.timing_suggestion}</p>
                  </div>

                  {/* Risk Factors */}
                  {repairPlan.risk_factors && repairPlan.risk_factors.length > 0 && (
                    <div className="bg-yellow-50 rounded-xl p-4 border border-yellow-200">
                      <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                        <ShieldIcon size={18} className="text-yellow-600 mr-2" />
                        Things to Avoid
                      </h4>
                      <ul className="space-y-2">
                        {repairPlan.risk_factors.map((risk, idx) => (
                          <li key={idx} className="flex items-start text-sm text-gray-700">
                            <span className="text-yellow-600 mr-2 mt-1">⚠</span>
                            <span>{risk}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <HeartIcon size={48} className="mx-auto mb-3 text-gray-300" />
                  <p>Click "Get Repair Plan" to see personalized steps</p>
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
    </div>
  );
};

export default PostFightSession;
