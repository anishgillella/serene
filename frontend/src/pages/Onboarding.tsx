import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, ArrowLeftIcon, MicIcon, CheckCircleIcon, HeartIcon, UserIcon, BookOpenIcon, UtensilsIcon, TrophyIcon, StarIcon, AlertCircleIcon, SparklesIcon, EyeIcon, PlayIcon, RefreshCwIcon, ClockIcon, MessageCircleIcon, HandIcon, GiftIcon, UsersIcon, ShieldIcon, RotateCcwIcon } from 'lucide-react';
import VoiceGuidanceModal from '../components/ui/VoiceGuidanceModal';

// Types - Using gender-neutral terminology
interface PartnerProfile {
    name: string;
    role: 'partner_a' | 'partner_b';  // Gender-neutral roles
    age: number | '';
    communication_style: string;
    stress_triggers: string[];
    soothing_mechanisms: string[];
    background_story: string;
    hobbies: string[];
    favorite_food: string;
    favorite_cuisine: string;
    favorite_sports: string[];
    favorite_books: string[];
    favorite_celebrities: string[];
    traumatic_experiences: string;
    key_life_experiences: string;
    partner_description: string;
    what_i_admire: string;
    what_frustrates_me: string;
    // Repair-specific fields (Phase 1)
    apology_preferences: string;
    post_conflict_need: 'space' | 'connection' | 'depends' | '';
    repair_gestures: string[];
    escalation_triggers: string[];
    // NEW: Expanded profile fields (Phase 2)
    relationship_duration: string;
    how_you_met: string;
    love_language: 'words' | 'acts' | 'gifts' | 'time' | 'touch' | '';
    conflict_role: 'pursue' | 'withdraw' | 'varies' | '';
    happiest_memory: string;
    biggest_fear: string;
    time_to_reconnect: 'minutes' | 'hours' | 'day' | 'depends' | '';
    reconnection_activities: string[];
    what_makes_you_feel_loved: string[];
    how_you_know_resolved: string;
    off_limit_topics: string[];
}

// Partner status from API
interface PartnerStatus {
    completed: boolean;
    name: string | null;
    updated_at: string | null;
}

interface RelationshipProfile {
    recurring_arguments: string[];
    shared_goals: string[];
    relationship_dynamic: string;
}

// Hybrid Input Component
// Hybrid Input Component
const HybridInput = ({
    value,
    onChange,
    placeholder,
    multiline = false,
    isList = false,
    autoFocus = false,
    onEnter
}: {
    value: string | string[];
    onChange: (val: string | string[]) => void;
    placeholder: string;
    multiline?: boolean;
    isList?: boolean;
    autoFocus?: boolean;
    onEnter?: () => void;
}) => {
    const [isListening, setIsListening] = useState(false);
    const [recognition, setRecognition] = useState<any>(null);

    // Local state to handle typing without immediate re-formatting
    const [localValue, setLocalValue] = useState<string>('');

    // Sync local state when prop changes externally (but avoid overriding user typing)
    useEffect(() => {
        if (isList && Array.isArray(value)) {
            // Only update if the parsed local value doesn't match the new prop value
            // This is a bit tricky, so we'll use a simple heuristic:
            // If the prop value is significantly different (e.g. from a reset or initial load), update local.
            // For now, we'll just initialize and update if it's empty or completely different.
            // A better way is to only update localValue if the parent value changes and it's NOT due to our own change.
            // But since we can't easily know that, we'll just initialize it and rely on local state for driving changes.

            // Actually, let's just sync on mount or if value changes length significantly?
            // Let's try: Update local value only if it's empty (initial load)
            if (localValue === '' && value.length > 0) {
                setLocalValue(value.join(', '));
            }
        } else if (!isList && typeof value === 'string') {
            if (localValue === '' && value) {
                setLocalValue(value);
            } else if (value !== localValue) {
                // If parent updates it (e.g. from speech recognition or reset)
                // We need to be careful not to overwrite typing.
                // For now, we will trust the parent if it changes.
                setLocalValue(value);
            }
        }
    }, [value, isList]);

    // Initialize local value on mount
    useEffect(() => {
        if (isList && Array.isArray(value)) {
            setLocalValue(value.join(', '));
        } else if (!isList) {
            setLocalValue(value as string);
        }
    }, []); // Run once on mount

    useEffect(() => {
        if ('webkitSpeechRecognition' in window) {
            const r = new (window as any).webkitSpeechRecognition();
            r.continuous = true;
            r.interimResults = false;
            r.lang = 'en-US';

            r.onresult = (event: any) => {
                const resultIndex = event.results.length - 1;
                const latestResult = event.results[resultIndex];

                if (latestResult.isFinal) {
                    const text = latestResult[0].transcript.trim();

                    if (isList) {
                        // For lists, we append intelligently
                        setLocalValue(prev => {
                            const separator = prev.trim().endsWith(',') ? ' ' : ', ';
                            const newValue = prev ? prev + separator + text : text;

                            // Update parent
                            const items = newValue.split(/[,;\n]+| and /).map((s: string) => s.trim()).filter(Boolean);
                            onChange(items);

                            return newValue;
                        });
                    } else {
                        setLocalValue(prev => {
                            const newValue = prev ? prev + ' ' + text : text;
                            onChange(newValue);
                            return newValue;
                        });
                    }
                }
            };

            r.onerror = (event: any) => {
                console.error("Speech recognition error", event.error);
                setIsListening(false);
            };

            setRecognition(r);

            return () => {
                if (r) r.stop();
            };
        }
    }, [isList, onChange]);

    const toggleListening = () => {
        if (!recognition) return;
        if (isListening) {
            recognition.stop();
            setIsListening(false);
        } else {
            recognition.start();
            setIsListening(true);
        }
    };

    const handleTextChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const newVal = e.target.value;
        setLocalValue(newVal);

        if (isList) {
            // Allow any separator: comma, newline, semicolon, or " and "
            // We don't filter(Boolean) immediately to allow typing trailing spaces/commas
            // But we need to send a clean array to the parent
            const items = newVal.split(/[,;\n]+| and /).map((s: string) => s.trim()).filter(Boolean);
            onChange(items);
        } else {
            onChange(newVal);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            if (multiline && !e.shiftKey) {
                return;
            }
            e.preventDefault();
            if (onEnter) onEnter();
        }
    };

    return (
        <div className={`relative ${multiline ? 'w-full' : 'w-full max-w-2xl mx-auto'}`}>
            {multiline ? (
                <textarea
                    value={localValue}
                    onChange={handleTextChange}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    autoFocus={autoFocus}
                    className="w-full pl-6 pr-20 py-4 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-2xl transition-all outline-none min-h-[200px] resize-y text-lg"
                />
            ) : (
                <input
                    type="text"
                    value={localValue}
                    onChange={handleTextChange}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    autoFocus={autoFocus}
                    className="w-full pl-6 pr-20 py-4 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-2xl transition-all outline-none text-lg"
                />
            )}
            {recognition && (
                <button
                    onClick={toggleListening}
                    className={`absolute right-4 top-4 p-3 rounded-full transition-colors ${isListening ? 'bg-red-100 text-red-600 animate-pulse' : 'text-text-tertiary hover:text-accent hover:bg-surface-elevated'
                        }`}
                    title="Speak to input"
                >
                    <MicIcon size={24} />
                </button>
            )}
        </div>
    );
};

const Onboarding = () => {
    const navigate = useNavigate();
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [partnerId, setPartnerId] = useState<'partner_a' | 'partner_b'>('partner_a');
    const [relationshipId] = useState('00000000-0000-0000-0000-000000000000');

    const [partnerProfile, setPartnerProfile] = useState<PartnerProfile>({
        name: '',
        role: 'partner_a',
        age: '',
        communication_style: '',
        stress_triggers: [],
        soothing_mechanisms: [],
        background_story: '',
        hobbies: [],
        favorite_food: '',
        favorite_cuisine: '',
        favorite_sports: [],
        favorite_books: [],
        favorite_celebrities: [],
        traumatic_experiences: '',
        key_life_experiences: '',
        partner_description: '',
        what_i_admire: '',
        what_frustrates_me: '',
        // Repair-specific fields (Phase 1)
        apology_preferences: '',
        post_conflict_need: '',
        repair_gestures: [],
        escalation_triggers: [],
        // Expanded profile fields (Phase 2)
        relationship_duration: '',
        how_you_met: '',
        love_language: '',
        conflict_role: '',
        happiest_memory: '',
        biggest_fear: '',
        time_to_reconnect: '',
        reconnection_activities: [],
        what_makes_you_feel_loved: [],
        how_you_know_resolved: '',
        off_limit_topics: []
    });

    const [relationshipProfile, setRelationshipProfile] = useState<RelationshipProfile>({
        recurring_arguments: [],
        shared_goals: [],
        relationship_dynamic: ''
    });

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showVoiceModal, setShowVoiceModal] = useState(false);
    const [showResetConfirm, setShowResetConfirm] = useState(false);
    const [partnerStatus, setPartnerStatus] = useState<{
        partner_a: PartnerStatus;
        partner_b: PartnerStatus;
    }>({
        partner_a: { completed: false, name: null, updated_at: null },
        partner_b: { completed: false, name: null, updated_at: null }
    });
    const [isLoadingStatus, setIsLoadingStatus] = useState(true);
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

    // Fetch partner status on mount
    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await fetch(`${apiUrl}/api/onboarding/status?relationship_id=${relationshipId}`, {
                    headers: { 'ngrok-skip-browser-warning': 'true' }
                });
                if (response.ok) {
                    const data = await response.json();
                    setPartnerStatus(data);
                }
            } catch (error) {
                console.error('Error fetching status:', error);
            } finally {
                setIsLoadingStatus(false);
            }
        };
        fetchStatus();
    }, [relationshipId, apiUrl]);

    // Show modal at start of Chapter 2 (Your Story)
    useEffect(() => {
        // Find index of first question in Chapter 2
        const chapter2Index = steps.findIndex(s => s.chapter === 2 && s.type === 'partner');
        if (currentStepIndex === chapter2Index) {
            setShowVoiceModal(true);
        }
    }, [currentStepIndex]);

    // Step Configuration - 32 questions across 6 chapters
    const steps = [
        // Partner Selection Hub (new welcome)
        { type: 'partner_select', title: "Who's filling this out?", description: "Each partner completes their own profile separately." },

        // Chapter 1: The Basics (3 questions)
        { type: 'chapter_start', chapter: 1, title: "The Basics", description: "First, tell us a bit about yourself." },
        { type: 'partner', field: 'name', label: "What's your name?", placeholder: "e.g., Alex", icon: UserIcon, chapter: 1 },
        { type: 'partner', field: 'age', label: "How old are you?", placeholder: "e.g., 28", icon: UserIcon, chapter: 1 },
        { type: 'partner', field: 'relationship_duration', label: "How long have you been together?", placeholder: "e.g., 2 years, 6 months", icon: ClockIcon, chapter: 1 },

        // Chapter 2: Your Story (6 questions)
        { type: 'chapter_start', chapter: 2, title: "Your Story", description: "Your past shapes who you are today." },
        { type: 'partner', field: 'background_story', label: "Tell us your story.", sublabel: "Where did you grow up? What was your childhood like?", placeholder: "I grew up in...", multiline: true, icon: BookOpenIcon, chapter: 2 },
        { type: 'partner', field: 'key_life_experiences', label: "What are the pivotal moments in your life?", sublabel: "Events that changed your perspective or defined your character.", placeholder: "Moving to a new city...", multiline: true, icon: StarIcon, chapter: 2 },
        { type: 'partner', field: 'hobbies', label: "What lights you up?", sublabel: "Hobbies, passions, or activities where you lose track of time.", placeholder: "Photography, Hiking...", isList: true, icon: TrophyIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_food', label: "What's your ultimate comfort food?", sublabel: "The meal that makes everything better.", placeholder: "Spicy Tuna Roll...", icon: UtensilsIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_books', label: "Books, movies, or shows that impacted you?", sublabel: "Stories or ideas that stuck with you.", placeholder: "The Alchemist, Breaking Bad...", isList: true, icon: BookOpenIcon, chapter: 2 },
        { type: 'partner', field: 'how_you_met', label: "How did you two meet?", sublabel: "The story of how your paths crossed.", placeholder: "We met at a friend's party...", multiline: true, icon: HeartIcon, chapter: 2 },

        // Chapter 3: Inner World (10 questions)
        { type: 'chapter_start', chapter: 3, title: "Inner World", description: "Help us understand how you process emotions." },
        { type: 'partner', field: 'communication_style', label: "How do you communicate under pressure?", sublabel: "Do you need space? Do you want to solve it now? Are you direct or indirect?", placeholder: "I tend to go quiet...", multiline: true, icon: MessageCircleIcon, chapter: 3 },
        { type: 'partner', field: 'stress_triggers', label: "What triggers your stress?", sublabel: "Specific situations or behaviors that set you off.", placeholder: "Being interrupted...", isList: true, icon: AlertCircleIcon, chapter: 3 },
        { type: 'partner', field: 'soothing_mechanisms', label: "What calms you down?", sublabel: "What helps you return to a baseline state?", placeholder: "Deep breathing, a walk...", isList: true, icon: HeartIcon, chapter: 3 },
        { type: 'partner', field: 'traumatic_experiences', label: "Any past experiences that affect you today?", sublabel: "Optional. Things that might make you sensitive to certain conflicts.", placeholder: "My parents divorce...", multiline: true, icon: ShieldIcon, chapter: 3 },
        { type: 'partner', field: 'love_language', label: "How do you prefer to receive love?", sublabel: "What makes you feel most appreciated and cared for?", icon: HeartIcon, chapter: 3, isChoice: true, choices: ['words', 'acts', 'gifts', 'time', 'touch'] },
        { type: 'partner', field: 'conflict_role', label: "In conflicts, do you tend to pursue or withdraw?", sublabel: "Do you want to talk it out immediately, or do you need space first?", icon: UsersIcon, chapter: 3, isChoice: true, choices: ['pursue', 'withdraw', 'varies'] },
        { type: 'partner', field: 'apology_preferences', label: "What makes an apology feel genuine to you?", sublabel: "What do you need to hear or see to feel truly understood?", placeholder: "I need them to acknowledge specifically what they did wrong...", multiline: true, icon: HeartIcon, chapter: 3 },
        { type: 'partner', field: 'post_conflict_need', label: "After a conflict, what do you need first?", sublabel: "Do you need time alone to process, or connection right away?", icon: SparklesIcon, chapter: 3, isChoice: true, choices: ['space', 'connection', 'depends'] },
        { type: 'partner', field: 'repair_gestures', label: "What small gestures help you feel better after a fight?", sublabel: "Things your partner can do that help you calm down or feel cared for.", placeholder: "Making me tea, a genuine hug, giving me space for 20 minutes...", isList: true, icon: GiftIcon, chapter: 3 },
        { type: 'partner', field: 'escalation_triggers', label: "What makes fights worse for you?", sublabel: "Behaviors or phrases that escalate the conflict.", placeholder: "Saying 'calm down', walking away mid-sentence...", isList: true, icon: AlertCircleIcon, chapter: 3 },

        // Chapter 4: Your Partner (5 questions)
        { type: 'chapter_start', chapter: 4, title: "Your Partner", description: "Tell us about the person you love." },
        { type: 'partner', field: 'partner_description', label: "How would you describe your partner?", sublabel: "Their personality, their vibe, their essence.", placeholder: "They are creative and...", multiline: true, icon: EyeIcon, chapter: 4 },
        { type: 'partner', field: 'what_i_admire', label: "What do you admire most about them?", sublabel: "The qualities that made you fall for them.", placeholder: "Their empathy...", multiline: true, icon: HeartIcon, chapter: 4 },
        { type: 'partner', field: 'what_frustrates_me', label: "What challenges do you face with them?", sublabel: "Be honest. What behaviors or traits are difficult for you?", placeholder: "They can be disorganized...", multiline: true, icon: AlertCircleIcon, chapter: 4 },
        { type: 'partner', field: 'happiest_memory', label: "Your happiest memory together?", sublabel: "A moment that captures the best of your relationship.", placeholder: "That trip we took to...", multiline: true, icon: StarIcon, chapter: 4 },
        { type: 'partner', field: 'biggest_fear', label: "Your biggest fear about this relationship?", sublabel: "What worries you most? Being honest helps us help you.", placeholder: "I worry that...", multiline: true, icon: ShieldIcon, chapter: 4 },

        // Chapter 5: Reconnection (4 questions)
        { type: 'chapter_start', chapter: 5, title: "Reconnection", description: "How you come back together after conflict." },
        { type: 'partner', field: 'time_to_reconnect', label: "How long do you typically need before you're ready to reconnect?", sublabel: "After a conflict, how much time do you need?", icon: ClockIcon, chapter: 5, isChoice: true, choices: ['minutes', 'hours', 'day', 'depends'] },
        { type: 'partner', field: 'reconnection_activities', label: "Activities that help you two reconnect?", sublabel: "Things you do together that rebuild closeness.", placeholder: "Going for a walk, cooking together, watching a show...", isList: true, icon: RefreshCwIcon, chapter: 5 },
        { type: 'partner', field: 'what_makes_you_feel_loved', label: "Small gestures that make you feel loved?", sublabel: "The little things that show your partner cares.", placeholder: "A random text, coffee in bed, a long hug...", isList: true, icon: HeartIcon, chapter: 5 },
        { type: 'partner', field: 'how_you_know_resolved', label: "How do you know a conflict is truly resolved?", sublabel: "What signals to you that things are okay again?", placeholder: "When we can laugh about it...", multiline: true, icon: CheckCircleIcon, chapter: 5 },

        // Chapter 6: Us Together (4 questions)
        { type: 'chapter_start', chapter: 6, title: "Us Together", description: "The dynamics of your relationship." },
        { type: 'relationship', field: 'relationship_dynamic', label: "How do you two interact?", sublabel: "Are you opposites? Two peas in a pod? Who leads, who follows?", placeholder: "We are opposites...", multiline: true, icon: UsersIcon, chapter: 6 },
        { type: 'relationship', field: 'recurring_arguments', label: "What do you fight about most?", sublabel: "The topics that keep coming up.", placeholder: "Chores, Money...", isList: true, icon: AlertCircleIcon, chapter: 6 },
        { type: 'partner', field: 'off_limit_topics', label: "Topics that should never come up during fights?", sublabel: "Things that are off-limits when you're arguing.", placeholder: "Past relationships, family issues...", isList: true, icon: ShieldIcon, chapter: 6 },
        { type: 'relationship', field: 'shared_goals', label: "What are you building together?", sublabel: "Your shared vision for the future.", placeholder: "Buying a house...", isList: true, icon: TrophyIcon, chapter: 6 },

        { type: 'success', chapter: 7 }
    ];

    const handleNext = () => {
        if (currentStepIndex < steps.length - 1) {
            setCurrentStepIndex(prev => prev + 1);
        }
    };

    const handleBack = () => {
        if (currentStepIndex > 0) {
            setCurrentStepIndex(prev => prev - 1);
        }
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        try {
            const response = await fetch(`${apiUrl}/api/onboarding/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({
                    relationship_id: relationshipId,
                    partner_id: partnerId,
                    partner_profile: {
                        ...partnerProfile,
                        age: Number(partnerProfile.age) || 0
                    },
                    relationship_profile: relationshipProfile
                })
            });

            if (response.ok) {
                // Update local status
                setPartnerStatus(prev => ({
                    ...prev,
                    [partnerId]: {
                        completed: true,
                        name: partnerProfile.name,
                        updated_at: new Date().toISOString()
                    }
                }));
                handleNext(); // Go to success step
            } else {
                console.error('Submission failed');
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleReset = async (partnerToReset: 'partner_a' | 'partner_b') => {
        try {
            const response = await fetch(
                `${apiUrl}/api/onboarding/profile/${partnerToReset}?relationship_id=${relationshipId}`,
                {
                    method: 'DELETE',
                    headers: { 'ngrok-skip-browser-warning': 'true' }
                }
            );
            if (response.ok) {
                setPartnerStatus(prev => ({
                    ...prev,
                    [partnerToReset]: { completed: false, name: null, updated_at: null }
                }));
                setShowResetConfirm(false);
            }
        } catch (error) {
            console.error('Error resetting profile:', error);
        }
    };

    const selectPartner = (role: 'partner_a' | 'partner_b') => {
        setPartnerId(role);
        setPartnerProfile(p => ({ ...p, role }));
        handleNext();
    };

    const currentStep = steps[currentStepIndex];
    const totalChapters = 6;

    // Format date for display
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    };

    // Renderers
    const renderPartnerSelect = () => (
        <div className="max-w-4xl mx-auto animate-fade-in">
            <div className="text-center mb-12">
                <div className="w-20 h-20 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-6">
                    <HeartIcon size={36} className="text-accent" />
                </div>
                <h1 className="text-h1 text-text-primary mb-4">Welcome to Serene</h1>
                <p className="text-body-lg text-text-secondary max-w-xl mx-auto">
                    Each partner fills out their own profile. This helps us understand both perspectives
                    and provide personalized guidance for your relationship.
                </p>
            </div>

            {isLoadingStatus ? (
                <div className="text-center text-text-secondary py-12">Loading...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Partner A Card */}
                    <div className={`relative p-8 rounded-3xl border-2 transition-all ${
                        partnerStatus.partner_a.completed
                            ? 'bg-blue-50/50 border-blue-200'
                            : 'bg-surface-elevated border-transparent hover:border-blue-300'
                    }`}>
                        {partnerStatus.partner_a.completed && (
                            <div className="absolute top-4 right-4">
                                <CheckCircleIcon size={24} className="text-green-500" />
                            </div>
                        )}
                        <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mb-6">
                            <UserIcon size={32} />
                        </div>
                        <h3 className="text-h3 text-text-primary mb-2">
                            {partnerStatus.partner_a.name || 'Partner A'}
                        </h3>
                        {partnerStatus.partner_a.completed ? (
                            <>
                                <p className="text-small text-text-tertiary mb-4">
                                    Completed {formatDate(partnerStatus.partner_a.updated_at)}
                                </p>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => selectPartner('partner_a')}
                                        className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
                                    >
                                        Edit Profile
                                    </button>
                                    <button
                                        onClick={() => {
                                            setPartnerId('partner_a');
                                            setShowResetConfirm(true);
                                        }}
                                        className="px-4 py-3 border border-red-200 text-red-600 rounded-xl hover:bg-red-50 transition-colors"
                                        title="Reset profile"
                                    >
                                        <RotateCcwIcon size={18} />
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <p className="text-body text-text-secondary mb-6">First partner</p>
                                <button
                                    onClick={() => selectPartner('partner_a')}
                                    className="w-full px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
                                >
                                    Start Profile
                                </button>
                            </>
                        )}
                    </div>

                    {/* Partner B Card */}
                    <div className={`relative p-8 rounded-3xl border-2 transition-all ${
                        partnerStatus.partner_b.completed
                            ? 'bg-purple-50/50 border-purple-200'
                            : 'bg-surface-elevated border-transparent hover:border-purple-300'
                    }`}>
                        {partnerStatus.partner_b.completed && (
                            <div className="absolute top-4 right-4">
                                <CheckCircleIcon size={24} className="text-green-500" />
                            </div>
                        )}
                        <div className="w-16 h-16 bg-purple-100 text-purple-600 rounded-2xl flex items-center justify-center mb-6">
                            <UserIcon size={32} />
                        </div>
                        <h3 className="text-h3 text-text-primary mb-2">
                            {partnerStatus.partner_b.name || 'Partner B'}
                        </h3>
                        {partnerStatus.partner_b.completed ? (
                            <>
                                <p className="text-small text-text-tertiary mb-4">
                                    Completed {formatDate(partnerStatus.partner_b.updated_at)}
                                </p>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => selectPartner('partner_b')}
                                        className="flex-1 px-6 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors"
                                    >
                                        Edit Profile
                                    </button>
                                    <button
                                        onClick={() => {
                                            setPartnerId('partner_b');
                                            setShowResetConfirm(true);
                                        }}
                                        className="px-4 py-3 border border-red-200 text-red-600 rounded-xl hover:bg-red-50 transition-colors"
                                        title="Reset profile"
                                    >
                                        <RotateCcwIcon size={18} />
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <p className="text-body text-text-secondary mb-6">Second partner</p>
                                <button
                                    onClick={() => selectPartner('partner_b')}
                                    className="w-full px-6 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors"
                                >
                                    Start Profile
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Both completed message */}
            {partnerStatus.partner_a.completed && partnerStatus.partner_b.completed && (
                <div className="mt-8 text-center">
                    <p className="text-body text-green-600 mb-4">
                        Both profiles are complete! You're ready for personalized guidance.
                    </p>
                    <button
                        onClick={() => navigate('/')}
                        className="px-8 py-3 bg-accent text-white rounded-xl hover:bg-accent-hover transition-colors"
                    >
                        Go to Home
                    </button>
                </div>
            )}

            {/* Reset Confirmation Modal */}
            {showResetConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl p-8 max-w-md mx-4">
                        <h3 className="text-h3 text-text-primary mb-4">Reset Profile?</h3>
                        <p className="text-body text-text-secondary mb-6">
                            This will delete all answers for {partnerId === 'partner_a' ? 'Partner A' : 'Partner B'}.
                            This action cannot be undone.
                        </p>
                        <div className="flex gap-4">
                            <button
                                onClick={() => setShowResetConfirm(false)}
                                className="flex-1 px-6 py-3 border border-border-subtle rounded-xl hover:bg-surface-hover transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleReset(partnerId)}
                                className="flex-1 px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors"
                            >
                                Reset
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );

    const renderChapterStart = () => (
        <div className="text-center max-w-lg mx-auto animate-fade-in">
            <div className="w-20 h-20 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <PlayIcon size={32} className="text-accent ml-1" />
            </div>
            <div className="text-accent font-medium tracking-widest uppercase mb-2">Chapter {currentStep.chapter}</div>
            <h2 className="text-h1 text-text-primary mb-6">{currentStep.title}</h2>
            <p className="text-body-lg text-text-secondary mb-10">
                {currentStep.description}
            </p>
            <button
                onClick={handleNext}
                className="px-10 py-4 bg-accent text-white rounded-2xl font-medium hover:bg-accent-hover transition-all shadow-lg hover:shadow-xl hover:-translate-y-1 text-lg"
            >
                Continue
            </button>
        </div>
    );

    // All choice labels for different question types
    const allChoiceLabels: Record<string, { title: string; description: string; icon?: any }> = {
        // Post-conflict need
        'space': { title: 'Space First', description: 'I need time alone to cool down and process', icon: SparklesIcon },
        'connection': { title: 'Connection First', description: 'I need to feel close again right away', icon: HeartIcon },
        'depends': { title: 'It Depends', description: 'It varies by situation', icon: AlertCircleIcon },
        // Love languages
        'words': { title: 'Words of Affirmation', description: 'Hearing "I love you" and compliments', icon: MessageCircleIcon },
        'acts': { title: 'Acts of Service', description: 'Actions speak louder than words', icon: HandIcon },
        'gifts': { title: 'Receiving Gifts', description: 'Thoughtful presents and surprises', icon: GiftIcon },
        'time': { title: 'Quality Time', description: 'Undivided attention and presence', icon: ClockIcon },
        'touch': { title: 'Physical Touch', description: 'Hugs, holding hands, closeness', icon: HeartIcon },
        // Conflict role
        'pursue': { title: 'Pursue', description: 'I want to talk it out right away', icon: MessageCircleIcon },
        'withdraw': { title: 'Withdraw', description: 'I need space to process first', icon: ShieldIcon },
        'varies': { title: 'It Varies', description: 'Depends on the situation', icon: AlertCircleIcon },
        // Time to reconnect
        'minutes': { title: 'A Few Minutes', description: 'I bounce back quickly', icon: ClockIcon },
        'hours': { title: 'A Few Hours', description: 'I need some time to decompress', icon: ClockIcon },
        'day': { title: 'About a Day', description: 'I need to sleep on it', icon: ClockIcon }
    };

    const renderQuestion = () => {
        const Icon = currentStep.icon || SparklesIcon;
        const isLast = currentStepIndex === steps.length - 2; // -2 because last is success
        const isChoiceQuestion = currentStep.isChoice && currentStep.choices;
        const numChoices = currentStep.choices?.length || 3;
        const gridCols = numChoices === 5 ? 'md:grid-cols-5' : numChoices === 4 ? 'md:grid-cols-4' : 'md:grid-cols-3';

        return (
            <div className="max-w-3xl mx-auto animate-fade-in">
                {/* Partner Identity Badge */}
                <div className={`mb-6 flex items-center justify-center gap-2 px-4 py-2 rounded-full mx-auto w-fit ${
                    partnerId === 'partner_a' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'
                }`}>
                    <UserIcon size={16} />
                    <span className="text-sm font-medium">
                        {partnerProfile.name || (partnerId === 'partner_a' ? 'Partner A' : 'Partner B')}
                    </span>
                </div>

                <div className="mb-8 text-center">
                    <div className="w-16 h-16 bg-surface-hover rounded-2xl flex items-center justify-center mx-auto mb-6 text-accent">
                        <Icon size={32} />
                    </div>
                    <h2 className="text-h2 text-text-primary mb-3">{currentStep.label}</h2>
                    {currentStep.sublabel && (
                        <p className="text-body text-text-secondary">{currentStep.sublabel}</p>
                    )}
                </div>

                <div className="mb-12">
                    {isChoiceQuestion ? (
                        <div className={`grid grid-cols-1 ${gridCols} gap-4 max-w-4xl mx-auto`}>
                            {currentStep.choices!.map((choice: string) => {
                                const currentValue = currentStep.type === 'partner'
                                    ? (partnerProfile as any)[currentStep.field!]
                                    : (relationshipProfile as any)[currentStep.field!];
                                const isSelected = currentValue === choice;
                                const label = allChoiceLabels[choice] || { title: choice, description: '' };
                                const ChoiceIcon = label.icon || SparklesIcon;

                                return (
                                    <button
                                        key={choice}
                                        onClick={() => {
                                            if (currentStep.type === 'partner') {
                                                setPartnerProfile(p => ({ ...p, [currentStep.field!]: choice }));
                                            } else {
                                                setRelationshipProfile(p => ({ ...p, [currentStep.field!]: choice }));
                                            }
                                        }}
                                        className={`p-5 rounded-2xl border-2 transition-all text-center ${
                                            isSelected
                                                ? 'border-accent bg-accent/5 shadow-lg'
                                                : 'border-border-subtle bg-surface-elevated hover:border-accent/50 hover:shadow-md'
                                        }`}
                                    >
                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3 ${
                                            isSelected ? 'bg-accent text-white' : 'bg-surface-hover text-text-tertiary'
                                        }`}>
                                            <ChoiceIcon size={20} />
                                        </div>
                                        <h3 className={`font-semibold mb-1 text-sm ${isSelected ? 'text-accent' : 'text-text-primary'}`}>
                                            {label.title}
                                        </h3>
                                        <p className="text-xs text-text-secondary">{label.description}</p>
                                    </button>
                                );
                            })}
                        </div>
                    ) : (
                        <HybridInput
                            key={currentStep.field} // Force re-render on step change
                            value={
                                currentStep.type === 'partner'
                                    ? (partnerProfile as any)[currentStep.field!]
                                    : (relationshipProfile as any)[currentStep.field!]
                            }
                            onChange={(val) => {
                                if (currentStep.type === 'partner') {
                                    setPartnerProfile(p => ({ ...p, [currentStep.field!]: val }));
                                } else {
                                    setRelationshipProfile(p => ({ ...p, [currentStep.field!]: val }));
                                }
                            }}
                            placeholder={currentStep.placeholder || ''}
                            multiline={currentStep.multiline}
                            isList={currentStep.isList}
                            autoFocus
                            onEnter={isLast ? handleSubmit : handleNext}
                        />
                    )}
                </div>

                <div className="flex justify-between items-center">
                    <button
                        onClick={handleBack}
                        className="flex items-center text-text-secondary hover:text-text-primary px-4 py-2 rounded-xl hover:bg-surface-hover transition-colors"
                    >
                        <ArrowLeftIcon size={20} className="mr-2" /> Back
                    </button>

                    {isLast ? (
                        <button
                            onClick={handleSubmit}
                            disabled={isSubmitting}
                            className="px-8 py-3 bg-accent text-white rounded-xl hover:bg-accent-hover flex items-center shadow-soft disabled:opacity-50 transition-all"
                        >
                            {isSubmitting ? 'Saving...' : 'Complete Profile'}
                        </button>
                    ) : (
                        <button
                            onClick={handleNext}
                            className="px-8 py-3 bg-accent text-white rounded-xl hover:bg-accent-hover flex items-center shadow-soft transition-all"
                        >
                            Next <ArrowRightIcon size={20} className="ml-2" />
                        </button>
                    )}
                </div>
            </div>
        );
    };

    const renderSuccess = () => {
        const otherPartner = partnerId === 'partner_a' ? 'partner_b' : 'partner_a';
        const otherPartnerStatus = partnerStatus[otherPartner];
        const otherPartnerName = otherPartnerStatus.name || (otherPartner === 'partner_a' ? 'Partner A' : 'Partner B');

        return (
            <div className="text-center max-w-lg mx-auto animate-fade-in">
                <div className="w-24 h-24 bg-green-50 text-green-600 rounded-full flex items-center justify-center mx-auto mb-8">
                    <CheckCircleIcon size={48} />
                </div>
                <h2 className="text-h2 text-text-primary mb-4">Profile Complete!</h2>
                <p className="text-body text-text-secondary mb-6">
                    {partnerProfile.name}'s profile has been saved. Serene now has a deep understanding of you.
                </p>

                {!otherPartnerStatus.completed && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-8">
                        <p className="text-amber-800 text-sm">
                            {otherPartnerName} hasn't completed their profile yet.
                            For the best experience, have them fill out their questionnaire too.
                        </p>
                    </div>
                )}

                {otherPartnerStatus.completed && (
                    <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-8">
                        <p className="text-green-800 text-sm">
                            Both profiles are complete! You're all set for personalized guidance.
                        </p>
                    </div>
                )}

                <div className="flex flex-col sm:flex-row justify-center gap-4">
                    <button
                        onClick={() => setCurrentStepIndex(0)}
                        className="px-8 py-3 border border-border-subtle rounded-xl hover:bg-surface-hover transition-colors"
                    >
                        Back to Partner Select
                    </button>
                    <button
                        onClick={() => navigate('/')}
                        className="px-8 py-3 bg-accent text-white rounded-xl hover:bg-accent-hover transition-colors shadow-soft"
                    >
                        Go to Home
                    </button>
                </div>
            </div>
        );
    };

    // Calculate progress
    const currentChapter = currentStep.chapter || 0;

    return (
        <div className="min-h-screen py-12 px-4 flex flex-col">
            {/* Progress Bar - Only show if in a chapter */}
            {currentChapter > 0 && currentChapter <= totalChapters && (
                <div className="max-w-2xl mx-auto w-full mb-12">
                    <div className="flex justify-between text-tiny text-text-tertiary mb-2 uppercase tracking-wider font-medium">
                        <span>Chapter {currentChapter} of {totalChapters}</span>
                        <span>{Math.round((currentStepIndex / (steps.length - 1)) * 100)}% Complete</span>
                    </div>
                    <div className="h-1.5 bg-surface-hover rounded-full overflow-hidden">
                        <div
                            className="h-full bg-accent transition-all duration-500 ease-out"
                            style={{ width: `${(currentStepIndex / (steps.length - 1)) * 100}%` }}
                        />
                    </div>
                </div>
            )}

            <div className="flex-1 flex flex-col justify-center">
                {currentStep.type === 'partner_select' && renderPartnerSelect()}
                {currentStep.type === 'chapter_start' && renderChapterStart()}
                {(currentStep.type === 'partner' || currentStep.type === 'relationship') && renderQuestion()}
                {currentStep.type === 'success' && renderSuccess()}
            </div>

            <VoiceGuidanceModal
                isOpen={showVoiceModal}
                onClose={() => setShowVoiceModal(false)}
            />
        </div>
    );
};

export default Onboarding;
