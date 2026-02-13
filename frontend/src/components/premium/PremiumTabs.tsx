import React from 'react';
import { motion } from 'framer-motion';

interface Tab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface PremiumTabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
}

export const PremiumTabs: React.FC<PremiumTabsProps> = ({
  tabs,
  activeTab,
  onTabChange,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="relative bg-white/60 backdrop-blur-lg rounded-2xl p-1.5 border border-white/50 shadow-subtle inline-flex"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              relative px-5 py-2.5 rounded-xl font-medium text-sm
              transition-colors duration-200
              flex items-center gap-2
              ${isActive ? 'text-warmGray-800' : 'text-warmGray-500 hover:text-warmGray-700'}
            `}
          >
            {/* Active background pill */}
            {isActive && (
              <motion.div
                layoutId="activeTab"
                className="absolute inset-0 bg-white rounded-xl shadow-cozy"
                transition={{
                  type: "spring",
                  stiffness: 400,
                  damping: 30,
                }}
              />
            )}

            {/* Icon */}
            <span className="relative z-10">
              {tab.icon}
            </span>

            {/* Label */}
            <span className="relative z-10 hidden sm:inline">
              {tab.label}
            </span>
          </button>
        );
      })}
    </motion.div>
  );
};

// Full-width variant
export const PremiumTabsFullWidth: React.FC<PremiumTabsProps> = ({
  tabs,
  activeTab,
  onTabChange,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="relative bg-white/60 backdrop-blur-lg rounded-2xl p-1.5 border border-white/50 shadow-subtle flex w-full overflow-x-auto whitespace-nowrap"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              relative flex-1 px-4 py-3 rounded-xl font-medium text-sm
              transition-colors duration-200
              flex items-center justify-center gap-2
              ${isActive ? 'text-warmGray-800' : 'text-warmGray-500 hover:text-warmGray-700'}
            `}
          >
            {/* Active background pill */}
            {isActive && (
              <motion.div
                layoutId="activeTabFull"
                className="absolute inset-0 bg-white rounded-xl shadow-cozy"
                transition={{
                  type: "spring",
                  stiffness: 400,
                  damping: 30,
                }}
              />
            )}

            {/* Icon with subtle animation */}
            <motion.span
              className="relative z-10"
              animate={isActive ? { scale: 1.1 } : { scale: 1 }}
              transition={{ duration: 0.2 }}
            >
              {tab.icon}
            </motion.span>

            {/* Label */}
            <span className="relative z-10">
              {tab.label}
            </span>
          </button>
        );
      })}
    </motion.div>
  );
};

export default PremiumTabs;
