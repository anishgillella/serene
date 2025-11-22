import React from 'react';
interface AnalyticsCardProps {
  title: string;
  value: string | number;
  color?: string;
  children?: React.ReactNode;
}
const AnalyticsCard: React.FC<AnalyticsCardProps> = ({
  title,
  value,
  color = 'bg-white/70',
  children
}) => {
  return <div className={`rounded-2xl p-4 ${color} backdrop-blur-sm shadow-soft mb-4`}>
      <h3 className="text-sm font-semibold text-gray-700 mb-1">{title}</h3>
      {typeof value === 'string' || typeof value === 'number' ? <p className="text-2xl font-bold text-gray-800">{value}</p> : null}
      {children}
    </div>;
};
export default AnalyticsCard;