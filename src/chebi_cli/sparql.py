from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_SPARQL_ENDPOINT = "uniprot"

SPARQL_ENDPOINTS: dict[str, str] = {
    "uniprot": "https://sparql.uniprot.org/sparql",
    "rhea": "https://sparql.rhea-db.org/sparql",
}

SPARQL_GRAPH_IRIS: dict[str, str] = {
    "uniprot": "http://sparql.uniprot.org/chebi",
    "rhea": "http://sparql.rhea-db.org/chebi",
}


@dataclass(frozen=True)
class SparqlPreset:
    name: str
    description: str
    query_template: str

    def render(self, *, graph: str, limit: int) -> str:
        return self.query_template.format(graph=graph, limit=limit)


SPARQL_PRESETS: dict[str, SparqlPreset] = {
    "graphs": SparqlPreset(
        name="graphs",
        description="List named graphs exposed by the endpoint.",
        query_template="""
SELECT ?graph
WHERE {{
  GRAPH ?graph {{
    ?s ?p ?o .
  }}
}}
GROUP BY ?graph
ORDER BY ?graph
LIMIT {limit}
""".strip(),
    ),
    "classes": SparqlPreset(
        name="classes",
        description="List RDF classes in the ChEBI graph with instance counts.",
        query_template="""
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?class (COUNT(?entity) AS ?entityCount)
WHERE {{
  GRAPH <{graph}> {{
    ?entity a ?class .
  }}
}}
GROUP BY ?class
ORDER BY DESC(xsd:integer(?entityCount)) ?class
LIMIT {limit}
""".strip(),
    ),
    "predicates": SparqlPreset(
        name="predicates",
        description="List predicates in the ChEBI graph with triple counts.",
        query_template="""
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?predicate (COUNT(*) AS ?tripleCount)
WHERE {{
  GRAPH <{graph}> {{
    ?subject ?predicate ?object .
  }}
}}
GROUP BY ?predicate
ORDER BY DESC(xsd:integer(?tripleCount)) ?predicate
LIMIT {limit}
""".strip(),
    ),
    "predicate-examples": SparqlPreset(
        name="predicate-examples",
        description="Show one sample subject and object for each predicate in the ChEBI graph.",
        query_template="""
SELECT ?predicate
       (SAMPLE(?subject) AS ?exampleSubject)
       (SAMPLE(?object) AS ?exampleObject)
WHERE {{
  GRAPH <{graph}> {{
    ?subject ?predicate ?object .
  }}
}}
GROUP BY ?predicate
ORDER BY ?predicate
LIMIT {limit}
""".strip(),
    ),
    "property-coverage": SparqlPreset(
        name="property-coverage",
        description="Summarize key ChEBI chemistry and curation properties.",
        query_template="""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?metric (COUNT(?s) AS ?count)
WHERE {{
  GRAPH <{graph}> {{
    {{ ?s a owl:Class . BIND("owl:Class" AS ?metric) }}
    UNION {{ ?s rdfs:label ?o . BIND("rdfs:label" AS ?metric) }}
    UNION {{ ?s oboinowl:hasSynonym ?o . BIND("hasSynonym" AS ?metric) }}
    UNION {{ ?s oboinowl:hasAlternativeId ?o . BIND("hasAlternativeId" AS ?metric) }}
    UNION {{ ?s <http://purl.obolibrary.org/obo/chebi/formula> ?o . BIND("formula" AS ?metric) }}
    UNION {{ ?s <http://purl.obolibrary.org/obo/chebi/inchi> ?o . BIND("inchi" AS ?metric) }}
    UNION {{ ?s <http://purl.obolibrary.org/obo/chebi/inchikey> ?o . BIND("inchikey" AS ?metric) }}
    UNION {{ ?s <http://purl.obolibrary.org/obo/chebi/smiles> ?o . BIND("smiles" AS ?metric) }}
    UNION {{ ?s owl:deprecated ?o . BIND("deprecated" AS ?metric) }}
    UNION {{ ?s up:name ?o . BIND("up:name" AS ?metric) }}
  }}
}}
GROUP BY ?metric
ORDER BY ?metric
LIMIT {limit}
""".strip(),
    ),
    "deprecated": SparqlPreset(
        name="deprecated",
        description="Count deprecated ChEBI classes and sample replacements.",
        query_template="""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT ?deprecated ?replacement
WHERE {{
  GRAPH <{graph}> {{
    ?deprecated owl:deprecated true .
    OPTIONAL {{ ?deprecated obo:IAO_0100001 ?replacement . }}
  }}
}}
ORDER BY ?deprecated
LIMIT {limit}
""".strip(),
    ),
}


def list_sparql_presets() -> list[dict[str, str]]:
    return [
        {"name": preset.name, "description": preset.description}
        for preset in sorted(SPARQL_PRESETS.values(), key=lambda item: item.name)
    ]


def resolve_sparql_endpoint(endpoint: str, override_base_url: str | None = None) -> tuple[str, str]:
    if override_base_url:
        graph = SPARQL_GRAPH_IRIS.get(endpoint, SPARQL_GRAPH_IRIS[DEFAULT_SPARQL_ENDPOINT])
        return override_base_url.rstrip("/"), graph
    try:
        return SPARQL_ENDPOINTS[endpoint], SPARQL_GRAPH_IRIS[endpoint]
    except KeyError as exc:
        raise KeyError(f"unknown SPARQL endpoint: {endpoint}") from exc


def render_sparql_preset(name: str, *, graph: str, limit: int) -> str:
    try:
        preset = SPARQL_PRESETS[name]
    except KeyError as exc:
        raise KeyError(f"unknown SPARQL preset: {name}") from exc
    return preset.render(graph=graph, limit=limit)


def sparql_accept_header(output_format: str, accept: str | None = None) -> str:
    if accept:
        return accept
    if output_format == "json":
        return "application/sparql-results+json, application/json;q=0.9"
    if output_format == "csv":
        return "text/csv"
    if output_format == "tsv":
        return "text/tab-separated-values"
    if output_format == "text":
        return "application/sparql-results+json, application/json;q=0.9, text/plain;q=0.8"
    return "*/*"


def parse_sparql_json(payload: dict[str, Any]) -> dict[str, Any]:
    if "boolean" in payload:
        return {"kind": "ask", "boolean": bool(payload["boolean"])}
    variables = list(payload.get("head", {}).get("vars", []))
    bindings = list(payload.get("results", {}).get("bindings", []))
    items = [
        {variable: _term_value(binding.get(variable)) for variable in variables}
        for binding in bindings
    ]
    return {
        "kind": "select",
        "variables": variables,
        "count": len(items),
        "items": items,
        "bindings": bindings,
    }


def _term_value(term: dict[str, Any] | None) -> str:
    if not term:
        return ""
    value = str(term.get("value", ""))
    lang = term.get("xml:lang") or term.get("lang")
    datatype = term.get("datatype")
    if lang:
        return f"{value}@{lang}"
    if datatype and datatype != "http://www.w3.org/2001/XMLSchema#string":
        return f"{value}^^{datatype}"
    return value


__all__ = [
    "DEFAULT_SPARQL_ENDPOINT",
    "SPARQL_ENDPOINTS",
    "SPARQL_GRAPH_IRIS",
    "SPARQL_PRESETS",
    "SparqlPreset",
    "list_sparql_presets",
    "parse_sparql_json",
    "render_sparql_preset",
    "resolve_sparql_endpoint",
    "sparql_accept_header",
]
