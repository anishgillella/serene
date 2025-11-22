import React from 'react';
import { useLocation } from 'react-router-dom';
interface LayoutProps {
  children: React.ReactNode;
}
const Layout: React.FC<LayoutProps> = ({
  children
}) => {
  const location = useLocation();
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
      default:
        return 'Idle';
    }
  };
  return <div className="min-h-screen w-full flex flex-col items-center p-4 md:p-6">
      <div className="fixed top-4 right-4 bg-white/30 backdrop-blur-sm py-1 px-3 rounded-full text-sm font-medium text-gray-700">
        {getStateName()}
      </div>
      <div className="fixed bottom-4 left-4 bg-white/30 backdrop-blur-sm py-1 px-3 rounded-full text-xs text-gray-600">
        Connected as Partner A
      </div>
      <div className="w-full max-w-md md:max-w-lg">{children}</div>
    </div>;
};
export default Layout;