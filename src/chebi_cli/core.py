from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from chebi_cli.client import ChebiClient, RawResponse
from chebi_cli.docs import coverage_summary
from chebi_cli.sparql import (
    list_sparql_presets,
    parse_sparql_json,
    render_sparql_preset,
    sparql_accept_header,
)

SearchType = str


@dataclass(frozen=True)
class Pagination:
    page: int = 1
    size: int = 15


def _with_optional(params: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    out = dict(params)
    for key, value in kwargs.items():
        if value is not None:
            out[key] = value
    return out


def _normalize_chebi_id(chebi_id: str) -> str:
    value = chebi_id.strip()
    if not value:
        raise ValueError("ChEBI identifier must not be empty")
    if value.lower().startswith("chebi:"):
        return value
    if value.isdigit():
        return f"CHEBI:{value}"
    return value


def _paginate(
    fetch_page: Callable[[int, int], dict[str, Any]],
    *,
    page: int,
    size: int,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    result = fetch_page(page, size)
    if not all_pages:
        return result

    aggregated_items: list[Any] = []
    current = result
    page_count = 0

    while True:
        page_count += 1
        _extend_items(aggregated_items, current)
        if max_pages is not None and page_count >= max_pages:
            break
        next_page = _extract_next_page(current)
        if next_page is None:
            break
        current = fetch_page(next_page, size)

    merged = dict(result)
    merged["results"] = aggregated_items
    merged["aggregated_pages"] = page_count
    return merged


def _extend_items(target: list[Any], payload: dict[str, Any]) -> None:
    if isinstance(payload.get("results"), list):
        target.extend(payload["results"])
    elif isinstance(payload.get("items"), list):
        target.extend(payload["items"])


def _extract_next_page(payload: dict[str, Any]) -> int | None:
    next_value = payload.get("next")
    if next_value is None:
        return None
    if isinstance(next_value, int):
        return next_value
    if isinstance(next_value, str) and "page=" in next_value:
        try:
            page_part = next_value.split("page=")[1].split("&")[0]
            return int(page_part)
        except (IndexError, ValueError):
            return None
    return None


def get_sources_list(client: ChebiClient) -> Any:
    return client.get_json("/public/advanced_search/sources_list")


def advanced_search(
    client: ChebiClient,
    *,
    specification: dict[str, Any],
    three_star_only: bool,
    has_structure: bool | None,
    pagination: Pagination,
    download: bool,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    def _fetch(page: int, size: int) -> dict[str, Any]:
        params = _with_optional(
            {
                "three_star_only": three_star_only,
                "page": page,
                "size": size,
                "download": download,
            },
            has_structure=has_structure,
        )
        response = client.post_json("/public/advanced_search/", params=params, body=specification)
        return _ensure_dict(response)

    return _paginate(
        _fetch,
        page=pagination.page,
        size=pagination.size,
        all_pages=all_pages,
        max_pages=max_pages,
    )


def get_compound(
    client: ChebiClient,
    *,
    chebi_id: str,
    only_ontology_parents: bool,
    only_ontology_children: bool,
) -> Any:
    return client.get_json(
        f"/public/compound/{_normalize_chebi_id(chebi_id)}/",
        params={
            "only_ontology_parents": only_ontology_parents,
            "only_ontology_children": only_ontology_children,
        },
    )


def get_compound_structure(
    client: ChebiClient,
    *,
    compound_id: int,
    width: int,
    height: int,
) -> str:
    return client.get_text(
        f"/public/compound/{compound_id}/structure/",
        params={"width": width, "height": height},
        accept="image/svg+xml,text/plain;q=0.9,*/*;q=0.8",
    )


def get_compounds(client: ChebiClient, *, chebi_ids: list[str]) -> Any:
    normalized = [_normalize_chebi_id(cid) for cid in chebi_ids]
    return client.get_json("/public/compounds/", params={"chebi_ids": ",".join(normalized)})


def post_compounds(client: ChebiClient, *, chebi_ids: list[str]) -> Any:
    normalized = [_normalize_chebi_id(cid) for cid in chebi_ids]
    return client.post_json("/public/compounds/", body={"chebi_ids": normalized})


def es_search(
    client: ChebiClient,
    *,
    term: str,
    pagination: Pagination,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    def _fetch(page: int, size: int) -> dict[str, Any]:
        response = client.get_json(
            "/public/es_search/",
            params={"term": term, "page": page, "size": size},
        )
        return _ensure_dict(response)

    return _paginate(
        _fetch,
        page=pagination.page,
        size=pagination.size,
        all_pages=all_pages,
        max_pages=max_pages,
    )


def get_molfile(client: ChebiClient, *, structure_id: int) -> str:
    return client.get_text(
        f"/public/molfile/{structure_id}/", accept="chemical/x-mdl-molfile,text/plain"
    )


def ontology_all_children_in_path_get(
    client: ChebiClient,
    *,
    relation: str,
    entity: str,
    three_star_only: bool,
    has_structure: bool | None,
    pagination: Pagination,
    download: bool,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    def _fetch(page: int, size: int) -> dict[str, Any]:
        params = _with_optional(
            {
                "relation": relation,
                "entity": _normalize_chebi_id(entity),
                "three_star_only": three_star_only,
                "page": page,
                "size": size,
                "download": download,
            },
            has_structure=has_structure,
        )
        response = client.get_json("/public/ontology/all_children_in_path/", params=params)
        return _ensure_dict(response)

    return _paginate(
        _fetch,
        page=pagination.page,
        size=pagination.size,
        all_pages=all_pages,
        max_pages=max_pages,
    )


def ontology_all_children_in_path_post(
    client: ChebiClient,
    *,
    relation: str,
    entity: str,
    three_star_only: bool,
    has_structure: bool | None,
    pagination: Pagination,
    download: bool,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    def _fetch(page: int, size: int) -> dict[str, Any]:
        params = _with_optional(
            {
                "three_star_only": three_star_only,
                "page": page,
                "size": size,
                "download": download,
            },
            has_structure=has_structure,
        )
        response = client.post_json(
            "/public/ontology/all_children_in_path/",
            params=params,
            body={"relation": relation, "entity": _normalize_chebi_id(entity)},
        )
        return _ensure_dict(response)

    return _paginate(
        _fetch,
        page=pagination.page,
        size=pagination.size,
        all_pages=all_pages,
        max_pages=max_pages,
    )


def ontology_children(client: ChebiClient, *, chebi_id: str) -> Any:
    return client.get_json(f"/public/ontology/children/{_normalize_chebi_id(chebi_id)}/")


def ontology_parents(client: ChebiClient, *, chebi_id: str) -> Any:
    return client.get_json(f"/public/ontology/parents/{_normalize_chebi_id(chebi_id)}/")


def structure_get(client: ChebiClient, *, structure_id: int, width: int, height: int) -> str:
    return client.get_text(
        f"/public/structure/{structure_id}/",
        params={"width": width, "height": height},
        accept="image/svg+xml,text/plain;q=0.9,*/*;q=0.8",
    )


def structure_search_get(
    client: ChebiClient,
    *,
    smiles: str,
    search_type: SearchType,
    similarity: float | None,
    three_star_only: bool,
    pagination: Pagination,
    download: bool,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    def _fetch(page: int, size: int) -> dict[str, Any]:
        params = _with_optional(
            {
                "smiles": smiles,
                "search_type": search_type,
                "three_star_only": three_star_only,
                "page": page,
                "size": size,
                "download": download,
            },
            similarity=similarity,
        )
        response = client.get_json("/public/structure_search/", params=params)
        return _ensure_dict(response)

    return _paginate(
        _fetch,
        page=pagination.page,
        size=pagination.size,
        all_pages=all_pages,
        max_pages=max_pages,
    )


def structure_search_post(
    client: ChebiClient,
    *,
    structure: str,
    search_type: SearchType,
    similarity: float | None,
    three_star_only: bool,
    pagination: Pagination,
    download: bool,
    all_pages: bool,
    max_pages: int | None,
) -> dict[str, Any]:
    def _fetch(page: int, size: int) -> dict[str, Any]:
        params = {
            "three_star_only": three_star_only,
            "page": page,
            "size": size,
            "download": download,
        }
        body = _with_optional({"structure": structure, "type": search_type}, similarity=similarity)
        response = client.post_json("/public/structure_search/", params=params, body=body)
        return _ensure_dict(response)

    return _paginate(
        _fetch,
        page=pagination.page,
        size=pagination.size,
        all_pages=all_pages,
        max_pages=max_pages,
    )


def calc_avg_mass(client: ChebiClient, *, structure: str) -> str:
    return client.post_text("/public/structure-calculations/avg-mass/", body=structure)


def calc_avg_mass_from_formula(client: ChebiClient, *, formula: str) -> str:
    return client.post_text("/public/structure-calculations/avg-mass/from-formula/", body=formula)


def calc_depict_indigo(
    client: ChebiClient,
    *,
    structure: str,
    width: int,
    height: int,
    transbg: bool,
) -> RawResponse:
    return client.post_binary(
        "/public/structure-calculations/depict-indigo/",
        params={"width": width, "height": height, "transbg": transbg},
        body=structure,
        accept="image/png",
    )


def calc_mol_formula(client: ChebiClient, *, structure: str) -> str:
    return client.post_text("/public/structure-calculations/mol-formula/", body=structure)


def calc_monoisotopic_mass(client: ChebiClient, *, structure: str) -> str:
    return client.post_text("/public/structure-calculations/monoisotopic-mass/", body=structure)


def calc_monoisotopic_mass_from_formula(client: ChebiClient, *, formula: str) -> str:
    return client.post_text(
        "/public/structure-calculations/monoisotopic-mass/from-formula/",
        body=formula,
    )


def calc_net_charge(client: ChebiClient, *, structure: str) -> str:
    return client.post_text("/public/structure-calculations/net-charge/", body=structure)


def workflow_resolve_term(
    client: ChebiClient,
    *,
    term: str,
    include_parents: bool,
    include_children: bool,
    include_structure_svg: bool,
    width: int,
    height: int,
) -> dict[str, Any]:
    search_payload = es_search(
        client,
        term=term,
        pagination=Pagination(page=1, size=5),
        all_pages=False,
        max_pages=None,
    )
    results = search_payload.get("results") if isinstance(search_payload, dict) else None
    if not isinstance(results, list) or not results:
        raise ValueError(f"No compounds found for term: {term}")

    top = results[0]
    if not isinstance(top, dict):
        raise ValueError("Unexpected search result shape from upstream API")

    accession = top.get("chebi_accession") or top.get("id") or top.get("chebi_id")
    if not isinstance(accession, str):
        raise ValueError("Could not determine ChEBI accession for top search result")

    compound = get_compound(
        client,
        chebi_id=accession,
        only_ontology_parents=False,
        only_ontology_children=False,
    )
    payload: dict[str, Any] = {
        "query": term,
        "match_count": len(results),
        "top_match": top,
        "compound": compound,
    }

    if include_parents:
        payload["parents"] = ontology_parents(client, chebi_id=accession)
    if include_children:
        payload["children"] = ontology_children(client, chebi_id=accession)

    if include_structure_svg:
        structure_id = top.get("id")
        if isinstance(structure_id, int):
            payload["structure_svg"] = get_compound_structure(
                client,
                compound_id=structure_id,
                width=width,
                height=height,
            )

    return payload


def workflow_formula_profile(client: ChebiClient, *, formula: str) -> dict[str, Any]:
    specification = {
        "formula_specification": {
            "and_specification": [{"term": formula}],
            "or_specification": [],
            "but_not_specification": [],
        }
    }
    matches = advanced_search(
        client,
        specification=specification,
        three_star_only=True,
        has_structure=None,
        pagination=Pagination(page=1, size=15),
        download=False,
        all_pages=False,
        max_pages=None,
    )
    return {
        "formula": formula,
        "avg_mass": calc_avg_mass_from_formula(client, formula=formula),
        "monoisotopic_mass": calc_monoisotopic_mass_from_formula(client, formula=formula),
        "search": matches,
    }


def workflow_structure_profile(
    client: ChebiClient,
    *,
    structure: str,
    similarity: float,
    three_star_only: bool,
) -> dict[str, Any]:
    similarity_hits = structure_search_post(
        client,
        structure=structure,
        search_type="similarity",
        similarity=similarity,
        three_star_only=three_star_only,
        pagination=Pagination(page=1, size=15),
        download=False,
        all_pages=False,
        max_pages=None,
    )
    connectivity_hits = structure_search_post(
        client,
        structure=structure,
        search_type="connectivity",
        similarity=None,
        three_star_only=three_star_only,
        pagination=Pagination(page=1, size=15),
        download=False,
        all_pages=False,
        max_pages=None,
    )
    return {
        "structure": structure,
        "mol_formula": calc_mol_formula(client, structure=structure),
        "avg_mass": calc_avg_mass(client, structure=structure),
        "monoisotopic_mass": calc_monoisotopic_mass(client, structure=structure),
        "net_charge": calc_net_charge(client, structure=structure),
        "similarity_search": similarity_hits,
        "connectivity_search": connectivity_hits,
    }


def parse_json_input(value: str | None, file_value: str | None) -> dict[str, Any]:
    if value and file_value:
        raise ValueError("Provide either --json or --json-file, not both")
    if file_value:
        with open(file_value, encoding="utf-8") as handle:
            payload = json.load(handle)
    elif value:
        payload = json.loads(value)
    else:
        raise ValueError("Missing required JSON input (--json or --json-file)")
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object")
    return payload


def sparql_query(
    client: ChebiClient,
    *,
    query: str,
    sparql_base_url: str,
    output_format: str,
    accept: str | None = None,
) -> dict[str, Any]:
    response = client.get_binary(
        sparql_base_url,
        params={"query": query},
        accept=sparql_accept_header(output_format, accept),
    )
    body = response.body.decode("utf-8", errors="replace")
    payload: dict[str, Any] = {
        "query": query,
        "contentType": response.headers.get("content-type", ""),
        "body": body,
    }
    if "json" in str(payload["contentType"]) or body.lstrip().startswith("{"):
        raw = json.loads(body)
        payload["raw"] = raw
        payload.update(parse_sparql_json(raw))
    return payload


def list_sparql_queries() -> dict[str, Any]:
    items = list_sparql_presets()
    return {"count": len(items), "items": items}


def sparql_preset(
    client: ChebiClient,
    *,
    name: str,
    graph: str,
    limit: int,
    sparql_base_url: str,
    output_format: str,
    accept: str | None = None,
) -> dict[str, Any]:
    query = render_sparql_preset(name, graph=graph, limit=limit)
    result = sparql_query(
        client,
        query=query,
        sparql_base_url=sparql_base_url,
        output_format=output_format,
        accept=accept,
    )
    result["preset"] = name
    result["graph"] = graph
    result["sparqlBaseUrl"] = sparql_base_url
    return result


def parse_id_list(
    values: list[str] | None,
    csv_value: str | None,
    file_value: str | None,
) -> list[str]:
    if sum(x is not None for x in (csv_value, file_value)) + (1 if values else 0) == 0:
        raise ValueError("Provide IDs via --id, --ids-csv, or --ids-file")
    items: list[str] = []
    if values:
        items.extend(values)
    if csv_value:
        items.extend([part.strip() for part in csv_value.split(",") if part.strip()])
    if file_value:
        with open(file_value, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    items.append(stripped)
    if not items:
        raise ValueError("No IDs provided")
    return items


def parse_text_input(value: str | None, file_value: str | None) -> str:
    if value and file_value:
        raise ValueError("Provide either --text or --text-file, not both")
    if file_value:
        with open(file_value, encoding="utf-8") as handle:
            text = handle.read()
    elif value is not None:
        text = value
    else:
        raise ValueError("Missing required input text")
    if not text.strip():
        raise ValueError("Input text must not be empty")
    return text


def format_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)


def format_jsonl(items: Iterable[Any]) -> str:
    lines = [json.dumps(item, sort_keys=True) for item in items]
    return "\n".join(lines)


def select_fields(payload: Any, fields: list[str] | None) -> Any:
    if not fields:
        return payload
    if isinstance(payload, dict):
        return {field: payload.get(field) for field in fields}
    if isinstance(payload, list):
        return [select_fields(item, fields) for item in payload]
    return payload


def render_text(payload: Any) -> str:
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            results = payload["results"]
            lines = [f"results: {len(results)}"]
            for item in results[:20]:
                if isinstance(item, dict):
                    cid = item.get("chebi_accession") or item.get("id") or item.get("chebi_id")
                    name = item.get("name") or item.get("ascii_name") or item.get("title")
                    lines.append(f"- {cid or '?'}\t{name or ''}".rstrip())
                else:
                    lines.append(f"- {item}")
            if len(results) > 20:
                lines.append(f"... ({len(results) - 20} more)")
            return "\n".join(lines)
        compact = []
        for key in sorted(payload.keys()):
            compact.append(f"{key}: {payload[key]}")
        return "\n".join(compact)
    if isinstance(payload, list):
        return "\n".join(str(item) for item in payload)
    return str(payload)


def list_all_endpoints() -> dict[str, object]:
    return coverage_summary()


def _ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"value": value}
