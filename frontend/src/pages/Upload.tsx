import React, { useState } from 'react';
import { UploadCloudIcon } from 'lucide-react';
import FileUploadCard from '../components/FileUploadCard';
const Upload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([{
    id: 1,
    filename: 'Relationship Handbook.pdf',
    type: 'handbook',
    status: 'ready' as const
  }, {
    id: 2,
    filename: 'Therapy Notes - July.pdf',
    type: 'notes',
    status: 'ready' as const
  }, {
    id: 3,
    filename: 'Communication Guide.pdf',
    type: 'guidance',
    status: 'processing' as const
  }]);
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => {
    setIsDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    // Simulate file upload
    if (e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const newFile = {
        id: Date.now(),
        filename: file.name,
        type: 'notes',
        status: 'pending' as const
      };
      setFiles(prev => [newFile, ...prev]);
      // Simulate processing
      setTimeout(() => {
        setFiles(prev => prev.map(f => f.id === newFile.id ? {
          ...f,
          status: 'processing' as const
        } : f));
        setTimeout(() => {
          setFiles(prev => prev.map(f => f.id === newFile.id ? {
            ...f,
            status: 'ready' as const
          } : f));
        }, 3000);
      }, 1500);
    }
  };
  return <div className="py-4">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-gray-800">
          PDF & Data Upload
        </h2>
        <p className="text-sm text-gray-600">Upload relationship resources</p>
      </div>
      <div className={`border-2 border-dashed rounded-xl p-8 mb-6 flex flex-col items-center justify-center transition-colors
          ${isDragging ? 'border-rose-400 bg-rose-50/50' : 'border-gray-300 bg-white/50'}`} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
        <UploadCloudIcon size={32} className={`mb-2 ${isDragging ? 'text-rose-400' : 'text-gray-400'}`} />
        <p className="text-sm font-medium text-gray-700">
          {isDragging ? 'Drop to upload' : 'Upload PDF (relationship handbook, notes, psychoeducation)'}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Drag & drop or click to browse
        </p>
        <input type="file" className="hidden" accept=".pdf" id="file-upload" />
        <label htmlFor="file-upload" className="mt-4 py-2 px-4 bg-white rounded-lg text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-50 transition-colors">
          Browse files
        </label>
      </div>
      <h3 className="font-medium text-gray-700 mb-3">Uploaded Files</h3>
      <div className="space-y-2">
        {files.map(file => <FileUploadCard key={file.id} filename={file.filename} type={file.type} status={file.status} />)}
      </div>
    </div>;
};
export default Upload;