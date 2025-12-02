import React from 'react';
import { MicIcon, XIcon } from 'lucide-react';

interface VoiceGuidanceModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const VoiceGuidanceModal: React.FC<VoiceGuidanceModalProps> = ({ isOpen, onClose }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-3xl max-w-md w-full p-8 relative shadow-2xl transform transition-all scale-100">
                <button
                    onClick={onClose}
                    className="absolute right-4 top-4 text-text-tertiary hover:text-text-primary transition-colors"
                >
                    <XIcon size={24} />
                </button>

                <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mb-6 mx-auto">
                    <MicIcon size={32} className="text-accent" />
                </div>

                <h3 className="text-h3 text-center text-text-primary mb-4">
                    Speak From the Heart
                </h3>

                <p className="text-body text-text-secondary text-center mb-8">
                    We know relationships are complex and hard to put into boxes.
                    <br /><br />
                    <strong>You don't need perfect answers.</strong>
                    <br /><br />
                    Use the microphone button to just talk to us naturally. Share as much detail as you want, and we'll handle the rest.
                </p>

                <button
                    onClick={onClose}
                    className="w-full py-4 bg-accent text-white rounded-2xl font-medium hover:bg-accent-hover transition-colors shadow-lg"
                >
                    Got it, let's talk
                </button>
            </div>
        </div>
    );
};

export default VoiceGuidanceModal;
