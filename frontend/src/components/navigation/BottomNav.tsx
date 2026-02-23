import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    LayoutDashboard,
    Mic,
    BarChart2,
    MessageCircle,
    Bell
} from 'lucide-react';

const BottomNav = () => {
    const location = useLocation();

    const navItems = [
        { icon: LayoutDashboard, label: 'Home', path: '/' },
        { icon: MessageCircle, label: 'Chat', path: '/chat' },
        { icon: Mic, label: 'Capture', path: '/fight-capture' },
        { icon: BarChart2, label: 'Stats', path: '/analytics' },
        { icon: Bell, label: 'Alerts', path: '/notifications' },
    ];

    return (
        <div className="md:hidden fixed bottom-0 left-0 right-0 bg-surface-elevated border-t border-border-subtle pb-safe z-50">
            <nav className="flex justify-around items-center h-16 px-2">
                {navItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={`flex flex-col items-center justify-center w-full h-full space-y-1 ${isActive ? 'text-accent' : 'text-text-tertiary'
                                }`}
                        >
                            <item.icon
                                size={22}
                                strokeWidth={isActive ? 2 : 1.5}
                                className={`transition-transform duration-200 ${isActive ? 'scale-110' : ''
                                    }`}
                            />
                            <span className="text-[10px] font-medium">{item.label}</span>
                        </NavLink>
                    );
                })}
            </nav>
        </div>
    );
};

export default BottomNav;
