import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, ArrowLeftIcon, MicIcon, CheckCircleIcon, HeartIcon, UserIcon, BookOpenIcon, UtensilsIcon, TrophyIcon, StarIcon, AlertCircleIcon, SparklesIcon, EyeIcon, PlayIcon } from 'lucide-react';
import VoiceGuidanceModal from '../components/ui/VoiceGuidanceModal';

// Types
interface PartnerProfile {
    name: string;
    role: 'boyfriend' | 'girlfriend' | 'partner_a' | 'partner_b';
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
}

interface RelationshipProfile {
    recurring_arguments: string[];
    shared_goals: string[];
    relationship_dynamic: string;
}

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

    // Ref to keep track of current value without restarting effect
    const valueRef = React.useRef(value);
    useEffect(() => {
        valueRef.current = value;
    }, [value]);

    useEffect(() => {
        if ('webkitSpeechRecognition' in window) {
            const r = new (window as any).webkitSpeechRecognition();
            r.continuous = true; // Enable continuous listening
            r.interimResults = false;
            r.lang = 'en-US';

            r.onresult = (event: any) => {
                // Get the latest result
                const resultIndex = event.results.length - 1;
                const latestResult = event.results[resultIndex];

                // Only process if it's a new result we haven't handled yet
                if (latestResult.isFinal) {
                    const text = latestResult[0].transcript.trim();

                    if (isList && Array.isArray(valueRef.current)) {
                        const items = text.split(/,| and /).map((s: string) => s.trim()).filter(Boolean);
                        onChange([...valueRef.current, ...items]);
                    } else {
                        // Use functional update pattern indirectly by referencing current value
                        // Since we can't access the *latest* state inside this closure easily without refs,
                        // we rely on the fact that 'value' is in the dependency array.
                        // However, with continuous listening, the effect might re-run and reset recognition.
                        // To fix this, we need to NOT re-create recognition on every value change.
                        // But we need the current value to append.

                        // BETTER APPROACH: Use a ref for the current value so we don't need to re-bind
                        // But for now, let's just fix the appending logic.

                        // The issue is likely that 'value' is stale or we are re-appending the whole transcript.
                        // With continuous=true, event.results accumulates.
                        // We should only append the NEWEST result.

                        // We are already doing that by taking event.results[length-1].
                        // The problem is likely that 'value' inside this callback is stale because
                        // the effect doesn't re-run (or if it does, it restarts recognition).

                        // If we put 'value' in deps, recognition restarts on every word. Bad.
                        // We need to remove 'value' from deps and use a functional update or ref.
                        // Since onChange is passed from parent, we can just call onChange(prev => ...)? 
                        // No, onChange expects a value, not a function usually.

                        // Let's use a ref to track the current value without re-triggering the effect.
                        // See below for the ref implementation.

                        // Using the ref value:
                        const currentValue = valueRef.current as string;
                        const newValue = currentValue ? currentValue + ' ' + text : text;
                        onChange(newValue);
                    }
                }
            };

            r.onerror = (event: any) => {
                console.error("Speech recognition error", event.error);
                setIsListening(false);
            };

            // Don't stop on end for continuous, unless manually stopped
            // r.onend = () => setIsListening(false); 

            setRecognition(r);

            // Cleanup function
            return () => {
                if (r) {
                    r.stop();
                    r.onresult = null;
                    r.onerror = null;
                    r.onend = null;
                }
            };
        }
    }, [isList]); // Remove 'value' and 'onChange' from deps to prevent restarting

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
        if (isList) {
            // Split by comma or newline
            onChange(e.target.value.split(/[\n,]+/).map(s => s.trim()).filter(Boolean));
        } else {
            onChange(e.target.value);
        }
    };

    // Handle Enter key
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            if (multiline && !e.shiftKey) {
                return; // Allow new lines in textarea
            }
            e.preventDefault();
            if (onEnter) onEnter();
        }
    };

    const displayValue = isList && Array.isArray(value) ? value.join(', ') : value as string;

    return (
        <div className={`relative ${multiline ? 'w-full' : 'w-full max-w-2xl mx-auto'}`}>
            {multiline ? (
                <textarea
                    value={displayValue}
                    onChange={handleTextChange}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    autoFocus={autoFocus}
                    className="w-full pl-6 pr-20 py-4 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-2xl transition-all outline-none min-h-[200px] resize-y text-lg"
                />
            ) : (
                <input
                    type="text"
                    value={displayValue}
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
        role: 'boyfriend',
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
        what_frustrates_me: ''
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
        { type: 'partner', field: 'name', label: "What's your name?", placeholder: "e.g., Adrian", icon: UserIcon, chapter: 1 },
        { type: 'partner', field: 'age', label: "How old are you?", placeholder: "e.g., 28", icon: UserIcon, chapter: 1 },
        { type: 'partner', field: 'role', label: "What is your role in the relationship?", placeholder: "e.g., Boyfriend, Partner A", icon: UserIcon, chapter: 1 },

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

        { type: 'chapter_start', chapter: 4, title: "Your Partner", description: "Tell us about the person you love." },
        { type: 'partner', field: 'partner_description', label: "How would you describe your partner?", sublabel: "Their personality, their vibe, their essence.", placeholder: "She is creative and...", multiline: true, icon: EyeIcon, chapter: 4 },
        { type: 'partner', field: 'what_i_admire', label: "What do you admire most about them?", sublabel: "The qualities that made you fall for them.", placeholder: "Her empathy...", multiline: true, icon: HeartIcon, chapter: 4 },
        { type: 'partner', field: 'what_frustrates_me', label: "What challenges do you face with them?", sublabel: "Be honest. What behaviors or traits are difficult for you?", placeholder: "She can be disorganized...", multiline: true, icon: AlertCircleIcon, chapter: 4 },

        { type: 'chapter_start', chapter: 5, title: "Us", description: "The dynamics of your relationship." },
        { type: 'relationship', field: 'relationship_dynamic', label: "How do you two interact?", sublabel: "Are you opposites? Two peas in a pod? Who leads, who follows?", placeholder: "We are opposites...", multiline: true, icon: HeartIcon, chapter: 5 },
        { type: 'relationship', field: 'recurring_arguments', label: "What do you fight about most?", sublabel: "The topics that keep coming up.", placeholder: "Chores, Money...", isList: true, icon: AlertCircleIcon, chapter: 5 },
        { type: 'relationship', field: 'shared_goals', label: "What are you building together?", sublabel: "Your shared vision for the future.", placeholder: "Buying a house...", isList: true, icon: TrophyIcon, chapter: 5 },

        { type: 'success', chapter: 6 }
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

    const currentStep = steps[currentStepIndex];

    // Renderers
    const renderWelcome = () => (
        <div className="text-center max-w-lg mx-auto animate-fade-in">
            <div className="w-24 h-24 bg-surface-hover rounded-full flex items-center justify-center mx-auto mb-8">
                <HeartIcon size={48} className="text-accent" />
            </div>
            <h2 className="text-h1 text-text-primary mb-6">Welcome to Serene</h2>
            <p className="text-body-lg text-text-secondary mb-10 leading-relaxed">
                Let's build a deep understanding of you and your relationship.
                We've broken this down into 5 short chapters.
            </p>
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
                    onClick={() => { setPartnerId('partner_a'); setPartnerProfile(p => ({ ...p, role: 'boyfriend' })); handleNext(); }}
                    className="p-10 bg-surface-elevated border-2 border-transparent rounded-3xl hover:border-accent hover:shadow-lg transition-all text-left group"
                >
                    <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <UserIcon size={32} />
                    </div>
                    <h3 className="text-h3 text-text-primary mb-2">Partner A</h3>
                    <p className="text-body text-text-secondary">Usually the Boyfriend (Default)</p>
                </button>

                <button
                    onClick={() => { setPartnerId('partner_b'); setPartnerProfile(p => ({ ...p, role: 'girlfriend' })); handleNext(); }}
                    className="p-10 bg-surface-elevated border-2 border-transparent rounded-3xl hover:border-accent hover:shadow-lg transition-all text-left group"
                >
                    <div className="w-16 h-16 bg-pink-50 text-pink-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <UserIcon size={32} />
                    </div>
                    <h3 className="text-h3 text-text-primary mb-2">Partner B</h3>
                    <p className="text-body text-text-secondary">Usually the Girlfriend</p>
                </button>
            </div>
        </div>
    );

    const renderQuestion = () => {
        const Icon = currentStep.icon || SparklesIcon;
        const isLast = currentStepIndex === steps.length - 2; // -2 because last is success

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

    const renderSuccess = () => (
        <div className="text-center max-w-lg mx-auto animate-fade-in">
            <div className="w-24 h-24 bg-green-50 text-green-600 rounded-full flex items-center justify-center mx-auto mb-8">
                <CheckCircleIcon size={48} />
            </div>
            <h2 className="text-h2 text-text-primary mb-4">All Set!</h2>
            <p className="text-body text-text-secondary mb-10">
                Your comprehensive profile has been created. Luna now has a deep understanding of you.
            </p>
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
