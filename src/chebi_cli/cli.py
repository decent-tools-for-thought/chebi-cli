from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from chebi_cli.client import ApiError, ChebiClient, ChebiError
from chebi_cli.config import ConfigError, load_app_config
from chebi_cli.core import (
    Pagination,
    advanced_search,
    calc_avg_mass,
    calc_avg_mass_from_formula,
    calc_depict_indigo,
    calc_mol_formula,
    calc_monoisotopic_mass,
    calc_monoisotopic_mass_from_formula,
    calc_net_charge,
    es_search,
    format_json,
    format_jsonl,
    get_compound,
    get_compound_structure,
    get_compounds,
    get_molfile,
    get_sources_list,
    list_all_endpoints,
    list_sparql_queries,
    ontology_all_children_in_path_get,
    ontology_all_children_in_path_post,
    ontology_children,
    ontology_parents,
    parse_id_list,
    parse_json_input,
    parse_text_input,
    post_compounds,
    render_text,
    select_fields,
    sparql_preset,
    sparql_query,
    structure_get,
    structure_search_get,
    structure_search_post,
    workflow_formula_profile,
    workflow_resolve_term,
    workflow_structure_profile,
)
from chebi_cli.docs import DOCS_URL, OPENAPI_URL
from chebi_cli.sparql import DEFAULT_SPARQL_ENDPOINT, SPARQL_PRESETS, resolve_sparql_endpoint

JsonObj = dict[str, Any]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chebi",
        description="Complete CLI wrapper for the ChEBI 2.0 backend API",
    )
    _add_connection_args(parser)
    sub = parser.add_subparsers(dest="command")

    _add_advanced_search_commands(sub)
    _add_compound_commands(sub)
    _add_compounds_commands(sub)
    _add_search_commands(sub)
    _add_ontology_commands(sub)
    _add_structure_commands(sub)
    _add_calc_commands(sub)
    _add_workflow_commands(sub)
    _add_docs_commands(sub)
    _add_sparql_commands(sub)
    _add_request_commands(sub)

    return parser


def _add_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", help="Override API base URL")
    parser.add_argument("--sparql-base-url", help="Override SPARQL endpoint URL")
    parser.add_argument("--timeout", type=float, help="Request timeout in seconds")
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--user", help="Basic auth user")
    parser.add_argument("--password", help="Basic auth password")
    parser.add_argument("--session-id", help="sessionid cookie value")


def _add_output_args(parser: argparse.ArgumentParser, include_jsonl: bool = True) -> None:
    formats = ["json", "text", "raw"]
    if include_jsonl:
        formats.insert(1, "jsonl")
    parser.add_argument("--format", choices=formats, default="json", help="Output format")
    parser.add_argument(
        "--field",
        action="append",
        help="Select specific output field (repeatable)",
    )


def _add_pagination_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--page", type=int, default=1, help="Page number")
    parser.add_argument("--size", type=int, default=15, help="Page size")
    parser.add_argument("--all-pages", action="store_true", help="Fetch all pages")
    parser.add_argument(
        "--max-pages", type=int, help="Limit fetched pages when --all-pages is used"
    )


def _add_search_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--three-star-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Filter to 3-star compounds only (default: true)",
    )
    parser.add_argument(
        "--has-structure",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Filter by structure availability",
    )
    parser.add_argument(
        "--download",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Request download payload mode when upstream supports it",
    )


def _add_advanced_search_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("advanced-search", help="Advanced compound search")
    adv_sub = parser.add_subparsers(dest="advanced_command", required=True)

    run = adv_sub.add_parser("run", help="POST /public/advanced_search/")
    run.add_argument("--json", help="Specification JSON payload")
    run.add_argument("--json-file", help="Path to specification JSON payload")
    _add_search_filter_args(run)
    _add_pagination_args(run)
    _add_output_args(run)
    run.set_defaults(handler=_cmd_advanced_search_run)

    sources = adv_sub.add_parser("sources-list", help="GET /public/advanced_search/sources_list")
    _add_output_args(sources)
    sources.set_defaults(handler=_cmd_sources_list)


def _add_compound_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("compound", help="Single-compound operations")
    comp_sub = parser.add_subparsers(dest="compound_command", required=True)

    get = comp_sub.add_parser("get", help="GET /public/compound/{chebi_id}/")
    get.add_argument("chebi_id")
    get.add_argument("--only-ontology-parents", action="store_true")
    get.add_argument("--only-ontology-children", action="store_true")
    _add_output_args(get)
    get.set_defaults(handler=_cmd_compound_get)

    structure = comp_sub.add_parser("structure", help="GET /public/compound/{id}/structure/")
    structure.add_argument("id", type=int)
    structure.add_argument("--width", type=int, default=300)
    structure.add_argument("--height", type=int, default=300)
    structure.add_argument("--output", help="Write SVG output to file")
    structure.add_argument("--format", choices=["raw", "text"], default="raw")
    structure.set_defaults(handler=_cmd_compound_structure)


def _add_compounds_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("compounds", help="Bulk compound operations")
    comp_sub = parser.add_subparsers(dest="compounds_command", required=True)

    for name, help_text, handler in (
        ("get", "GET /public/compounds/", _cmd_compounds_get),
        ("post", "POST /public/compounds/", _cmd_compounds_post),
    ):
        cmd = comp_sub.add_parser(name, help=help_text)
        cmd.add_argument("--id", action="append", dest="ids", help="Single ChEBI ID, repeatable")
        cmd.add_argument("--ids-csv", help="Comma separated ChEBI IDs")
        cmd.add_argument("--ids-file", help="Path to newline-delimited IDs")
        _add_output_args(cmd)
        cmd.set_defaults(handler=handler)


def _add_search_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("search", help="Search commands")
    s_sub = parser.add_subparsers(dest="search_command", required=True)

    es = s_sub.add_parser("es", help="GET /public/es_search/")
    es.add_argument("term")
    _add_pagination_args(es)
    _add_output_args(es)
    es.set_defaults(handler=_cmd_es_search)

    sget = s_sub.add_parser("structure-get", help="GET /public/structure_search/")
    sget.add_argument("--smiles", required=True)
    sget.add_argument(
        "--search-type", choices=["connectivity", "similarity", "substructure"], required=True
    )
    sget.add_argument("--similarity", type=float)
    _add_search_filter_args(sget)
    _add_pagination_args(sget)
    _add_output_args(sget)
    sget.set_defaults(handler=_cmd_structure_search_get)

    spost = s_sub.add_parser("structure-post", help="POST /public/structure_search/")
    spost.add_argument("--structure", help="Structure payload")
    spost.add_argument("--structure-file", help="Path to structure payload")
    spost.add_argument(
        "--search-type",
        choices=["connectivity", "similarity", "substructure"],
        default="connectivity",
    )
    spost.add_argument("--similarity", type=float)
    spost.add_argument(
        "--three-star-only",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    spost.add_argument(
        "--download",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    _add_pagination_args(spost)
    _add_output_args(spost)
    spost.set_defaults(handler=_cmd_structure_search_post)


def _add_ontology_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("ontology", help="Ontology endpoints")
    o_sub = parser.add_subparsers(dest="ontology_command", required=True)

    parents = o_sub.add_parser("parents", help="GET /public/ontology/parents/{chebi_id}/")
    parents.add_argument("chebi_id")
    _add_output_args(parents)
    parents.set_defaults(handler=_cmd_ontology_parents)

    children = o_sub.add_parser("children", help="GET /public/ontology/children/{chebi_id}/")
    children.add_argument("chebi_id")
    _add_output_args(children)
    children.set_defaults(handler=_cmd_ontology_children)

    all_get = o_sub.add_parser(
        "all-children-get", help="GET /public/ontology/all_children_in_path/"
    )
    all_get.add_argument("--relation", required=True)
    all_get.add_argument("--entity", required=True)
    _add_search_filter_args(all_get)
    _add_pagination_args(all_get)
    _add_output_args(all_get)
    all_get.set_defaults(handler=_cmd_ontology_all_children_get)

    all_post = o_sub.add_parser(
        "all-children-post", help="POST /public/ontology/all_children_in_path/"
    )
    all_post.add_argument("--relation", required=True)
    all_post.add_argument("--entity", required=True)
    _add_search_filter_args(all_post)
    _add_pagination_args(all_post)
    _add_output_args(all_post)
    all_post.set_defaults(handler=_cmd_ontology_all_children_post)


def _add_structure_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("structure", help="Structure resources")
    s_sub = parser.add_subparsers(dest="structure_command", required=True)

    get = s_sub.add_parser("get", help="GET /public/structure/{id}/")
    get.add_argument("id", type=int)
    get.add_argument("--width", type=int, default=300)
    get.add_argument("--height", type=int, default=300)
    get.add_argument("--output", help="Write SVG output to file")
    get.add_argument("--format", choices=["raw", "text"], default="raw")
    get.set_defaults(handler=_cmd_structure_get)

    molfile = s_sub.add_parser("molfile", help="GET /public/molfile/{id}/")
    molfile.add_argument("id", type=int)
    molfile.add_argument("--output", help="Write MOL output to file")
    molfile.add_argument("--format", choices=["raw", "text"], default="raw")
    molfile.set_defaults(handler=_cmd_structure_molfile)


def _add_calc_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("calc", help="Structure calculation endpoints")
    c_sub = parser.add_subparsers(dest="calc_command", required=True)

    for name, help_text, handler in (
        ("avg-mass", "POST /public/structure-calculations/avg-mass/", _cmd_calc_avg_mass),
        (
            "avg-mass-from-formula",
            "POST /public/structure-calculations/avg-mass/from-formula/",
            _cmd_calc_avg_mass_from_formula,
        ),
        ("mol-formula", "POST /public/structure-calculations/mol-formula/", _cmd_calc_mol_formula),
        (
            "monoisotopic-mass",
            "POST /public/structure-calculations/monoisotopic-mass/",
            _cmd_calc_monoisotopic_mass,
        ),
        (
            "monoisotopic-mass-from-formula",
            "POST /public/structure-calculations/monoisotopic-mass/from-formula/",
            _cmd_calc_monoisotopic_mass_from_formula,
        ),
        ("net-charge", "POST /public/structure-calculations/net-charge/", _cmd_calc_net_charge),
    ):
        cmd = c_sub.add_parser(name, help=help_text)
        cmd.add_argument("--text")
        cmd.add_argument("--text-file")
        cmd.add_argument("--format", choices=["raw", "text", "json"], default="raw")
        cmd.set_defaults(handler=handler)

    depict = c_sub.add_parser(
        "depict-indigo", help="POST /public/structure-calculations/depict-indigo/"
    )
    depict.add_argument("--text")
    depict.add_argument("--text-file")
    depict.add_argument("--width", type=int, default=300)
    depict.add_argument("--height", type=int, default=300)
    depict.add_argument("--transbg", action=argparse.BooleanOptionalAction, default=False)
    depict.add_argument("--output", required=True, help="Output path for PNG file")
    depict.add_argument("--format", choices=["raw", "text", "json"], default="raw")
    depict.set_defaults(handler=_cmd_calc_depict_indigo)


def _add_workflow_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("workflow", help="Higher-order workflow commands")
    w_sub = parser.add_subparsers(dest="workflow_command", required=True)

    resolve = w_sub.add_parser(
        "resolve-term",
        help="Search term, resolve top compound, optionally include ontology and structure",
    )
    resolve.add_argument("term")
    resolve.add_argument("--include-parents", action="store_true")
    resolve.add_argument("--include-children", action="store_true")
    resolve.add_argument("--include-structure-svg", action="store_true")
    resolve.add_argument("--width", type=int, default=300)
    resolve.add_argument("--height", type=int, default=300)
    _add_output_args(resolve)
    resolve.set_defaults(handler=_cmd_workflow_resolve_term)

    formula = w_sub.add_parser(
        "formula-profile",
        help="Compute formula masses and run advanced formula search",
    )
    formula.add_argument("formula")
    _add_output_args(formula)
    formula.set_defaults(handler=_cmd_workflow_formula_profile)

    structure = w_sub.add_parser(
        "structure-profile",
        help="Compute structure properties and run similarity/connectivity searches",
    )
    structure.add_argument("--structure")
    structure.add_argument("--structure-file")
    structure.add_argument("--similarity", type=float, default=0.8)
    structure.add_argument(
        "--three-star-only",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    _add_output_args(structure)
    structure.set_defaults(handler=_cmd_workflow_structure_profile)


def _add_docs_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("docs", help="Schema and coverage commands")
    d_sub = parser.add_subparsers(dest="docs_command", required=True)

    urls = d_sub.add_parser("urls", help="Print upstream docs/schema URLs")
    urls.add_argument("--format", choices=["text", "json"], default="text")
    urls.set_defaults(handler=_cmd_docs_urls)

    coverage = d_sub.add_parser("coverage", help="List wrapped endpoint coverage")
    _add_output_args(coverage)
    coverage.set_defaults(handler=_cmd_docs_coverage)

    schema = d_sub.add_parser("schema", help="Fetch OpenAPI schema")
    schema.add_argument("--format", choices=["json", "text"], default="json")
    schema.set_defaults(handler=_cmd_docs_schema)


def _add_sparql_result_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["json", "text", "csv", "tsv", "raw"], default="text")
    parser.add_argument("--accept", help="Override Accept header")
    parser.add_argument(
        "--endpoint",
        choices=["uniprot", "rhea"],
        default=DEFAULT_SPARQL_ENDPOINT,
        help="Named SPARQL endpoint profile",
    )


def _add_sparql_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("sparql", help="SPARQL query and dataset-statistics commands")
    s_sub = parser.add_subparsers(dest="sparql_command", required=True)

    query = s_sub.add_parser("query", help="Run an arbitrary SPARQL query")
    query.add_argument("query", nargs="?")
    query.add_argument("--file")
    _add_sparql_result_args(query)
    query.set_defaults(handler=_cmd_sparql_query)

    queries = s_sub.add_parser("queries", help="List built-in SPARQL preset queries")
    queries.add_argument("--format", choices=["json", "text", "tsv"], default="text")
    queries.set_defaults(handler=_cmd_sparql_queries)

    show = s_sub.add_parser("show", help="Print one built-in SPARQL preset query")
    show.add_argument("name", choices=sorted(SPARQL_PRESETS))
    show.add_argument("--limit", type=int, default=25)
    show.add_argument(
        "--endpoint",
        choices=["uniprot", "rhea"],
        default=DEFAULT_SPARQL_ENDPOINT,
        help="Named SPARQL endpoint profile for graph IRI expansion",
    )
    show.add_argument("--format", choices=["text", "json"], default="text")
    show.set_defaults(handler=_cmd_sparql_show)

    for preset_name in sorted(SPARQL_PRESETS):
        preset = s_sub.add_parser(preset_name, help=SPARQL_PRESETS[preset_name].description)
        preset.add_argument("--limit", type=int, default=25)
        _add_sparql_result_args(preset)
        preset.set_defaults(handler=_cmd_sparql_preset, preset_name=preset_name)


def _add_request_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    req = sub.add_parser("request", help="Direct request escape hatch")
    req.add_argument("--method", choices=["GET", "POST"], required=True)
    req.add_argument(
        "--path", required=True, help="Path relative to /chebi/backend/api, e.g. /public/es_search/"
    )
    req.add_argument(
        "--param", action="append", default=[], help="Query param key=value (repeatable)"
    )
    req.add_argument("--json", help="JSON request body for POST")
    req.add_argument("--json-file", help="Path to JSON body file")
    req.add_argument("--text", help="Raw text request body for POST")
    req.add_argument("--text-file", help="Path to text body file")
    req.add_argument("--accept", help="Override Accept header")
    req.add_argument("--format", choices=["json", "text", "raw"], default="json")
    req.set_defaults(handler=_cmd_request)


def _dispatch(args: argparse.Namespace) -> int:
    config = load_app_config(
        config_path=args.config,
        cli_base_url=args.base_url,
        cli_sparql_base_url=args.sparql_base_url,
        cli_timeout=args.timeout,
        cli_user=args.user,
        cli_password=args.password,
        cli_session_id=args.session_id,
    )

    handler = getattr(args, "handler", None)
    if handler is None:
        parser = _parser()
        parser.print_help(sys.stdout)
        return 0

    with ChebiClient(config) as client:
        typed_handler = cast(Callable[[argparse.Namespace, ChebiClient], int], handler)
        return typed_handler(args, client)


def _render_payload(payload: Any, fmt: str, fields: list[str] | None) -> str:
    selected = select_fields(payload, fields)
    if fmt == "json":
        return format_json(selected)
    if fmt == "jsonl":
        if isinstance(selected, dict) and isinstance(selected.get("results"), list):
            return format_jsonl(selected["results"])
        if isinstance(selected, list):
            return format_jsonl(selected)
        return format_jsonl([selected])
    if fmt == "raw":
        if isinstance(selected, str):
            return selected
        return json.dumps(selected, sort_keys=True)
    return render_text(selected)


def _pagination(args: argparse.Namespace) -> Pagination:
    if args.page < 1:
        raise ValueError("--page must be >= 1")
    if args.size < 1:
        raise ValueError("--size must be >= 1")
    if args.max_pages is not None and args.max_pages < 1:
        raise ValueError("--max-pages must be >= 1")
    return Pagination(page=args.page, size=args.size)


def _print_and_exit(payload: str) -> int:
    sys.stdout.write(payload)
    if not payload.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def _cmd_sources_list(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = get_sources_list(client)
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_advanced_search_run(args: argparse.Namespace, client: ChebiClient) -> int:
    spec = parse_json_input(args.json, args.json_file)
    payload = advanced_search(
        client,
        specification=spec,
        three_star_only=args.three_star_only,
        has_structure=args.has_structure,
        pagination=_pagination(args),
        download=args.download,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_compound_get(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = get_compound(
        client,
        chebi_id=args.chebi_id,
        only_ontology_parents=args.only_ontology_parents,
        only_ontology_children=args.only_ontology_children,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_compound_structure(args: argparse.Namespace, client: ChebiClient) -> int:
    content = get_compound_structure(
        client, compound_id=args.id, width=args.width, height=args.height
    )
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        return _print_and_exit(args.output)
    return _print_and_exit(content)


def _cmd_compounds_get(args: argparse.Namespace, client: ChebiClient) -> int:
    ids = parse_id_list(args.ids, args.ids_csv, args.ids_file)
    payload = get_compounds(client, chebi_ids=ids)
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_compounds_post(args: argparse.Namespace, client: ChebiClient) -> int:
    ids = parse_id_list(args.ids, args.ids_csv, args.ids_file)
    payload = post_compounds(client, chebi_ids=ids)
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_es_search(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = es_search(
        client,
        term=args.term,
        pagination=_pagination(args),
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_structure_search_get(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = structure_search_get(
        client,
        smiles=args.smiles,
        search_type=args.search_type,
        similarity=args.similarity,
        three_star_only=args.three_star_only,
        pagination=_pagination(args),
        download=args.download,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_structure_search_post(args: argparse.Namespace, client: ChebiClient) -> int:
    structure = parse_text_input(args.structure, args.structure_file)
    payload = structure_search_post(
        client,
        structure=structure,
        search_type=args.search_type,
        similarity=args.similarity,
        three_star_only=args.three_star_only,
        pagination=_pagination(args),
        download=args.download,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_ontology_parents(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = ontology_parents(client, chebi_id=args.chebi_id)
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_ontology_children(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = ontology_children(client, chebi_id=args.chebi_id)
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_ontology_all_children_get(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = ontology_all_children_in_path_get(
        client,
        relation=args.relation,
        entity=args.entity,
        three_star_only=args.three_star_only,
        has_structure=args.has_structure,
        pagination=_pagination(args),
        download=args.download,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_ontology_all_children_post(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = ontology_all_children_in_path_post(
        client,
        relation=args.relation,
        entity=args.entity,
        three_star_only=args.three_star_only,
        has_structure=args.has_structure,
        pagination=_pagination(args),
        download=args.download,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_structure_get(args: argparse.Namespace, client: ChebiClient) -> int:
    content = structure_get(client, structure_id=args.id, width=args.width, height=args.height)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        return _print_and_exit(args.output)
    return _print_and_exit(content)


def _cmd_structure_molfile(args: argparse.Namespace, client: ChebiClient) -> int:
    content = get_molfile(client, structure_id=args.id)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        return _print_and_exit(args.output)
    return _print_and_exit(content)


def _text_result(value: str, fmt: str) -> str:
    if fmt == "json":
        return format_json({"value": value})
    return value


def _cmd_calc_avg_mass(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    return _print_and_exit(_text_result(calc_avg_mass(client, structure=text), args.format))


def _cmd_calc_avg_mass_from_formula(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    return _print_and_exit(
        _text_result(calc_avg_mass_from_formula(client, formula=text), args.format)
    )


def _cmd_calc_mol_formula(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    return _print_and_exit(_text_result(calc_mol_formula(client, structure=text), args.format))


def _cmd_calc_monoisotopic_mass(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    return _print_and_exit(
        _text_result(calc_monoisotopic_mass(client, structure=text), args.format)
    )


def _cmd_calc_monoisotopic_mass_from_formula(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    return _print_and_exit(
        _text_result(calc_monoisotopic_mass_from_formula(client, formula=text), args.format)
    )


def _cmd_calc_net_charge(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    return _print_and_exit(_text_result(calc_net_charge(client, structure=text), args.format))


def _cmd_calc_depict_indigo(args: argparse.Namespace, client: ChebiClient) -> int:
    text = parse_text_input(args.text, args.text_file)
    raw = calc_depict_indigo(
        client,
        structure=text,
        width=args.width,
        height=args.height,
        transbg=args.transbg,
    )
    output_path = Path(args.output)
    output_path.write_bytes(raw.body)
    if args.format == "json":
        return _print_and_exit(
            format_json(
                {
                    "output": str(output_path),
                    "bytes": len(raw.body),
                    "content_type": raw.headers.get("content-type"),
                }
            )
        )
    return _print_and_exit(str(output_path))


def _cmd_workflow_resolve_term(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = workflow_resolve_term(
        client,
        term=args.term,
        include_parents=args.include_parents,
        include_children=args.include_children,
        include_structure_svg=args.include_structure_svg,
        width=args.width,
        height=args.height,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_workflow_formula_profile(args: argparse.Namespace, client: ChebiClient) -> int:
    payload = workflow_formula_profile(client, formula=args.formula)
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_workflow_structure_profile(args: argparse.Namespace, client: ChebiClient) -> int:
    structure = parse_text_input(args.structure, args.structure_file)
    payload = workflow_structure_profile(
        client,
        structure=structure,
        similarity=args.similarity,
        three_star_only=args.three_star_only,
    )
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_docs_urls(args: argparse.Namespace, _client: ChebiClient) -> int:
    payload: JsonObj = {
        "docs_url": DOCS_URL,
        "openapi_url": OPENAPI_URL,
        "sparql_endpoints": {
            "uniprot": "https://sparql.uniprot.org/sparql",
            "rhea": "https://sparql.rhea-db.org/sparql",
        },
    }
    if args.format == "json":
        return _print_and_exit(format_json(payload))
    return _print_and_exit(
        "\n".join(
            [
                f"docs: {DOCS_URL}",
                f"schema: {OPENAPI_URL}",
                "sparql-uniprot: https://sparql.uniprot.org/sparql",
                "sparql-rhea: https://sparql.rhea-db.org/sparql",
            ]
        )
    )


def _cmd_docs_coverage(args: argparse.Namespace, _client: ChebiClient) -> int:
    payload = list_all_endpoints()
    return _print_and_exit(_render_payload(payload, args.format, args.field))


def _cmd_docs_schema(_args: argparse.Namespace, client: ChebiClient) -> int:
    schema = client.get_json("/schema/")
    return _print_and_exit(format_json(schema))


def _resolve_sparql_query(args: argparse.Namespace) -> str:
    if getattr(args, "file", None):
        return Path(args.file).read_text(encoding="utf-8")
    query = getattr(args, "query", None)
    if isinstance(query, str) and query:
        return query
    raise ValueError("Provide a SPARQL query string or --file")


def _resolve_sparql_target(args: argparse.Namespace, client: ChebiClient) -> tuple[str, str]:
    override = args.sparql_base_url
    default_base_url, _graph = resolve_sparql_endpoint(DEFAULT_SPARQL_ENDPOINT)
    client_base_url = getattr(client, "sparql_base_url", default_base_url)
    if override is None and client_base_url != default_base_url:
        override = client_base_url
    return resolve_sparql_endpoint(args.endpoint, override)


def _render_sparql_result(payload: dict[str, Any], output_format: str) -> str:
    if output_format in {"csv", "tsv", "raw"}:
        return str(payload["body"])
    if output_format == "json":
        return format_json(payload.get("raw", payload))
    if payload.get("kind") == "ask":
        return "true" if payload.get("boolean") else "false"
    if payload.get("kind") == "select":
        variables = cast(list[str], payload.get("variables", []))
        items = cast(list[dict[str, Any]], payload.get("items", []))
        if not items:
            return ""
        widths = {
            column: max(len(column), *(len(str(item.get(column, ""))) for item in items))
            for column in variables
        }
        lines = ["  ".join(column.ljust(widths[column]) for column in variables)]
        for item in items:
            lines.append(
                "  ".join(str(item.get(column, "")).ljust(widths[column]) for column in variables)
            )
        return "\n".join(lines)
    return str(payload["body"])


def _cmd_sparql_query(args: argparse.Namespace, client: ChebiClient) -> int:
    sparql_base_url, _graph = _resolve_sparql_target(args, client)
    payload = sparql_query(
        client,
        query=_resolve_sparql_query(args),
        sparql_base_url=sparql_base_url,
        output_format=args.format,
        accept=args.accept,
    )
    return _print_and_exit(_render_sparql_result(payload, args.format))


def _cmd_sparql_queries(args: argparse.Namespace, _client: ChebiClient) -> int:
    payload = list_sparql_queries()
    if args.format == "json":
        return _print_and_exit(format_json(payload))
    if args.format == "tsv":
        lines = ["name\tdescription"]
        lines.extend(f"{item['name']}\t{item['description']}" for item in payload["items"])
        return _print_and_exit("\n".join(lines))
    lines = [f"{item['name']}: {item['description']}" for item in payload["items"]]
    return _print_and_exit("\n".join(lines))


def _cmd_sparql_show(args: argparse.Namespace, _client: ChebiClient) -> int:
    _sparql_base_url, graph = resolve_sparql_endpoint(args.endpoint)
    query = SPARQL_PRESETS[args.name].render(graph=graph, limit=args.limit)
    if args.format == "json":
        return _print_and_exit(
            format_json(
                {"name": args.name, "endpoint": args.endpoint, "graph": graph, "query": query}
            )
        )
    return _print_and_exit(query)


def _cmd_sparql_preset(args: argparse.Namespace, client: ChebiClient) -> int:
    sparql_base_url, graph = _resolve_sparql_target(args, client)
    payload = sparql_preset(
        client,
        name=args.preset_name,
        graph=graph,
        limit=args.limit,
        sparql_base_url=sparql_base_url,
        output_format=args.format,
        accept=args.accept,
    )
    return _print_and_exit(_render_sparql_result(payload, args.format))


def _parse_query_params(raw_params: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in raw_params:
        if "=" not in item:
            raise ValueError(f"Invalid --param value {item!r}; expected key=value")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError(f"Invalid --param value {item!r}; empty key")
        params[key] = value
    return params


def _cmd_request(args: argparse.Namespace, client: ChebiClient) -> int:
    params = _parse_query_params(args.param)
    if args.method == "GET":
        if args.accept:
            content = client.get_text(args.path, params=params, accept=args.accept)
            return _print_and_exit(content)
        payload = client.get_json(args.path, params=params)
        return _print_and_exit(_render_payload(payload, args.format, None))

    json_body = (
        parse_json_input(args.json, args.json_file) if (args.json or args.json_file) else None
    )
    text_body = (
        parse_text_input(args.text, args.text_file) if (args.text or args.text_file) else None
    )
    if json_body is not None and text_body is not None:
        raise ValueError("Provide either JSON body or text body, not both")
    if json_body is not None:
        payload = client.post_json(args.path, params=params, body=json_body)
        return _print_and_exit(_render_payload(payload, args.format, None))
    if text_body is not None:
        payload = client.post_text(args.path, params=params, body=text_body)
        return _print_and_exit(_text_result(payload, args.format))
    payload = client.post_json(args.path, params=params, body={})
    return _print_and_exit(_render_payload(payload, args.format, None))


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        return _dispatch(args)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    except (ValueError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ApiError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1
    except ChebiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


Handler = Callable[[argparse.Namespace, ChebiClient], int]
