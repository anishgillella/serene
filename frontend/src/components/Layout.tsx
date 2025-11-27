import React from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './navigation/Sidebar';
import BottomNav from './navigation/BottomNav';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const isFullWidthPage = ['/fight-capture', '/post-fight'].includes(location.pathname);

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary font-sans">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <main className={`transition-all duration-300 md:ml-64 pb-20 md:pb-0 min-h-screen`}>
        <div className={`w-full p-4 md:p-8 ${isFullWidthPage ? 'max-w-full' : 'max-w-5xl mx-auto'}`}>
          {children}
        </div>
      </main>

      {/* Mobile Bottom Nav */}
      <BottomNav />
    </div>
  );
};

export default Layout;