export type FindingCategory =
  | 'credit_displacement'
  | 'missing_attribution'
  | 'context_omission'
  | 'representation_gap'
  | 'unsupported_claim';

export type FindingStatus = 'Open' | 'Reviewed' | 'Accepted' | 'Dismissed';

export type FindingSeverity = 'high' | 'medium' | 'low';

export interface Evidence {
  id: string;
  title: string;
  source: string;
  author?: string;
  date?: string;
  quote?: string;
  excerpt: string;
  url?: string;
  repository?: string;
}

export interface RelatedEntity {
  id: string;
  name: string;
  role: string;
  type: 'Person' | 'Institution' | 'Publication' | 'Discovery' | 'Artifact';
}

export interface ProvenanceStep {
  id: string;
  label: string;
  sublabel?: string;
  type: 'person' | 'artifact' | 'recipient' | 'event';
}

export interface ProvenanceGraph {
  nodes: ProvenanceStep[];
  flow: string[]; // Node IDs in sequence
}

export interface Finding {
  id: string;
  documentId: string;
  category: FindingCategory;
  categoryTitle: string;
  title: string;
  description: string;
  whyFlagged: string;
  severity: FindingSeverity;
  confidence?: number; // 0 to 1, populated only if backend provides it
  passage: string;
  page: number;
  paragraphIndex?: number;
  highlightText: string;
  evidence: Evidence[];
  relatedEntities: RelatedEntity[];
  provenance?: ProvenanceGraph;
  status: FindingStatus;
  suggestedRevision?: {
    originalText: string;
    suggestedText: string;
    evidenceUsed: Evidence[];
    rationale: string;
  };
}

export interface DocumentPage {
  pageNumber: number;
  title?: string;
  paragraphs: {
    id: string;
    text: string;
    annotations?: {
      findingId: string;
      highlightText: string;
      category: FindingCategory;
    }[];
  }[];
  imageUrl?: string;
}

export interface Document {
  id: string;
  title: string;
  subtitle?: string;
  author?: string;
  uploadDate: string;
  fileType: 'PDF' | 'DOCX' | 'TXT' | 'PASTE';
  fileSize?: string;
  analysisType: string;
  historicalContextCoverage?: {
    scoreDisplay: string;
    isDemoValue: boolean;
    note: string;
  };
  pages: DocumentPage[];
  metadata: {
    peopleCount: number;
    claimsCount: number;
    sourcesCount: number;
    peopleList: string[];
    claimsList: string[];
    sourcesList: string[];
  };
}

export type EntityType =
  | 'Person'
  | 'Institution'
  | 'Publication'
  | 'Discovery'
  | 'Artifact'
  | 'Event'
  | 'Document';

export type RelationshipType =
  | 'AUTHORED'
  | 'WORKED_AT'
  | 'CONTRIBUTED_TO'
  | 'PRODUCED'
  | 'CITED_BY'
  | 'COLLABORATED_WITH'
  | 'USED_BY'
  | 'ASSOCIATED_WITH';

export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  subtitle?: string;
  description?: string;
  affiliation?: string;
  documentsCount?: number;
  evidenceCount?: number;
  isDemoData?: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: RelationshipType;
  label: string;
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  isDemoData: boolean;
}

export interface ReportSummary {
  documentId: string;
  documentTitle: string;
  analysisDate: string;
  totalFindings: number;
  categoryBreakdown: Record<FindingCategory, number>;
  historicalContextCoverage?: {
    scoreDisplay: string;
    isDemoValue: boolean;
  };
  evidenceCoverage: {
    verifiedClaims: number;
    totalClaims: number;
    percentage: string;
    isDemoValue: boolean;
  };
  findings: Finding[];
}
