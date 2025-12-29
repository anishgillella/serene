import React from 'react';
import { X, MessageSquare, Eye, Sparkles, Bot } from 'lucide-react';

interface MessagingPreferences {
    id: string;
    relationship_id: string;
    partner_id: string;
    luna_assistance_enabled: boolean;
    suggestion_mode: string;
    intervention_enabled: boolean;
    intervention_sensitivity: string;
    show_read_receipts: boolean;
    show_typing_indicators: boolean;
    demo_mode_enabled: boolean;
}

interface SettingsDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    preferences: MessagingPreferences | null;
    onUpdatePreference: (key: string, value: boolean | string) => void;
    saving: boolean;
}

const SettingsDrawer: React.FC<SettingsDrawerProps> = ({
    isOpen,
    onClose,
    preferences,
    onUpdatePreference,
    saving
}) => {
    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/60 z-40 transition-opacity backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Drawer */}
            <div className={`
                fixed top-0 right-0 h-full w-full max-w-sm z-50
                transform transition-transform duration-300 ease-in-out
                bg-white shadow-2xl border-l border-gray-200
                ${isOpen ? 'translate-x-0' : 'translate-x-full'}
            `}>
                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b border-gray-200 bg-gray-50">
                    <h2 className="text-lg font-semibold text-gray-900">Chat Settings</h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-200 rounded-full transition-colors"
                    >
                        <X size={20} className="text-gray-600" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 space-y-6 overflow-y-auto h-[calc(100%-72px)] bg-white">
                    {/* Privacy Section */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <div className="p-1.5 bg-blue-100 rounded-lg">
                                <Eye size={18} className="text-blue-600" />
                            </div>
                            <h3 className="font-semibold text-gray-900">Privacy</h3>
                        </div>
                        <div className="space-y-4 bg-gray-50 rounded-xl p-4">
                            <ToggleSetting
                                label="Read Receipts"
                                description="Let your partner know when you've read their messages"
                                checked={preferences?.show_read_receipts ?? true}
                                onChange={(checked) => onUpdatePreference('show_read_receipts', checked)}
                                disabled={saving || !preferences}
                            />
                            <div className="border-t border-gray-200" />
                            <ToggleSetting
                                label="Typing Indicators"
                                description="Show your partner when you're typing a message"
                                checked={preferences?.show_typing_indicators ?? true}
                                onChange={(checked) => onUpdatePreference('show_typing_indicators', checked)}
                                disabled={saving || !preferences}
                            />
                        </div>
                    </section>

                    {/* Demo Mode Section */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <div className="p-1.5 bg-orange-100 rounded-lg">
                                <Bot size={18} className="text-orange-600" />
                            </div>
                            <h3 className="font-semibold text-gray-900">Demo Mode</h3>
                            <span className="text-xs bg-orange-100 text-orange-700 px-2.5 py-1 rounded-full font-medium">
                                Testing
                            </span>
                        </div>
                        <div className="space-y-4 bg-orange-50 rounded-xl p-4 border border-orange-200">
                            <ToggleSetting
                                label="AI Partner Simulation"
                                description="Partner B will be simulated by AI using their onboarding profile"
                                checked={preferences?.demo_mode_enabled ?? false}
                                onChange={(checked) => onUpdatePreference('demo_mode_enabled', checked)}
                                disabled={saving || !preferences}
                            />
                            {preferences?.demo_mode_enabled && (
                                <p className="text-xs text-orange-600 mt-2">
                                    Your partner's responses will be generated by AI based on their personality profile. Great for testing!
                                </p>
                            )}
                        </div>
                    </section>

                    {/* Messaging Section */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <div className="p-1.5 bg-green-100 rounded-lg">
                                <MessageSquare size={18} className="text-green-600" />
                            </div>
                            <h3 className="font-semibold text-gray-900">Messaging</h3>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                            <p className="text-sm text-gray-600">
                                Message history is automatically saved and encrypted for your relationship.
                            </p>
                        </div>
                    </section>

                    {/* Luna AI Section - Coming Soon */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <div className="p-1.5 bg-purple-100 rounded-lg">
                                <Sparkles size={18} className="text-purple-600" />
                            </div>
                            <h3 className="font-semibold text-gray-900">Luna AI Assistance</h3>
                            <span className="text-xs bg-purple-100 text-purple-700 px-2.5 py-1 rounded-full font-medium">
                                Coming Soon
                            </span>
                        </div>
                        <div className="space-y-4 bg-gray-50 rounded-xl p-4 opacity-50">
                            <ToggleSetting
                                label="Luna Suggestions"
                                description="Get AI-powered suggestions before sending sensitive messages"
                                checked={preferences?.luna_assistance_enabled ?? true}
                                onChange={() => {}}
                                disabled={true}
                            />
                            <div className="border-t border-gray-200" />
                            <ToggleSetting
                                label="Conflict Detection"
                                description="Luna will alert you when conversations may be escalating"
                                checked={preferences?.intervention_enabled ?? true}
                                onChange={() => {}}
                                disabled={true}
                            />
                        </div>
                    </section>

                    {/* Info Footer */}
                    <div className="pt-4 border-t border-gray-200">
                        <p className="text-xs text-gray-500 text-center">
                            Changes are saved automatically
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
};

interface ToggleSettingProps {
    label: string;
    description: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
}

const ToggleSetting: React.FC<ToggleSettingProps> = ({
    label,
    description,
    checked,
    onChange,
    disabled = false
}) => {
    return (
        <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{description}</p>
            </div>
            <button
                onClick={() => !disabled && onChange(!checked)}
                disabled={disabled}
                className={`
                    relative w-12 h-7 rounded-full transition-colors flex-shrink-0
                    ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}
                    ${checked ? 'bg-blue-600' : 'bg-gray-300'}
                `}
            >
                <span
                    className={`
                        absolute top-1 left-1 w-5 h-5 rounded-full bg-white shadow-md
                        transition-transform duration-200
                        ${checked ? 'translate-x-5' : 'translate-x-0'}
                    `}
                />
            </button>
        </div>
    );
};

export default SettingsDrawer;
