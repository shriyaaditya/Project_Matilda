'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getDocumentAnalysis, getLatestDocumentId } from '@/lib/api/documents';
import { Document, Finding } from '@/types/matilda';
import DocumentSidebar from '@/components/workspace/DocumentSidebar';
import DocumentViewer from '@/components/workspace/DocumentViewer';
import FindingPanel from '@/components/workspace/FindingPanel';
import RestoreContextModal from '@/components/workspace/RestoreContextModal';

function WorkspaceContent() {
  const searchParams = useSearchParams();
  const docId = searchParams.get('id');
  const isDemo = searchParams.get('demo') === 'true';

  const [document, setDocument] = useState<Document | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string | null>(null);
  const [activePage, setActivePage] = useState<number>(1);
  const [isRestoreModalOpen, setIsRestoreModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDocumentFound, setNoDocumentFound] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNoDocumentFound(false);

    try {
      if (isDemo) {
        const res = await getDocumentAnalysis('doc-rosalind-franklin-001', true);
        setDocument(res.document);
        setFindings(res.findings);
        if (res.findings.length > 0) setSelectedFindingId(res.findings[0].id);
        return;
      }

      let targetId = docId;
      if (!targetId) {
        targetId = await getLatestDocumentId();
      }

      if (!targetId) {
        setNoDocumentFound(true);
        setDocument(null);
        setFindings([]);
        return;
      }

      const res = await getDocumentAnalysis(targetId, false);
      setDocument(res.document);
      setFindings(res.findings);

      if (res.findings.length > 0) {
        setSelectedFindingId(res.findings[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load document analysis from backend API.');
    } finally {
      setIsLoading(false);
    }
  }, [docId, isDemo]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectFinding = (findingId: string) => {
    setSelectedFindingId(findingId);
    const targetFinding = findings.find((f) => f.id === findingId);
    if (targetFinding) {
      setActivePage(targetFinding.page);
    }
  };

  const handleApplyRevision = (findingId: string, _suggestedText: string) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === findingId ? { ...f, status: 'Accepted' } : f))
    );
  };

  const selectedFinding = findings.find((f) => f.id === selectedFindingId) || null;

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5]">
        <div className="animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mb-4" />
        <p className="font-serif text-base text-[#1C1917]">Loading Matilda Workspace...</p>
      </div>
    );
  }

  if (noDocumentFound) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5] p-8 text-center max-w-lg mx-auto">
        <div className="w-12 h-12 rounded-full bg-[#E7E2D8] text-[#1C1917] flex items-center justify-center font-bold text-lg mb-4">
          📄
        </div>
        <h2 className="font-serif text-2xl font-bold text-[#1C1917] mb-2">No Active Analysis Document</h2>
        <p className="text-xs text-[#737373] mb-6">
          No document was found in PostgreSQL. Upload a manuscript or PDF paper to run attribution analysis.
        </p>
        <div className="flex gap-4">
          <Link
            href="/upload"
            className="px-6 py-2.5 bg-[#1C1917] text-white text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#4A463D] transition-colors"
          >
            Upload Document
          </Link>
          <a
            href="/workspace?demo=true"
            className="px-6 py-2.5 bg-white border border-[#D6CFBF] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#FAF8F5] transition-colors"
          >
            Load Explicit Demo Mode
          </a>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5] p-8 text-center max-w-lg mx-auto">
        <div className="w-12 h-12 rounded-full bg-[#FEF2F2] text-[#991B1B] flex items-center justify-center font-bold text-lg mb-4">
          ⚠️
        </div>
        <h2 className="font-serif text-2xl font-bold text-[#1C1917] mb-2">Backend Connection Error</h2>
        <p className="text-xs text-[#737373] mb-6 font-mono bg-[#FAF8F5] p-3 border border-[#E7E2D8] text-left overflow-auto max-h-40 w-full">
          {error}
        </p>
        <div className="flex gap-4">
          <button
            onClick={() => loadData()}
            className="px-6 py-2.5 bg-[#1C1917] text-white text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#4A463D] transition-colors"
          >
            Retry Connection
          </button>
          <a
            href="/workspace?demo=true"
            className="px-6 py-2.5 bg-white border border-[#D6CFBF] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#FAF8F5] transition-colors"
          >
            Load Explicit Demo Mode
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col lg:flex-row h-[calc(100vh-57px)] overflow-hidden bg-[#FAF8F5]">
      {/* LEFT SIDEBAR */}
      <DocumentSidebar
        document={document}
        findings={findings}
        selectedFindingId={selectedFindingId}
        onSelectFinding={handleSelectFinding}
        activeCategoryFilter={activeCategoryFilter}
        onSelectCategoryFilter={setActiveCategoryFilter}
      />

      {/* CENTER DOCUMENT VIEWER */}
      <DocumentViewer
        documentData={document}
        findings={findings}
        selectedFindingId={selectedFindingId}
        onSelectFinding={handleSelectFinding}
        activePage={activePage}
        onPageChange={setActivePage}
      />

      {/* RIGHT FINDING / EVIDENCE PANEL */}
      <FindingPanel
        finding={selectedFinding}
        onOpenRestoreContext={() => setIsRestoreModalOpen(true)}
      />

      {/* RESTORE CONTEXT MODAL DIALOG */}
      <RestoreContextModal
        finding={selectedFinding}
        isOpen={isRestoreModalOpen}
        onClose={() => setIsRestoreModalOpen(false)}
        onApplyRevision={handleApplyRevision}
      />
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5]">
        <div className="animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mb-4" />
        <p className="font-serif text-base text-[#1C1917]">Loading Workspace...</p>
      </div>
    }>
      <WorkspaceContent />
    </Suspense>
  );
}
