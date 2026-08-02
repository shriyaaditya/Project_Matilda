'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { uploadDocument } from '@/lib/api/documents';

type TabMode = 'file' | 'text';

export default function UploadContainer() {
  const router = useRouter();
  const [tab, setTab] = useState<TabMode>('file');
  const [file, setFile] = useState<File | null>(null);
  const [textInput, setTextInput] = useState('');
  const [analysisType, setAnalysisType] = useState('Full Attribution & Provenance Audit');
  const [reasoningEnabled, setReasoningEnabled] = useState(true);
  const [explanationEnabled, setExplanationEnabled] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<'Uploading' | 'Analyzing' | 'Complete' | 'Error'>('Uploading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (tab === 'file' && !file) return;
    if (tab === 'text' && !textInput.trim()) return;

    setIsProcessing(true);
    setProcessingStatus('Uploading');
    setErrorMessage(null);

    try {
      setProcessingStatus('Analyzing');
      const res = await uploadDocument({
        file: file || undefined,
        text: tab === 'text' ? textInput : undefined,
        analysisType,
        reasoningEnabled,
        explanationEnabled,
      });

      setProcessingStatus('Complete');
      router.push(`/workspace?id=${res.id}`);
    } catch (err: any) {
      setProcessingStatus('Error');
      setErrorMessage(err.message || 'An unexpected error occurred during document analysis.');
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full px-6 py-12">
      {/* Headline */}
      <div className="text-center mb-10 space-y-3">
        <h1 className="font-serif text-4xl sm:text-5xl font-bold tracking-tight text-[#1C1917]">
          Analyze a document with Matilda.
        </h1>
        <p className="text-sm sm:text-base text-[#737373] max-w-xl mx-auto font-sans">
          Identify historical attribution issues, missing context, credit displacement, and representation gaps across primary sources.
        </p>
      </div>

      {!isProcessing ? (
        <div className="bg-white border border-[#E7E2D8] rounded-sm p-8 shadow-paper space-y-6">
          {errorMessage && (
            <div className="p-4 bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] text-xs font-semibold rounded-sm">
              <span className="font-bold block mb-1">Analysis Error:</span>
              {errorMessage}
            </div>
          )}

          {/* Input Method Toggle */}
          <div className="flex border-b border-[#E7E2D8] pb-4 gap-6">
            <button
              onClick={() => setTab('file')}
              className={`text-xs font-bold tracking-wider uppercase transition-colors pb-2 border-b-2 ${
                tab === 'file'
                  ? 'text-[#1C1917] border-[#1C1917]'
                  : 'text-[#737373] border-transparent hover:text-[#1C1917]'
              }`}
            >
              Upload Document (PDF, DOCX, TXT)
            </button>
            <button
              onClick={() => setTab('text')}
              className={`text-xs font-bold tracking-wider uppercase transition-colors pb-2 border-b-2 ${
                tab === 'text'
                  ? 'text-[#1C1917] border-[#1C1917]'
                  : 'text-[#737373] border-transparent hover:text-[#1C1917]'
              }`}
            >
              Paste Document Text
            </button>
          </div>

          {tab === 'file' ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-sm p-12 text-center transition-all cursor-pointer ${
                isDragOver
                  ? 'border-[#1C1917] bg-[#FAF8F5]'
                  : 'border-[#D6CFBF] hover:border-[#1C1917] bg-[#FAF8F5]/50'
              }`}
            >
              <input
                type="file"
                id="file-upload"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="file-upload" className="cursor-pointer block space-y-4">
                <div className="w-12 h-12 rounded-full bg-[#E7E2D8] flex items-center justify-center mx-auto text-[#1C1917]">
                  📄
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#1C1917]">
                    {file ? file.name : 'Drag and drop your manuscript or paper here'}
                  </p>
                  <p className="text-xs text-[#737373] mt-1">
                    Supports PDF, DOCX, and TXT files up to 50MB
                  </p>
                </div>
                {!file && (
                  <span className="inline-block text-xs font-semibold px-4 py-2 bg-white border border-[#D6CFBF] text-[#1C1917] rounded-sm hover:bg-[#FAF8F5]">
                    Browse Files
                  </span>
                )}
              </label>
            </div>
          ) : (
            <div className="space-y-2">
              <label htmlFor="paste-text-area" className="text-xs font-bold text-[#1C1917] uppercase tracking-wider block">
                Document Excerpt or Manuscript Text
              </label>
              <textarea
                id="paste-text-area"
                aria-label="Document Excerpt or Manuscript Text"
                rows={10}
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste scholarly article, textbook passage, or historical document text..."
                className="w-full p-4 font-serif text-sm bg-[#FAF8F5] border border-[#E7E2D8] focus:outline-none focus:border-[#1C1917] rounded-sm text-[#1C1917]"
              />
            </div>
          )}

          {/* Configurable LLM Reasoning Controls */}
          <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-4 rounded-sm space-y-3">
            <span className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest block">
              PHASE 9 NEURO-SYMBOLIC LLM SETTINGS
            </span>
            <div className="flex flex-col sm:flex-row gap-4 text-xs">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={reasoningEnabled}
                  onChange={(e) => setReasoningEnabled(e.target.checked)}
                  className="rounded border-[#D6CFBF] text-[#1C1917]"
                />
                <span className="font-medium text-[#1C1917]">Enable Gemini LLM Reasoning</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={explanationEnabled}
                  onChange={(e) => setExplanationEnabled(e.target.checked)}
                  className="rounded border-[#D6CFBF] text-[#1C1917]"
                />
                <span className="font-medium text-[#1C1917]">Enable Grounded Explanations</span>
              </label>
            </div>
          </div>

          {/* Primary CTA */}
          <div className="pt-2">
            <button
              onClick={handleAnalyze}
              disabled={(tab === 'file' && !file) || (tab === 'text' && !textInput.trim())}
              className="w-full py-4 bg-[#1C1917] hover:bg-[#4A463D] disabled:bg-[#D6CFBF] disabled:cursor-not-allowed text-white text-xs font-bold uppercase tracking-widest transition-colors rounded-sm shadow-paper"
            >
              ANALYZE DOCUMENT
            </button>
          </div>
        </div>
      ) : (
        /* Real Verifiable Status View (Uploading -> Analyzing -> Complete) */
        <div className="bg-white border border-[#E7E2D8] rounded-sm p-10 shadow-paper text-center space-y-6">
          <div className="inline-block animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mx-auto" />

          <div className="space-y-2">
            <h2 className="font-serif text-2xl font-bold text-[#1C1917]">
              Matilda Document Processing
            </h2>
            <p className="text-xs text-[#737373] uppercase tracking-wider font-mono">
              Status: {processingStatus}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
