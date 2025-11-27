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
  color = 'bg-surface-elevated',
  children,
  className = ''
}) => {
  return (
    <div className={`flex flex-col rounded-2xl p-6 ${color} border border-border-subtle shadow-soft transition-all hover:shadow-subtle ${className}`}>
      <div className="flex justify-between items-start mb-4 shrink-0">
        <h3 className="text-tiny font-medium text-text-tertiary uppercase tracking-wider">{title}</h3>
        {value !== undefined && (
          <div className="text-right">
            <div className="text-h2 text-text-primary">{value}</div>
            {subValue && <div className="text-tiny text-text-secondary mt-0.5">{subValue}</div>}
          </div>
        )}
      </div>
      <div className="relative flex-1 min-h-0">
        {children}
      </div>
    </div>
  );
};

export default AnalyticsCard;