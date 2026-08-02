'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getDocumentReport, updateFindingStatus } from '@/lib/api/reports';
import { getLatestDocumentId } from '@/lib/api/documents';
import { ReportSummary as ReportSummaryType, FindingStatus } from '@/types/matilda';
import ReportSummary from '@/components/reports/ReportSummary';
import FindingList from '@/components/reports/FindingList';

function ReportsContent() {
  const searchParams = useSearchParams();
  const docId = searchParams.get('id');
  const isDemo = searchParams.get('demo') === 'true';

  const [report, setReport] = useState<ReportSummaryType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noDocumentFound, setNoDocumentFound] = useState(false);

  const loadReport = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNoDocumentFound(false);

    try {
      if (isDemo) {
        const data = await getDocumentReport('doc-rosalind-franklin-001', true);
        setReport(data);
        return;
      }

      let targetId = docId;
      if (!targetId) {
        targetId = await getLatestDocumentId();
      }

      if (!targetId) {
        setNoDocumentFound(true);
        setReport(null);
        return;
      }

      const data = await getDocumentReport(targetId, false);
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to Reports API.');
    } finally {
      setIsLoading(false);
    }
  }, [docId, isDemo]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleStatusChange = async (findingId: string, newStatus: FindingStatus) => {
    if (!report) return;
    setReport((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        findings: prev.findings.map((f) =>
          f.id === findingId ? { ...f, status: newStatus } : f
        ),
      };
    });

    await updateFindingStatus(report.documentId, findingId, newStatus);
  };

  const handleExportPDF = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5]">
        <div className="animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mb-4" />
        <p className="font-serif text-base text-[#1C1917]">Generating Audit Report...</p>
      </div>
    );
  }

  if (noDocumentFound) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5] p-8 text-center max-w-lg mx-auto">
        <div className="w-12 h-12 rounded-full bg-[#E7E2D8] text-[#1C1917] flex items-center justify-center font-bold text-lg mb-4">
          📊
        </div>
        <h2 className="font-serif text-2xl font-bold text-[#1C1917] mb-2">No Active Report Available</h2>
        <p className="text-xs text-[#737373] mb-6">
          No document report was found in PostgreSQL. Upload a document to generate a complete audit report.
        </p>
        <div className="flex gap-4">
          <Link
            href="/upload"
            className="px-6 py-2.5 bg-[#1C1917] text-white text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#4A463D] transition-colors"
          >
            Upload Document
          </Link>
          <a
            href="/reports?demo=true"
            className="px-6 py-2.5 bg-white border border-[#D6CFBF] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#FAF8F5] transition-colors"
          >
            Load Explicit Demo Report
          </a>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5] p-8 text-center max-w-lg mx-auto">
        <div className="w-12 h-12 rounded-full bg-[#FEF2F2] text-[#991B1B] flex items-center justify-center font-bold text-lg mb-4">
          ⚠️
        </div>
        <h2 className="font-serif text-2xl font-bold text-[#1C1917] mb-2">Report Fetch Error</h2>
        <p className="text-xs text-[#737373] mb-6 font-mono bg-white p-3 border border-[#E7E2D8] text-left overflow-auto max-h-40 w-full">
          {error}
        </p>
        <div className="flex gap-4">
          <button
            onClick={() => loadReport()}
            className="px-6 py-2.5 bg-[#1C1917] text-white text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#4A463D] transition-colors"
          >
            Retry Connection
          </button>
          <a
            href="/reports?demo=true"
            className="px-6 py-2.5 bg-white border border-[#D6CFBF] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#FAF8F5] transition-colors"
          >
            Load Explicit Demo Report
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-[#FAF8F5] overflow-y-auto">
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        {/* REPORT SUMMARY CARD */}
        <ReportSummary report={report} onExport={handleExportPDF} />

        {/* FINDING INVENTORY LIST TABLE */}
        <FindingList findings={report.findings} onStatusChange={handleStatusChange} />
      </div>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5]">
        <div className="animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mb-4" />
        <p className="font-serif text-base text-[#1C1917]">Loading Report...</p>
      </div>
    }>
      <ReportsContent />
    </Suspense>
  );
}
