'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { getKnowledgeGraph } from '@/lib/api/graph';
import { KnowledgeGraphData, GraphNode } from '@/types/matilda';
import KnowledgeGraphCanvas from '@/components/graph/KnowledgeGraphCanvas';
import GraphFilters from '@/components/graph/GraphFilters';
import EntityDetailPanel from '@/components/graph/EntityDetailPanel';

function KnowledgeGraphContent() {
  const searchParams = useSearchParams();
  const isDemo = searchParams.get('demo') === 'true';

  const [graphData, setGraphData] = useState<KnowledgeGraphData | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('ALL');
  const [relationshipFilter, setRelationshipFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getKnowledgeGraph({
        search: searchQuery,
        entityType: entityTypeFilter,
        relationshipType: relationshipFilter,
        demoMode: isDemo,
      });
      setGraphData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to Knowledge Graph API.');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, entityTypeFilter, relationshipFilter, isDemo]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const selectedNode: GraphNode | null =
    graphData?.nodes.find((n) => n.id === selectedNodeId) || null;

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-57px)] overflow-hidden bg-[#FAF8F5]">
      {/* GRAPH FILTERS BAR */}
      <GraphFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedEntityType={entityTypeFilter}
        onEntityTypeChange={setEntityTypeFilter}
        selectedRelType={relationshipFilter}
        onRelTypeChange={setRelationshipFilter}
      />

      {/* GRAPH CANVAS & DRAWER */}
      <div className="flex-1 relative flex overflow-hidden">
        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5]">
            <div className="animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mb-4" />
            <p className="font-serif text-base text-[#1C1917]">Building Knowledge Graph Canvas...</p>
          </div>
        ) : error || !graphData ? (
          <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5] p-8 text-center max-w-lg mx-auto">
            <div className="w-12 h-12 rounded-full bg-[#FEF2F2] text-[#991B1B] flex items-center justify-center font-bold text-lg mb-4">
              ⚠️
            </div>
            <h2 className="font-serif text-2xl font-bold text-[#1C1917] mb-2">Graph Connection Error</h2>
            <p className="text-xs text-[#737373] mb-6 font-mono bg-white p-3 border border-[#E7E2D8] text-left overflow-auto max-h-40 w-full">
              {error}
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => fetchGraph()}
                className="px-6 py-2.5 bg-[#1C1917] text-white text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#4A463D] transition-colors"
              >
                Retry Graph Connection
              </button>
              <a
                href="/graph?demo=true"
                className="px-6 py-2.5 bg-white border border-[#D6CFBF] text-[#1C1917] text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-[#FAF8F5] transition-colors"
              >
                Load Explicit Demo Graph
              </a>
            </div>
          </div>
        ) : (
          <>
            <KnowledgeGraphCanvas
              data={graphData}
              selectedNodeId={selectedNodeId}
              onSelectNode={(node) => setSelectedNodeId(node.id)}
            />

            <EntityDetailPanel
              node={selectedNode}
              onClose={() => setSelectedNodeId(null)}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default function KnowledgeGraphPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex flex-col items-center justify-center bg-[#FAF8F5]">
        <div className="animate-spin w-8 h-8 border-2 border-[#1C1917] border-t-transparent rounded-full mb-4" />
        <p className="font-serif text-base text-[#1C1917]">Loading Knowledge Graph...</p>
      </div>
    }>
      <KnowledgeGraphContent />
    </Suspense>
  );
}
