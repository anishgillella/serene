import React from 'react';

interface AlertBadgeProps {
  count: number;
}

const AlertBadge: React.FC<AlertBadgeProps> = ({ count }) => {
  if (count <= 0) return null;

  return (
    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-amber-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
      {count > 99 ? '99+' : count}
    </span>
  );
};

export default AlertBadge;
