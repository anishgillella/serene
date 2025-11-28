import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadIcon, FileTextIcon, CheckCircleIcon, LoaderIcon, XIcon, AlertCircleIcon, SparklesIcon, ArrowLeftIcon } from 'lucide-react';

interface UploadedFile {
  id: string;
  filename: string;
  pdfType: string;
  status: 'uploading' | 'processing' | 'success' | 'error';
  progress?: number;
  message?: string;
  extractedTextLength?: number;
  abortController?: AbortController;
  logs?: string[];
  pdfId?: string;
}

interface ExistingFile {
  id: string;
  filename: string;
  pdf_type: string;
  uploaded_at: string;
  extracted_text_length: number;
}

const Upload = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [existingFiles, setExistingFiles] = useState<ExistingFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedPdfType, setSelectedPdfType] = useState<string>('boyfriend_profile');
  const [relationshipId, setRelationshipId] = useState<string>('00000000-0000-0000-0000-000000000000');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  useEffect(() => {
    fetchExistingFiles();
  }, [relationshipId]);

  const fetchExistingFiles = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/pdfs/list/${relationshipId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setExistingFiles(data.files);
        }
      }
    } catch (error) {
      console.error('Error fetching existing files:', error);
    }
  };

  const pollLogs = async (fileId: string, pdfId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiUrl}/api/pdfs/logs/${pdfId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.logs && data.logs.length > 0) {
            setFiles(prev => prev.map(f => {
              if (f.id === fileId) {
                // Determine progress based on logs
                let progress = f.progress || 10;
                const lastLog = data.logs[data.logs.length - 1];

                if (lastLog.includes("Extracted")) progress = 30;
                if (lastLog.includes("embeddings")) progress = 50;
                if (lastLog.includes("S3")) progress = 70;
                if (lastLog.includes("Pinecone")) progress = 90;

                // Check for completion or error
                if (lastLog.includes("Processing complete!") || lastLog.includes("Updated database record")) {
                  clearInterval(interval);
                  fetchExistingFiles(); // Refresh list
                  return { ...f, logs: data.logs, status: 'success', progress: 100, message: 'Processing complete!' };
                }
                if (lastLog.includes("Error") || lastLog.includes("Failed")) {
                  clearInterval(interval);
                  return { ...f, logs: data.logs, status: 'error', message: 'Processing failed' };
                }

                return { ...f, logs: data.logs, progress };
              }
              return f;
            }));
          }
        }
      } catch (e) {
        console.error("Error polling logs:", e);
      }
    }, 1000);

    // Store interval ID to clear it later if needed (e.g. on unmount)
    // For now, we rely on the closure or component unmount clearing it (but setInterval persists)
    // Ideally we should track intervals in a ref, but for this simple case:
    return () => clearInterval(interval);
  };

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
      const fileId = `${Date.now()}_${Math.random().toString(36).substr(2, 9)} `;
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
    const abortController = new AbortController();

    try {
      // Update status to processing with abort controller
      setFiles(prev => prev.map(f =>
        f.id === fileInfo.id ? { ...f, status: 'processing', progress: 5, abortController } : f
      ));

      const formData = new FormData();
      formData.append('file', file);
      formData.append('relationship_id', relationshipId);
      formData.append('pdf_type', fileInfo.pdfType);

      const response = await fetch(`${apiUrl}/api/pdfs/upload`, {
        method: 'POST',
        body: formData,
        signal: abortController.signal
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success) {
        // Start polling for logs
        pollLogs(fileInfo.id, data.pdf_id);

        // Update status to processing with pdfId
        setFiles(prev => prev.map(f =>
          f.id === fileInfo.id ? {
            ...f,
            status: 'processing',
            progress: 10,
            pdfId: data.pdf_id,
            message: 'Processing in background...'
          } : f
        ));
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        setFiles(prev => prev.map(f =>
          f.id === fileInfo.id ? {
            ...f,
            status: 'error',
            message: 'Upload cancelled'
          } : f
        ));
      } else {
        console.error('Error uploading file:', error);
        setFiles(prev => prev.map(f =>
          f.id === fileInfo.id ? {
            ...f,
            status: 'error',
            message: error.message || 'Upload failed'
          } : f
        ));
      }
    }
  };

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const cancelUpload = (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (file && file.abortController) {
      file.abortController.abort();
    }
  };

  const pdfTypeOptions = [
    { value: 'boyfriend_profile', label: 'Boyfriend Profile', description: 'Character description for boyfriend' },
    { value: 'girlfriend_profile', label: 'Girlfriend Profile', description: 'Character description for girlfriend' },
    { value: 'reference_book', label: 'Relationship Book', description: 'Romance/relationship book (e.g. "Attached", "The Seven Principles")' }
  ];

  return (
    <div className="flex flex-col min-h-[80vh] py-6">
      {/* Back Button */}
      <div className="mb-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
        >
          <ArrowLeftIcon size={20} className="mr-2" />
          <span className="text-sm font-medium">Back to Home</span>
        </button>
      </div>

      <div className="text-center mb-8">
        <h2 className="text-h2 text-text-primary mb-2">
          Upload PDFs for RAG Pipeline
        </h2>
        <p className="text-body text-text-secondary">
          Upload PDFs to extract text via OCR and store in vector database
        </p>
      </div>

      {/* Configuration */}
      <div className="bg-surface-elevated rounded-xl p-6 mb-8 border border-border-subtle shadow-soft">
        <div className="space-y-5">
          <div>
            <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
              PDF Type
            </label>
            <select
              value={selectedPdfType}
              onChange={(e) => setSelectedPdfType(e.target.value)}
              className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none appearance-none"
            >
              {pdfTypeOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="text-tiny text-text-tertiary mt-1.5">
              {pdfTypeOptions.find(opt => opt.value === selectedPdfType)?.description}
            </p>
          </div>

          <div>
            <label className="block text-tiny font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
              Relationship ID
            </label>
            <input
              type="text"
              value={relationshipId}
              onChange={(e) => setRelationshipId(e.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              className="w-full px-4 py-2.5 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl transition-all outline-none font-mono text-small"
            />
            <p className="text-tiny text-text-tertiary mt-1.5">
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
        className={`border border-dashed rounded-xl p-12 mb-8 transition-all flex flex-col items-center justify-center text-center ${isDragging
          ? 'border-accent bg-surface-hover'
          : 'border-border-medium bg-transparent hover:border-accent hover:bg-surface-hover'
          }`}
      >
        <UploadIcon size={40} className={`mb-4 ${isDragging ? 'text-accent' : 'text-text-tertiary'}`} strokeWidth={1.5} />
        <h3 className="text-h3 text-text-primary mb-2">
          {isDragging ? 'Drop PDF here' : 'Drag & Drop PDF files here'}
        </h3>
        <p className="text-body text-text-secondary mb-6">
          or click to browse
        </p>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-6 py-2.5 bg-white border border-border-subtle text-text-primary hover:border-accent hover:text-accent rounded-xl font-medium transition-all shadow-soft hover:shadow-subtle"
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

      {/* Uploaded Files List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-h3 text-text-primary mb-4">
            Uploaded Files ({files.length})
          </h3>
          {files.map((file) => (
            <div
              key={file.id}
              className="bg-surface-elevated rounded-xl p-4 shadow-soft border border-border-subtle"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start flex-1">
                  <div className={`p-2.5 rounded-lg mr-4 ${file.status === 'success' ? 'bg-green-50 text-green-600' :
                    file.status === 'error' ? 'bg-red-50 text-red-600' :
                      file.status === 'processing' ? 'bg-blue-50 text-blue-600' :
                        'bg-surface-hover text-text-tertiary'
                    }`}>
                    {file.status === 'success' ? (
                      <CheckCircleIcon size={20} strokeWidth={1.5} />
                    ) : file.status === 'error' ? (
                      <AlertCircleIcon size={20} strokeWidth={1.5} />
                    ) : file.status === 'processing' ? (
                      <LoaderIcon size={20} className="animate-spin" strokeWidth={1.5} />
                    ) : (
                      <FileTextIcon size={20} strokeWidth={1.5} />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center mb-1">
                      <h4 className="text-body font-medium text-text-primary truncate">
                        {file.filename}
                      </h4>
                      <span className="ml-3 text-tiny font-medium bg-surface-hover text-text-secondary px-2 py-0.5 rounded border border-border-subtle">
                        {pdfTypeOptions.find(opt => opt.value === file.pdfType)?.label}
                      </span>
                    </div>

                    {file.status === 'processing' && (
                      <div className="mt-2">
                        <div className="flex items-center text-tiny text-text-secondary mb-1.5">
                          <SparklesIcon size={12} className="mr-1.5 text-accent" />
                          <span>{file.message || 'Running OCR and storing in vector database...'}</span>
                        </div>
                        <div className="w-full bg-surface-hover rounded-full h-1">
                          <div
                            className="bg-accent h-1 rounded-full transition-all duration-300"
                            style={{ width: `${file.progress || 0}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {file.status === 'success' && (
                      <div className="mt-1 text-tiny text-text-secondary">
                        <CheckCircleIcon size={12} className="inline mr-1.5 text-green-600" />
                        <span className="text-green-600 font-medium">Success!</span>
                        {file.extractedTextLength && (
                          <span className="ml-2 text-text-tertiary">
                            Extracted {file.extractedTextLength.toLocaleString()} characters
                          </span>
                        )}
                      </div>
                    )}

                    {file.status === 'error' && (
                      <div className="mt-1 text-tiny text-red-600">
                        <AlertCircleIcon size={12} className="inline mr-1.5" />
                        <span>{file.message || 'Upload failed'}</span>
                      </div>
                    )}

                    {/* Logs Display */}
                    {file.logs && file.logs.length > 0 && (
                      <div className="mt-3 bg-gray-900 rounded-lg p-3 font-mono text-xs text-green-400 max-h-32 overflow-y-auto shadow-inner border border-gray-800">
                        {file.logs.map((log, i) => {
                          // Remove timestamp (HH:MM:SS - )
                          const cleanLog = log.replace(/^\d{2}:\d{2}:\d{2} - /, '');
                          return (
                            <div key={i} className="whitespace-pre-wrap break-words border-b border-gray-800/50 last:border-0 py-0.5">
                              {cleanLog}
                            </div>
                          );
                        })}
                        <div ref={el => el?.scrollIntoView({ behavior: 'smooth' })} />
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center">
                  {file.status === 'processing' && (
                    <button
                      onClick={() => cancelUpload(file.id)}
                      className="ml-4 px-3 py-1 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors border border-red-100"
                    >
                      Cancel
                    </button>
                  )}

                  <button
                    onClick={() => removeFile(file.id)}
                    className="ml-4 p-2 text-text-tertiary hover:text-text-primary hover:bg-surface-hover rounded-full transition-colors"
                  >
                    <XIcon size={18} strokeWidth={1.5} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Previously Uploaded Files */}
      {existingFiles.length > 0 && (
        <div className="space-y-3 mb-8">
          <h3 className="text-h3 text-text-primary mb-4 flex items-center">
            <CheckCircleIcon size={20} className="mr-2 text-green-600" />
            Previously Uploaded ({existingFiles.length})
          </h3>
          {existingFiles.map((file) => (
            <div
              key={file.id}
              className="bg-surface-elevated rounded-xl p-4 shadow-soft border border-border-subtle opacity-80 hover:opacity-100 transition-opacity"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start flex-1">
                  <div className="p-2.5 rounded-lg mr-4 bg-green-50 text-green-600">
                    <FileTextIcon size={20} strokeWidth={1.5} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center mb-1">
                      <h4 className="text-body font-medium text-text-primary truncate">
                        {file.filename}
                      </h4>
                      <span className="ml-3 text-tiny font-medium bg-surface-hover text-text-secondary px-2 py-0.5 rounded border border-border-subtle">
                        {pdfTypeOptions.find(opt => opt.value === file.pdf_type)?.label || file.pdf_type}
                      </span>
                    </div>

                    <div className="mt-1 text-tiny text-text-secondary">
                      <span className="text-text-tertiary">
                        Uploaded {new Date(file.uploaded_at).toLocaleDateString()} • {file.extracted_text_length.toLocaleString()} chars
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="mt-8 bg-surface-hover border border-border-subtle rounded-xl p-5">
        <div className="flex items-start">
          <SparklesIcon size={20} className="text-accent mr-3 mt-0.5" strokeWidth={1.5} />
          <div className="flex-1">
            <h4 className="text-small font-semibold text-text-primary mb-2">
              How it works
            </h4>
            <ul className="text-tiny text-text-secondary space-y-1.5 list-disc list-inside">
              <li>PDFs are automatically processed with Mistral OCR</li>
              <li>Extracted text is embedded using Voyage AI</li>
              <li>Stored in Pinecone vector database for RAG retrieval</li>
              <li>Used for personalized conflict analysis and repair plans</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
