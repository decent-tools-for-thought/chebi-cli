from __future__ import annotations

from typing import Any

import pytest

from chebi_cli.client import RawResponse
from chebi_cli.core import (
    format_jsonl,
    list_sparql_queries,
    parse_id_list,
    parse_json_input,
    parse_text_input,
    render_text,
    select_fields,
    sparql_preset,
    sparql_query,
    workflow_formula_profile,
)
from chebi_cli.sparql import parse_sparql_json, render_sparql_preset


def test_select_fields_dict() -> None:
    payload: dict[str, Any] = {"a": 1, "b": 2, "c": 3}
    assert select_fields(payload, ["a", "c"]) == {"a": 1, "c": 3}


def test_format_jsonl() -> None:
    out = format_jsonl([{"a": 1}, {"b": 2}])
    assert out.splitlines() == ['{"a": 1}', '{"b": 2}']


def test_parse_json_input_requires_one_source(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        parse_json_input(None, None)

    fp = tmp_path / "p.json"
    fp.write_text('{"x": 1}', encoding="utf-8")
    assert parse_json_input(None, str(fp)) == {"x": 1}


def test_parse_id_list_accepts_mixed_sources(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fp = tmp_path / "ids.txt"
    fp.write_text("CHEBI:1\nCHEBI:2\n", encoding="utf-8")
    out = parse_id_list(["CHEBI:3"], "CHEBI:4,CHEBI:5", str(fp))
    assert out == ["CHEBI:3", "CHEBI:4", "CHEBI:5", "CHEBI:1", "CHEBI:2"]


def test_parse_text_input(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fp = tmp_path / "smi.txt"
    fp.write_text("CCO", encoding="utf-8")
    assert parse_text_input(None, str(fp)) == "CCO"


def test_render_text_results() -> None:
    payload = {"results": [{"chebi_accession": "CHEBI:1", "name": "foo"}]}
    text = render_text(payload)
    assert "results: 1" in text
    assert "CHEBI:1" in text


def test_workflow_formula_profile_aggregates_calls(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "chebi_cli.core.advanced_search",
        lambda *_args, **_kwargs: {"results": [{"chebi_accession": "CHEBI:1"}]},
    )
    monkeypatch.setattr(
        "chebi_cli.core.calc_avg_mass_from_formula", lambda *_args, **_kwargs: "151.16"
    )
    monkeypatch.setattr(
        "chebi_cli.core.calc_monoisotopic_mass_from_formula",
        lambda *_args, **_kwargs: "151.0633",
    )
    payload = workflow_formula_profile(client=None, formula="C8H9NO2")  # type: ignore[arg-type]
    assert payload["formula"] == "C8H9NO2"
    assert payload["avg_mass"] == "151.16"
    assert payload["monoisotopic_mass"] == "151.0633"


def test_parse_sparql_json_select() -> None:
    parsed = parse_sparql_json(
        {
            "head": {"vars": ["count"]},
            "results": {
                "bindings": [
                    {
                        "count": {
                            "type": "literal",
                            "datatype": "http://www.w3.org/2001/XMLSchema#int",
                            "value": "7",
                        }
                    }
                ]
            },
        }
    )
    assert parsed["kind"] == "select"
    assert parsed["items"] == [{"count": "7^^http://www.w3.org/2001/XMLSchema#int"}]


def test_render_sparql_preset_includes_graph_and_limit() -> None:
    query = render_sparql_preset("predicates", graph="http://example.test/chebi", limit=7)
    assert "GRAPH <http://example.test/chebi>" in query
    assert "LIMIT 7" in query


def test_list_sparql_queries_reports_presets() -> None:
    payload = list_sparql_queries()
    assert payload["count"] >= 1
    assert any(item["name"] == "predicates" for item in payload["items"])


def test_sparql_query_parses_boolean_result() -> None:
    class DummyClient:
        def get_binary(self, *_args, **_kwargs) -> RawResponse:
            return RawResponse(
                status_code=200,
                headers={"content-type": "application/sparql-results+json"},
                body=b'{"head":{"link":[]},"boolean":true}',
            )

    payload = sparql_query(
        DummyClient(),  # type: ignore[arg-type]
        query="ASK { ?s ?p ?o }",
        sparql_base_url="https://example.test/sparql",
        output_format="json",
    )
    assert payload["kind"] == "ask"
    assert payload["boolean"] is True


def test_sparql_preset_attaches_metadata(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "chebi_cli.core.sparql_query",
        lambda *_args, **_kwargs: {"kind": "select", "variables": [], "items": [], "body": ""},
    )
    payload = sparql_preset(
        client=None,  # type: ignore[arg-type]
        name="predicates",
        graph="http://example.test/chebi",
        limit=5,
        sparql_base_url="https://example.test/sparql",
        output_format="json",
    )
    assert payload["preset"] == "predicates"
    assert payload["graph"] == "http://example.test/chebi"
