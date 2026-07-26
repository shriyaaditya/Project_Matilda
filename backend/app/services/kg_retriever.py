import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class KGRetriever:
    """
    Traverses NetworkX knowledge graph for document concepts and fields.
    Extracts provenance-backed candidate paths.
    """

    def __init__(self, nx_graph: nx.DiGraph) -> None:
        self.graph = nx_graph

    def find_candidates_for_concepts(
        self, document_concepts: list[str], document_fields: list[str]
    ) -> list[dict[str, Any]]:
        """
        Traverses NetworkX graph to discover historical women connected to document concepts.
        Primary Path: Document Concept -> CONCEPT <- CONTRIBUTED_TO <- PERSON (Concept Specific)
        Context Path: Document Concept / Field -> FIELD <- ASSOCIATED_WITH <- PERSON (Context Only)
        """
        candidates_map: dict[str, dict[str, Any]] = {}
        clean_doc_concepts = {c.strip().lower(): c.strip() for c in document_concepts if c and len(c.strip()) >= 3}
        clean_doc_fields = {f.strip().lower(): f.strip() for f in document_fields if f and len(f.strip()) >= 3}

        for node_id, data in self.graph.nodes(data=True):
            ntype = data.get("node_type")
            label = data.get("label", "")
            lbl_lower = label.lower()

            if ntype == "CONCEPT":
                # Check if this graph concept matches any document concept
                matched_doc_concept = None
                for dc_lower, dc_orig in clean_doc_concepts.items():
                    if dc_lower in lbl_lower or lbl_lower in dc_lower:
                        matched_doc_concept = dc_orig
                        break

                if matched_doc_concept:
                    # Find incoming edges to this CONCEPT node
                    for u, _v, edge_data in self.graph.in_edges(node_id, data=True):
                        u_data = self.graph.nodes[u]
                        if u_data.get("node_type") == "PERSON":
                            edge_type = edge_data.get("edge_type", "")
                            p_qid = u_data.get("wikidata_qid")
                            key = p_qid or u_data.get("label")

                            is_direct_contribution = edge_type == "CONTRIBUTED_TO"

                            path_item = {
                                "source": u_data.get("label"),
                                "edge_type": edge_type,
                                "target": label,
                                "matched_document_concept": matched_doc_concept,
                                "provenance": edge_data.get("provenance", {}),
                            }

                            if key not in candidates_map:
                                candidates_map[key] = {
                                    "person_label": u_data.get("label"),
                                    "wikidata_qid": p_qid,
                                    "has_concept_specific_evidence": is_direct_contribution,
                                    "matched_concepts": [matched_doc_concept],
                                    "graph_paths": [path_item],
                                    "provenance_records": [edge_data.get("provenance", {})],
                                    "relationship_types": [edge_type],
                                    "min_distance": 1,
                                    "is_external_discovery": False,
                                }
                            else:
                                cand = candidates_map[key]
                                if is_direct_contribution:
                                    cand["has_concept_specific_evidence"] = True
                                if matched_doc_concept not in cand["matched_concepts"]:
                                    cand["matched_concepts"].append(matched_doc_concept)
                                cand["graph_paths"].append(path_item)
                                cand["provenance_records"].append(edge_data.get("provenance", {}))
                                cand["relationship_types"].append(edge_type)

            elif ntype == "FIELD":
                # Check if this graph field matches document fields
                matched_field = None
                for df_lower, df_orig in clean_doc_fields.items():
                    if df_lower in lbl_lower or lbl_lower in df_lower:
                        matched_field = df_orig
                        break

                if matched_field:
                    # Find incoming ASSOCIATED_WITH edges
                    for u, _v, edge_data in self.graph.in_edges(node_id, data=True):
                        u_data = self.graph.nodes[u]
                        if u_data.get("node_type") == "PERSON":
                            edge_type = edge_data.get("edge_type", "")
                            p_qid = u_data.get("wikidata_qid")
                            key = p_qid or u_data.get("label")

                            path_item = {
                                "source": u_data.get("label"),
                                "edge_type": edge_type,
                                "target": label,
                                "matched_document_field": matched_field,
                                "provenance": edge_data.get("provenance", {}),
                            }

                            if key not in candidates_map:
                                candidates_map[key] = {
                                    "person_label": u_data.get("label"),
                                    "wikidata_qid": p_qid,
                                    "has_concept_specific_evidence": False,
                                    "matched_concepts": [],
                                    "graph_paths": [path_item],
                                    "provenance_records": [edge_data.get("provenance", {})],
                                    "relationship_types": [edge_type],
                                    "min_distance": 2,
                                    "is_external_discovery": False,
                                }
                            else:
                                cand = candidates_map[key]
                                cand["graph_paths"].append(path_item)
                                cand["provenance_records"].append(edge_data.get("provenance", {}))
                                cand["relationship_types"].append(edge_type)

        return list(candidates_map.values())
