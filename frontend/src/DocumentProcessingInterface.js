import React, { useState, useCallback, useRef } from 'react';
import DocumentProcessing from './DocumentProcessing';

const {
  ProcessingStatus, 
  useOCRExtraction, 
  useDocumentValidation, 
  useFileProcessing,
  DigitalSignature,
  DocumentViewer
} = DocumentProcessing;

// Import DocIcons separately
const DocIcons = {
  Upload: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  ),
  Scan: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.707A1 1 0 013 7V4z" />
    </svg>
  ),
  Document: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Validate: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  Signature: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  ),
  Eye: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
  Download: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  X: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  Check: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
};

// Simple Document Processing Interface for MIND14
export const DocumentProcessingInterface = ({ language = 'en', onDocumentProcessed }) => {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [processingStatus, setProcessingStatus] = useState('idle');
  const fileInputRef = useRef(null);
  
  const isRTL = language === 'ar';
  
  const text = {
    en: {
      title: 'Document Processing Center',
      subtitle: 'Upload, analyze, and validate your documents with AI',
      uploadTitle: 'Upload Documents',
      uploadDesc: 'Drag and drop files or click to browse',
      supportedFormats: 'Supported: PDF, Images (JPG, PNG), Word documents',
      processDocument: 'Process Document',
      extractText: 'Extract Text (OCR)',
      validateID: 'Validate ID Document',
      addSignature: 'Add Digital Signature',
      downloadProcessed: 'Download Processed',
      documentType: 'Document Type',
      selectType: 'Select document type...',
      nationalID: 'National ID',
      passport: 'Passport',
      drivingLicense: 'Driving License',
      other: 'Other Document',
      noFileSelected: 'Select a document to view and process'
    },
    ar: {
      title: 'مركز معالجة المستندات',
      subtitle: 'ارفع وحلل وتحقق من مستنداتك بالذكاء الاصطناعي',
      uploadTitle: 'رفع المستندات',
      uploadDesc: 'اسحب وأفلت الملفات أو انقر للتصفح',
      supportedFormats: 'المدعوم: PDF، الصور (JPG، PNG)، مستندات Word',
      processDocument: 'معالجة المستند',
      extractText: 'استخراج النص (OCR)',
      validateID: 'التحقق من الهوية',
      addSignature: 'إضافة التوقيع الرقمي',
      downloadProcessed: 'تحميل المعالج',
      documentType: 'نوع المستند',
      selectType: 'اختر نوع المستند...',
      nationalID: 'الهوية الوطنية',
      passport: 'جواز السفر',
      drivingLicense: 'رخصة القيادة',
      other: 'مستند آخر',
      noFileSelected: 'اختر مستندًا للعرض والمعالجة'
    }
  };

  const currentText = text[language];

  // Document Icons
  const DocIcons = {
    Upload: () => (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    ),
    Document: () => (
      <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    Eye: () => (
      <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
    ),
    X: () => (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    )
  };

  const documentTypes = [
    { id: 'nationalID', label: currentText.nationalID },
    { id: 'passport', label: currentText.passport },
    { id: 'drivingLicense', label: currentText.drivingLicense },
    { id: 'other', label: currentText.other }
  ];

  const handleFileUpload = useCallback((uploadedFiles) => {
    const newFiles = Array.from(uploadedFiles).map(file => ({
      id: Date.now() + Math.random(),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploaded'
    }));
    
    setFiles(prev => [...prev, ...newFiles]);
    
    if (newFiles.length > 0) {
      setSelectedFile(newFiles[0]);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFiles = e.dataTransfer.files;
    handleFileUpload(droppedFiles);
  }, [handleFileUpload]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const processDocument = async () => {
    setProcessingStatus('processing');
    // Simulate processing
    setTimeout(() => {
      setProcessingStatus('complete');
      if (onDocumentProcessed) {
        onDocumentProcessed({
          file: selectedFile?.file,
          extractedText: 'Sample extracted text from document...',
          status: 'processed'
        });
      }
    }, 3000);
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6" dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="w-20 h-20 mx-auto bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-3xl backdrop-blur-sm border border-purple-500/20 flex items-center justify-center">
          <DocIcons.Document />
        </div>
        <h1 className="text-3xl font-bold text-white">{currentText.title}</h1>
        <p className="text-gray-400 max-w-2xl mx-auto">{currentText.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Upload & Controls */}
        <div className="space-y-6">
          {/* File Upload */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">{currentText.uploadTitle}</h3>
            
            <div
              className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center transition-colors hover:border-purple-500 hover:bg-purple-500/5 cursor-pointer"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
            >
              <DocIcons.Upload />
              <p className="text-gray-300 mb-2 mt-4">{currentText.uploadDesc}</p>
              <p className="text-sm text-gray-500">{currentText.supportedFormats}</p>
              
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,.gif,.docx,.doc"
                onChange={(e) => handleFileUpload(e.target.files)}
                className="hidden"
              />
            </div>

            {/* Uploaded Files */}
            {files.length > 0 && (
              <div className="mt-4 space-y-2">
                {files.map((fileItem) => (
                  <div
                    key={fileItem.id}
                    className={`flex items-center space-x-3 p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedFile?.id === fileItem.id
                        ? 'bg-purple-600/20 border border-purple-500'
                        : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                    onClick={() => setSelectedFile(fileItem)}
                  >
                    <DocIcons.Document />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{fileItem.name}</p>
                      <p className="text-xs text-gray-400">
                        {(fileItem.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setFiles(prev => prev.filter(f => f.id !== fileItem.id));
                        if (selectedFile?.id === fileItem.id) {
                          setSelectedFile(null);
                        }
                      }}
                      className="text-gray-400 hover:text-red-400"
                    >
                      <DocIcons.X />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Document Type Selection */}
          {selectedFile && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">{currentText.documentType}</h3>
              <select
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-purple-500"
                defaultValue=""
              >
                <option value="" disabled>{currentText.selectType}</option>
                {documentTypes.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Processing Controls */}
          {selectedFile && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">{currentText.processDocument}</h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  onClick={processDocument}
                  disabled={processingStatus === 'processing'}
                  className="flex items-center justify-center space-x-2 p-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg transition-colors"
                >
                  <span className="text-sm">{currentText.extractText}</span>
                </button>
                
                <button
                  className="flex items-center justify-center space-x-2 p-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-lg transition-colors"
                >
                  <span className="text-sm">{currentText.validateID}</span>
                </button>
                
                <button
                  className="flex items-center justify-center space-x-2 p-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-lg transition-colors"
                >
                  <span className="text-sm">{currentText.addSignature}</span>
                </button>
                
                <button
                  className="flex items-center justify-center space-x-2 p-3 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white rounded-lg transition-colors"
                >
                  <span className="text-sm">{currentText.downloadProcessed}</span>
                </button>
              </div>

              {/* Processing Status */}
              {processingStatus === 'processing' && (
                <div className="mt-4 flex items-center space-x-3">
                  <div className="w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm text-purple-400">Processing document...</span>
                </div>
              )}
              
              {processingStatus === 'complete' && (
                <div className="mt-4 flex items-center space-x-3">
                  <div className="w-5 h-5 text-green-400">✓</div>
                  <span className="text-sm text-green-400">Processing complete!</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Panel - Document Viewer */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          {selectedFile ? (
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Document Preview</h3>
              {selectedFile.file.type.startsWith('image/') && (
                <img 
                  src={URL.createObjectURL(selectedFile.file)} 
                  alt="Document" 
                  className="max-w-full h-auto rounded border border-gray-600"
                />
              )}
              {selectedFile.file.type === 'application/pdf' && (
                <div className="text-center text-gray-400 py-12">
                  <DocIcons.Document />
                  <p className="mt-4">PDF Document: {selectedFile.file.name}</p>
                  <p className="text-sm">Size: {(selectedFile.file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center">
              <DocIcons.Eye />
              <p className="text-gray-400 mt-4">{currentText.noFileSelected}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Component is already exported at line 62