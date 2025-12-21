import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    LayoutDashboard,
    Calendar,
    Mic,
    History,
    BarChart2,
    Upload,
    Settings,
    Moon,
    Heart,
    User
} from 'lucide-react';
import { useRelationship } from '../../contexts/RelationshipContext';

const Sidebar = () => {
    const location = useLocation();

    // Use relationship context for dynamic partner names
    const { partnerAName, partnerBName } = useRelationship();
    const displayName = partnerAName || "Partner A";
    const partnerName = partnerBName || "Partner B";

    // Get initials for avatar
    const getInitials = (name: string) => {
        return name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
    };

    const navItems = [
        { icon: LayoutDashboard, label: 'Home', path: '/' },
        { icon: Mic, label: 'Fight Capture', path: '/fight-capture' },
        { icon: Calendar, label: 'Calendar', path: '/calendar' },
        { icon: History, label: 'History', path: '/history' },
        { icon: BarChart2, label: 'Analytics', path: '/analytics' },
        { icon: Upload, label: 'Upload', path: '/upload' },
        { icon: Heart, label: 'Onboarding', path: '/onboarding' },
        { icon: User, label: 'Profile', path: '/profile' },
    ];

    return (
        <aside className="hidden md:flex flex-col w-64 h-screen fixed left-0 top-0 bg-surface-elevated border-r border-border-subtle z-50">
            {/* Logo */}
            <div className="p-8 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center">
                    <Moon size={18} className="text-accent fill-accent" />
                </div>
                <span className="text-h3 font-medium text-text-primary tracking-tight">Luna</span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 space-y-2">
                {navItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                                ? 'bg-surface-hover text-text-primary font-medium shadow-sm'
                                : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                                }`}
                        >
                            <item.icon
                                size={20}
                                strokeWidth={1.5}
                                className={`transition-colors ${isActive ? 'text-accent' : 'text-text-tertiary group-hover:text-accent'
                                    }`}
                            />
                            <span>{item.label}</span>
                        </NavLink>
                    );
                })}
            </nav>

            {/* User Profile / Settings */}
            <div className="p-4 mt-auto border-t border-border-subtle">
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-surface-hover cursor-pointer transition-colors">
                    <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent font-medium text-xs">
                        {getInitials(displayName)}
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-small font-medium text-text-primary truncate">
                            {displayName}
                        </div>
                        <div className="text-tiny text-text-tertiary truncate">
                            with {partnerName}
                        </div>
                    </div>
                    <Settings size={16} className="text-text-tertiary" />
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
