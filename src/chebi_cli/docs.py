from __future__ import annotations

OPENAPI_URL = "https://www.ebi.ac.uk/chebi/backend/api/schema/"
DOCS_URL = "https://www.ebi.ac.uk/chebi/backend/api/docs/"

ENDPOINTS: tuple[str, ...] = (
    "GET /public/advanced_search/sources_list",
    "POST /public/advanced_search/",
    "GET /public/compound/{chebi_id}/",
    "GET /public/compound/{id}/structure/",
    "GET /public/compounds/",
    "POST /public/compounds/",
    "GET /public/es_search/",
    "GET /public/molfile/{id}/",
    "GET /public/ontology/all_children_in_path/",
    "POST /public/ontology/all_children_in_path/",
    "GET /public/ontology/children/{chebi_id}/",
    "GET /public/ontology/parents/{chebi_id}/",
    "POST /public/structure-calculations/avg-mass/",
    "POST /public/structure-calculations/avg-mass/from-formula/",
    "POST /public/structure-calculations/depict-indigo/",
    "POST /public/structure-calculations/mol-formula/",
    "POST /public/structure-calculations/monoisotopic-mass/",
    "POST /public/structure-calculations/monoisotopic-mass/from-formula/",
    "POST /public/structure-calculations/net-charge/",
    "GET /public/structure/{id}/",
    "GET /public/structure_search/",
    "POST /public/structure_search/",
)


def coverage_summary() -> dict[str, object]:
    return {
        "docs_url": DOCS_URL,
        "openapi_url": OPENAPI_URL,
        "wrapped_endpoints": list(ENDPOINTS),
    }
