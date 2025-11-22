import React from 'react';
import { FileTextIcon, CheckCircleIcon, LoaderIcon } from 'lucide-react';
interface FileUploadCardProps {
  filename: string;
  type: string;
  status: 'pending' | 'processing' | 'ready';
  onClick?: () => void;
}
const FileUploadCard: React.FC<FileUploadCardProps> = ({
  filename,
  type,
  status,
  onClick
}) => {
  const statusIcons = {
    pending: <LoaderIcon size={16} className="text-gray-400" />,
    processing: <LoaderIcon size={16} className="text-blue-400 animate-spin" />,
    ready: <CheckCircleIcon size={16} className="text-green-500" />
  };
  const statusText = {
    pending: 'Pending',
    processing: 'Processing',
    ready: 'Ready'
  };
  return <div className="flex items-center bg-white/70 rounded-xl p-3 mb-2 cursor-pointer hover:bg-white/90 transition-colors" onClick={onClick}>
      <div className="bg-lavender p-2 rounded-lg mr-3">
        <FileTextIcon size={20} className="text-gray-700" />
      </div>
      <div className="flex-1">
        <h4 className="text-sm font-medium text-gray-800 truncate">
          {filename}
        </h4>
        <p className="text-xs text-gray-500">{type}</p>
      </div>
      <div className="flex items-center">
        <span className="text-xs mr-1">{statusText[status]}</span>
        {statusIcons[status]}
      </div>
    </div>;
};
export default FileUploadCard;