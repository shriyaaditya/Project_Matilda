import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.openalex_service import OpenAlexService
from app.services.qid_resolver import QIDResolver
from app.services.wikidata_service import WikidataService

logger = logging.getLogger(__name__)


class GraphEnricher:
    def __init__(self, db: AsyncSession | None = None, max_concurrency: int = 15) -> None:
        self.db = db
        self.wikidata_service = WikidataService(db)
        self.openalex_service = OpenAlexService(db)
        self.qid_resolver = QIDResolver(db)
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _enrich_single_person(
        self, seed_person: dict[str, Any]
    ) -> dict[str, Any]:
        async with self.semaphore:
            label = seed_person.get("label", "").strip()
            qid = seed_person.get("wikidata_qid")
            props = dict(seed_person.get("properties", {}))
            v_status = props.get("verification_status", "PENDING_WIKIDATA_VERIFICATION")
            conf_score = 1.0 if qid else 0.0

            unresolved_info: dict[str, Any] | None = None
            api_errors: list[dict[str, Any]] = []

            # 1. QID Resolution if missing
            if not qid:
                try:
                    res_qid, res_status, conf_score, candidates = await self.qid_resolver.resolve_person_qid(
                        label, props
                    )
                    if res_qid:
                        qid = res_qid
                        v_status = res_status
                    else:
                        v_status = "PENDING_WIKIDATA_VERIFICATION"
                        unresolved_info = {
                            "label": label,
                            "reason": "Ambiguous or low confidence Wikidata match",
                            "evaluated_candidates": candidates,
                        }
                except Exception as err:
                    logger.error("QID resolution error for %s: %s", label, err)
                    api_errors.append({"person": label, "error": str(err), "phase": "qid_resolution"})

            enriched_person_props = dict(props)
            enriched_person_props["verification_status"] = v_status
            enriched_person_props["resolution_confidence"] = conf_score

            wikidata_details: dict[str, Any] | None = None
            if qid:
                try:
                    wikidata_details = await self.wikidata_service.get_entity_details(qid)
                    if wikidata_details:
                        if wikidata_details.get("birth_year"):
                            enriched_person_props["birth_year"] = wikidata_details["birth_year"]
                        if wikidata_details.get("death_year"):
                            enriched_person_props["death_year"] = wikidata_details["death_year"]
                        if wikidata_details.get("aliases"):
                            enriched_person_props["aliases"] = list(
                                set(enriched_person_props.get("aliases", []) + wikidata_details["aliases"])
                            )
                        if wikidata_details.get("occupations"):
                            enriched_person_props["occupations"] = list(
                                set(enriched_person_props.get("occupations", []) + wikidata_details["occupations"])
                            )
                        if wikidata_details.get("description"):
                            enriched_person_props["description"] = wikidata_details["description"]
                        if wikidata_details.get("orcid"):
                            enriched_person_props["orcid"] = wikidata_details["orcid"]
                except Exception as err:
                    logger.error("Wikidata enrichment error for %s (%s): %s", label, qid, err)
                    api_errors.append({"person": label, "qid": qid, "error": str(err), "phase": "wikidata_details"})

            person_node = {
                "node_type": "PERSON",
                "label": label,
                "wikidata_qid": qid,
                "properties": enriched_person_props,
            }

            local_edges: list[dict[str, Any]] = []
            local_fields: list[dict[str, Any]] = []
            local_insts: list[dict[str, Any]] = []
            local_concepts: list[dict[str, Any]] = []
            local_pub_nodes: list[dict[str, Any]] = []
            local_alias_nodes: list[dict[str, Any]] = []
            local_candidates: list[dict[str, Any]] = []
            local_coauthor_nodes: list[dict[str, Any]] = []

            # 1b. ALIAS Node and ALIAS_OF Edge construction from Wikidata/Person aliases
            aliases_list = enriched_person_props.get("aliases", [])
            for alias_str in set(aliases_list):
                clean_alias = alias_str.strip()
                if clean_alias and clean_alias.lower() != label.lower():
                    local_alias_nodes.append({
                        "node_type": "ALIAS",
                        "label": clean_alias,
                        "wikidata_qid": None,
                        "properties": {
                            "canonical_name": label,
                            "source": "WIKIDATA_ALIAS",
                        },
                    })
                    local_edges.append({
                        "source_label": clean_alias,
                        "source_qid": None,
                        "target_label": label,
                        "target_qid": qid,
                        "edge_type": "ALIAS_OF",
                        "provenance": {
                            "source_uri": f"wikidata:{qid}#alias" if qid else f"seed_manifest:{label}",
                            "reference_text": f"Alias record for {label}.",
                            "retrieved_at": datetime.now(UTC).isoformat(),
                        },
                    })

            # 2. ASSOCIATED_WITH Edges (FIELD) from seed metadata and Wikidata P101 claims
            primary_field = props.get("primary_field")
            all_fields = set()
            if primary_field:
                all_fields.add(primary_field.strip())
            if wikidata_details and wikidata_details.get("fields"):
                for f_name in wikidata_details["fields"]:
                    all_fields.add(f_name.strip())

            for f_lbl in all_fields:
                local_fields.append({
                    "node_type": "FIELD",
                    "label": f_lbl,
                    "wikidata_qid": None,
                    "properties": {},
                })
                local_edges.append({
                    "source_label": label,
                    "source_qid": qid,
                    "target_label": f_lbl,
                    "target_qid": None,
                    "edge_type": "ASSOCIATED_WITH",
                    "provenance": {
                        "source_uri": f"wikidata:{qid}#P101" if qid else f"seed_manifest:{label}",
                        "reference_text": f"Structured field of work claim for {label}.",
                        "retrieved_at": datetime.now(UTC).isoformat(),
                    },
                })

            # 3. WORKED_AT Edges (INSTITUTION) from Wikidata P108 claims
            if wikidata_details and wikidata_details.get("employers"):
                for emp_name in wikidata_details["employers"]:
                    local_insts.append({
                        "node_type": "INSTITUTION",
                        "label": emp_name.strip(),
                        "wikidata_qid": None,
                        "properties": {},
                    })
                    local_edges.append({
                        "source_label": label,
                        "source_qid": qid,
                        "target_label": emp_name.strip(),
                        "target_qid": None,
                        "edge_type": "WORKED_AT",
                        "provenance": {
                            "source_uri": f"wikidata:{qid}#P108",
                            "reference_text": f"Wikidata employer property claim P108 for {label}.",
                            "retrieved_at": datetime.now(UTC).isoformat(),
                        },
                    })

            # 4. CONTRIBUTED_TO Edges ONLY from explicit Wikidata P800 notable work claims
            if wikidata_details and wikidata_details.get("notable_works"):
                for work_name in wikidata_details["notable_works"]:
                    local_concepts.append({
                        "node_type": "CONCEPT",
                        "label": work_name.strip(),
                        "wikidata_qid": None,
                        "properties": {
                            "category": primary_field or "STEM",
                            "evidence_status": "VERIFIED_NOTABLE_WORK",
                        },
                    })
                    local_edges.append({
                        "source_label": label,
                        "source_qid": qid,
                        "target_label": work_name.strip(),
                        "target_qid": None,
                        "edge_type": "CONTRIBUTED_TO",
                        "provenance": {
                            "source_uri": f"wikidata:{qid}#P800",
                            "reference_text": f"Wikidata explicit notable work claim P800 for {label}.",
                            "retrieved_at": datetime.now(UTC).isoformat(),
                        },
                    })

            # 5. OpenAlex Discovery: Top works saved as PUBLICATION and CONCEPT nodes
            orcid_val = wikidata_details.get("orcid") if wikidata_details else None
            try:
                openalex_authors = await self.openalex_service.search_author_by_identifier(
                    name=label, wikidata_qid=qid, orcid=orcid_val
                )
                if openalex_authors:
                    top_author = openalex_authors[0]
                    oa_id = top_author.get("id")
                    if oa_id:
                        works_data = await self.openalex_service.get_author_concepts_and_works(oa_id)
                        for work in works_data.get("results", [])[:3]:
                            work_title = work.get("title")
                            work_id = work.get("id")
                            work_doi = work.get("doi")
                            pub_year = work.get("publication_year")

                            if work_title:
                                clean_work_title = work_title.strip()
                                # Create dedicated PUBLICATION node
                                local_pub_nodes.append({
                                    "node_type": "PUBLICATION",
                                    "label": clean_work_title,
                                    "wikidata_qid": None,
                                    "properties": {
                                        "openalex_id": work_id,
                                        "doi": work_doi,
                                        "publication_year": pub_year,
                                        "citation_count": work.get("cited_by_count", 0),
                                    },
                                })
                                # Create CONCEPT node for backwards compatibility
                                local_concepts.append({
                                    "node_type": "CONCEPT",
                                    "label": clean_work_title,
                                    "wikidata_qid": None,
                                    "properties": {
                                        "category": primary_field or "STEM",
                                        "evidence_status": "CONTRIBUTION_CANDIDATE",
                                        "openalex_id": work_id,
                                        "citation_count": work.get("cited_by_count", 0),
                                    },
                                })
                                # CONTRIBUTED_TO Edge
                                local_edges.append({
                                    "source_label": label,
                                    "source_qid": qid,
                                    "target_label": clean_work_title,
                                    "target_qid": None,
                                    "edge_type": "CONTRIBUTED_TO",
                                    "provenance": {
                                        "source_uri": work_id or f"openalex:{label}",
                                        "reference_text": f"OpenAlex publication claim for {label}.",
                                        "retrieved_at": datetime.now(UTC).isoformat(),
                                    },
                                })
                                # AUTHORED Edge (to Publication node)
                                local_edges.append({
                                    "source_label": label,
                                    "source_qid": qid,
                                    "target_label": clean_work_title,
                                    "target_qid": None,
                                    "edge_type": "AUTHORED",
                                    "provenance": {
                                        "source_uri": work_id or f"openalex:{label}",
                                        "reference_text": f"OpenAlex authorship metadata for {label}.",
                                        "retrieved_at": datetime.now(UTC).isoformat(),
                                    },
                                })

                                # Build CITED_BY Edges using referenced_works / citing works
                                if work_id:
                                    try:
                                        citing_data = await self.openalex_service.get_related_or_citing_works(work_id)
                                        for citing_work in citing_data.get("results", [])[:2]:
                                            c_title = citing_work.get("title")
                                            c_id = citing_work.get("id")
                                            c_doi = citing_work.get("doi")
                                            c_year = citing_work.get("publication_year")
                                            if c_title:
                                                clean_c_title = c_title.strip()
                                                local_pub_nodes.append({
                                                    "node_type": "PUBLICATION",
                                                    "label": clean_c_title,
                                                    "wikidata_qid": None,
                                                    "properties": {
                                                        "openalex_id": c_id,
                                                        "doi": c_doi,
                                                        "publication_year": c_year,
                                                        "citation_count": citing_work.get("cited_by_count", 0),
                                                    },
                                                })
                                                # CITED_BY Edge: cited_work (source) -> citing_work (target)
                                                local_edges.append({
                                                    "source_label": clean_work_title,
                                                    "source_qid": None,
                                                    "target_label": clean_c_title,
                                                    "target_qid": None,
                                                    "edge_type": "CITED_BY",
                                                    "provenance": {
                                                        "source_uri": c_id or work_id,
                                                        "reference_text": "OpenAlex citation metadata",
                                                        "retrieved_at": datetime.now(UTC).isoformat(),
                                                    },
                                                })
                                    except Exception:
                                        pass

                                local_candidates.append({
                                    "person_label": label,
                                    "person_qid": qid,
                                    "candidate_concept_title": work_title,
                                    "openalex_id": work_id,
                                    "citation_count": work.get("cited_by_count", 0),
                                    "publication_year": work.get("publication_year"),
                                    "evidence_status": "CONTRIBUTION_CANDIDATE",
                                    "reason": "OpenAlex high-impact publication candidate. Preserved in evidence layer.",
                                })

                            # Extract co-authors from authorships array to build COLLABORATED_WITH edges
                            for authorship in work.get("authorships", []):
                                author_obj = authorship.get("author", {})
                                coauthor_name = author_obj.get("display_name")
                                coauthor_id = author_obj.get("id")
                                coauthor_orcid = author_obj.get("orcid")

                                if not coauthor_name or coauthor_name.strip().lower() == label.lower():
                                    continue

                                clean_coauthor_name = coauthor_name.strip()
                                local_coauthor_nodes.append({
                                    "node_type": "PERSON",
                                    "label": clean_coauthor_name,
                                    "wikidata_qid": None,
                                    "properties": {
                                        "openalex_id": coauthor_id,
                                        "orcid": coauthor_orcid,
                                        "verification_status": "OPENALEX_COAUTHOR",
                                    },
                                })
                                local_edges.append({
                                    "source_label": label,
                                    "source_qid": qid,
                                    "target_label": clean_coauthor_name,
                                    "target_qid": None,
                                    "edge_type": "COLLABORATED_WITH",
                                    "provenance": {
                                        "source_uri": work_id or f"openalex:{label}",
                                        "reference_text": f"OpenAlex co-authorship metadata on work '{work_title}' for {label} and {clean_coauthor_name}.",
                                        "retrieved_at": datetime.now(UTC).isoformat(),
                                    },
                                })
            except Exception as err:
                logger.warning("OpenAlex enrichment error for %s: %s", label, err)
                api_errors.append({"person": label, "error": str(err), "phase": "openalex_enrichment"})

            return {
                "person_node": person_node,
                "is_resolved": qid is not None,
                "unresolved_info": unresolved_info,
                "api_errors": api_errors,
                "fields": local_fields,
                "insts": local_insts,
                "concepts": local_concepts,
                "publications": local_pub_nodes,
                "aliases": local_alias_nodes,
                "coauthors": local_coauthor_nodes,
                "edges": local_edges,
                "candidates": local_candidates,
            }

    async def enrich_dataset(self, seed_data: dict[str, Any]) -> dict[str, Any]:
        nodes_in = seed_data.get("nodes", [])
        person_seeds = [n for n in nodes_in if n.get("node_type") == "PERSON"]

        tasks = [self._enrich_single_person(p) for p in person_seeds]
        results = await asyncio.gather(*tasks)

        person_nodes_map: dict[str, dict[str, Any]] = {}
        field_nodes_map: dict[str, dict[str, Any]] = {}
        inst_nodes_map: dict[str, dict[str, Any]] = {}
        concept_nodes_map: dict[str, dict[str, Any]] = {}
        pub_nodes_map: dict[str, dict[str, Any]] = {}
        alias_nodes_map: dict[str, dict[str, Any]] = {}

        generated_edges: list[dict[str, Any]] = []
        evidence_layer: list[dict[str, Any]] = []
        contribution_candidates: list[dict[str, Any]] = []
        unresolved_identities: list[dict[str, Any]] = []
        api_error_logs: list[dict[str, Any]] = []

        # Pre-seed non-person nodes
        for n in nodes_in:
            ntype = n.get("node_type")
            lbl = n.get("label", "").strip()
            if ntype == "FIELD":
                field_nodes_map[lbl.lower()] = n
            elif ntype == "INSTITUTION":
                inst_nodes_map[lbl.lower()] = n
            elif ntype == "CONCEPT":
                concept_nodes_map[lbl.lower()] = n
            elif ntype == "PUBLICATION":
                pub_nodes_map[lbl.lower()] = n
            elif ntype == "ALIAS":
                alias_nodes_map[lbl.lower()] = n

        resolved_qid_cnt = 0
        unresolved_qid_cnt = 0

        for r in results:
            p_node = r["person_node"]
            person_nodes_map[p_node["label"].lower()] = p_node

            if r["is_resolved"]:
                resolved_qid_cnt += 1
            else:
                unresolved_qid_cnt += 1

            if r["unresolved_info"]:
                unresolved_identities.append(r["unresolved_info"])

            api_error_logs.extend(r["api_errors"])
            generated_edges.extend(r["edges"])
            contribution_candidates.extend(r["candidates"])

            for f in r["fields"]:
                field_nodes_map[f["label"].lower()] = f
            for i in r["insts"]:
                inst_nodes_map[i["label"].lower()] = i
            for c in r["concepts"]:
                concept_nodes_map[c["label"].lower()] = c
            for pub in r.get("publications", []):
                pub_nodes_map[pub["label"].lower()] = pub
            for al in r.get("aliases", []):
                alias_nodes_map[al["label"].lower()] = al
            for co in r.get("coauthors", []):
                co_key = co["label"].lower()
                if co_key not in person_nodes_map:
                    person_nodes_map[co_key] = co

        all_nodes = (
            list(person_nodes_map.values())
            + list(field_nodes_map.values())
            + list(inst_nodes_map.values())
            + list(concept_nodes_map.values())
            + list(pub_nodes_map.values())
            + list(alias_nodes_map.values())
        )

        valid_prov_cnt = sum(1 for e in generated_edges if e.get("provenance", {}).get("source_uri"))
        prov_pct = (valid_prov_cnt / len(generated_edges) * 100) if generated_edges else 100.0

        return {
            "version": seed_data.get("version", "1.0.0"),
            "enrichment_metadata": {
                "generated_at": datetime.now(UTC).isoformat(),
                "total_seed_count": len(person_seeds),
                "resolved_qid_count": resolved_qid_cnt,
                "unresolved_qid_count": unresolved_qid_cnt,
                "provenance_coverage_pct": round(prov_pct, 2),
                "api_failures_count": len(api_error_logs),
                "api_error_logs": api_error_logs,
            },
            "nodes": all_nodes,
            "edges": generated_edges,
            "contribution_candidates": contribution_candidates,
            "unresolved_identities": unresolved_identities,
            "evidence_layer": evidence_layer,
        }
