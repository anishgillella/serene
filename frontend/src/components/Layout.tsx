import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { HomeIcon } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({
  children
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get the current state name for the status indicator
  const getStateName = () => {
    switch (location.pathname) {
      case '/':
        return 'Idle';
      case '/fight-capture':
        return 'Fight Capture';
      case '/post-fight':
        return 'Post-Fight Session';
      case '/analytics':
        return 'Analytics';
      case '/upload':
        return 'PDF & Data';
      case '/calendar':
        return 'Calendar';
      case '/history':
        return 'History';
      default:
        return 'Idle';
    }
  };
  const isFullWidthPage = location.pathname === '/post-fight' || location.pathname === '/analytics' || location.pathname === '/upload' || location.pathname === '/calendar';
  
  return <div className="min-h-screen w-full flex flex-col items-center p-4 md:p-6">
      {/* Home icon button - top left */}
      {location.pathname !== '/' && (
        <button
          onClick={() => navigate('/')}
          className="fixed top-4 left-4 bg-white/30 backdrop-blur-sm hover:bg-white/50 p-2 rounded-full text-gray-700 transition-all shadow-soft hover:shadow-cozy z-50"
          aria-label="Go to home"
        >
          <HomeIcon size={20} className="text-rose-500" />
        </button>
      )}
      
      {/* Status indicator - top right */}
      <div className="fixed top-4 right-4 bg-white/30 backdrop-blur-sm py-1 px-3 rounded-full text-sm font-medium text-gray-700">
        {getStateName()}
      </div>
      
      {/* Connected status - bottom left */}
      <div className="fixed bottom-4 left-4 bg-white/30 backdrop-blur-sm py-1 px-3 rounded-full text-xs text-gray-600">
        Connected as Adrian
      </div>
      
      <div className={`w-full ${isFullWidthPage ? 'max-w-full' : 'max-w-md md:max-w-lg'}`}>{children}</div>
    </div>;
};

export default Layout;