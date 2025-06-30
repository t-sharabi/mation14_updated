import React, { useState, useRef, useEffect, useCallback } from 'react';
import Tesseract from 'tesseract.js';
import { PDFDocument } from 'pdf-lib';
import * as pdfjs from 'pdfjs-dist';
import mammoth from 'mammoth';
import JSZip from 'jszip';
import CryptoJS from 'crypto-js';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/5.3.31/pdf.worker.min.js`;

// Document Processing Icons
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
  Clipboard: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  ),
  Shield: ({ className = "w-5 h-5" }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
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

// Document Processing Status Component
export const ProcessingStatus = ({ status, progress, language }) => {
  const text = {
    en: {
      uploading: 'Uploading document...',
      processing: 'Processing document...',
      extracting: 'Extracting text...',
      validating: 'Validating document...',
      analyzing: 'Analyzing content...',
      complete: 'Processing complete',
      error: 'Processing failed'
    },
    ar: {
      uploading: 'جاري رفع المستند...',
      processing: 'جاري معالجة المستند...',
      extracting: 'جاري استخراج النص...',
      validating: 'جاري التحقق من المستند...',
      analyzing: 'جاري تحليل المحتوى...',
      complete: 'اكتملت المعالجة',
      error: 'فشلت المعالجة'
    }
  };

  const currentText = text[language] || text.en;
  const isRTL = language === 'ar';

  const getStatusColor = () => {
    switch (status) {
      case 'complete': return 'text-green-400';
      case 'error': return 'text-red-400';
      default: return 'text-purple-400';
    }
  };

  return (
    <div className={`flex items-center space-x-3 ${isRTL ? 'flex-row-reverse space-x-reverse' : ''}`}>
      <div className="flex-shrink-0">
        {status === 'complete' ? (
          <DocIcons.Check className={`w-5 h-5 ${getStatusColor()}`} />
        ) : status === 'error' ? (
          <DocIcons.X className={`w-5 h-5 ${getStatusColor()}`} />
        ) : (
          <div className="w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${getStatusColor()}`}>
          {currentText[status]}
        </p>
        {progress > 0 && status !== 'complete' && status !== 'error' && (
          <div className="mt-1 w-full bg-gray-700 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// OCR Text Extraction Hook
export const useOCRExtraction = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const extractText = useCallback(async (file, language = 'eng+ara') => {
    setIsProcessing(true);
    setProgress(0);
    setError(null);

    try {
      const result = await Tesseract.recognize(file, language, {
        logger: (info) => {
          if (info.status === 'recognizing text') {
            setProgress(Math.round(info.progress * 100));
          }
        }
      });

      setProgress(100);
      setIsProcessing(false);
      return {
        text: result.data.text,
        confidence: result.data.confidence,
        words: result.data.words,
        lines: result.data.lines,
        paragraphs: result.data.paragraphs
      };
    } catch (err) {
      setError(err.message);
      setIsProcessing(false);
      throw err;
    }
  }, []);

  return { extractText, isProcessing, progress, error };
};

// Document Validation Hook
export const useDocumentValidation = () => {
  const validateIDDocument = useCallback(async (extractedText, documentType) => {
    // Simulate ID validation logic
    const patterns = {
      nationalID: {
        pattern: /\b\d{10}\b|\b\d{3}-\d{2}-\d{4}\b/,
        fields: ['id_number', 'name', 'date_of_birth', 'nationality']
      },
      passport: {
        pattern: /[A-Z]{1,2}\d{6,9}/,
        fields: ['passport_number', 'name', 'date_of_birth', 'nationality', 'expiry_date']
      },
      drivingLicense: {
        pattern: /\b[A-Z]{1,2}\d{6,8}\b/,
        fields: ['license_number', 'name', 'date_of_birth', 'license_class', 'expiry_date']
      }
    };

    const config = patterns[documentType];
    if (!config) {
      throw new Error('Unsupported document type');
    }

    const isValid = config.pattern.test(extractedText);
    const extractedFields = extractDocumentFields(extractedText, config.fields);
    
    return {
      isValid,
      confidence: isValid ? 0.85 + Math.random() * 0.15 : 0.3 + Math.random() * 0.4,
      documentType,
      fields: extractedFields,
      issues: isValid ? [] : ['Invalid document format', 'Missing required fields']
    };
  }, []);

  const extractDocumentFields = (text, fields) => {
    // Basic field extraction logic (can be enhanced with ML models)
    const extracted = {};
    
    fields.forEach(field => {
      switch (field) {
        case 'id_number':
        case 'passport_number':
        case 'license_number':
          const numMatch = text.match(/\b\d{8,12}\b/) || text.match(/[A-Z]{1,2}\d{6,9}/);
          extracted[field] = numMatch ? numMatch[0] : '';
          break;
        case 'name':
          const nameMatch = text.match(/[A-Z][a-z]+ [A-Z][a-z]+/);
          extracted[field] = nameMatch ? nameMatch[0] : '';
          break;
        case 'date_of_birth':
        case 'expiry_date':
          const dateMatch = text.match(/\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}/);
          extracted[field] = dateMatch ? dateMatch[0] : '';
          break;
        case 'nationality':
          const countries = ['SAUDI', 'AMERICAN', 'BRITISH', 'EGYPTIAN', 'EMIRATE'];
          const nationalityMatch = countries.find(country => 
            text.toUpperCase().includes(country)
          );
          extracted[field] = nationalityMatch || '';
          break;
        default:
          extracted[field] = '';
      }
    });

    return extracted;
  };

  return { validateIDDocument };
};

// File Format Processing Hook
export const useFileProcessing = () => {
  const processPDF = useCallback(async (file) => {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjs.getDocument(arrayBuffer).promise;
    const numPages = pdf.numPages;
    let fullText = '';
    const pages = [];

    for (let i = 1; i <= numPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items.map(item => item.str).join(' ');
      fullText += pageText + '\n';
      pages.push({
        pageNumber: i,
        text: pageText,
        viewport: page.getViewport({ scale: 1.0 })
      });
    }

    return { fullText, pages, numPages };
  }, []);

  const processWordDocument = useCallback(async (file) => {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });
    return {
      text: result.value,
      messages: result.messages
    };
  }, []);

  const processImage = useCallback(async (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          resolve({
            width: img.width,
            height: img.height,
            dataUrl: e.target.result
          });
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }, []);

  return { processPDF, processWordDocument, processImage };
};

// Digital Signature Component
export const DigitalSignature = ({ onSignature, isOpen, onClose, language }) => {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [signature, setSignature] = useState(null);
  const isRTL = language === 'ar';

  const text = {
    en: {
      title: 'Digital Signature',
      instruction: 'Please sign in the box below',
      clear: 'Clear',
      save: 'Save Signature',
      cancel: 'Cancel'
    },
    ar: {
      title: 'التوقيع الرقمي',
      instruction: 'يرجى التوقيع في المربع أدناه',
      clear: 'مسح',
      save: 'حفظ التوقيع',
      cancel: 'إلغاء'
    }
  };

  const currentText = text[language];

  useEffect(() => {
    if (isOpen && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }, [isOpen]);

  const startDrawing = (e) => {
    setIsDrawing(true);
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setSignature(null);
  };

  const saveSignature = () => {
    const canvas = canvasRef.current;
    const dataUrl = canvas.toDataURL();
    const signatureData = {
      dataUrl,
      timestamp: new Date().toISOString(),
      hash: CryptoJS.SHA256(dataUrl).toString()
    };
    setSignature(signatureData);
    onSignature(signatureData);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl border border-gray-700" dir={isRTL ? 'rtl' : 'ltr'}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">{currentText.title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <DocIcons.X />
          </button>
        </div>

        <div className="space-y-4">
          <p className="text-gray-300 text-sm">{currentText.instruction}</p>
          
          <div className="border-2 border-dashed border-gray-600 rounded-lg p-4">
            <canvas
              ref={canvasRef}
              width={500}
              height={200}
              className="w-full border border-gray-500 rounded cursor-crosshair bg-white"
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
            />
          </div>

          <div className="flex space-x-3">
            <button
              onClick={clearSignature}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
            >
              {currentText.clear}
            </button>
            <button
              onClick={saveSignature}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg transition-colors text-sm"
            >
              {currentText.save}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors text-sm"
            >
              {currentText.cancel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Document Viewer Component
export const DocumentViewer = ({ file, extractedText, validationResult, language }) => {
  const [viewMode, setViewMode] = useState('original');
  const isRTL = language === 'ar';

  const text = {
    en: {
      original: 'Original',
      extracted: 'Extracted Text',
      validation: 'Validation Results',
      confidence: 'Confidence',
      valid: 'Valid',
      invalid: 'Invalid',
      issues: 'Issues Found'
    },
    ar: {
      original: 'الأصل',
      extracted: 'النص المستخرج',
      validation: 'نتائج التحقق',
      confidence: 'مستوى الثقة',
      valid: 'صالح',
      invalid: 'غير صالح',
      issues: 'المشاكل الموجودة'
    }
  };

  const currentText = text[language];

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700" dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Tab Navigation */}
      <div className="border-b border-gray-700">
        <div className="flex space-x-0">
          {[
            { id: 'original', label: currentText.original, icon: DocIcons.Document },
            { id: 'extracted', label: currentText.extracted, icon: DocIcons.Clipboard },
            { id: 'validation', label: currentText.validation, icon: DocIcons.Validate }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setViewMode(tab.id)}
              className={`flex items-center space-x-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                viewMode === tab.id
                  ? 'border-purple-500 text-purple-400 bg-gray-750'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-750'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {viewMode === 'original' && (
          <div className="space-y-4">
            {file && file.type.startsWith('image/') && (
              <img 
                src={URL.createObjectURL(file)} 
                alt="Document" 
                className="max-w-full h-auto rounded border border-gray-600"
              />
            )}
            {file && file.type === 'application/pdf' && (
              <div className="text-center text-gray-400">
                <DocIcons.Document className="w-16 h-16 mx-auto mb-4" />
                <p>PDF Document: {file.name}</p>
                <p className="text-sm">Size: {(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            )}
          </div>
        )}

        {viewMode === 'extracted' && (
          <div className="space-y-4">
            {extractedText ? (
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-600">
                <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono">
                  {extractedText}
                </pre>
              </div>
            ) : (
              <div className="text-center text-gray-400">
                <DocIcons.Scan className="w-16 h-16 mx-auto mb-4" />
                <p>No text extracted yet</p>
              </div>
            )}
          </div>
        )}

        {viewMode === 'validation' && (
          <div className="space-y-4">
            {validationResult ? (
              <div className="space-y-4">
                {/* Validation Status */}
                <div className={`p-4 rounded-lg border ${
                  validationResult.isValid 
                    ? 'border-green-600 bg-green-900/20' 
                    : 'border-red-600 bg-red-900/20'
                }`}>
                  <div className="flex items-center space-x-3">
                    {validationResult.isValid ? (
                      <DocIcons.Check className="w-6 h-6 text-green-400" />
                    ) : (
                      <DocIcons.X className="w-6 h-6 text-red-400" />
                    )}
                    <div>
                      <p className={`font-semibold ${
                        validationResult.isValid ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {validationResult.isValid ? currentText.valid : currentText.invalid}
                      </p>
                      <p className="text-sm text-gray-400">
                        {currentText.confidence}: {Math.round(validationResult.confidence * 100)}%
                      </p>
                    </div>
                  </div>
                </div>

                {/* Extracted Fields */}
                {validationResult.fields && Object.keys(validationResult.fields).length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-white">Extracted Information:</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(validationResult.fields).map(([field, value]) => (
                        <div key={field} className="bg-gray-900 rounded p-3 border border-gray-600">
                          <p className="text-xs text-gray-400 uppercase tracking-wide">
                            {field.replace('_', ' ')}
                          </p>
                          <p className="text-white font-medium">
                            {value || 'Not detected'}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Issues */}
                {validationResult.issues && validationResult.issues.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-red-400">{currentText.issues}:</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
                      {validationResult.issues.map((issue, index) => (
                        <li key={index}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-400">
                <DocIcons.Shield className="w-16 h-16 mx-auto mb-4" />
                <p>No validation results yet</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default {
  ProcessingStatus,
  useOCRExtraction,
  useDocumentValidation,
  useFileProcessing,
  DigitalSignature,
  DocumentViewer,
  DocIcons
};