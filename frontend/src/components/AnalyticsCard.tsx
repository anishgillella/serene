import React from 'react';

interface AnalyticsCardProps {
  title: string;
  value?: string | number;
  subValue?: string;
  color?: string;
  children?: React.ReactNode;
  className?: string;
}

const AnalyticsCard: React.FC<AnalyticsCardProps> = ({
  title,
  value,
  subValue,
  color = 'bg-white/60',
  children,
  className = ''
}) => {
  return (
    <div className={`rounded-3xl p-6 ${color} backdrop-blur-xl shadow-lg border border-white/40 transition-all hover:shadow-xl ${className}`}>
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">{title}</h3>
        {value !== undefined && (
          <div className="text-right">
            <div className="text-2xl font-bold text-slate-800">{value}</div>
            {subValue && <div className="text-xs font-medium text-slate-400">{subValue}</div>}
          </div>
        )}
      </div>
      <div className="relative">
        {children}
      </div>
    </div>
  );
};

export default AnalyticsCard;