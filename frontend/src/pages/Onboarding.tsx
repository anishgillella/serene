import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, ArrowLeftIcon, MicIcon, CheckCircleIcon, HeartIcon, UserIcon, UsersIcon, BookOpenIcon, UtensilsIcon, TrophyIcon, StarIcon, AlertCircleIcon, SparklesIcon, EyeIcon, PlayIcon } from 'lucide-react';
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
    // NEW: Repair-specific fields (Phase 1)
    apology_preferences: string;
    post_conflict_need: 'space' | 'connection' | 'depends' | '';
    repair_gestures: string[];
    escalation_triggers: string[];
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

    // Track which partner's onboarding we're in and completion status
    const [currentOnboardingPartner, setCurrentOnboardingPartner] = useState<'partner_a' | 'partner_b'>('partner_a');
    const [partnerACompleted, setPartnerACompleted] = useState(false);
    const [partnerAName, setPartnerAName] = useState('');

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
        // NEW: Repair-specific fields (Phase 1)
        apology_preferences: '',
        post_conflict_need: '',
        repair_gestures: [],
        escalation_triggers: []
    });

    const [relationshipProfile, setRelationshipProfile] = useState<RelationshipProfile>({
        recurring_arguments: [],
        shared_goals: [],
        relationship_dynamic: ''
    });

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showVoiceModal, setShowVoiceModal] = useState(false);

    // Show modal at start of Chapter 2 (Your Story)
    useEffect(() => {
        // Find index of first question in Chapter 2
        const chapter2Index = steps.findIndex(s => s.chapter === 2 && s.type === 'partner');
        if (currentStepIndex === chapter2Index) {
            setShowVoiceModal(true);
        }
    }, [currentStepIndex]);

    // Step Configuration
    const steps = [
        { type: 'welcome', title: "Welcome to Luna", description: "Let's get to know you better so we can help you build a stronger relationship." },

        { type: 'chapter_start', chapter: 1, title: "The Basics", description: "First, tell us a bit about yourself." },
        { type: 'partner', field: 'name', label: "What's your name?", placeholder: "e.g., Alex", icon: UserIcon, chapter: 1 },
        { type: 'partner', field: 'age', label: "How old are you?", placeholder: "e.g., 28", icon: UserIcon, chapter: 1 },
        // Role selection - only shown for Partner A (Partner B's role is pre-set)
        { type: 'role_select', chapter: 1 },

        { type: 'chapter_start', chapter: 2, title: "Your Story", description: "Your past shapes who you are today." },
        { type: 'partner', field: 'background_story', label: "Tell us your story.", sublabel: "Where did you grow up? What was your childhood like? How did you get to where you are now?", placeholder: "I grew up in...", multiline: true, icon: BookOpenIcon, chapter: 2 },
        { type: 'partner', field: 'key_life_experiences', label: "What are the pivotal moments in your life?", sublabel: "Events that changed your perspective or defined your character.", placeholder: "Moving to a new city...", multiline: true, icon: StarIcon, chapter: 2 },
        { type: 'partner', field: 'hobbies', label: "What lights you up?", sublabel: "Hobbies, passions, or activities where you lose track of time.", placeholder: "Photography, Hiking...", isList: true, icon: TrophyIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_food', label: "What's your ultimate comfort food?", sublabel: "The meal that makes everything better.", placeholder: "Spicy Tuna Roll...", icon: UtensilsIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_cuisine', label: "Favorite cuisine?", placeholder: "Japanese, Italian...", icon: UtensilsIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_books', label: "Books that impacted you?", sublabel: "Stories or ideas that stuck with you.", placeholder: "The Alchemist...", isList: true, icon: BookOpenIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_sports', label: "Sports you play or watch?", placeholder: "Basketball...", isList: true, icon: TrophyIcon, chapter: 2 },
        { type: 'partner', field: 'favorite_celebrities', label: "Public figures you admire?", placeholder: "Keanu Reeves...", isList: true, icon: StarIcon, chapter: 2 },

        { type: 'chapter_start', chapter: 3, title: "Inner World", description: "Help us understand how you process emotions." },
        { type: 'partner', field: 'communication_style', label: "How do you communicate under pressure?", sublabel: "Do you need space? Do you want to solve it now? Are you direct or indirect?", placeholder: "I tend to go quiet...", multiline: true, icon: SparklesIcon, chapter: 3 },
        { type: 'partner', field: 'stress_triggers', label: "What triggers your stress?", sublabel: "Specific situations or behaviors that set you off.", placeholder: "Being interrupted...", isList: true, icon: AlertCircleIcon, chapter: 3 },
        { type: 'partner', field: 'soothing_mechanisms', label: "What calms you down?", sublabel: "What helps you return to a baseline state?", placeholder: "Deep breathing, a walk...", isList: true, icon: HeartIcon, chapter: 3 },
        { type: 'partner', field: 'traumatic_experiences', label: "Any past experiences that affect you today?", sublabel: "Optional. Things that might make you sensitive to certain conflicts.", placeholder: "My parents divorce...", multiline: true, icon: AlertCircleIcon, chapter: 3 },

        // NEW: Repair-specific questions (Phase 1)
        { type: 'partner', field: 'apology_preferences', label: "What makes an apology feel genuine to you?", sublabel: "What do you need to hear or see to feel like your partner truly understands?", placeholder: "I need them to acknowledge specifically what they did wrong...", multiline: true, icon: HeartIcon, chapter: 3 },
        { type: 'partner', field: 'post_conflict_need', label: "After a conflict, what do you need first?", sublabel: "Do you need time alone to process, or do you need connection right away?", placeholder: "Space to cool down / Connection right away / Depends on situation", icon: SparklesIcon, chapter: 3, isChoice: true, choices: ['space', 'connection', 'depends'] },
        { type: 'partner', field: 'repair_gestures', label: "What small gestures help you feel better after a fight?", sublabel: "Things your partner can do that help you calm down or feel cared for.", placeholder: "Making me tea, a genuine hug, giving me space for 20 minutes...", isList: true, icon: HeartIcon, chapter: 3 },
        { type: 'partner', field: 'escalation_triggers', label: "What does your partner do during fights that makes things worse?", sublabel: "Behaviors or phrases that escalate the conflict for you.", placeholder: "Saying 'calm down', walking away mid-sentence, bringing up past issues...", isList: true, icon: AlertCircleIcon, chapter: 3 },

        { type: 'chapter_start', chapter: 4, title: "Your Partner", description: "Tell us about the person you love." },
        { type: 'partner', field: 'partner_description', label: "How would you describe your partner?", sublabel: "Their personality, their vibe, their essence.", placeholder: "She is creative and...", multiline: true, icon: EyeIcon, chapter: 4 },
        { type: 'partner', field: 'what_i_admire', label: "What do you admire most about them?", sublabel: "The qualities that made you fall for them.", placeholder: "Her empathy...", multiline: true, icon: HeartIcon, chapter: 4 },
        { type: 'partner', field: 'what_frustrates_me', label: "What challenges do you face with them?", sublabel: "Be honest. What behaviors or traits are difficult for you?", placeholder: "She can be disorganized...", multiline: true, icon: AlertCircleIcon, chapter: 4 },

        { type: 'chapter_start', chapter: 5, title: "Us", description: "The dynamics of your relationship." },
        { type: 'relationship', field: 'relationship_dynamic', label: "How do you two interact?", sublabel: "Are you opposites? Two peas in a pod? Who leads, who follows?", placeholder: "We are opposites...", multiline: true, icon: HeartIcon, chapter: 5 },
        { type: 'relationship', field: 'recurring_arguments', label: "What do you fight about most?", sublabel: "The topics that keep coming up.", placeholder: "Chores, Money...", isList: true, icon: AlertCircleIcon, chapter: 5 },
        { type: 'relationship', field: 'shared_goals', label: "What are you building together?", sublabel: "Your shared vision for the future.", placeholder: "Buying a house...", isList: true, icon: TrophyIcon, chapter: 5 },

        { type: 'partner_handoff', chapter: 6 },
        { type: 'success', chapter: 7 }
    ];

    const handleNext = () => {
        if (currentStepIndex < steps.length - 1) {
            let nextIndex = currentStepIndex + 1;

            // Skip role_select for Partner B (their role is already set)
            if (currentOnboardingPartner === 'partner_b' && steps[nextIndex]?.type === 'role_select') {
                nextIndex++;
            }

            // Skip partner_handoff for Partner B (go straight to success)
            if (currentOnboardingPartner === 'partner_b' && steps[nextIndex]?.type === 'partner_handoff') {
                nextIndex++;
            }

            setCurrentStepIndex(nextIndex);
        }
    };

    const handleBack = () => {
        if (currentStepIndex > 0) {
            let prevIndex = currentStepIndex - 1;

            // Skip role_select for Partner B when going back
            if (currentOnboardingPartner === 'partner_b' && steps[prevIndex]?.type === 'role_select') {
                prevIndex--;
            }

            setCurrentStepIndex(prevIndex);
        }
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
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
                if (currentOnboardingPartner === 'partner_a') {
                    // Partner A completed - go to handoff screen
                    setPartnerAName(partnerProfile.name);
                    setPartnerACompleted(true);
                    handleNext(); // Go to partner_handoff step
                } else {
                    // Partner B completed - go to final success
                    handleNext(); // Go to success step
                }
            } else {
                console.error('Submission failed');
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Reset form and start Partner B's onboarding
    const startPartnerBOnboarding = () => {
        // Reset all form state for Partner B
        setPartnerProfile({
            name: '',
            role: 'partner_b',
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
            apology_preferences: '',
            post_conflict_need: '',
            repair_gestures: [],
            escalation_triggers: []
        });
        setRelationshipProfile({
            recurring_arguments: [],
            shared_goals: [],
            relationship_dynamic: ''
        });
        setPartnerId('partner_b');
        setCurrentOnboardingPartner('partner_b');
        // Go back to welcome screen for Partner B
        setCurrentStepIndex(0);
    };

    const currentStep = steps[currentStepIndex];

    // Renderers
    const renderWelcome = () => (
        <div className="text-center max-w-lg mx-auto animate-fade-in">
            <div className="w-24 h-24 bg-surface-hover rounded-full flex items-center justify-center mx-auto mb-8">
                <HeartIcon size={48} className="text-accent" />
            </div>
            {currentOnboardingPartner === 'partner_b' ? (
                <>
                    <h2 className="text-h1 text-text-primary mb-6">Welcome, Partner B!</h2>
                    <p className="text-body-lg text-text-secondary mb-4 leading-relaxed">
                        {partnerAName} has completed their profile.
                        Now it's your turn to share your perspective.
                    </p>
                    <p className="text-body text-text-tertiary mb-10">
                        This helps us create personalized repair plans that work for both of you.
                    </p>
                </>
            ) : (
                <>
                    <h2 className="text-h1 text-text-primary mb-6">Welcome to Serene</h2>
                    <p className="text-body-lg text-text-secondary mb-10 leading-relaxed">
                        Let's build a deep understanding of you and your relationship.
                        We've broken this down into 5 short chapters.
                    </p>
                </>
            )}
            <button
                onClick={handleNext}
                className="px-10 py-4 bg-accent text-white rounded-2xl font-medium hover:bg-accent-hover transition-all shadow-lg hover:shadow-xl hover:-translate-y-1 text-lg"
            >
                Start Chapter 1
            </button>
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

    const renderRoleSelect = () => (
        <div className="max-w-3xl mx-auto animate-fade-in">
            <h2 className="text-h2 text-text-primary mb-4 text-center">Who are you?</h2>
            <p className="text-body text-text-secondary mb-12 text-center">Select your role in the relationship.</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <button
                    onClick={() => { setPartnerId('partner_a'); setPartnerProfile(p => ({ ...p, role: 'partner_a' })); handleNext(); }}
                    className="p-10 bg-surface-elevated border-2 border-transparent rounded-3xl hover:border-accent hover:shadow-lg transition-all text-left group"
                >
                    <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <UserIcon size={32} />
                    </div>
                    <h3 className="text-h3 text-text-primary mb-2">Partner A</h3>
                    <p className="text-body text-text-secondary">First partner (default)</p>
                </button>

                <button
                    onClick={() => { setPartnerId('partner_b'); setPartnerProfile(p => ({ ...p, role: 'partner_b' })); handleNext(); }}
                    className="p-10 bg-surface-elevated border-2 border-transparent rounded-3xl hover:border-accent hover:shadow-lg transition-all text-left group"
                >
                    <div className="w-16 h-16 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <UserIcon size={32} />
                    </div>
                    <h3 className="text-h3 text-text-primary mb-2">Partner B</h3>
                    <p className="text-body text-text-secondary">Second partner</p>
                </button>
            </div>
        </div>
    );

    const renderQuestion = () => {
        const Icon = currentStep.icon || SparklesIcon;
        const isLast = currentStepIndex === steps.length - 2; // -2 because last is success
        const isChoiceQuestion = currentStep.isChoice && currentStep.choices;

        return (
            <div className="max-w-3xl mx-auto animate-fade-in">
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
                        // Choice-based input for post_conflict_need
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
                            {currentStep.choices!.map((choice: string) => {
                                const currentValue = currentStep.type === 'partner'
                                    ? (partnerProfile as any)[currentStep.field!]
                                    : (relationshipProfile as any)[currentStep.field!];
                                const isSelected = currentValue === choice;
                                const choiceLabels: Record<string, { title: string; description: string }> = {
                                    'space': { title: 'Space First', description: 'I need time alone to cool down and process' },
                                    'connection': { title: 'Connection First', description: 'I need to feel close again right away' },
                                    'depends': { title: 'It Depends', description: 'It depends on the situation' }
                                };
                                const label = choiceLabels[choice] || { title: choice, description: '' };

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
                                        className={`p-6 rounded-2xl border-2 transition-all text-left ${
                                            isSelected
                                                ? 'border-accent bg-accent/5 shadow-lg'
                                                : 'border-border-subtle bg-surface-elevated hover:border-accent/50 hover:shadow-md'
                                        }`}
                                    >
                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${
                                            isSelected ? 'bg-accent text-white' : 'bg-surface-hover text-text-tertiary'
                                        }`}>
                                            {choice === 'space' && <SparklesIcon size={20} />}
                                            {choice === 'connection' && <HeartIcon size={20} />}
                                            {choice === 'depends' && <AlertCircleIcon size={20} />}
                                        </div>
                                        <h3 className={`font-semibold mb-1 ${isSelected ? 'text-accent' : 'text-text-primary'}`}>
                                            {label.title}
                                        </h3>
                                        <p className="text-small text-text-secondary">{label.description}</p>
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

    // Partner handoff screen - shown after Partner A completes
    const renderPartnerHandoff = () => (
        <div className="text-center max-w-lg mx-auto animate-fade-in">
            <div className="w-24 h-24 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-8">
                <UsersIcon size={48} />
            </div>
            <h2 className="text-h2 text-text-primary mb-4">
                Great job, {partnerAName || 'Partner A'}!
            </h2>
            <p className="text-body text-text-secondary mb-6">
                Your profile has been saved. For personalized repair plans to work,
                we need to understand both partners.
            </p>
            <div className="bg-surface-elevated rounded-2xl p-6 mb-8">
                <div className="flex items-center justify-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                        <CheckCircleIcon size={20} />
                    </div>
                    <span className="text-text-primary font-medium">{partnerAName || 'Partner A'}</span>
                    <span className="text-text-tertiary">completed</span>
                </div>
                <div className="flex items-center justify-center gap-3">
                    <div className="w-10 h-10 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center">
                        <UserIcon size={20} />
                    </div>
                    <span className="text-text-primary font-medium">Partner B</span>
                    <span className="text-text-tertiary">waiting...</span>
                </div>
            </div>
            <p className="text-body-sm text-text-tertiary mb-8">
                Please hand the device to your partner so they can complete their profile.
            </p>
            <button
                onClick={startPartnerBOnboarding}
                className="px-10 py-4 bg-accent text-white rounded-2xl font-medium hover:bg-accent-hover transition-all shadow-lg hover:shadow-xl hover:-translate-y-1 text-lg"
            >
                Start Partner B's Profile
            </button>
        </div>
    );

    const renderSuccess = () => (
        <div className="text-center max-w-lg mx-auto animate-fade-in">
            <div className="w-24 h-24 bg-green-50 text-green-600 rounded-full flex items-center justify-center mx-auto mb-8">
                <CheckCircleIcon size={48} />
            </div>
            <h2 className="text-h2 text-text-primary mb-4">
                {partnerACompleted ? 'Both Profiles Complete!' : 'All Set!'}
            </h2>
            <p className="text-body text-text-secondary mb-6">
                {partnerACompleted
                    ? 'Luna now has a deep understanding of both of you. Personalized repair plans are now enabled!'
                    : 'Your comprehensive profile has been created. Luna now has a deep understanding of you.'
                }
            </p>
            {partnerACompleted && (
                <div className="bg-surface-elevated rounded-2xl p-6 mb-8">
                    <div className="flex items-center justify-center gap-6">
                        <div className="text-center">
                            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-2">
                                <CheckCircleIcon size={24} />
                            </div>
                            <span className="text-text-secondary text-sm">{partnerAName}</span>
                        </div>
                        <HeartIcon size={24} className="text-accent" />
                        <div className="text-center">
                            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-2">
                                <CheckCircleIcon size={24} />
                            </div>
                            <span className="text-text-secondary text-sm">{partnerProfile.name}</span>
                        </div>
                    </div>
                </div>
            )}
            <div className="flex justify-center space-x-4">
                <button
                    onClick={() => navigate('/')}
                    className="px-8 py-3 border border-border-subtle rounded-xl hover:bg-surface-hover transition-colors"
                >
                    Go Home
                </button>
                <button
                    onClick={() => navigate('/library')}
                    className="px-8 py-3 bg-accent text-white rounded-xl hover:bg-accent-hover transition-colors shadow-soft"
                >
                    Upload Books
                </button>
            </div>
        </div>
    );

    // Calculate progress
    const currentChapter = currentStep.chapter || 0;
    const totalChapters = 5;

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
                {currentStep.type === 'welcome' && renderWelcome()}
                {currentStep.type === 'chapter_start' && renderChapterStart()}
                {currentStep.type === 'role_select' && renderRoleSelect()}
                {(currentStep.type === 'partner' || currentStep.type === 'relationship') && renderQuestion()}
                {currentStep.type === 'partner_handoff' && renderPartnerHandoff()}
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
