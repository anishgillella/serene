import React, { useState, useRef } from 'react';
import { UploadIcon, FileTextIcon, CheckCircleIcon, LoaderIcon, XIcon, AlertCircleIcon, SparklesIcon } from 'lucide-react';

interface UploadedFile {
  id: string;
  filename: string;
  pdfType: string;
  status: 'uploading' | 'processing' | 'success' | 'error';
  progress?: number;
  message?: string;
  extractedTextLength?: number;
}

const Upload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedPdfType, setSelectedPdfType] = useState<string>('boyfriend_profile');
  const [relationshipId, setRelationshipId] = useState<string>('00000000-0000-0000-0000-000000000000');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    );

    if (droppedFiles.length > 0) {
      handleFiles(droppedFiles);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter(
        file => file.type === 'application/pdf'
      );
      handleFiles(selectedFiles);
    }
  };

  const handleFiles = async (fileList: File[]) => {
    for (const file of fileList) {
      const fileId = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const newFile: UploadedFile = {
        id: fileId,
        filename: file.name,
        pdfType: selectedPdfType,
        status: 'uploading',
        progress: 0
      };

      setFiles(prev => [...prev, newFile]);

      // Upload file
      await uploadFile(file, newFile);
    }
  };

  const uploadFile = async (file: File, fileInfo: UploadedFile) => {
    try {
      // Update status to processing
      setFiles(prev => prev.map(f => 
        f.id === fileInfo.id ? { ...f, status: 'processing', progress: 50 } : f
      ));

      const formData = new FormData();
      formData.append('file', file);
      formData.append('relationship_id', relationshipId);
      formData.append('pdf_type', fileInfo.pdfType);

      const response = await fetch(`${apiUrl}/api/pdfs/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Update status to success
      setFiles(prev => prev.map(f => 
        f.id === fileInfo.id ? { 
          ...f, 
          status: 'success', 
          progress: 100,
          message: `Extracted ${data.extracted_text_length} characters`,
          extractedTextLength: data.extracted_text_length
        } : f
      ));

    } catch (error: any) {
      console.error('Error uploading file:', error);
      setFiles(prev => prev.map(f => 
        f.id === fileInfo.id ? { 
          ...f, 
          status: 'error',
          message: error.message || 'Upload failed'
        } : f
      ));
    }
  };

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const pdfTypeOptions = [
    { value: 'boyfriend_profile', label: 'Boyfriend Profile', description: 'Character description for boyfriend' },
    { value: 'girlfriend_profile', label: 'Girlfriend Profile', description: 'Character description for girlfriend' },
    { value: 'handbook', label: 'Relationship Handbook', description: 'Shared relationship guide or handbook' },
    { value: 'notes', label: 'Notes', description: 'Custom notes or documents' }
  ];

  return (
    <div className="flex flex-col min-h-[80vh] py-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-2">
          Upload PDFs for RAG Pipeline
        </h2>
        <p className="text-sm text-gray-600">
          Upload PDFs to extract text via OCR and store in vector database
        </p>
      </div>

      {/* Configuration */}
      <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 mb-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              PDF Type
            </label>
            <select
              value={selectedPdfType}
              onChange={(e) => setSelectedPdfType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {pdfTypeOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {pdfTypeOptions.find(opt => opt.value === selectedPdfType)?.description}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Relationship ID
            </label>
            <input
              type="text"
              value={relationshipId}
              onChange={(e) => setRelationshipId(e.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Default relationship ID (can be changed)
            </p>
          </div>
        </div>
      </div>

      {/* Upload Area */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 mb-6 transition-all ${
          isDragging
            ? 'border-purple-500 bg-purple-50'
            : 'border-gray-300 bg-white/50 hover:border-purple-300 hover:bg-purple-50/50'
        }`}
      >
        <div className="flex flex-col items-center justify-center text-center">
          <UploadIcon size={48} className={`mb-4 ${isDragging ? 'text-purple-500' : 'text-gray-400'}`} />
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            {isDragging ? 'Drop PDF here' : 'Drag & Drop PDF files here'}
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            or click to browse
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-6 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg font-medium transition-colors"
          >
            Select PDF Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      </div>

      {/* Uploaded Files List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            Uploaded Files ({files.length})
          </h3>
          {files.map((file) => (
            <div
              key={file.id}
              className="bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-sm border border-gray-200"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start flex-1">
                  <div className={`p-2 rounded-lg mr-3 ${
                    file.status === 'success' ? 'bg-green-100' :
                    file.status === 'error' ? 'bg-red-100' :
                    file.status === 'processing' ? 'bg-blue-100' :
                    'bg-gray-100'
                  }`}>
                    {file.status === 'success' ? (
                      <CheckCircleIcon size={20} className="text-green-600" />
                    ) : file.status === 'error' ? (
                      <AlertCircleIcon size={20} className="text-red-600" />
                    ) : file.status === 'processing' ? (
                      <LoaderIcon size={20} className="text-blue-600 animate-spin" />
                    ) : (
                      <FileTextIcon size={20} className="text-gray-600" />
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center mb-1">
                      <h4 className="text-sm font-medium text-gray-800 truncate">
                        {file.filename}
                      </h4>
                      <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                        {pdfTypeOptions.find(opt => opt.value === file.pdfType)?.label}
                      </span>
                    </div>
                    
                    {file.status === 'processing' && (
                      <div className="mt-2">
                        <div className="flex items-center text-xs text-gray-600 mb-1">
                          <SparklesIcon size={12} className="mr-1" />
                          <span>Running OCR and storing in vector database...</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${file.progress || 0}%` }}
                          />
                        </div>
                      </div>
                    )}
                    
                    {file.status === 'success' && (
                      <div className="mt-2 text-xs text-gray-600">
                        <CheckCircleIcon size={12} className="inline mr-1 text-green-600" />
                        <span className="text-green-700 font-medium">Success!</span>
                        {file.extractedTextLength && (
                          <span className="ml-2">
                            Extracted {file.extractedTextLength.toLocaleString()} characters
                          </span>
                        )}
                      </div>
                    )}
                    
                    {file.status === 'error' && (
                      <div className="mt-2 text-xs text-red-600">
                        <AlertCircleIcon size={12} className="inline mr-1" />
                        <span>{file.message || 'Upload failed'}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                <button
                  onClick={() => removeFile(file.id)}
                  className="ml-4 p-1 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <XIcon size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
        <div className="flex items-start">
          <SparklesIcon size={20} className="text-blue-600 mr-3 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-blue-900 mb-1">
              How it works
            </h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• PDFs are automatically processed with Mistral OCR</li>
              <li>• Extracted text is embedded using Voyage AI</li>
              <li>• Stored in Pinecone vector database for RAG retrieval</li>
              <li>• Used for personalized conflict analysis and repair plans</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
