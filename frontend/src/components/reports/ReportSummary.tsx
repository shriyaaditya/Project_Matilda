'use client';

import { ReportSummary as ReportSummaryType } from '@/types/matilda';
import Link from 'next/link';

interface Props {
  report: ReportSummaryType;
  onExport: () => void;
}

export default function ReportSummary({ report, onExport }: Props) {
  return (
    <div className="bg-white border border-[#E7E2D8] rounded-sm p-6 sm:p-8 shadow-paper space-y-6">
      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E7E2D8] pb-6">
        <div>
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-widest block mb-1">
            DOCUMENT ANALYSIS AUDIT REPORT
          </span>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-[#1C1917]">
            {report.documentTitle}
          </h1>
          <p className="text-xs text-[#737373] mt-1 font-mono">
            Analysis Date: {report.analysisDate} • Document ID: {report.documentId}
          </p>
        </div>

        {/* CTAs */}
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/workspace"
            className="px-4 py-2 bg-white border border-[#D6CFBF] hover:bg-[#FAF8F5] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm transition-colors"
          >
            RETURN TO WORKSPACE
          </Link>
          <button
            onClick={onExport}
            className="px-5 py-2 bg-[#1C1917] hover:bg-[#4A463D] text-white text-xs font-bold uppercase tracking-wider rounded-sm shadow-paper transition-colors"
          >
            EXPORT REPORT
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-4 rounded-sm">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
            TOTAL FINDINGS
          </span>
          <span className="font-serif text-3xl font-bold text-[#1C1917] block mt-1">
            {report.totalFindings}
          </span>
        </div>

        {report.historicalContextCoverage && (
          <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-4 rounded-sm">
            <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
              CONTEXT COVERAGE
            </span>
            <span className="font-serif text-3xl font-bold text-[#1C1917] block mt-1">
              {report.historicalContextCoverage.scoreDisplay}
            </span>
          </div>
        )}

        <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-4 rounded-sm">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
            VERIFIED CLAIMS
          </span>
          <span className="font-serif text-3xl font-bold text-[#1C1917] block mt-1">
            {report.evidenceCoverage.verifiedClaims} / {report.evidenceCoverage.totalClaims}
          </span>
        </div>

        <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-4 rounded-sm">
          <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider block">
            EVIDENCE RATIO
          </span>
          <span className="font-serif text-3xl font-bold text-[#1C1917] block mt-1">
            {report.evidenceCoverage.percentage}
          </span>
        </div>
      </div>

      {/* Category Breakdown Progress */}
      <div className="space-y-3 pt-2">
        <h3 className="text-[10px] font-bold text-[#1C1917] uppercase tracking-widest border-b border-[#E7E2D8] pb-1">
          FINDINGS BY CATEGORY BREAKDOWN
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 text-xs">
          <div className="bg-[#FEF2F2] border border-[#FCA5A5] p-3 rounded-sm">
            <span className="text-[10px] font-bold text-[#991B1B] block">Credit Displacement</span>
            <span className="font-serif text-xl font-bold text-[#B91C1C]">
              {report.categoryBreakdown.credit_displacement}
            </span>
          </div>
          <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-3 rounded-sm">
            <span className="text-[10px] font-bold text-[#737373] block">Missing Attribution</span>
            <span className="font-serif text-xl font-bold text-[#1C1917]">
              {report.categoryBreakdown.missing_attribution}
            </span>
          </div>
          <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-3 rounded-sm">
            <span className="text-[10px] font-bold text-[#737373] block">Context Omission</span>
            <span className="font-serif text-xl font-bold text-[#1C1917]">
              {report.categoryBreakdown.context_omission}
            </span>
          </div>
          <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-3 rounded-sm">
            <span className="text-[10px] font-bold text-[#737373] block">Representation Gap</span>
            <span className="font-serif text-xl font-bold text-[#1C1917]">
              {report.categoryBreakdown.representation_gap}
            </span>
          </div>
          <div className="bg-[#FAF8F5] border border-[#E7E2D8] p-3 rounded-sm">
            <span className="text-[10px] font-bold text-[#737373] block">Unsupported Claim</span>
            <span className="font-serif text-xl font-bold text-[#1C1917]">
              {report.categoryBreakdown.unsupported_claim}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
