import React, { useState, useEffect } from 'react';
import {
    UserIcon,
    BookOpenIcon,
    TrophyIcon,
    UtensilsIcon,
    StarIcon,
    SparklesIcon,
    AlertCircleIcon,
    HeartIcon,
    EyeIcon,
    PencilIcon,
    CheckIcon,
    XIcon,
    Loader2
} from 'lucide-react';

// Types (Mirroring Onboarding.tsx)
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

interface FullProfile {
    partner_profile: PartnerProfile;
    relationship_profile: RelationshipProfile;
}

const Profile = () => {
    const [profile, setProfile] = useState<FullProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [editingField, setEditingField] = useState<string | null>(null);
    const [editValue, setEditValue] = useState<string | string[]>('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchProfile();
    }, []);

    const fetchProfile = async () => {
        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${apiUrl}/api/onboarding/profile`);
            const data = await response.json();

            if (data.exists) {
                setProfile(data.data);
            } else {
                setError("No profile found. Please complete onboarding first.");
            }
        } catch (err) {
            console.error("Error fetching profile:", err);
            setError("Failed to load profile.");
        } finally {
            setLoading(false);
        }
    };

    const startEditing = (field: string, value: string | string[], section: 'partner' | 'relationship') => {
        setEditingField(`${section}.${field}`);
        setEditValue(value);
    };

    const cancelEditing = () => {
        setEditingField(null);
        setEditValue('');
    };

    const saveField = async (field: string, section: 'partner' | 'relationship') => {
        if (!profile) return;
        setSaving(true);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

            // Construct update payload
            const updatePayload: any = {};
            if (section === 'partner') {
                updatePayload.partner_profile = { [field]: editValue };
            } else {
                updatePayload.relationship_profile = { [field]: editValue };
            }

            const response = await fetch(`${apiUrl}/api/onboarding/profile`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatePayload)
            });

            if (response.ok) {
                // Update local state
                setProfile(prev => {
                    if (!prev) return null;
                    const newProfile = { ...prev };
                    if (section === 'partner') {
                        (newProfile.partner_profile as any)[field] = editValue;
                    } else {
                        (newProfile.relationship_profile as any)[field] = editValue;
                    }
                    return newProfile;
                });
                setEditingField(null);
            } else {
                alert("Failed to save changes.");
            }
        } catch (err) {
            console.error("Error saving profile:", err);
            alert("Error saving changes.");
        } finally {
            setSaving(false);
        }
    };

    const renderField = (
        label: string,
        value: string | string[] | number,
        field: string,
        section: 'partner' | 'relationship',
        icon: React.ElementType,
        isList: boolean = false,
        multiline: boolean = false
    ) => {
        const isEditing = editingField === `${section}.${field}`;
        const displayValue = isList && Array.isArray(value) ? value.join(', ') : value;

        return (
            <div className="bg-surface-elevated p-6 rounded-2xl mb-4 group hover:shadow-md transition-all border border-transparent hover:border-border-subtle">
                <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2 text-text-secondary mb-1">
                        <div className="p-1.5 bg-surface-hover rounded-lg">
                            {React.createElement(icon, { size: 16, className: "text-accent" })}
                        </div>
                        <span className="text-small font-medium uppercase tracking-wider">{label}</span>
                    </div>

                    {!isEditing && (
                        <button
                            onClick={() => startEditing(field, value as any, section)}
                            className="text-text-tertiary hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity p-2 hover:bg-surface-hover rounded-lg"
                        >
                            <PencilIcon size={16} />
                        </button>
                    )}
                </div>

                {isEditing ? (
                    <div className="animate-fade-in">
                        {multiline ? (
                            <textarea
                                value={isList && Array.isArray(editValue) ? editValue.join(', ') : editValue as string}
                                onChange={(e) => setEditValue(isList ? e.target.value.split(',').map(s => s.trim()) : e.target.value)}
                                className="w-full p-3 bg-surface-hover rounded-xl border border-accent outline-none min-h-[100px] text-body"
                                autoFocus
                            />
                        ) : (
                            <input
                                type="text"
                                value={isList && Array.isArray(editValue) ? editValue.join(', ') : editValue as string}
                                onChange={(e) => setEditValue(isList ? e.target.value.split(',').map(s => s.trim()) : e.target.value)}
                                className="w-full p-3 bg-surface-hover rounded-xl border border-accent outline-none text-body"
                                autoFocus
                            />
                        )}
                        <div className="flex justify-end gap-2 mt-3">
                            <button
                                onClick={cancelEditing}
                                className="px-3 py-1.5 text-text-secondary hover:bg-surface-hover rounded-lg text-small"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => saveField(field, section)}
                                disabled={saving}
                                className="px-3 py-1.5 bg-accent text-white rounded-lg text-small flex items-center gap-1 hover:bg-accent-hover"
                            >
                                {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckIcon size={14} />}
                                Save
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="text-body-lg text-text-primary whitespace-pre-wrap pl-9">
                        {displayValue || <span className="text-text-tertiary italic">Not set</span>}
                    </div>
                )}
            </div>
        );
    };

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center">
            <Loader2 className="animate-spin text-accent" size={32} />
        </div>
    );

    if (error) return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
            <AlertCircleIcon className="text-red-500 mb-4" size={48} />
            <h2 className="text-h2 mb-2">Profile Not Found</h2>
            <p className="text-text-secondary mb-6">{error}</p>
            <a href="/onboarding" className="px-6 py-3 bg-accent text-white rounded-xl hover:bg-accent-hover">
                Start Onboarding
            </a>
        </div>
    );

    if (!profile) return null;

    const p = profile.partner_profile;
    const r = profile.relationship_profile;

    return (
        <div className="max-w-4xl mx-auto py-8 px-4 animate-fade-in">
            <header className="mb-10">
                <h1 className="text-h1 text-text-primary mb-2">Your Profile</h1>
                <p className="text-body text-text-secondary">
                    This is what Luna knows about you. Keep it updated for better advice.
                </p>
            </header>

            <div className="space-y-12">
                {/* Section 1: The Basics */}
                <section>
                    <h2 className="text-h3 text-text-primary mb-6 flex items-center gap-2">
                        <UserIcon className="text-accent" /> The Basics
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {renderField("Name", p.name, "name", "partner", UserIcon)}
                        {renderField("Age", p.age, "age", "partner", UserIcon)}
                    </div>
                </section>

                {/* Section 2: Your Story */}
                <section>
                    <h2 className="text-h3 text-text-primary mb-6 flex items-center gap-2">
                        <BookOpenIcon className="text-accent" /> Your Story
                    </h2>
                    <div className="space-y-2">
                        {renderField("Background Story", p.background_story, "background_story", "partner", BookOpenIcon, false, true)}
                        {renderField("Key Life Experiences", p.key_life_experiences, "key_life_experiences", "partner", StarIcon, false, true)}
                        {renderField("Hobbies", p.hobbies, "hobbies", "partner", TrophyIcon, true)}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {renderField("Favorite Food", p.favorite_food, "favorite_food", "partner", UtensilsIcon)}
                            {renderField("Favorite Cuisine", p.favorite_cuisine, "favorite_cuisine", "partner", UtensilsIcon)}
                        </div>
                        {renderField("Favorite Books", p.favorite_books, "favorite_books", "partner", BookOpenIcon, true)}
                        {renderField("Favorite Sports", p.favorite_sports, "favorite_sports", "partner", TrophyIcon, true)}
                        {renderField("Favorite Celebrities", p.favorite_celebrities, "favorite_celebrities", "partner", StarIcon, true)}
                    </div>
                </section>

                {/* Section 3: Inner World */}
                <section>
                    <h2 className="text-h3 text-text-primary mb-6 flex items-center gap-2">
                        <SparklesIcon className="text-accent" /> Inner World
                    </h2>
                    <div className="space-y-2">
                        {renderField("Communication Style", p.communication_style, "communication_style", "partner", SparklesIcon, false, true)}
                        {renderField("Stress Triggers", p.stress_triggers, "stress_triggers", "partner", AlertCircleIcon, true)}
                        {renderField("Soothing Mechanisms", p.soothing_mechanisms, "soothing_mechanisms", "partner", HeartIcon, true)}
                        {renderField("Traumatic Experiences", p.traumatic_experiences, "traumatic_experiences", "partner", AlertCircleIcon, false, true)}
                    </div>
                </section>

                {/* Section 4: Your Partner */}
                <section>
                    <h2 className="text-h3 text-text-primary mb-6 flex items-center gap-2">
                        <EyeIcon className="text-accent" /> Your Partner
                    </h2>
                    <div className="space-y-2">
                        {renderField("Description", p.partner_description, "partner_description", "partner", EyeIcon, false, true)}
                        {renderField("What You Admire", p.what_i_admire, "what_i_admire", "partner", HeartIcon, false, true)}
                        {renderField("What Frustrates You", p.what_frustrates_me, "what_frustrates_me", "partner", AlertCircleIcon, false, true)}
                    </div>
                </section>

                {/* Section 5: Us */}
                <section>
                    <h2 className="text-h3 text-text-primary mb-6 flex items-center gap-2">
                        <HeartIcon className="text-accent" /> Us
                    </h2>
                    <div className="space-y-2">
                        {renderField("Relationship Dynamic", r.relationship_dynamic, "relationship_dynamic", "relationship", HeartIcon, false, true)}
                        {renderField("Recurring Arguments", r.recurring_arguments, "recurring_arguments", "relationship", AlertCircleIcon, true)}
                        {renderField("Shared Goals", r.shared_goals, "shared_goals", "relationship", TrophyIcon, true)}
                    </div>
                </section>
            </div>
        </div>
    );
};

export default Profile;
