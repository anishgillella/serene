import React from 'react';
import { UserIcon } from 'lucide-react';
interface ParticipantBadgeProps {
  name: string;
  isActive?: boolean;
  isSilent?: boolean;
}
const ParticipantBadge: React.FC<ParticipantBadgeProps> = ({
  name,
  isActive = false,
  isSilent = false
}) => {
  return <div className={`flex items-center rounded-full py-2 px-4 mb-2 
      ${isActive ? 'bg-white/80 shadow-sm wave-animation' : 'bg-white/50'}`}>
      <div className="mr-2 bg-lavender rounded-full p-1">
        <UserIcon size={14} />
      </div>
      <span className="text-sm font-medium">{name}</span>
      {isSilent && <span className="ml-2 text-xs text-gray-500">(silent)</span>}
      {isActive && !isSilent && <div className="ml-2 w-2 h-2 rounded-full bg-green-400"></div>}
    </div>;
};
export default ParticipantBadge;